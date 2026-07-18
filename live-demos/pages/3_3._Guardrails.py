"""Guardrails — keep the assistant on-task and safe.

Builds on Memory and adds exactly ONE thing: GUARDRAILS. The bot is
scoped to "Northwind Cloud" support, and every message passes a cheap,
INDEPENDENT pre-flight scope check BEFORE the main model runs. Two layers:
  1. a rule written into the system prompt (soft — a clever message can bypass it), and
  2. an independent classifier call that fails closed (a hard gate).

What's still missing: it stays on-task, but it only knows what's in its prompt —
no access to real product knowledge. Grounding with retrieval (RAG) comes next.
"""
import streamlit as st

from shared.core import boot, chat, layer_badge, stream_assistant
from shared.slides import render_slides

client = boot("3 · Guardrails")

st.title("3 · Guardrails")
layer_badge([1, 3, 7])
st.caption("🧭 **Guardrails:** an independent check before the answer ships.")
st.caption(
    "Add **guardrails** (governance) on top of memory: scope the bot to "
    "Northwind Cloud support and screen every message with an **independent check** "
    "before the main model runs, so it stays on-task and safe."
)
render_slides("guardrails")

# --- Guardrail 1: the narrow persona, written into the system prompt -----------
SYSTEM_PROMPT = (
    "You are the support assistant for 'Northwind Cloud', a SaaS product. "
    "You help ONLY with Northwind Cloud accounts, billing, features, and "
    "troubleshooting. Be concise and friendly. If a request is outside Northwind "
    "Cloud support, politely say it's out of scope. Never help with unsafe, "
    "illegal, or harmful requests."
)

# --- Guardrail 2: an INDEPENDENT scope check (a separate model call, not the prompt).
SCOPE_CHECK_PROMPT = (
    "You are a scope classifier for a Northwind Cloud support bot. "
    "Decide if the user message is about Northwind Cloud product "
    "support (accounts, billing, features, troubleshooting) AND is "
    "safe/benign. Answer with ONLY the single word 'yes' or 'no'."
)

# ════════════════════════ THE APP ════════════════════════
# Controls + conversation run uninterrupted; the explanation of what the
# guardrails *are* lives below, after the app.
st.markdown("##### ▶️ The app")
guardrails_on = st.toggle(
    "Guardrails ON",
    value=st.session_state.get("guardrails_on", True),
    key="guardrails_on",
    help="When ON, each message is screened for scope before the main model runs. "
         "Turn OFF to watch the same bot wander off-task.",
)
if st.button("🧹 Clear conversation"):
    st.session_state["gr_history"] = []
    st.rerun()

# Memory carries over from the previous lab's idea: we keep + replay the conversation.
st.session_state.setdefault("gr_history", [])
history: list[dict] = st.session_state["gr_history"]


def in_scope(user_msg: str) -> bool:
    """Cheap pre-flight guardrail: one tiny classification call (fail-closed)."""
    check_messages = [
        {"role": "system", "content": SCOPE_CHECK_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    verdict = chat(client, check_messages, max_tokens=3, temperature=0).choices[0].message.content
    return verdict.strip().lower().startswith("yes")


for turn in history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

prompt = st.chat_input("Ask about Northwind Cloud (accounts, billing, features) — or try something off-topic…")
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    blocked = False
    if guardrails_on:
        with st.spinner("Guardrail: checking scope…"):
            blocked = not in_scope(prompt)

    with st.chat_message("assistant"):
        if blocked:
            st.error("🚫 Guardrail blocked: off-topic — I can only help with Northwind Cloud support.")
            st.caption("Guardrail: 🚫 blocked — the scope check said out of scope, so the main model was never called.")
            answer = "🚫 Guardrail blocked: off-topic — I can only help with Northwind Cloud support."
        else:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
            answer, _ = stream_assistant(client, messages, placeholder=st.empty())
            st.caption("Guardrail: ✅ in scope" if guardrails_on
                       else "Guardrail: ⚠️ OFF — message answered without a scope check.")

    history.append({"role": "assistant", "content": answer})

# ═══════════════ CONCEPTS — what the guardrails actually are ═══════════════
st.markdown("##### 🛡️ Under the hood — what the guardrails actually are")
st.markdown(
    "**Two layers, not one.** A guardrail is *partly* a rule written into the system "
    "prompt — but that alone is **soft** (a clever message can talk the model out of it). "
    "So this demo also adds an **independent check** that runs *before* the main model."
)
st.markdown("**Guardrail 1 — a rule in the system prompt** (an instruction the model is asked to follow):")
st.code(SYSTEM_PROMPT, language="text")
st.markdown("**Guardrail 2 — an independent scope check** (a *separate* model call that runs first and can block the message before the main model ever sees it):")
st.code(SCOPE_CHECK_PROMPT, language="text")
st.caption(
    "Guardrail 1 is 'just a document in the prompt' — necessary but bypassable. Guardrail 2 is a "
    "separate, fail-closed gate. Production systems layer both, plus input/output filters, tool "
    "RBAC, and approval gates (see the agent-loop lab)."
)

st.divider()
st.warning(
    "**What's missing — real knowledge.** It stays on-task, but it only knows what's "
    "in its prompt; ask for a specific fact (your exact refund window, a feature detail) "
    "and it gets vague or guesses. **➡️ Next — Grounding & RAG puts it on real content.**"
)
st.caption(
    "Try it: ask a Northwind question, then a follow-up ('and how do I undo that?') — memory "
    "still works. Then ask something off-topic with guardrails ON vs OFF to see the gate fire."
)
