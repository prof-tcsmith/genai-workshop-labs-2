import streamlit as st

from shared.core import render_key_sidebar, ensure_access, STACK
from shared.slides import render_slides

st.set_page_config(page_title="Enterprise AI — the building blocks", page_icon="🧱", layout="wide")
ensure_access()
render_key_sidebar()

st.title("🧱 The journey — 11 dimensions of GenAI, stop by stop")
st.write(
    "The intro slides gave you the **goals**, the **7-layer stack**, and the **eleven dimensions**. "
    "This app is where the journey happens: each stop below demonstrates one or more dimensions **live**, "
    "adds **one** capability, and names what's still missing — which sets up the next stop. "
    "Pick a provider and paste the workshop key in the sidebar, then walk the stops in order."
)

if st.session_state.get("key"):
    st.success("Key connected — start at **1. Chatbot** in the sidebar, or from the list below.")
else:
    st.info("⬅️ Pick a provider and paste the workshop key in the sidebar to begin.")

# The itinerary. Stop numbers match the sidebar; the dimension numbers match the
# intro deck's "Eleven dimensions" slide. (None = the browser interlude.)
STOPS = [
    ("pages/1_1._Chatbot.py", "1 · Chatbot", "Dimension 1 · context engineering", [1, 3],
     "A system prompt + a user message — behavior lives in the context, not the weights. Missing: memory."),
    ("pages/2_2._Memory.py", "2 · Memory", "Dimension 2 · memory", [1, 3],
     "The bot remembers: the full history is replayed each turn (and it isn't free). Missing: guardrails."),
    ("pages/3_3._Guardrails.py", "3 · Guardrails", "Dimension 3 · guardrails", [1, 3, 7],
     "Scope + an independent pre-flight check, before the answer ships. Missing: real knowledge."),
    ("pages/4_4._Grounding_and_RAG.py", "4 · Grounding & RAG", "Dimension 4 · retrieval-augmented generation", [3, 4, 6],
     "Retrieve → cite → abstain: grounded answers from your documents. Missing: quality depends on the data."),
    ("pages/5_5._Build_and_break_a_RAG.py", "5 · Build & break a RAG", "Dimension 5 · data access", [4, 6],
     "Tune chunking and watch quality collapse — retrieval quality is data quality. Missing: it still can't act."),
    (None, "🌐 Interlude · Structured outputs", "Dimension 6 · structured outputs", [3],
     "Messy text in → schema-clean JSON out: the model becomes a system component. Runs in your browser."),
    ("pages/6_6._Tools_and_the_agent_loop.py", "6 · Tools & the agent loop", "Dimensions 7 & 9 · tool use + approvals", [2, 3, 5],
     "The model acts: plan → call → observe, with a human approval gate. Missing: coordination + governance at scale."),
    ("pages/7_7._Multi-agent_and_governance.py", "7 · Multi-agent & governance", "Dimensions 8, 10 & 11 · MCP + logging + governance", [2, 7],
     "Specialist agents collaborate (A2A) over a real MCP server, under RBAC, approvals, and an audit log. Missing: it hasn't been attacked."),
    ("pages/8_8._Red_team.py", "8 · Red-team & govern", "Dimension 11 · governance, under attack", [7],
     "Attack the system, then switch the controls on to stop it — defense in depth."),
    ("pages/9_9._Evaluate_and_validate.py", "9 · Evaluate & validate", "Beyond the 11 · validation", [7],
     "Is it good enough to ship? A golden-set eval, an LLM-as-judge, an abstention check, and a go/no-go."),
]
PROMPT_LAB_URL = "https://prof-tcsmith.github.io/genai-workshop-labs/prompt-lab/"

for path, label, dims, layers, desc in STOPS:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{label}**  \n🧭 *{dims}*  \n{desc}")
        with c2:
            st.caption("Layers " + ", ".join(str(x) for x in layers))
            if path:
                st.page_link(path, label="Open →")
            else:
                st.link_button("Open ↗", PROMPT_LAB_URL)

st.divider()
st.markdown(
    "### ▶ Then: see the blocks become a real application\n"
    "These stops are the **concepts**. Two applied cases build the *same* result — a "
    "**Canvas-ready quiz from your course materials** — two different ways:\n\n"
    "- 🎓 **[Course Content Studio ↗](https://genai-workshop-labs-awybgq8gnmnrevxna2ukv3.streamlit.app/)** — "
    "the **hand-built** pipeline: real services (a real vector DB, a real database, a real MCP tool) wired "
    "together by you. *Runs in your browser.*\n"
    "- 🤖 **[Autonomous Course-Builder ↗](https://github.com/prof-tcsmith/genai-workshop-labs/tree/main/course-builder)** — "
    "the **agentic** version: an orchestrator + specialist agents (Researcher / Item-writer / Critic / Exporter) "
    "assemble it themselves over **MCP**, under governance (approval gate + audit). *Run locally via Docker.*"
)

render_slides("overview", label="📊 Recap — the 7-layer stack (from the intro slides)", expanded=False)

with st.expander("The 7-layer stack (legend) / safety / session slides"):
    st.markdown("\n".join(f"- **{k}** — {v}" for k, v in STACK.items()))
    st.caption(
        "Note: layer 1 (*Experience*) is the **interface** — and it isn't necessarily human. Another "
        "system can call your app via API, or the app can expose itself **as an agent over A2A** that "
        "other agents call (Level 7 shows agents as callers). Same layer, same trust requirements."
    )
    st.markdown(
        "Session slides: [Dimensions of GenAI (60-min deck) ↗](https://prof-tcsmith.github.io/genai-workshop-labs/day.html) · "
        "everything else: [the hub ↗](https://prof-tcsmith.github.io/genai-workshop-labs/)"
    )
    st.markdown(
        "---\nYour key stays in your browser session only. Demos use the cheap `gpt-4o-mini` model with "
        "capped output and a per-session request limit. Please don't paste sensitive data — shared key, teaching environment."
    )
