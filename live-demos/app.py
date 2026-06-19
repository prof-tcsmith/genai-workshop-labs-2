import streamlit as st

from shared.core import render_key_sidebar, ensure_access, STACK
from shared.slides import render_slides

st.set_page_config(page_title="Live demos — Enterprise AI for IS Faculty", page_icon="🎬", layout="wide")
ensure_access()
render_key_sidebar()

st.title("🎬 Enterprise AI — five progressive live demos")
st.write(
    "Each level adds **one** capability and lights up more of the 7-layer stack. "
    "Paste the workshop OpenAI key in the sidebar, then walk Levels 1 → 5 and watch what changes."
)
render_slides("overview", label="📊 Start here — the 7-layer stack (interactive)", expanded=True)

if st.session_state.get("key"):
    st.success("Key connected. Open a level from the sidebar or the list below.")
else:
    st.info("⬅️ Paste the workshop OpenAI key in the sidebar to begin.")

levels = [
    ("pages/1_Chatbot.py", "Level 1 · Chatbot", [1, 3], "A system prompt + one message. No memory, no guardrails — the bare minimum."),
    ("pages/2_Memory_and_guardrails.py", "Level 2 · Memory + guardrails", [1, 3, 7], "A narrow support bot that remembers the conversation and refuses to go off-task."),
    ("pages/3_Context_engineering.py", "Level 3 · Context engineering", [4, 6], "Retrieve from an info store and engineer the context, for grounded, cited answers."),
    ("pages/4_MCP_and_tools.py", "Level 4 · MCP + tools", [2, 5], "An agent that calls tools through an MCP-style server — it can now act, not just talk."),
    ("pages/5_A2A_and_governance.py", "Level 5 · A2A + governance", [2, 7], "Specialist agents collaborate (A2A) under approval gates, RBAC, and an audit log."),
]
for path, label, layers, desc in levels:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{label}**  \n{desc}")
        with c2:
            st.caption("Layers " + ", ".join(str(x) for x in layers))
            st.page_link(path, label="Open →")

with st.expander("The 7-layer stack (legend) / safety"):
    st.markdown("\n".join(f"- **{k}** — {v}" for k, v in STACK.items()))
    st.markdown(
        "---\nYour key stays in your browser session only. Demos use the cheap `gpt-4o-mini` model with "
        "capped output and a per-session request limit. Please don't paste sensitive data — shared key, teaching environment."
    )
