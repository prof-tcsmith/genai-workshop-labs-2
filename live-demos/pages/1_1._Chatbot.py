import streamlit as st

from shared.core import boot, layer_badge, stream_assistant
from shared.slides import render_slides

client = boot("1 · Chatbot")

st.title("1 · Chatbot")
layer_badge([1, 3])
st.caption("🧭 **Context engineering:** behavior lives in the context, not the weights.")
st.caption("A system prompt + one message. **No memory. No guardrails.** This is all a bare chatbot is.")
render_slides("chatbot")

st.info(
    "**ChatGPT is an *application*, not the model.** The LLM (here, `gpt-4o-mini`) is "
    "one layer *inside* an app. The app's job is to assemble a request and send it to "
    "that model. The simplest possible app is just **two messages**:\n\n"
    "- a **system prompt** — your standing instructions that set the model's role, tone, "
    "and rules (how you steer the model); and\n"
    "- a **user prompt** — what the person types this turn (the experience).\n\n"
    "Edit both below, hit Send, and open *“Exactly what is sent to the API”* — that "
    "tiny payload **is** the whole application. (The panel next to it shows what the "
    "*model* actually receives — they are not the same thing.)",
    icon="🧩",
)

sys = st.text_area("System prompt (how you steer the model)",
                   "You are a helpful, concise assistant.", height=80)
msg = st.text_input("Your message (the user prompt / the experience)",
                    "Explain what a system prompt is, in one sentence.")

if st.button("Send", type="primary"):
    messages = [{"role": "system", "content": sys}, {"role": "user", "content": msg}]
    with st.expander("Exactly what is sent to the API"):
        st.json(messages)
        st.caption(
            "This is the **API request** — the contract between your app and the provider. "
            "It is *not* what the model itself reads. Open the next panel for that."
        )
    with st.expander("…and what the **model** actually sees"):
        st.markdown(
            "The model never sees JSON, and there is no field called `role` inside it. "
            "Server-side, the provider flattens those messages into **one continuous token "
            "sequence** using a **chat template** — reserved special tokens mark where each "
            "turn begins and ends. Open-weight models publish their template; hosted models "
            "(`gpt-4o-mini`, Claude) apply their own internally. Illustrative, Llama-3 style:"
        )
        st.code(
            "<|begin_of_text|>"
            "<|start_header_id|>system<|end_header_id|>\n\n"
            f"{sys}<|eot_id|>"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            f"{msg}<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n",
            language="text",
        )
        st.markdown(
            "…and even that is a readable stand-in: the model consumes **token IDs**, not characters.\n\n"
            "**Why this matters later today**\n"
            "- **Roles are a convention, not a wall.** “System” is just text in a specially "
            "marked region of one stream — nothing physically stops the model from obeying "
            "instructions that arrive in *user* or *retrieved* text. That is why **prompt "
            "injection** works (Lab 2, and the red-team take-home).\n"
            "- **Memory isn't free.** Every turn re-serialises the whole history into this "
            "stream, and you pay for it in tokens on **every** call (that's the next lab).\n"
            "- **The context window is measured here** — in tokens of this stream, not in messages."
        )
    st.subheader("Response")
    stream_assistant(client, messages, placeholder=st.empty())
    st.warning(
        "**What's missing — memory.** Send another message and it won't recall this one; "
        "each request is independent. **➡️ Next — Memory.** "
        "(The later labs add guardrails, grounding, tools, and governance.)"
    )

st.divider()
st.caption("Try changing the system prompt (e.g., 'Answer only in haiku') and resend — the system prompt is the cheapest, fastest way to steer behavior.")
