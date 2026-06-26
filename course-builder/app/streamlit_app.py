"""Autonomous Course-Builder — the agentic 'after' picture of Course Content Studio.

An orchestrator coordinates four specialist agents (Researcher, Item-writer, Critic,
Exporter) that call tools over a real, networked MCP server to produce a reviewed,
Canvas-ready quiz — under governance (a human approval gate + an audit log).

(c) Dr. Tim Smith, 2026
"""
import base64

import streamlit as st

from lib import agents, mcp_client

st.set_page_config(page_title="Autonomous Course-Builder", page_icon="🤖", layout="wide")
print("(c) Dr. Tim Smith, 2026")

st.title("🤖 Autonomous Course-Builder")
st.caption(
    "An **orchestrator** coordinates four agents — **Researcher → Item-writer → Critic → Exporter** — "
    "that call tools over a **real MCP server** to generate a reviewed, Canvas-ready quiz. It's the "
    "agentic *after* picture of the hand-built Course Content Studio: same kind of MCP tools, now "
    "assembled by agents, under governance (approval gate + audit log)."
)

# --- MCP connection panel ----------------------------------------------------
with st.expander(f"🔌 Tools over MCP · {mcp_client.server_url()}", expanded=False):
    st.caption(
        "The agents never import the tool backends — they call these named tools over the network "
        "(streamable-http). The same decoupling Lab 4 / Level 7 teach."
    )
    try:
        for t in mcp_client.list_tools():
            st.markdown(f"- **`{t['name']}`** — {t['description'][:100]}")
    except Exception as exc:  # the server must be up (docker compose brings it up)
        st.error(f"Can't reach the MCP server at `{mcp_client.server_url()}`. "
                 f"Start it (`docker compose up`, or run mcp-server/server.py). [{exc}]")

# --- 1 · Objective -----------------------------------------------------------
st.subheader("1 · Choose a learning objective")
try:
    objectives = mcp_client.call_tool("course_lookup", {"kind": "objectives"}) or []
except Exception:
    objectives = []
labels = [o["text"] for o in objectives] + ["✏️ Custom objective…"]
choice = st.selectbox("Objective (from the seeded course, via MCP `course_lookup`)", labels)
objective = st.text_input("Type a custom objective", "") if choice.startswith("✏️") else choice
n_items = st.slider("How many items to generate", 2, 6, 4)

# --- 2 · Run the agents ------------------------------------------------------
st.subheader("2 · Run the multi-agent build")
if st.button("▶ Run the agents", type="primary"):
    if not (objective or "").strip():
        st.warning("Pick or type a learning objective first.")
    else:
        st.session_state.pop("cb_export", None)
        with st.spinner("Orchestrator → Researcher → Item-writer → Critic, calling tools over MCP…"):
            st.session_state["cb"] = agents.run_build(objective.strip(), n_items=n_items, max_revisions=2)

cb = st.session_state.get("cb")
if cb:
    # --- 3 · A2A timeline ----------------------------------------------------
    st.subheader("3 · Agent-to-agent (A2A) messages")
    st.caption("Each agent is a separate set of LLM calls. This is them coordinating.")
    for m in cb["a2a"]:
        st.markdown(f"**{m['from']} → {m['to']}**")
        st.info(m["content"])

    # --- 4 · Reviewed items --------------------------------------------------
    st.subheader("4 · Reviewed items")
    if not cb["items"]:
        st.warning("No grounded items could be produced for that objective (retrieval found nothing usable).")
    for i, it in enumerate(cb["items"], 1):
        rv = it.get("_review", {})
        st.markdown(f"{'✅' if rv.get('ok') else '⚠️'} **{i}. [{it['type']}]** {it['stem']}")
        if it["type"] in ("mcq", "true_false"):
            for j, opt in enumerate(it["options"]):
                st.markdown(f"- {'✅' if str(j) in it['correct'] else '▫️'} {opt}")
        else:
            st.markdown(f"- _Accepted answers:_ {', '.join(it['correct'])}")
        st.caption(
            f"🔎 grounded={rv.get('grounded')} · clear={rv.get('clear')} · "
            f"cites **{it['citation'].get('source')}** · {rv.get('notes', '')}"
        )

    # --- 5 · Approval gate + export -----------------------------------------
    exp = st.session_state.get("cb_export")
    if cb["items"] and not exp:
        st.subheader("5 · Human approval gate")
        st.warning(
            "Nothing is exported until you approve. Only the **Exporter** agent may call `export_qti` "
            "(over MCP) — and only after this human gate. That's the governance point."
        )
        if st.button("✅ Approve & export to Canvas QTI", type="primary"):
            st.session_state["cb_export"] = agents.export(
                cb["items"], "Enterprise AI Foundations — Quiz", audit=cb["audit"])
            st.rerun()
    if exp:
        st.subheader("5 · Exported ✅")
        st.success("The Exporter built the package over MCP. Download it for Canvas:")
        st.download_button("⬇️ quiz_qti.zip", data=base64.b64decode(exp["base64"]),
                           file_name=exp["filename"], mime="application/zip")
        with st.expander("Answer key"):
            st.code(exp["answer_key"])

    # --- 6 · Audit log -------------------------------------------------------
    st.subheader("6 · Audit log (append-only)")
    st.caption("Every A2A message, MCP tool call, critic round, and the approval decision — the governance trail.")
    for i, e in enumerate(cb["audit"], 1):
        st.markdown(f"`{i:02d}` **{e['event']}** — {e['detail']}")

st.divider()
st.info(
    "**The point:** an orchestrator + specialist agents (A2A) reach real tools over **MCP**, run a "
    "critique→revise loop for quality, and stay **governed** (human approval + audit). Compare with "
    "Course Content Studio, which builds the same kind of result by hand."
)
