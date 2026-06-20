import streamlit as st

from shared.core import render_key_sidebar, ensure_access, STACK
from shared.slides import render_slides

st.set_page_config(page_title="Live demos — Enterprise AI for IS Faculty", page_icon="🎬", layout="wide")
ensure_access()
render_key_sidebar()

st.title("🎬 Enterprise AI — six progressive live demos")
st.write(
    "Each level adds **one** capability and lights up more of the 7-layer stack. "
    "Paste the workshop OpenAI key in the sidebar, then walk Levels 1 → 6 — at each "
    "step, see the new capability and what's still missing (which sets up the next)."
)
render_slides("overview", label="📊 Start here — the 7-layer stack (interactive)", expanded=True)

if st.session_state.get("key"):
    st.success("Key connected. Open a level from the sidebar or the list below.")
else:
    st.info("⬅️ Paste the workshop OpenAI key in the sidebar to begin.")

levels = [
    ("pages/1_Chatbot.py", "Level 1 · Chatbot", [1, 3], "A system prompt + a user message. ChatGPT is an *app*; the LLM is one layer inside it. Missing: memory."),
    ("pages/2_Memory.py", "Level 2 · Memory", [1, 3], "The bot remembers the conversation (full history replayed each turn). Missing: guardrails."),
    ("pages/3_Guardrails.py", "Level 3 · Guardrails", [1, 3, 7], "Scope + an independent pre-flight check keep it on-task and safe. Missing: real knowledge."),
    ("pages/4_Context_engineering.py", "Level 4 · Context engineering", [3, 4, 6], "Retrieve from an info store and engineer the context — grounded, cited answers. Missing: the ability to act."),
    ("pages/5_MCP_and_tools.py", "Level 5 · MCP + tools", [2, 3, 5], "An agent calls tools through an MCP-style server — it can now act, not just talk. Missing: coordination + governance."),
    ("pages/6_A2A_and_governance.py", "Level 6 · A2A + governance", [2, 7], "Specialist agents collaborate (A2A) under approval gates, RBAC, and an audit log."),
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
