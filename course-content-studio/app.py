"""Course Content Studio — home / story page.

Tells the build-to-application story, shows what's configured, and links the labs.
The same 7-layer stack as the live demos — but built up into a real professor tool.
"""
import streamlit as st

st.set_page_config(page_title="Course Content Studio", page_icon="🎓", layout="wide")

from lib.config import gate  # noqa: E402  (must come after set_page_config)

gate()

from lib import config  # noqa: E402
from lib.ui import render_deck  # noqa: E402

st.title("🎓 Course Content Studio — from chunks to a course tool")
st.markdown(
    "This track builds a **real professor tool** on the *same 7-layer stack* as the live demos. "
    "Every lab adds one real piece — a model that guesses → ground it in **your** documents "
    "(a real vector DB) → join **authoritative** facts (a real database) → notice the app is "
    "welded to its tools → **decouple them with MCP** → assemble it all into **Course Content "
    "Studio**: upload your course materials, generate quizzes & assignments grounded in them, and "
    "export a **Canvas-importable QTI package**. We wire the whole pipeline *by hand* — the perfect "
    "\"before\" picture for next session's autonomy & agents."
)

st.caption(
    "◀ New here? Start with **[Enterprise AI — the building blocks ↗](https://muma-genai.streamlit.app/)** "
    "(chatbot → memory → guardrails → grounding & RAG → build & break a RAG → tools & the agent loop → "
    "multi-agent & governance → red-team) — the concepts this capstone is built on and extends."
)

# The story deck — start here.
render_deck("overview-ccs", label="📊 Start here — the build-to-application story", expanded=True)

# --- What's configured -----------------------------------------------------
st.subheader("What's configured")
st.caption(
    "Live status of the services this app talks to. **Running locally?** Paste keys in the "
    "**🔌 Connections** sidebar. **Deployed?** Set them in Streamlit **Secrets**."
)
status = config.configured()
cols = st.columns(len(status))
for col, (label, ok) in zip(cols, status.items()):
    col.markdown(f"{'✅' if ok else '⬜'} **{label}**")
    col.caption("ready" if ok else "not set")
st.caption("MCP tools run **in-process** by default — no separate server to configure.")
if not all(status.values()):
    st.info(
        "Greyed-out services aren't wired up yet. Paste keys in the 🔌 Connections sidebar, or see "
        "**SETUP.md** (Pinecone + Neon, free tiers) and **FACILITATOR.md** for the full checklist.",
        icon="🛠️",
    )

# --- Navigation ------------------------------------------------------------
st.subheader("The labs — in order")
st.caption("Each lab has an interactive concept deck (architecture + cool feature → shortcoming → next).")

nav = [
    ("pages/1_RAG_with_Pinecone.py", "1 · RAG with Pinecone",
     "Ingest, chunk & embed your docs → cosine search on a real vector DB → grounded, cited answers."),
    ("pages/2_Structured_lookup_PG.py", "2 · Structured lookup (Postgres)",
     "Query authoritative structured facts — objectives, rubrics, a reusable question bank."),
    ("pages/3_The_coupling_problem.py", "3 · The coupling problem",
     "See the app welded to each tool's SDK, creds and shape — brittle and unshareable."),
    ("pages/4_MCP_decoupled_tools.py", "4 · MCP — decouple the tools",
     "Re-expose vector search + Postgres lookup as MCP tools the app (or any agent) calls over one protocol."),
    ("pages/5_Course_Content_Studio.py", "5 · Capstone: Course Content Studio",
     "Upload PDF/PPTX/HTML/MD → generate grounded quizzes & assignments → export Canvas QTI .zip."),
    ("pages/6_Whats_next_agents.py", "6 · What's next — autonomy & agents",
     "We built it by hand. Next session: agents + harnesses that plan and assemble pipelines themselves."),
]
for path, label, desc in nav:
    st.page_link(path, label=f"**{label}**", icon="➡️")
    st.caption(desc)

# --- About / safety --------------------------------------------------------
with st.expander("ℹ️ About & safety"):
    st.markdown(
        "- **Shared workshop keys.** This app uses workshop-provided API keys and a shared "
        "participant code — please don't redistribute them.\n"
        "- **Participant-gated.** Access is limited to workshop attendees via a participant code.\n"
        "- **Don't paste sensitive data.** Treat anything you upload or type as if a third-party "
        "LLM and vector DB will see it — use sample or non-confidential course materials only.\n"
        "- **Generated content needs review.** Every quiz/assignment item is a draft: review, "
        "edit, and approve before you export or use it. Nothing exports until you approve it.\n"
        "- **Same governance ideas as the demos:** grounded-only generation, source citations, "
        "confidence flags, and human-in-the-loop sign-off (Layer 7)."
    )
