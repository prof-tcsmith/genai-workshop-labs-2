import streamlit as st

from shared.core import boot, chat, layer_badge

client = boot("Level 1 · Chatbot")

st.title("Level 1 · Chatbot")
layer_badge([1, 3])
st.caption("A system prompt + one message. **No memory. No guardrails.** This is all a bare chatbot is.")

sys = st.text_area("System prompt (Layer 3 — how you steer the model)",
                   "You are a helpful, concise assistant.", height=80)
msg = st.text_input("Your message (Layer 1 — the experience)",
                    "Explain what a system prompt is, in one sentence.")

if st.button("Send", type="primary"):
    messages = [{"role": "system", "content": sys}, {"role": "user", "content": msg}]
    with st.expander("Exactly what is sent to the model"):
        st.json(messages)
    ans = chat(client, messages).choices[0].message.content
    st.subheader("Response")
    st.write(ans)
    st.warning(
        "**No memory** — send another message and it won't recall this one. "
        "**No guardrails** — it will attempt whatever the prompt allows. "
        "Levels 2–5 add memory, guardrails, grounding, tools, and governance."
    )

st.divider()
st.caption("Try changing the system prompt (e.g., 'Answer only in haiku') and resend — the system prompt is the cheapest, fastest way to steer behavior.")
