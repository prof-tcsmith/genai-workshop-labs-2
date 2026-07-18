"""Grounding & RAG.

Teaching point: the same model, same question — answered from the MODEL ALONE
vs. GROUNDED on retrieved chunks. Ungrounded answers are fluent but unverifiable
(and can hallucinate). Grounded answers cite the snippet/doc they came from, so
you can check them. Quality comes from the context you assemble, not cleverness.
"""
import streamlit as st

from shared import store
from shared.core import boot, layer_badge, stream_assistant, try_this
from shared.slides import render_slides

client = boot("4 · Grounding & RAG")

st.title("4 · Grounding & RAG")
layer_badge([3, 4, 6])
st.caption("🧭 **Retrieval-augmented generation (RAG):** retrieve → cite → abstain.")
st.caption(
    "Retrieve the right snippets from a small information store, "
    "then **ground** the model on them. Compare the model answering alone "
    "vs. grounded + cited — same question, very different trust."
)
render_slides("grounding-rag")

# --- 1. Pick the documents to put in the store, then build the index (cached) ---
STEMS = ["refund_policy", "support_kb", "hr_leave_policy", "security_notes_RESTRICTED"]
st.markdown("##### ▶️ The app")
picked = st.multiselect(
    "Documents in the store", STEMS, default=["refund_policy", "support_kb"],
    help="Only these docs can be retrieved. The model has no other source of truth.",
)
if not picked:
    st.info("Pick at least one document to build the store.")
    st.stop()

key = "rag_index_" + "_".join(sorted(picked))
if key not in st.session_state:
    docs = store.load_corpus(names=picked)
    if not docs:
        st.error("No corpus found at shared/corpus/.")
        st.stop()
    with st.spinner("Building the information store (embedding the corpus once)…"):
        st.session_state[key] = store.build_index(client, docs)
index = st.session_state[key]
st.caption(f"📚 Store ready: **{len(index['items'])} chunks** from {len(picked)} document(s).")

# --- 2. The question + how many chunks to retrieve ---
question = st.text_input(
    "Question", "How long do I have to get a refund as an enterprise customer?",
)
top_k = st.slider("Top-k chunks to retrieve", 1, 6, 3,
                  help="How many of the most-similar chunks we ground the model on.")

if st.button("Answer both ways", type="primary") and question.strip():
    q = question.strip()

    # --- 3. Retrieve top-k chunks and show them transparently ---
    hits = store.search(client, index, q, k=top_k)
    with st.expander(f"🔎 Retrieved chunks — top {len(hits)} (cosine similarity)", expanded=True):
        if not hits:
            st.write("No chunks retrieved.")
        for i, (item, score) in enumerate(hits, start=1):
            st.markdown(f"**{i}. `{item['doc']}`** · score `{score:.3f}`")
            st.write(item["text"])

    # --- 4. Build the grounded prompt (forces use-context + citation) ---
    context = "\n\n".join(
        f"[chunk {i} · source: {it['doc']}]\n{it['text']}" for i, (it, _) in enumerate(hits, start=1)
    ) or "(no chunks retrieved)"
    grounded_messages = [
        {"role": "system", "content":
            "Answer ONLY from the context below. Cite the source doc(s) you used in "
            "brackets, e.g. [refund_policy]. If the answer is not in the context, say "
            "you don't know — do not guess."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q}"},
    ]
    ungrounded_messages = [
        {"role": "system", "content": "You are a helpful support assistant. Answer concisely."},
        {"role": "user", "content": q},
    ]

    # --- 5. Two answers side by side: model alone vs. grounded + cited ---
    col_u, col_g = st.columns(2)
    with col_u:
        st.subheader("⚠️ Model alone (ungrounded)")
        stream_assistant(client, ungrounded_messages, placeholder=st.empty())
        st.caption("Fluent but **unverifiable** — guessing from training data, no link to your policy.")
    with col_g:
        st.subheader("✅ Grounded on retrieved chunks")
        stream_assistant(client, grounded_messages, placeholder=st.empty())
        st.caption("Drawn from — and **citing** — the chunks above. You can check every claim.")

try_this(
    "Run the default question and read the two columns side by side. The left one *sounds* just "
    "as confident — but only the right one can be checked against a source.",
    "Ask something the corpus cannot answer: **“What is the CEO's mobile number?”** The grounded "
    "side should **abstain**; watch whether the ungrounded side invents something.",
    "Drop **Top-k** to 1 and re-ask the refund question. If the rule was split across chunks, the "
    "answer quietly loses the detail — retrieval, not the model, decided that.",
    "Remove **refund_policy** from the store and re-ask. The grounded answer should now say it "
    "doesn't know. *Abstaining is engineered* — it comes from the instruction plus the missing "
    "context, not from the model being humble.",
)

st.warning(
    "**What's missing — retrieval quality depends on your data + pipeline.** Bad chunking "
    "or stale/leaky sources silently wreck the answer. **➡️ Next — Build & break a RAG.** "
    "shows exactly how."
)
