import streamlit as st

from shared.core import render_key_sidebar, render_route_sidebar, ensure_access, STACK
from shared.slides import render_slides

st.set_page_config(page_title="Enterprise AI — the building blocks", page_icon="🧱", layout="wide")
ensure_access()
render_route_sidebar()
render_key_sidebar()

st.title("🧱 Today's route — five labs")
st.write(
    "The intro slides gave you the **goals**, the **7-layer stack**, and the **eleven dimensions**. "
    "This app is where the journey happens: **five labs**, each demonstrating its dimensions **live** — "
    "and each lab opens by *breaking* the one before it. "
    "Pick a provider and paste the workshop key in the sidebar, then start at **Lab 1**."
)

if st.session_state.get("key"):
    st.success("Key connected — start at **Lab 1** below (or in the sidebar).")
else:
    st.info("⬅️ Pick a provider and paste the workshop key in the sidebar to begin.")

# The five labs of the 60-minute hands-on hour. Each lab = a problem the
# previous lab just created: forgets → answers anything → can't prove it →
# can't act → can't govern the actor.
ROUTE = [
    ("Lab 1 · A model becomes an app", "Dimensions 1–2 · context + memory",
     "The bare model forgets your last sentence. Steer it with a **system prompt** (the model never "
     "changes — the *context* does), then give it **memory**: the full history, replayed each turn — and it isn't free.",
     [("pages/1_1._Chatbot.py", "1 · Chatbot →"), ("pages/2_2._Memory.py", "2 · Memory →")]),
    ("Lab 2 · It will answer anything", "Dimension 3 · guardrails",
     "Your scoped assistant happily drifts off-task — that's liability. Add **layered guardrails**: a scoped "
     "prompt plus an **independent pre-flight check** that blocks a request before the main model runs. Try to sneak past it.",
     [("pages/3_3._Guardrails.py", "3 · Guardrails →")]),
    ("Lab 3 · Ground it — then break it", "Dimensions 4–5 · RAG + data access",
     "Fluent but **unverifiable** — and it knows nothing about *your* documents. Ground it: retrieve → cite → "
     "**abstain**. Then use the sliders to break it — chunking, stale docs, a permission leak — and watch quality "
     "collapse with the model untouched: most RAG failures are **data** failures.",
     [("pages/4_4._Grounding_and_RAG.py", "4 · Grounding & RAG →"),
      ("pages/5_5._Build_and_break_a_RAG.py", "5 · Build & break →")]),
    ("Lab 4 · It knows, but can't act", "Dimensions 7 & 9 · tools + approvals",
     "Grounded answers still leave a human doing the work. The **agent loop** — plan → call a tool → observe → "
     "repeat — lets the model *act*, with the irreversible write held at a **human approval gate**: approve, deny, "
     "or let it run autonomously.",
     [("pages/6_6._Tools_and_the_agent_loop.py", "6 · Tools & the agent loop →")]),
    ("Lab 5 · Agents over MCP + A2A ⛰️", "Dimensions 8, 10 & 11 · MCP + logging + governance",
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
    "### 🎓 The Case — one agentic system that assembles all five labs\n"
    "The five labs are the **concepts**. The **Case** puts them together into a real agentic workflow — "
    "**Prior-Authorization Triage**: an orchestrator + specialist agents decide a *synthetic* coverage request "
    "against policy, **grounded in retrieval**, **judged by an LLM critic**, and **governed by a human approval "
    "gate + an audit log**. We demo it live; **running it yourself is your homework**.\n\n"
    "- 🏥 **[Prior-Authorization Triage ↗](https://github.com/prof-tcsmith/genai-workshop-labs/tree/main/prior-auth-agent)** — "
    "specialist agents over **A2A + a real MCP server**, RAG-grounded, with a human approval gate + audit. Runs locally "
    "via **Docker** (only an OpenAI key). *Synthetic data — a demonstration of AI system architecture, not medical advice.*"
)

render_slides("overview", label="📊 Recap — the 7-layer stack (from the intro slides)", expanded=False)

with st.expander("The 7-layer stack (legend) / safety / session slides"):
    st.markdown("\n".join(f"- **{k}** — {v}" for k, v in STACK.items()))
    st.caption(
        "Note: layer 1 (*Experience*) is the **interface** — and it isn't necessarily human. Another "
        "system can call your app via API, or the app can expose itself **as an agent over A2A** that "
        "other agents call (Lab 5 shows agents as callers). Same layer, same trust requirements."
    )
    st.markdown(
        "Session slides: [GenAI Day slides (60-min deck) ↗](https://prof-tcsmith.github.io/genai-workshop-labs/day.html) · "
        "everything else: [the hub ↗](https://prof-tcsmith.github.io/genai-workshop-labs/)"
    )
    st.markdown(
        "---\nYour key stays in your browser session only. Demos use the cheap `gpt-4o-mini` model with "
        "capped output and a per-session request limit. Please don't paste sensitive data — shared key, teaching environment."
    )
