"""Multi-agent (A2A) collaboration + governance.

Three specialised agents collaborate to handle a customer REFUND end-to-end,
under explicit governance. Everything is OBSERVABLE in the UI:

  • A2A MESSAGES  — a timeline of who-said-what-to-whom between agents.
  • RBAC          — only the ACTION agent may run the write tool issue_refund;
                    a research-side write attempt is BLOCKED in code.
  • APPROVAL GATE — a human must click Approve before any refund executes.
  • AUDIT LOG     — append-only trail of every message, tool call, RBAC check,
                    and the approval decision + outcome.

The agents are LLM calls with distinct roles:
  ORCHESTRATOR  coordinates and makes the policy decision.
  RESEARCH      READ-ONLY: get_order / search_policy to gather facts.
  ACTION        the ONLY agent allowed to perform issue_refund (a write).

The three tools now live behind a real MCP server (``shared.mcp_tools``), reached
over a genuine MCP client session — in-process by default, networked-capable via
an ``mcp_server_url`` secret. Exposing a tool over MCP is a *capability*; WHO may
call it is decided by the orchestrator's RBAC, not the server.
"""
import json

import streamlit as st

from shared import mcp_client
from shared.core import boot, chat, layer_badge, stream_assistant, tool_calls_to_message, try_this
from shared.slides import render_slides

client = boot("7 · Multi-agent + governance")

st.title("7 · Multi-agent + governance")
layer_badge([2, 7])
st.caption("🧭 **MCP + A2A · logging · governance:** decoupled tools, an audit trail, least privilege.")
st.caption(
    "Multiple agents collaborate on a refund — calling their tools over a "
    "**real MCP server** — but every step runs under governance: role-based tool access, a "
    "human approval gate, and an append-only audit log."
)
render_slides("governance")

# --- RBAC policy: which role may invoke which MCP tool ------------------------
# The governance rule, enforced in code (not just a prompt). The MCP server
# exposes every tool; THIS is what decides who may call each one.
RBAC = {
    "research": {"get_order", "search_policy"},   # READ-ONLY
    "action": {"issue_refund"},                    # WRITE — action agent only
    "orchestrator": set(),                         # delegates; calls no tools
}

# --- Session state: audit log + the pending (awaiting-approval) decision ------
st.session_state.setdefault("audit", [])      # append-only list of dicts
st.session_state.setdefault("a2a", [])        # A2A message timeline
st.session_state.setdefault("pending", None)  # the refund proposal, if any


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


# --- MCP panel: the tools now live behind a real MCP server -------------------
with st.expander(f"🔌 Tools run behind a real MCP server · mode: {mcp_client.mode()}", expanded=True):
    st.caption(
        "The agents don't call Python functions — they call **named tools over the MCP protocol** "
        "(a genuine client→server→tool round-trip). **Why this matters — decoupling:** calling a "
        "backend's API directly (say, the Postgres API) would *weld* the system to that backend — "
        "tight coupling, brittle architecture. MCP interposes an interface that is **purpose-constrained** "
        "(only the verbs the job needs) and **generalized** (any backend can serve them): swap the "
        "backend, the agents don't change. In-process by default; set an `mcp_server_url` secret to "
        "point at a networked server, with no app-code change."
    )
    _cat = mcp_catalog()
    for _col, _t in zip(st.columns(len(_cat) or 1), _cat):
        _params = ", ".join((_t["input_schema"] or {}).get("properties", {}).keys())
        _col.markdown(f"**`{_t['name']}`**  \n`({_params})`  \n{_t['description'][:90]}")
    st.info(
        "**Capability ≠ authorization.** The server *exposes* all three tools to anyone who can reach "
        "it. WHO may call each is enforced by the orchestrator's **RBAC** (below), not by the server — "
        "that separation is the governance point."
    )


def run_research(order_id: str, placeholder=None) -> str:
    """RESEARCH agent: a read-only tool loop (capped). Streams its final findings."""
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
            result, _blocked = call_tool("research", c["name"], args)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)})
    # Stream the final findings (no tools attached) into the placeholder.
    findings, _ = stream_assistant(client, messages, placeholder=placeholder)
    return findings or "(no findings)"


def run_orchestrator(order_id: str, findings: str) -> dict:
    """ORCHESTRATOR agent: decides eligibility + proposes refund or denial (JSON)."""
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
    return d


# --- UI: kick off the workflow -----------------------------------------------
st.subheader("1 · Run the multi-agent workflow")
order_id = st.text_input("Customer refund request — order id", "4471",
                         help="Try 4471 (enterprise, in window) vs 5012 (standard, expired).")

if st.button("Run workflow", type="primary"):
    # Fresh run: reset observable state so the demo is clean each time.
    st.session_state["audit"] = []
    st.session_state["a2a"] = []
    st.session_state["pending"] = None

    # Orchestrator delegates fact-finding to the Research agent.
    a2a("Orchestrator", "Research", f"Gather facts for order {order_id}.")
    st.markdown("**Research agent — gathering facts (streaming):**")
    findings = run_research(order_id, placeholder=st.empty())
    a2a("Research", "Orchestrator", findings)

    # Orchestrator makes the policy decision.
    with st.spinner("Orchestrator deciding per policy…"):
        decision = run_orchestrator(order_id, findings)
    audit("orchestrator_decision", decision)

    if decision["decision"] == "refund":
        # Propose the action to the Action agent and OPEN the approval gate.
        amt = float(decision.get("amount") or 0)
        a2a("Orchestrator", "Action", f"Propose: refund ${amt:.2f} for order {order_id}.")
        st.session_state["pending"] = {"order_id": order_id, "amount": amt,
                                       "reason": decision.get("reason", "")}
        audit("approval_pending", st.session_state["pending"])
    else:
        a2a("Orchestrator", "Action", f"No action: deny refund for order {order_id}.")
        audit("orchestrator_denied", {"order_id": order_id, "reason": decision.get("reason", "")})

# --- A2A message timeline -----------------------------------------------------
if st.session_state["a2a"]:
    st.subheader("2 · Agent-to-agent (A2A) messages")
    st.caption("Each agent is a separate LLM call. This is them coordinating.")
    for m in st.session_state["a2a"]:
        st.markdown(f"**{m['from']} → {m['to']}**")
        st.info(m["content"])

# --- RBAC rule (always visible) ----------------------------------------------
st.subheader("3 · RBAC — who may call which tool")
st.caption("Enforced in code on every tool call. A read-side write attempt is blocked.")
st.json({role: sorted(tools) for role, tools in RBAC.items()})
if any(e["event"] == "rbac_BLOCKED" for e in st.session_state["audit"]):
    st.error("🚫 RBAC blocked a tool call this run (see audit log).")

# --- Approval gate: nothing executes until a human approves -------------------
pending = st.session_state["pending"]
if pending:
    st.subheader("4 · Human approval gate")
    st.warning(
        f"⏸️ PENDING — proposed refund **${pending['amount']:.2f}** for order "
        f"**{pending['order_id']}**.\n\nReason: {pending['reason']}\n\n"
        "Nothing has been executed. A human must approve."
    )
    c_yes, c_no = st.columns(2)
    if c_yes.button("✅ Approve & execute", type="primary"):
        audit("approval_decision", {"by": "human", "decision": "approved"})
        # ONLY the Action agent may execute the write — routed through RBAC.
        result, blocked = call_tool("action", "issue_refund",
                                    {"order_id": pending["order_id"], "amount": pending["amount"]})
        a2a("Action", "Orchestrator", f"Executed refund: {json.dumps(result)}")
        audit("outcome", {"status": "blocked" if blocked else "executed", "result": result})
        st.session_state["pending"] = None
        st.success(f"💸 Refund executed — {result.get('confirmation', 'n/a')}.")
        st.rerun()
    if c_no.button("🚫 Deny"):
        audit("approval_decision", {"by": "human", "decision": "denied"})
        a2a("Action", "Orchestrator", "Human denied the refund — no action taken.")
        audit("outcome", {"status": "denied", "result": None})
        st.session_state["pending"] = None
        st.error("Refund denied by human reviewer. Nothing executed.")
        st.rerun()

# --- Demonstrate RBAC blocking a write from the WRONG agent -------------------
with st.expander("🔒 Prove RBAC: try a write from the Research (read-only) role"):
    st.caption("The Research agent is read-only. If it ever attempts issue_refund, "
               "the dispatch layer blocks it BEFORE the function runs.")
    if st.button("Attempt research-side issue_refund (should be BLOCKED)"):
        res, blocked = call_tool("research", "issue_refund",
                                 {"order_id": order_id, "amount": 999})
        if blocked:
            st.error(f"🚫 BLOCKED by RBAC: {res['error']}")
        else:
            st.write(res)

# --- Audit log (append-only) --------------------------------------------------
st.subheader("5 · Audit log (append-only)")
st.caption("Every A2A message, tool call, RBAC check, and decision is recorded — "
           "the governance trail you can hand an auditor.")
if st.session_state["audit"]:
    for i, e in enumerate(st.session_state["audit"], 1):
        st.markdown(f"`{i:02d}` **{e['event']}** — {json.dumps(e['detail'])}")
else:
    st.write("No events yet — run the workflow.")

try_this(
    "Run the workflow, then read section **2 · A2A messages**. Each line is a *separate model "
    "call* handing work to another agent — that hand-off is all “multi-agent” means.",
    "Open **🔒 Prove RBAC** and fire the research-side write. It's refused in **code**, before "
    "any model is consulted. Capability is not authorization.",
    "At the **approval gate**, deny once and approve once. Compare the audit log each time — the "
    "decision, not just the outcome, is recorded.",
    "Read the **audit log** bottom-up and try to reconstruct who did what, with which tool, and "
    "who approved it. If you can't answer that from the log, you can't defend the system.",
)

st.divider()
st.info(
    "**Takeaway:** specialised agents collaborate and reach their tools over a standard "
    "**MCP** server (decoupled, swappable for a networked one) — but trust comes from governance "
    ": least-privilege RBAC on every tool call, a human in the loop before any irreversible "
    "action, and a complete audit trail."
)
st.warning(
    "**What's missing — it hasn't been adversarially tested.** Governance rules only "
    "help if they hold up under attack (prompt injection, data exfiltration, tricking an "
    "agent into a write). **➡️ Take-home — Red-team & govern** attacks the system, then turns "
    "the controls on to stop it."
)
