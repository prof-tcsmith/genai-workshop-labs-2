import streamlit as st

from shared.core import boot, layer_badge, stream_assistant
from shared.slides import render_slides

client = boot("Level 1 · Chatbot")

st.title("Level 1 · Chatbot")
layer_badge([1, 3])
st.caption("A system prompt + one message. **No memory. No guardrails.** This is all a bare chatbot is.")
render_slides("chatbot")

st.info(
    "**ChatGPT is an *application*, not the model.** The LLM (here, `gpt-4o-mini`) is "
    "one layer *inside* an app. The app's job is to assemble a request and send it to "
    "that model. The simplest possible app is just **two messages**:\n\n"
    "- a **system prompt** — your standing instructions that set the model's role, tone, "
    "and rules (Layer 3, how you steer the model); and\n"
    "- a **user prompt** — what the person types this turn (Layer 1, the experience).\n\n"
    "Edit both below, hit Send, and open *“Exactly what is sent to the model”* — that "
    "tiny payload **is** the whole application.",
    icon="🧩",
)

sys = st.text_area("System prompt (Layer 3 — how you steer the model)",
                   "You are a helpful, concise assistant.", height=80)
msg = st.text_input("Your message (Layer 1 — the user prompt / the experience)",
                    "Explain what a system prompt is, in one sentence.")

if st.button("Send", type="primary"):
    messages = [{"role": "system", "content": sys}, {"role": "user", "content": msg}]
    with st.expander("Exactly what is sent to the model"):
        st.json(messages)
    st.subheader("Response")
    stream_assistant(client, messages, placeholder=st.empty())
    st.warning(
        "**What's missing — memory.** Send another message and it won't recall this one; "
        "each request is independent. **➡️ Level 2 adds memory.** "
        "(Levels 2–6 then add memory, guardrails, grounding, tools, and governance.)"
    )

st.divider()
st.caption("Try changing the system prompt (e.g., 'Answer only in haiku') and resend — the system prompt is the cheapest, fastest way to steer behavior.")
