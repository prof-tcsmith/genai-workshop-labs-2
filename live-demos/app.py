import streamlit as st

from shared.core import render_key_sidebar, ensure_access, STACK
from shared.slides import render_slides

st.set_page_config(page_title="Enterprise AI — the building blocks", page_icon="🧱", layout="wide")
ensure_access()
render_key_sidebar()

st.title("🧱 Enterprise AI — the building blocks")
st.write(
    "Nine hands-on building blocks. Each adds **one** capability and lights up more of "
    "the 7-layer stack. Pick a provider and paste the workshop key in the sidebar, then work Levels "
    "1 → 9 — at each step you see the new capability *and* what's still missing, which "
    "sets up the next block."
)
render_slides("overview", label="📊 Start here — the 7-layer stack (interactive)", expanded=True)

if st.session_state.get("key"):
    st.success("Key connected. Open a level from the sidebar or the list below.")
else:
    st.info("⬅️ Pick a provider and paste the workshop key in the sidebar to begin.")

levels = [
    ("pages/1_Chatbot.py", "Level 1 · Chatbot", [1, 3],
     "A system prompt + a user message. ChatGPT is an *app*; the LLM is one layer inside it. Missing: memory."),
    ("pages/2_Memory.py", "Level 2 · Memory", [1, 3],
     "The bot remembers the conversation (full history replayed each turn). Missing: guardrails."),
    ("pages/3_Guardrails.py", "Level 3 · Guardrails", [1, 3, 7],
     "Scope + an independent pre-flight check keep it on-task and safe. Missing: real knowledge."),
    ("pages/4_Grounding_and_RAG.py", "Level 4 · Grounding & RAG", [3, 4, 6],
     "Retrieve from your documents → grounded, cited answers. Missing: retrieval quality depends on the data + pipeline."),
    ("pages/5_Build_and_break_RAG.py", "Level 5 · Build & break a RAG", [4, 6],
     "Tune chunking and watch quality collapse — most RAG failures are data failures. Missing: it still can't act."),
    ("pages/6_Tools_and_the_agent_loop.py", "Level 6 · Tools & the agent loop", [2, 3, 5],
     "The model calls tools in a plan → act → observe loop, with a human approval gate. Missing: coordination + governance at scale."),
    ("pages/7_Multi_agent_and_governance.py", "Level 7 · Multi-agent & governance", [2, 7],
     "Specialist agents collaborate (A2A) under RBAC, approval gates, and an audit log. Missing: it hasn't been attacked."),
    ("pages/8_Red_team.py", "Level 8 · Red-team & govern", [7],
     "Attack the system, then switch the controls on to stop it — defense in depth."),
    ("pages/9_Evaluate_and_validate.py", "Level 9 · Evaluate & validate", [7],
     "Is it ready to ship? Run a golden-set eval, an LLM-as-judge, and an abstention check, then a go/no-go."),
]
for path, label, layers, desc in levels:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{label}**  \n{desc}")
        with c2:
            st.caption("Layers " + ", ".join(str(x) for x in layers))
            st.page_link(path, label="Open →")

st.divider()
st.markdown(
    "### ▶ Then: see the blocks become a real application\n"
    "These nine blocks are the **concepts**. Two applied cases build the *same* result — a "
    "**Canvas-ready quiz from your course materials** — two different ways:\n\n"
    "- 🎓 **[Course Content Studio ↗](https://genai-workshop-labs-awybgq8gnmnrevxna2ukv3.streamlit.app/)** — "
    "the **hand-built** pipeline: real services (a real vector DB, a real database, a real MCP tool) wired "
    "together by you. *Runs in your browser.*\n"
    "- 🤖 **[Autonomous Course-Builder ↗](https://github.com/prof-tcsmith/genai-workshop-labs/tree/main/course-builder)** — "
    "the **agentic** version: an orchestrator + specialist agents (Researcher / Item-writer / Critic / Exporter) "
    "assemble it themselves over **MCP**, under governance (approval gate + audit). *Run locally via Docker.*"
)

with st.expander("The 7-layer stack (legend) / safety"):
    st.markdown("\n".join(f"- **{k}** — {v}" for k, v in STACK.items()))
    st.markdown(
        "---\nYour key stays in your browser session only. Demos use the cheap `gpt-4o-mini` model with "
        "capped output and a per-session request limit. Please don't paste sensitive data — shared key, teaching environment."
    )
