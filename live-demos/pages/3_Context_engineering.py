"""Level 3 · Context engineering + information store (RAG).

Teaching point: the *answer* is only as good as the *context you assemble*.
We retrieve relevant chunks, then EXPLICITLY build the prompt around them so
participants can SEE how grounded context is engineered — and contrast it with
the same model asked the same question with no retrieval at all.
"""
import streamlit as st

from shared import store
from shared.core import boot, layer_badge, stream_assistant
from shared.slides import render_slides

client = boot("Level 3 · Context engineering")

st.title("Level 3 · Context engineering (RAG)")
layer_badge([3, 4, 6])
st.caption(
    "Retrieve the right snippets (Layer 4) from a small information store (Layer 6), "
    "then **engineer the prompt** around them (Layer 3). The model answers from what "
    "you give it — so context, not cleverness, drives quality."
)
render_slides("context")

# --- 1. Information store: load corpus + build the index ONCE, cached in session ---
# Building the index calls the embeddings API once; we guard so reruns reuse it.
if "ctx_index" not in st.session_state:
    docs = store.load_corpus(["support_kb", "refund_policy"])
    if not docs:
        st.error("No corpus found at shared/corpus/. Expected support_kb.md and refund_policy.md.")
        st.stop()
    with st.spinner("Building the information store (embedding the corpus once)…"):
        st.session_state["ctx_index"] = store.build_index(client, docs)
index = st.session_state["ctx_index"]
st.caption(
    f"📚 Store ready: **{len(index['items'])} chunks** from "
    f"{len(set(it['doc'] for it in index['items']))} document(s)."
)

# --- 2. The question + how many chunks to retrieve ---
question = st.text_input(
    "Question",
    "How long do I have to get a refund as an enterprise customer?",
)
top_k = st.slider("Top-k chunks to retrieve", 1, 6, 3,
                  help="How many of the most-similar chunks we feed the model.")
show_ungrounded = st.checkbox(
    "Also show the ungrounded answer (no retrieval)",
    help="Ask the same model the same question with NO context, for contrast.",
)

run = st.button("Retrieve & answer", type="primary")

# --- Prompt-engineering helpers ----------------------------------------------
# The system instruction is the heart of context engineering: it tells the model
# to stay inside the retrieved context and to cite the source document.
SYSTEM_INSTRUCTION = (
    "You are a precise support assistant. "
    "Answer ONLY from the context below. Cite the source doc in brackets, e.g. [refund_policy]. "
    "If the answer is not present in the context, say you don't know — do not guess."
)


def build_context_block(hits) -> str:
    """Wrap retrieved snippets into a single, clearly-delimited context string."""
    blocks = []
    for i, (item, score) in enumerate(hits, start=1):
        blocks.append(
            f"[Snippet {i} | source: {item['doc']} | similarity: {score:.3f}]\n{item['text']}"
        )
    return "\n\n".join(blocks) if blocks else "(no snippets retrieved)"


if run and question.strip():
    # --- 3. Retrieve top-k chunks and show them transparently ---
    hits = store.search(client, index, question, k=top_k)
    with st.expander(f"🔎 Retrieved context — top {len(hits)} chunk(s)", expanded=True):
        if not hits:
            st.write("No chunks retrieved.")
        for i, (item, score) in enumerate(hits, start=1):
            st.markdown(f"**{i}. `{item['doc']}`** · cosine similarity `{score:.3f}`")
            st.write(item["text"])
            if i < len(hits):
                st.divider()

    # --- 4. CONTEXT ENGINEERING: assemble the exact prompt and SHOW it ---
    context_block = build_context_block(hits)
    user_content = (
        f"Context:\n{context_block}\n\n"
        f"Question: {question.strip()}\n\n"
        "Answer using only the context above, and cite the source doc(s)."
    )
    grounded_messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_content},
    ]
    with st.expander("🧩 The engineered prompt (exactly what we send the model)"):
        st.caption(
            "This is the teaching point: retrieval gives us snippets, but *we* decide "
            "how to frame them. The instructions force grounding + citation."
        )
        st.json(grounded_messages)

    # --- 5. Grounded, cited answer (streamed) ---
    if show_ungrounded:
        # --- 6. Contrast: same question, NO retrieved context ---
        ungrounded_messages = [
            {"role": "system", "content": "You are a helpful support assistant."},
            {"role": "user", "content": question.strip()},
        ]
        col_g, col_u = st.columns(2)
        with col_g:
            st.subheader("✅ Grounded (with retrieval)")
            stream_assistant(client, grounded_messages, placeholder=st.empty())
        with col_u:
            st.subheader("⚠️ Ungrounded (no retrieval)")
            stream_assistant(client, ungrounded_messages, placeholder=st.empty())
        st.caption(
            "Notice the difference: the grounded answer cites the source and uses the "
            "**enterprise-specific** policy; the ungrounded one tends to be vague, generic, "
            "or confidently wrong (it has no access to Northwind's actual policy)."
        )
    else:
        st.subheader("✅ Grounded answer")
        stream_assistant(client, grounded_messages, placeholder=st.empty())
        st.caption(
            "The answer is drawn from — and cites — the retrieved snippets above. "
            "Tick the box to see how the same model answers with no context."
        )

elif run:
    st.warning("Enter a question first.")

st.divider()
st.info(
    "**Takeaway: retrieval quality dominates output quality.** A great model on the wrong "
    "snippets gives a confident wrong answer. Better chunks + a tighter engineered prompt "
    "beat a bigger model almost every time."
)
