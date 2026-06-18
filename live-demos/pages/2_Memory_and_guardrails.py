"""Level 2 · Memory + guardrails — a NARROW support assistant.

Versus Level 1 (a bare chatbot) this page adds two visible things:
  1. MEMORY  — a multi-turn chat that keeps history in st.session_state and
     replays the FULL history (plus a system prompt) on every turn, so the
     model can use prior context.
  2. GUARDRAILS — the bot is scoped to "Northwind Cloud" product support only.
     A cheap pre-flight chat() call classifies each message as in/out of scope;
     off-topic (or unsafe) messages are blocked before the main model runs.
"""
import streamlit as st

from shared.core import boot, chat, layer_badge

client = boot("Level 2 · Memory + guardrails")

st.title("Level 2 · Memory + guardrails")
layer_badge([1, 3, 7])
st.caption(
    "A **narrow** Northwind Cloud support assistant. Unlike Level 1 it **remembers** "
    "the conversation (Layer 1 experience + Layer 3 model) and is **scoped by a "
    "guardrail** (Layer 7 governance) so it stays on-task."
)

# --- The narrow persona (Layer 3): this is what makes the bot "narrow". --------
SYSTEM_PROMPT = (
    "You are the support assistant for 'Northwind Cloud', a SaaS product. "
    "You help ONLY with Northwind Cloud accounts, billing, features, and "
    "troubleshooting. Be concise and friendly. If a request is outside Northwind "
    "Cloud support, politely say it's out of scope. Never help with unsafe, "
    "illegal, or harmful requests."
)

# --- Controls -----------------------------------------------------------------
guardrails_on = st.toggle(
    "Guardrails ON",
    value=st.session_state.get("guardrails_on", True),
    key="guardrails_on",
    help="When ON, each message is screened for scope before the main model runs. "
         "Turn OFF to watch the bot wander off-task.",
)
if st.button("🧹 Clear conversation"):
    st.session_state["history"] = []
    st.rerun()

# Running conversation history lives here: a list of {"role", "content"}.
# This IS the memory — Level 1 had none.
st.session_state.setdefault("history", [])
history: list[dict] = st.session_state["history"]


def in_scope(user_msg: str) -> bool:
    """Cheap pre-flight guardrail: one tiny classification call.

    Asks the model a yes/no question and treats anything that isn't a clear
    'yes' as out of scope (fail-closed)."""
    check_messages = [
        {
            "role": "system",
            "content": (
                "You are a scope classifier for a Northwind Cloud support bot. "
                "Decide if the user message is about Northwind Cloud product "
                "support (accounts, billing, features, troubleshooting) AND is "
                "safe/benign. Answer with ONLY the single word 'yes' or 'no'."
            ),
        },
        {"role": "user", "content": user_msg},
    ]
    # Tiny + deterministic: this check should be cheap and stable.
    verdict = chat(client, check_messages, max_tokens=3, temperature=0).choices[0].message.content
    return verdict.strip().lower().startswith("yes")


# --- Render the conversation so far -------------------------------------------
for turn in history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

# --- Handle a new message -----------------------------------------------------
prompt = st.chat_input("Ask about Northwind Cloud (accounts, billing, features, troubleshooting)…")
if prompt:
    # Echo + store the user's turn immediately so it shows and is remembered.
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    blocked = False
    if guardrails_on:
        with st.spinner("Guardrail: checking scope…"):
            blocked = not in_scope(prompt)

    with st.chat_message("assistant"):
        if blocked:
            # Guardrail fired: do NOT call the main model.
            st.error("🚫 Guardrail blocked: off-topic — I can only help with Northwind Cloud support.")
            st.caption("Guardrail: 🚫 blocked — the scope check said this is out of scope, so the main model was never called.")
            answer = "🚫 Guardrail blocked: off-topic — I can only help with Northwind Cloud support."
        else:
            # MEMORY in action: send the system prompt + the FULL history so the
            # answer can build on everything said earlier this session.
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
            answer = chat(client, messages).choices[0].message.content
            st.markdown(answer)
            if guardrails_on:
                st.caption("Guardrail: ✅ in scope")
            else:
                st.caption("Guardrail: ⚠️ OFF — message answered without a scope check.")

    # Store the assistant's turn so it becomes part of the memory next turn.
    history.append({"role": "assistant", "content": answer})

# --- Teaching aids ------------------------------------------------------------
with st.expander("🧠 Memory (what the model sees)"):
    st.caption(
        "This is the running history kept in `st.session_state`. On every turn we "
        "prepend the system prompt and send ALL of it — that's why the bot can "
        "recall earlier messages. Level 1 sent only a single message."
    )
    st.json([{"role": "system", "content": SYSTEM_PROMPT}] + history)

st.divider()
st.caption(
    "Try it: ask a Northwind question, then a follow-up like 'and how do I undo that?' — "
    "memory lets it follow along. Then ask something off-topic (e.g. 'write me a poem') "
    "with guardrails ON vs OFF to see the difference."
)
