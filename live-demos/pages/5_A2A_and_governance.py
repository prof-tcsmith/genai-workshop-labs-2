"""Level 5 · Agent-to-agent (A2A) collaboration + governance.

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
"""
import json

import streamlit as st

from shared import store
from shared.core import boot, chat, layer_badge, stream_assistant, tool_calls_to_message
from shared.slides import render_slides

client = boot("Level 5 · A2A + governance")

st.title("Level 5 · Agent-to-agent + governance")
layer_badge([2, 7])
st.caption(
    "Multiple agents (Layer 2 orchestration) collaborate on a refund — but every "
    "step runs under governance (Layer 7): role-based tool access, a human "
    "approval gate, and an append-only audit log."
)
render_slides("governance")

# --- Mock enterprise system (the "order DB") ---------------------------------
ORDERS = {
    "4471": {"placed_days_ago": 12, "status": "delivered", "amount": 240.0, "customer_type": "enterprise"},
    "5012": {"placed_days_ago": 60, "status": "delivered", "amount": 90.0, "customer_type": "standard"},
}

# --- RBAC policy: which role may invoke which tool ----------------------------
# This is the governance rule enforced in code (not just a prompt).
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


# --- Read tools (data layer the RESEARCH agent is allowed to call) ------------
def get_order(order_id: str) -> dict:
    o = ORDERS.get(str(order_id).strip())
    return o if o else {"error": f"order {order_id} not found"}


def get_policy_index():
    """Build + cache the refund_policy index once (uses store / embeddings)."""
    if "refund_index" not in st.session_state:
        docs = store.load_corpus(["refund_policy"])
        if not docs:
            st.error("No refund_policy.md found at shared/corpus/.")
            st.stop()
        with st.spinner("Indexing the refund policy (once)…"):
            st.session_state["refund_index"] = store.build_index(client, docs)
    return st.session_state["refund_index"]


def search_policy(query: str) -> dict:
    hits = store.search(client, get_policy_index(), query, k=3)
    return {"snippets": [{"doc": it["doc"], "text": it["text"], "score": round(s, 3)}
                         for it, s in hits]}


# --- RBAC-enforcing tool dispatch --------------------------------------------
# Every tool call goes through here. If a role calls a tool it is not permitted
# to use, the call is BLOCKED before any function runs, and the block is audited.
def call_tool(role: str, name: str, args: dict):
    if name not in RBAC.get(role, set()):
        audit("rbac_BLOCKED", {"role": role, "tool": name, "reason": "not permitted for role"})
        return {"error": f"RBAC: role '{role}' may not call '{name}'"}, True
    audit("rbac_allowed", {"role": role, "tool": name})
    audit("tool_call", {"role": role, "tool": name, "args": args})
    if name == "get_order":
        result = get_order(args.get("order_id", ""))
    elif name == "search_policy":
        result = search_policy(args.get("query", ""))
    elif name == "issue_refund":
        result = issue_refund(args.get("order_id", ""), args.get("amount", 0.0))
    else:
        result = {"error": f"unknown tool {name}"}
    audit("tool_result", {"tool": name, "result": result})
    return result, False


# --- Write tool (ACTION agent only; reached only after human approval) --------
def issue_refund(order_id: str, amount: float) -> dict:
    # Mock side effect — in real life this hits the payments system.
    return {"refunded": True, "order_id": str(order_id), "amount": float(amount),
            "confirmation": f"RF-{order_id}"}


# Tool schemas exposed to the RESEARCH agent (read-only set).
RESEARCH_TOOLS = [
    {"type": "function", "function": {
        "name": "get_order", "description": "Look up an order by id.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "search_policy", "description": "Search the refund policy for relevant text.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
]


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
        content, calls = stream_assistant(client, messages, tools=RESEARCH_TOOLS, placeholder=None)
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

st.divider()
st.info(
    "**Takeaway:** orchestration lets specialised agents collaborate (Layer 2), but "
    "trust comes from governance (Layer 7): least-privilege RBAC on tools, a human "
    "in the loop before any irreversible action, and a complete audit trail."
)
