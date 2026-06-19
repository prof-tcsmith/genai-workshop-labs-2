import streamlit as st
from lib.llm import home_setup, CHAT_MODEL_DEFAULT
from lib.slides import render_slides

home_setup("Workshop labs — Enterprise AI for IS Faculty")

st.title("🧪 Enterprise AI — hands-on labs")
st.write(
    "Companion labs to the *Enterprise AI for IS Faculty* deck. "
    "These are the **do** to the deck's **show**: real LLM calls, real retrieval, a real agent, and a real attack."
)
render_slides("overview", label="📊 Start here — the 7-layer stack (interactive)", expanded=True)

key = st.session_state.get("openai_key")
if key:
    st.success("Key connected. Pick a lab from the sidebar or the list below.")
else:
    st.info("⬅️ Paste the workshop OpenAI key in the sidebar to begin. Tim hands it out at the session.")

st.subheader("Labs")
labs = [
    ("pages/1_Grounding.py", "1 · Grounding: prompt → retrieval → tool", "Layers 3–4", "One question, three levels of grounding. See verifiability appear."),
    ("pages/2_Build_and_break_RAG.py", "2 · Build & break a RAG", "Layers 4 & 6", "Build a tiny retrieval pipeline, then sabotage it and watch quality collapse."),
    ("pages/3_Agent_loop.py", "3 · Agent loop with tools", "Layer 2", "Give a goal; watch plan → tool → observe → loop. Toggle the approval gate."),
    ("pages/4_Red_team.py", "4 · Red-team & govern an agent", "Layer 7", "Attack an HR-policy agent, then switch on controls and watch attacks fail."),
]
for path, label, layer, desc in labs:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{label}**  \n{desc}")
        with c2:
            st.caption(layer)
            st.page_link(path, label="Open lab →")

st.markdown("There's also a **browser-only prompt lab** (no Python) linked from the workshop hub page.")

with st.expander("How these work / safety"):
    st.markdown(
        f"""
- **Your key stays in your browser session only** — it is never logged or stored by these apps.
- Labs use the cheap **`{CHAT_MODEL_DEFAULT}`** model with capped output, and there's a per-session request limit to protect the shared key.
- Retrieval uses an **in-memory index** over OpenAI embeddings — no external database.
- Please don't paste sensitive data; this is a teaching environment on a shared key.
"""
    )
