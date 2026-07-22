"""Multi-agent (A2A) collaboration + governance — told as ONE refund's journey.

Watch a single customer refund travel through three specialised AI agents:

  🔎 RESEARCH      READ-ONLY — gathers the facts (get_order / search_policy).
  🧭 ORCHESTRATOR  makes the policy call; touches no tools itself.
  ⚡ ACTION        the ONLY agent allowed to move money (issue_refund, a write).

At every step a guardrail is doing its job, and each one is observable:

  • MCP           — the tools live behind a real MCP server (a genuine
                    client→server→tool round-trip), so the backend is swappable.
  • RBAC          — each agent may call only the tools its job needs; a read-side
                    write attempt is BLOCKED in code, before the server is reached.
  • APPROVAL GATE — a human must approve before any refund executes.
  • AUDIT LOG     — an append-only record of every message, tool call, RBAC
                    check, decision, and outcome.

The spine: exposing a tool over MCP is a *capability*; WHO may call it is the
app's RBAC, not the server. Capability is not authorization.
"""
import json

import streamlit as st

from shared import mcp_client
from shared.core import boot, chat, layer_badge, stream_assistant, tool_calls_to_message, try_this
from shared.slides import render_slides

client = boot("7 · Multi-agent + governance")

st.title("7 · Multi-agent + governance")
layer_badge([2, 7])
st.caption(
    "🧭 **Three AI agents team up on one customer refund** — one gathers facts, one decides, "
    "one acts — while guardrails decide *who* may act, require a human to approve anything "
    "irreversible, and write down every step."
)
render_slides("governance")

# --- RBAC policy: which role may invoke which MCP tool ------------------------
# The governance rule, enforced IN CODE (not just a prompt). The MCP server
# exposes every tool; THIS is what decides who may call each one.
RBAC = {
    "research": {"get_order", "search_policy"},   # READ-ONLY
    "action": {"issue_refund"},                    # WRITE — action agent only
    "orchestrator": set(),                         # delegates; calls no tools
}

ROLE_META = {
    "orchestrator": ("🧭", "Orchestrator", "Runs the show and makes the policy call. Touches no tools itself — it delegates."),
    "research":     ("🔎", "Research", "Read-only. Looks up the order and searches the refund policy to gather facts."),
    "action":       ("⚡", "Action", "The only agent allowed to move money — it runs the refund write."),
}

# Friendly labels for the audit event stream (plain-English view).
FRIENDLY = {
    "a2a_message": "💬 message", "rbac_allowed": "✅ allowed", "rbac_BLOCKED": "🚫 blocked",
    "mcp_call": "🔧 tool call", "mcp_result": "📦 tool result", "orchestrator_decision": "🧭 decision",
    "orchestrator_denied": "🧭 decision · deny", "approval_pending": "⏸️ waiting for human",
    "approval_decision": "👤 human decision", "outcome": "💸 outcome",
}

# --- Session state ------------------------------------------------------------
st.session_state.setdefault("audit", [])      # append-only list of dicts
st.session_state.setdefault("a2a", [])        # A2A message timeline (feeds the audit trail)
st.session_state.setdefault("pending", None)  # the refund proposal awaiting approval, if any
st.session_state.setdefault("outcome", None)  # the resolved outcome, if any
st.session_state.setdefault("run", None)      # the full run record, so the story survives reruns


def audit(event: str, detail) -> None:
    """Append one immutable entry to the audit trail."""
    st.session_state["audit"].append({"event": event, "detail": detail})


def a2a(sender: str, recipient: str, content: str) -> None:
    """Record one agent-to-agent message (and audit it)."""
    msg = {"from": sender, "to": recipient, "content": content}
    st.session_state["a2a"].append(msg)
    audit("a2a_message", msg)


# --- The MCP tool catalog (advertised by shared.mcp_tools over the protocol) --
@st.cache_data(show_spinner=False)
def mcp_catalog() -> list[dict]:
    """Ask the MCP server what tools it advertises (once)."""
    return mcp_client.list_tools()


def _openai_schema(tool: dict) -> dict:
    """Convert one MCP tool dict into an OpenAI function-tool schema."""
    return {"type": "function", "function": {
        "name": tool["name"],
        "description": tool["description"],
        "parameters": tool["input_schema"] or {"type": "object", "properties": {}},
    }}


def tools_for_role(role: str) -> list[dict]:
    """OpenAI tool schemas for ONLY the MCP tools this role's RBAC permits."""
    allowed = RBAC.get(role, set())
    return [_openai_schema(t) for t in mcp_catalog() if t["name"] in allowed]


# --- RBAC-enforcing dispatch — every permitted call goes over MCP -------------
# If a role calls a tool it is not permitted to use, the call is BLOCKED before
# it ever reaches the MCP server, and the block is audited.
def call_tool(role: str, name: str, args: dict):
    if name not in RBAC.get(role, set()):
        audit("rbac_BLOCKED", {"role": role, "tool": name, "reason": "not permitted for role"})
        return {"error": f"RBAC: role '{role}' may not call '{name}'"}, True
    audit("rbac_allowed", {"role": role, "tool": name})
    audit("mcp_call", {"role": role, "tool": name, "args": args})
    try:
        result = mcp_client.call_tool(name, args)
    except Exception as exc:  # surface MCP/transport errors instead of crashing the page
        result = {"error": f"MCP call failed: {type(exc).__name__}: {exc}"}
    audit("mcp_result", {"tool": name, "result": result})
    return result, False


# --- The agents ---------------------------------------------------------------
def run_research(order_id: str, placeholder=None):
    """RESEARCH agent: a read-only tool loop (capped). Captures every MCP
    round-trip so the UI can show them, and streams its final findings.

    Returns (findings, calls_record, messages) where calls_record is a list of
    {tool, args, result, allowed} — one per real tool call it made."""
    calls_record: list[dict] = []
    messages = [
        {"role": "system", "content":
            "You are the READ-ONLY Research Agent for refunds. Use get_order to fetch "
            "the order and search_policy to find the relevant refund rules. Then report "
            "concise FINDINGS: order details, the policy window for that customer type, "
            "and whether any approval threshold applies. Do not decide — just gather facts."},
        {"role": "user", "content": f"Gather the facts needed to handle a refund for order {order_id}."},
    ]
    for _ in range(5):  # cap the tool loop
        content, calls = stream_assistant(client, messages, tools=tools_for_role("research"), placeholder=None)
        if not calls:
            break
        messages.append(tool_calls_to_message(content, calls))
        for c in calls:
            try:
                args = json.loads(c["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            result, blocked = call_tool("research", c["name"], args)
            calls_record.append({"tool": c["name"], "args": args, "result": result, "allowed": not blocked})
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)})
    findings, _ = stream_assistant(client, messages, placeholder=placeholder)
    return (findings or "(no findings)"), calls_record, messages


def run_orchestrator(order_id: str, findings: str):
    """ORCHESTRATOR agent: decides eligibility + proposes refund or denial.
    Returns (decision_dict, messages)."""
    messages = [
        {"role": "system", "content":
            "You are the Orchestrator. Given the Research Agent's findings, decide per "
            "the refund policy whether to refund. Reply with ONLY a JSON object: "
            '{"decision": "refund" | "deny", "amount": number, "reason": "..."}. '
            "amount is the refund amount if decision is refund, else 0."},
        {"role": "user", "content": f"Order {order_id} findings:\n{findings}"},
    ]
    raw = chat(client, messages, temperature=0).choices[0].message.content or "{}"
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        d = json.loads(raw)
    except Exception:
        d = {"decision": "deny", "amount": 0, "reason": f"unparseable orchestrator reply: {raw}"}
    d.setdefault("decision", "deny")
    d.setdefault("amount", 0)
    d.setdefault("reason", "")
    return d, messages


def do_run(order_id: str) -> None:
    """Run the whole multi-agent workflow for one order, recording everything into
    session_state so the story below can render (and survive the approval rerun)."""
    order_id = str(order_id).strip()
    st.session_state.update(audit=[], a2a=[], pending=None, outcome=None, run=None)

    with st.status("Agents working…", expanded=True) as status:
        st.write(f"🧭 → 🔎 Orchestrator asks Research to gather the facts for order **{order_id}**.")
        a2a("Orchestrator", "Research", f"Gather facts for order {order_id}.")
        findings, calls_record, research_msgs = run_research(order_id, placeholder=st.empty())
        a2a("Research", "Orchestrator", findings)

        st.write("🧭 Orchestrator decides per policy…")
        decision, orch_msgs = run_orchestrator(order_id, findings)
        audit("orchestrator_decision", decision)

        if decision["decision"] == "refund":
            amt = float(decision.get("amount") or 0)
            a2a("Orchestrator", "Action", f"Propose refund ${amt:.2f} for order {order_id}.")
            st.session_state["pending"] = {"order_id": order_id, "amount": amt,
                                           "reason": decision.get("reason", "")}
            audit("approval_pending", st.session_state["pending"])
        else:
            a2a("Orchestrator", "Action", f"No action — deny refund for order {order_id}.")
            audit("orchestrator_denied", {"order_id": order_id, "reason": decision.get("reason", "")})
            st.session_state["outcome"] = {"status": "orchestrator_denied", "result": None}

        st.session_state["run"] = {
            "order_id": order_id, "findings": findings, "research_calls": calls_record,
            "decision": decision, "research_msgs": research_msgs, "orch_msgs": orch_msgs,
        }
        status.update(label="Done — read the story below.", state="complete", expanded=False)


# =============================================================================
#  1 · Meet the three agents (the cast)
# =============================================================================
st.markdown("#### Meet the three agents")
for col, role in zip(st.columns(3), ("research", "orchestrator", "action")):
    icon, name, blurb = ROLE_META[role]
    with col.container(border=True):
        st.markdown(f"### {icon} {name}")
        st.caption(blurb)
        allowed = sorted(RBAC[role])
        if allowed:
            st.markdown("Tools it may use:  " + "  ".join(f"`{t}`" for t in allowed))
        else:
            st.markdown("Tools it may use:  *none — it delegates*")
st.caption(
    "Each agent may use **only** the tools its job needs. That rule is **RBAC** (role-based access "
    "control), and it's enforced in code — not merely requested in a prompt."
)

# =============================================================================
#  2 · Run control — two scenarios
# =============================================================================
st.markdown("#### Run a refund")
st.caption("Two orders take two different governed paths. Pick one:")
c1, c2 = st.columns(2)
if c1.button("▶️ Order 4471 — enterprise, in window", use_container_width=True, type="primary"):
    do_run("4471")
if c2.button("▶️ Order 5012 — standard, expired", use_container_width=True):
    do_run("5012")
with st.expander("…or try another order id"):
    other = st.text_input("Order id", "4471", label_visibility="collapsed")
    if st.button("Run this order"):
        do_run(other)


# =============================================================================
#  3 · The story — one refund, start to finish
# =============================================================================
def render_story() -> None:
    run = st.session_state.get("run")
    if not run:
        st.info("Pick a scenario above to watch one refund travel through the three agents.")
        return

    order_id, dec = run["order_id"], run["decision"]
    st.markdown("#### The story — one refund, start to finish")

    with st.chat_message("orchestrator", avatar="🧭"):
        st.markdown(
            f"**Orchestrator** — new refund request for order **{order_id}**. I don't touch tools "
            "myself, so I'll ask **Research** to gather the facts, then decide."
        )

    with st.chat_message("research", avatar="🔎"):
        st.markdown("**Research agent** — read-only. I looked up the order and searched the refund policy.")
        st.markdown(run["findings"])
        calls = run["research_calls"]
        with st.expander(f"🔧 Show the {len(calls)} tool round-trip(s) — the real calls behind those facts", expanded=False):
            for i, rc in enumerate(calls, 1):
                badge = "✅ RBAC allowed" if rc["allowed"] else "🚫 RBAC blocked"
                st.markdown(f"**Call {i} · `{rc['tool']}`**  ·  {badge}")
                rq, rs = st.columns(2)
                rq.caption("request →")
                rq.code(json.dumps(rc["args"], indent=2), language="json")
                rs.caption("← response")
                rs.code(json.dumps(rc["result"], indent=2, default=str)[:900], language="json")
                if i < len(calls):
                    st.divider()
            if not calls:
                st.caption("No tool calls captured for this run.")

    with st.chat_message("orchestrator", avatar="🧭"):
        if dec["decision"] == "refund":
            amt = float(dec.get("amount") or 0)
            st.markdown(f"**Orchestrator decides:** ✅ **refund ${amt:.2f}** — {dec.get('reason', '')}")
            st.markdown("🧭 → ⚡ **To Action:** propose this refund. It moves money, so a **human must approve** first.")
        else:
            st.markdown(f"**Orchestrator decides:** 🛑 **deny** — {dec.get('reason', '')}")
            st.markdown("🧭 → ⚡ **To Action:** nothing to do — policy says deny.")
        with st.expander("raw decision (JSON)", expanded=False):
            st.code(json.dumps(dec, indent=2), language="json")

    pending, outcome = st.session_state.get("pending"), st.session_state.get("outcome")

    # Approval gate — rendered inline, at the exact point money would move.
    if pending and not outcome:
        with st.chat_message("human", avatar="👤"):
            st.markdown("**Approval gate** — a person must approve before any money moves.")
            with st.container(border=True):
                st.warning(
                    f"⏸️ Proposed: refund **${pending['amount']:.2f}** for order **{pending['order_id']}**. "
                    "Nothing has executed yet."
                )
                yes, no = st.columns(2)
                if yes.button("✅ Approve & execute", type="primary", use_container_width=True):
                    audit("approval_decision", {"by": "human", "decision": "approved"})
                    result, blocked = call_tool("action", "issue_refund",
                                                {"order_id": pending["order_id"], "amount": pending["amount"]})
                    a2a("Action", "Orchestrator", f"Executed refund: {json.dumps(result)}")
                    st.session_state["outcome"] = {"status": "blocked" if blocked else "executed", "result": result}
                    audit("outcome", st.session_state["outcome"])
                    st.session_state["pending"] = None
                    st.rerun()
                if no.button("🚫 Deny", use_container_width=True):
                    audit("approval_decision", {"by": "human", "decision": "denied"})
                    a2a("Action", "Orchestrator", "Human denied the refund — no action taken.")
                    st.session_state["outcome"] = {"status": "denied", "result": None}
                    audit("outcome", st.session_state["outcome"])
                    st.session_state["pending"] = None
                    st.rerun()

    # Outcome bubble.
    outcome = st.session_state.get("outcome")
    if outcome:
        status = outcome["status"]
        if status == "executed":
            with st.chat_message("action", avatar="⚡"):
                conf = (outcome["result"] or {}).get("confirmation", "n/a")
                st.markdown(f"**Action agent** — refund executed. Confirmation **{conf}**.")
                st.caption("This is the only agent RBAC allows to make this write.")
        elif status == "denied":
            with st.chat_message("human", avatar="👤"):
                st.markdown("**Human denied** the refund at the gate — nothing was executed.")
        elif status == "orchestrator_denied":
            with st.chat_message("action", avatar="⚡"):
                st.markdown("**No action taken** — the Orchestrator denied the refund per policy, so Action had nothing to do.")
        elif status == "blocked":
            with st.chat_message("action", avatar="⚡"):
                st.error(f"The write was blocked by RBAC: {(outcome['result'] or {}).get('error', '')}")


render_story()

# =============================================================================
#  4 · What kept this safe
# =============================================================================
st.markdown("#### What kept this safe")

rbac_events = [e for e in st.session_state["audit"] if e["event"] in ("rbac_allowed", "rbac_BLOCKED")]
if rbac_events:
    st.markdown("**The role checks that ran** (every tool call is checked against RBAC, in code):")
    for e in rbac_events:
        d = e["detail"]
        if e["event"] == "rbac_allowed":
            st.markdown(f"- ✅ **{d['role']}** allowed to call `{d['tool']}`")
        else:
            st.markdown(f"- 🚫 **{d['role']}** **BLOCKED** from `{d['tool']}` — {d.get('reason', '')}")
else:
    st.caption("Run a scenario to see the role checks that ran.")

with st.container(border=True):
    st.markdown("**See the guardrail catch a rule-break**")
    st.caption(
        "The Research agent is read-only. Ask it to issue a refund and watch RBAC stop it **in code** — "
        "before the request ever reaches the tool server."
    )
    if st.button("Have the read-only Research agent try to issue a refund →"):
        oid = (st.session_state.get("run") or {}).get("order_id", "4471")
        res, blocked = call_tool("research", "issue_refund", {"order_id": oid, "amount": 999})
        if blocked:
            st.error(f"🚫 Blocked by RBAC: {res['error']}")
        else:
            st.write(res)

with st.expander(f"📋 Full audit log — {len(st.session_state['audit'])} events (the trail you'd hand an auditor)"):
    audit_log = st.session_state["audit"]
    if not audit_log:
        st.caption("No events yet — run a scenario.")
    else:
        for i, e in enumerate(audit_log, 1):
            d = e["detail"]
            if e["event"] == "a2a_message":
                extra = f"{d['from']} → {d['to']}"
            elif e["event"] in ("rbac_allowed", "rbac_BLOCKED"):
                extra = f"{d['role']} · {d['tool']}"
            elif e["event"] in ("mcp_call", "mcp_result"):
                extra = f"{d.get('tool', '')}"
            elif e["event"] == "orchestrator_decision":
                extra = f"{d.get('decision', '')} ${float(d.get('amount') or 0):.2f}"
            elif e["event"] == "approval_decision":
                extra = d.get("decision", "")
            elif e["event"] == "outcome":
                extra = d.get("status", "")
            else:
                extra = ""
            st.markdown(f"`{i:02d}`  {FRIENDLY.get(e['event'], e['event'])}  ·  {extra}")
        with st.expander("raw JSON"):
            st.code(json.dumps(audit_log, indent=2, default=str), language="json")

# =============================================================================
#  5 · Under the hood
# =============================================================================
st.markdown("#### Under the hood")

with st.expander(f"🔌 The tools run behind a real MCP server · mode: {mcp_client.mode()}"):
    st.caption(
        "The agents don't call Python functions — they call **named tools over the MCP protocol** "
        "(a genuine client→server→tool round-trip). **Why it matters — decoupling:** the agents go "
        "through a standard adapter, so you can swap the backend (Postgres, a SaaS API, a different "
        "service) without changing the agents. In-process by default; set an `mcp_server_url` secret "
        "to point at a networked server with no app-code change."
    )
    _cat = mcp_catalog()
    for _col, _t in zip(st.columns(len(_cat) or 1), _cat):
        _params = ", ".join((_t["input_schema"] or {}).get("properties", {}).keys())
        _col.markdown(f"**`{_t['name']}`**  \n`({_params})`  \n{_t['description'][:90]}")
    st.info(
        "**Capability ≠ authorization.** The server *exposes* all three tools to anyone who can reach "
        "it. WHO may call each is the app's **RBAC**, not the server — that separation is the point."
    )

with st.expander("🧾 Raw agent messages — the actual arrays sent to the model"):
    run = st.session_state.get("run")
    if not run:
        st.caption("Run a scenario to capture the raw messages.")
    else:
        st.caption("Research agent — the real messages array (system prompt, tool calls, tool results):")
        st.code(json.dumps(run["research_msgs"], indent=2, default=str)[:4500], language="json")
        st.caption("Orchestrator — its messages (findings in, JSON decision out at temperature 0):")
        st.code(json.dumps(run["orch_msgs"], indent=2, default=str)[:2500], language="json")

# =============================================================================
#  Try this + takeaway
# =============================================================================
try_this(
    "Run **Order 4471** (enterprise, in window). Watch 🔎 Research gather facts, 🧭 Orchestrator decide, "
    "and the ⏸️ approval gate open before any money moves. Approve it and see ⚡ Action execute.",
    "Now run **Order 5012** (standard, expired). Same three agents, but the Orchestrator **denies** — no "
    "gate, no action. One governance path handled both outcomes.",
    "Inside the Research bubble, open **🔧 Show the tool round-trips**. Every fact came from a real named "
    "tool call over MCP, each with an RBAC ✅ — that's the “look under the hood”.",
    "Under **What kept this safe**, click **Have the read-only Research agent try to issue a refund**. It's "
    "refused in *code*, before the tool server is reached. Capability is not authorization.",
    "Approve one run and deny another, then open the **audit log**. The *decision* is recorded, not just the "
    "outcome — that's what makes the system defensible.",
)

st.divider()
st.info(
    "**Takeaway:** the acronyms aren't five topics — they're the guardrails on one refund's single "
    "journey. Agents reach their tools over a standard **MCP** server (decoupled, swappable), but trust "
    "comes from governance: **least-privilege RBAC** on every call, a **human in the loop** before any "
    "irreversible action, and a **complete audit trail**. Capability is not permission."
)
st.warning(
    "**What's missing — it hasn't been adversarially tested.** Governance rules only help if they hold "
    "up under attack (prompt injection, or tricking an agent into leaking data or making an unauthorized "
    "payment). **➡️ Take-home — Red-team & govern** attacks the system, then turns the controls on to stop it."
)
