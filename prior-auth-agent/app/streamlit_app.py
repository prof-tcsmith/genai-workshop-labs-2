"""Prior-Authorization Triage — the applied Case: an agentic system that assembles
every lab concept (context, guardrails, RAG, the agent loop, MCP + A2A, governance).

An orchestrator coordinates specialist agents (Researcher, Reviewer, Critic,
Case-worker) that call tools over a real, networked MCP server to triage synthetic
prior-authorization requests against synthetic coverage policies — under governance
(a human approval gate + an audit log).

SYNTHETIC teaching data only. Not real patients. Not medical advice.
(c) Dr. Tim Smith, 2026
"""
import streamlit as st

from lib import agents, mcp_client

st.set_page_config(page_title="Prior-Auth Triage — the Case", page_icon="🏥", layout="wide")
print("(c) Dr. Tim Smith, 2026")

st.title("🏥 Prior-Authorization Triage — the applied Case")
st.caption(
    "An **orchestrator** coordinates specialist agents — **Researcher → Reviewer → Critic → "
    "Case-worker** — that call tools over a **real MCP server** to triage a coverage request "
    "against policy. It assembles every lab: **context + memory**, a **guardrail**, **RAG** over "
    "the policies, the **agent loop**, **MCP + A2A**, and **governance** (a human approval gate + "
    "an LLM-as-evaluator critic + an audit log)."
)
st.warning(
    "⚕️ **Synthetic teaching data only** — fictional members, fictional policies. This is a "
    "demonstration of AI **system architecture**, not a medical device and not medical advice.",
    icon="⚕️")

# --- MCP connection panel ----------------------------------------------------
with st.expander(f"🔌 Tools over MCP · {mcp_client.server_url()}", expanded=False):
    st.caption(
        "The agents never import the tool backends — they call these named tools over the network "
        "(streamable-http). The same decoupling Lab 5 (Level 7) teaches: swap the backend, the "
        "agents don't change."
    )
    try:
        for t in mcp_client.list_tools():
            st.markdown(f"- **`{t['name']}`** — {t['description'][:110]}")
    except Exception as exc:
        st.error(f"Can't reach the MCP server at `{mcp_client.server_url()}`. "
                 f"Start it (`docker compose up`, or run mcp-server/server.py). [{exc}]")

# --- 1 · Pick a request from the queue --------------------------------------
st.subheader("1 · Pick a request from the queue")
try:
    requests = mcp_client.call_tool("list_requests") or []
except Exception:
    requests = []
if not requests:
    st.info("No requests available — is the MCP server up?")
    st.stop()

labels = [f"{r['id']} · {r['member_name']} · {r['service']}" for r in requests]
pick = st.selectbox("Pending prior-authorization requests (from MCP `list_requests`)", labels)
request = requests[labels.index(pick)]
with st.container(border=True):
    st.markdown(f"**{request['id']} — {request['service']}**  ·  policy `{request['policy_id']}`")
    st.markdown(f"**Member:** {request['member_name']} ({request['plan']}) · `{request['member_id']}`")
    st.markdown(f"**Clinical note:** {request['clinical_note']}")

# --- 2 · Run the agents ------------------------------------------------------
st.subheader("2 · Run the triage agents")
sloppy = st.toggle(
    "🧪 Demo fault: make the Reviewer rushed (watch the Critic catch it)",
    value=False,
    help="Like Lab 3's sabotage sliders: the first draft uses a rushed reviewer prompt, so the "
         "Critic (the LLM evaluator) visibly fails it and sends it back for revision. Revisions "
         "always use the careful prompt.")
if st.button("▶ Run the agents", type="primary"):
    st.session_state.pop("pa_submit", None)
    with st.status("Orchestrator running — agents coordinating over MCP…", expanded=True) as status:
        def _live(frm: str, to: str, content: str) -> None:
            status.write(f"**{frm} → {to}** · {content}")
        st.session_state["pa"] = agents.run_triage(request, max_revisions=2, log=_live,
                                                   sloppy_reviewer=sloppy)
        status.update(label="Triage complete — full trace below", state="complete", expanded=False)
    st.session_state["pa_req"] = request

pa = st.session_state.get("pa")
if pa and st.session_state.get("pa_req", {}).get("id") == request["id"]:
    det = pa["determination"]

    # --- 3 · A2A timeline ----------------------------------------------------
    st.subheader("3 · Agent-to-agent (A2A) messages")
    st.caption(
        "Honest labels: the **Reviewer** and **Critic** are LLM calls; the **Orchestrator** and "
        "**Researcher** are deterministic code (routing + retrieval). Knowing which is which is "
        "part of governing a system like this."
    )
    for m in pa["a2a"]:
        st.markdown(f"**{m['from']} → {m['to']}**")
        st.info(m["content"])

    if not det:
        st.warning("No grounded determination could be produced (retrieval found nothing usable).")
        st.stop()

    # --- 4 · Determination ---------------------------------------------------
    st.subheader("4 · Determination (grounded in policy)")
    rv = pa["review"] or {}
    color = {"approve": "✅", "deny": "⛔", "pend": "⏸️"}.get(det["decision"], "•")
    st.markdown(f"### {color} **{det['decision'].upper()}**")
    st.markdown(f"**Rationale.** {det['rationale']}")
    if det.get("criteria"):
        st.markdown("**Criteria assessed:**")
        for c in det["criteria"]:
            mark = {"yes": "✅", "no": "⛔", "unknown": "❓"}.get(c.get("met"), "•")
            st.markdown(f"- {mark} **{c['criterion']}** — {c.get('evidence', '')}")
    st.caption(f"🔎 critic (LLM as evaluator): grounded={rv.get('grounded')} · "
               f"consistent={rv.get('consistent')} · cites **{det['citation'].get('source')}** · "
               f"{rv.get('notes', '')}")

    # --- 5 · Human approval gate + submit ------------------------------------
    sub = st.session_state.get("pa_submit")
    if not sub:
        st.subheader("5 · Human approval gate")
        st.warning(
            "Nothing is recorded until a human signs off — **the agents never deny on their own**, "
            "and when documentation is missing they **pend** (ask for more) rather than deny. Only "
            "the **Case-worker** may call `submit_determination` (over MCP), and only after this "
            "gate. In healthcare the human in the loop is the point, not a formality — recent U.S. "
            "regulatory guidance on prior authorization requires exactly this kind of human review."
        )
        if st.button(f"✅ Approve & record: {det['decision'].upper()}", type="primary"):
            st.session_state["pa_submit"] = agents.submit(request, det, audit=pa["audit"])
            st.rerun()
    else:
        st.subheader("5 · Recorded ✅")
        st.success(f"The Case-worker recorded the determination over MCP: "
                   f"**{sub.get('decision', det['decision']).upper()}** for {request['id']}.")

    # --- 6 · Audit log -------------------------------------------------------
    st.subheader("6 · Audit log (append-only)")
    st.caption("Every A2A message, MCP tool call, critic round, and the approval decision.")
    for i, e in enumerate(pa["audit"], 1):
        st.markdown(f"`{i:02d}` **{e['event']}** — {e['detail']}")

st.divider()
st.info(
    "**The point:** an orchestrator + specialist agents (A2A) reach real tools over **MCP**, ground "
    "every decision in retrieved policy, run a **critique→revise** loop where an **LLM evaluates** "
    "the draft, and stay **governed** (RBAC on the write + a human approval gate + an audit log). "
    "This is the five labs, assembled."
)
