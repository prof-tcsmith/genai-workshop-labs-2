"""Memory — a chatbot that remembers.

Versus the bare, stateless Chatbot this adds exactly ONE thing: MEMORY.
We keep the conversation in ``st.session_state`` and replay the FULL history
(plus the system prompt) on every turn, so the model can build on what was said
earlier. The bare Chatbot sent only a single message.

What's still missing: there are NO guardrails — it's a general assistant that
will attempt anything, on any topic. Guardrails come next.
"""
import streamlit as st

from shared.core import boot, layer_badge, stream_assistant, try_this
from shared.slides import render_slides

client = boot("2 · Memory")

st.title("2 · Memory")
layer_badge([1, 3])
st.caption("🧭 **Memory:** state = the history replayed each turn (and it isn't free).")
st.caption(
    "Add **memory**: the bot now **remembers the conversation**. We keep the history "
    "in session and replay all of it (plus the system prompt) every turn — so "
    "follow-ups just work. The bare Chatbot sent only one message and forgot it instantly."
)
render_slides("memory")

# ════════════════════════ THE APP ════════════════════════
# System prompt → the conversation → the reset. One uninterrupted unit; the
# memory panel and the experiments come after it.
st.markdown("##### ▶️ The app")

# This list IS the memory — the bare Chatbot had none.
st.session_state.setdefault("mem_history", [])
history: list[dict] = st.session_state["mem_history"]

app = st.container(border=True)
with app:
    system_prompt = st.text_area(
        "System prompt (how you steer the model)",
        "You are a helpful, concise assistant.",
        height=70,
    )

    # Render the conversation so far.
    for turn in history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    prompt = st.chat_input("Chat — then ask a follow-up that refers back to what you said…")
    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            # MEMORY in action: send the system prompt + the FULL history every turn.
            messages = [{"role": "system", "content": system_prompt}] + history
            answer, _ = stream_assistant(client, messages, placeholder=st.empty())
        history.append({"role": "assistant", "content": answer})

    # Reset lives at the bottom of the app, out of the way of the conversation.
    if st.button("🧹 Clear conversation"):
        st.session_state["mem_history"] = []
        st.rerun()

# ═══════════════ CONCEPTS — the memory itself ═══════════════
st.markdown("##### 🧠 Memory — exactly what's re-sent to the API every turn")
st.caption(
    "The running history kept in `st.session_state`. On every turn we prepend "
    "the system prompt and send ALL of it — that's why it recalls earlier turns. "
    "The bare Chatbot sent a single message with no history."
)
st.json([{"role": "system", "content": system_prompt}] + history)

try_this(
    "Tell it **“My name is Dana and I manage the Tampa team.”** Then ask **“What's my name?”** "
    "It remembers — not because the model learned anything, but because your last message *and* "
    "that one are both re-sent.",
    "Ask a follow-up with a pronoun: **“How big is that team?”** Watch it resolve *that* from "
    "the history. This is the whole difference from Lab 1.",
    "After a few turns, watch the memory panel above **grow**. Every turn re-sends the entire "
    "conversation — that is what memory costs you, on every single call.",
    "Hit **🧹 Clear conversation** at the bottom of the app, then ask **“What's my name?”** "
    "again. Gone. The “memory” was only ever that list.",
)

st.divider()
st.warning(
    "**What's missing — guardrails.** This bot will answer *anything*, on *any* topic. "
    "Ask it something off-topic, out of scope, or unsafe and it happily complies — "
    "nothing keeps it on task. **➡️ Next — Guardrails.**"
)
st.caption(
    "Try it: ask a question, then a follow-up like 'and how do I undo that?' — memory "
    "lets it follow along. Then ask something totally off-topic and watch it answer anyway."
)
