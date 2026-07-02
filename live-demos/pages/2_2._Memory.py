"""Level 2 · Memory — a chatbot that remembers.

Versus Level 1 (a bare, stateless chatbot) this adds exactly ONE thing: MEMORY.
We keep the conversation in ``st.session_state`` and replay the FULL history
(plus the system prompt) on every turn, so the model can build on what was said
earlier. Level 1 sent only a single message.

What's still missing: there are NO guardrails — it's a general assistant that
will attempt anything, on any topic. Level 3 adds guardrails.
"""
import streamlit as st

from shared.core import boot, layer_badge, stream_assistant
from shared.slides import render_slides

client = boot("Level 2 · Memory")

st.title("Level 2 · Memory")
layer_badge([1, 3])
st.caption("🧭 **Dimension 2 of 11 — memory:** state = the history replayed each turn (and it isn't free).")
st.caption(
    "Add **memory**: the bot now **remembers the conversation**. We keep the history "
    "in session and replay all of it (plus the system prompt) every turn — so "
    "follow-ups just work. Level 1 sent only one message and forgot it instantly."
)
render_slides("memory")

system_prompt = st.text_area(
    "System prompt (Layer 3 — how you steer the model)",
    "You are a helpful, concise assistant.",
    height=70,
)
if st.button("🧹 Clear conversation"):
    st.session_state["mem_history"] = []
    st.rerun()

# This list IS the memory — Level 1 had none.
st.session_state.setdefault("mem_history", [])
history: list[dict] = st.session_state["mem_history"]

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

with st.expander("🧠 Memory — exactly what the model sees every turn"):
    st.caption(
        "The running history kept in `st.session_state`. On every turn we prepend "
        "the system prompt and send ALL of it — that's why it recalls earlier turns. "
        "Level 1 sent a single message with no history."
    )
    st.json([{"role": "system", "content": system_prompt}] + history)

st.divider()
st.warning(
    "**What's missing — guardrails.** This bot will answer *anything*, on *any* topic. "
    "Ask it something off-topic, out of scope, or unsafe and it happily complies — "
    "nothing keeps it on task. **➡️ Level 3 adds guardrails.**"
)
st.caption(
    "Try it: ask a question, then a follow-up like 'and how do I undo that?' — memory "
    "lets it follow along. Then ask something totally off-topic and watch it answer anyway."
)
