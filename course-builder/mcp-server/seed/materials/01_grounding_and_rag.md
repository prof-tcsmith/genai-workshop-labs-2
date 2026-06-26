# Grounding and Retrieval-Augmented Generation (RAG)

A large language model answers from its training data, which may be stale, generic,
or simply wrong for your organization. **Grounding** means forcing the model to
answer from *your* documents instead of its memory.

**Retrieval-Augmented Generation (RAG)** is the standard grounding pattern. It has
three steps:

1. **Retrieve** — embed the user's question as a vector and find the most similar
   chunks of your source documents using cosine similarity.
2. **Augment** — paste those retrieved chunks into the prompt as context.
3. **Generate** — instruct the model to answer using only that context, and to say
   "I don't have enough information" when the context does not contain the answer.

The quality of a RAG system depends far more on **retrieval quality** than on the
model. If the retriever returns the wrong chunks, even the best model will produce a
confident but ungrounded answer. Most RAG failures are therefore *data* failures:
poor chunking, stale documents, or missing content.

A grounded answer should **cite its source** so a human can verify it. Citations turn
an opaque answer into a checkable claim. An answer the system cannot ground should be
**refused** rather than guessed — abstention is the correct behavior when retrieval
confidence is low.
