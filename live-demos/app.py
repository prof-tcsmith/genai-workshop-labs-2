import streamlit as st

from shared.core import render_key_sidebar, render_route_sidebar, ensure_access, STACK
from shared.slides import render_slides

st.set_page_config(page_title="Enterprise AI — the building blocks", page_icon="🧱", layout="wide")
ensure_access()
render_route_sidebar()
render_key_sidebar()

st.title("🧱 Today's route — five stops")
st.write(
    "The intro slides gave you the **goals**, the **7-layer stack**, and the **eleven dimensions**. "
    "This app is where the journey happens: **five stops**, each demonstrating its dimensions **live** — "
    "and each stop opens by *breaking* the one before it. "
    "Pick a provider and paste the workshop key in the sidebar, then start at **Stop 1**."
)

if st.session_state.get("key"):
    st.success("Key connected — start at **Stop 1** below (or in the sidebar).")
else:
    st.info("⬅️ Pick a provider and paste the workshop key in the sidebar to begin.")

# The five stops of the 60-minute hands-on hour. Each stop = a problem the
# previous stop just created: forgets → answers anything → can't prove it →
# can't act → can't govern the actor.
ROUTE = [
    ("Stop 1 · A model becomes an app", "Dimensions 1–2 · context + memory",
     "The bare model forgets your last sentence. Steer it with a **system prompt** (the model never "
     "changes — the *context* does), then give it **memory**: the full history, replayed each turn — and it isn't free.",
     [("pages/1_1._Chatbot.py", "1 · Chatbot →"), ("pages/2_2._Memory.py", "2 · Memory →")]),
    ("Stop 2 · It will answer anything", "Dimension 3 · guardrails",
     "Your scoped assistant happily drifts off-task — that's liability. Add **layered guardrails**: a scoped "
     "prompt plus an **independent pre-flight check** that blocks a request before the main model runs. Try to sneak past it.",
     [("pages/3_3._Guardrails.py", "3 · Guardrails →")]),
    ("Stop 3 · Ground it — then break it", "Dimensions 4–5 · RAG + data access",
     "Fluent but **unverifiable** — and it knows nothing about *your* documents. Ground it: retrieve → cite → "
     "**abstain**. Then use the sliders to break it — chunking, stale docs, a permission leak — and watch quality "
     "collapse with the model untouched: most RAG failures are **data** failures.",
     [("pages/4_4._Grounding_and_RAG.py", "4 · Grounding & RAG →"),
      ("pages/5_5._Build_and_break_a_RAG.py", "5 · Build & break →")]),
    ("Stop 4 · It knows, but can't act", "Dimensions 7 & 9 · tools + approvals",
     "Grounded answers still leave a human doing the work. The **agent loop** — plan → call a tool → observe → "
     "repeat — lets the model *act*, with the irreversible write held at a **human approval gate**: approve, deny, "
     "or let it run autonomously.",
     [("pages/6_6._Tools_and_the_agent_loop.py", "6 · Tools & the agent loop →")]),
    ("Stop 5 · Agents over MCP + A2A ⛰️", "Dimensions 8, 10 & 11 · MCP + logging + governance",
     "One agent with welded-in tools = tight coupling and no least-privilege. The summit: **specialist agents "
     "coordinating over A2A**, reaching tools through a **real MCP server**, under **RBAC**, a human approval "
     "gate, and an audit log. Capability ≠ authorization.",
     [("pages/7_7._Multi-agent_and_governance.py", "7 · Multi-agent & governance →")]),
]

for stop, dims, desc, links in ROUTE:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{stop}**  \n🧭 *{dims}*  \n{desc}")
        with c2:
            for path, label in links:
                st.page_link(path, label=label)

st.divider()
st.markdown(
    "### 🎓 Homework — two applied cases (a category of their own)\n"
    "The five stops are the **concepts**. These two applications assemble those same concepts into a real "
    "tool — a **Canvas-ready quiz from your course materials** — two different ways. We'll discuss in the "
    "session *how* each one demonstrates what you just did; **exploring them is your homework**:\n\n"
    "- 🎓 **[Course Content Studio ↗](https://genai-workshop-labs-awybgq8gnmnrevxna2ukv3.streamlit.app/)** — "
    "the **hand-built** pipeline (Stops 1–3 writ large): real services — a real vector DB, a real database, a "
    "real MCP tool — wired together by you, with a required human review before anything exports. *Runs in your browser.*\n"
    "- 🤖 **[Autonomous Course-Builder ↗](https://github.com/prof-tcsmith/genai-workshop-labs/tree/main/course-builder)** — "
    "the **agentic** version (Stops 4–5 writ large): an orchestrator + specialist agents (Researcher / Item-writer / "
    "Critic / Exporter) assemble the same result themselves over **MCP**, under governance (approval gate + audit). "
    "*Run locally via Docker.*"
)

render_slides("overview", label="📊 Recap — the 7-layer stack (from the intro slides)", expanded=False)

with st.expander("The 7-layer stack (legend) / safety / session slides"):
    st.markdown("\n".join(f"- **{k}** — {v}" for k, v in STACK.items()))
    st.caption(
        "Note: layer 1 (*Experience*) is the **interface** — and it isn't necessarily human. Another "
        "system can call your app via API, or the app can expose itself **as an agent over A2A** that "
        "other agents call (Stop 5 shows agents as callers). Same layer, same trust requirements."
    )
    st.markdown(
        "Session slides: [Dimensions of GenAI (60-min deck) ↗](https://prof-tcsmith.github.io/genai-workshop-labs/day.html) · "
        "everything else: [the hub ↗](https://prof-tcsmith.github.io/genai-workshop-labs/)"
    )
    st.markdown(
        "---\nYour key stays in your browser session only. Demos use the cheap `gpt-4o-mini` model with "
        "capped output and a per-session request limit. Please don't paste sensitive data — shared key, teaching environment."
    )
