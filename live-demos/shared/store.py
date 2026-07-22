"""In-memory document store + retrieval (OpenAI embeddings + NumPy cosine).

Shared by the Guardrails and Grounding/RAG demos (a search_kb tool).
No external vector DB — fits in RAM at demo scale.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import streamlit as st

from .core import api_guard

CORPUS = Path(__file__).resolve().parent / "corpus"


def load_corpus(names: list[str] | None = None) -> dict[str, str]:
    docs: dict[str, str] = {}
    if not CORPUS.exists():
        return docs
    for p in sorted(CORPUS.glob("*.md")):
        if names and p.stem not in names:
            continue
        docs[p.stem] = p.read_text(encoding="utf-8")
    return docs


def chunk(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = text.strip()
    step = max(1, size - overlap)
    out, i = [], 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            out.append(piece)
        i += step
    return out


def embed(client, texts: list[str]) -> np.ndarray:
    if client.embed_raw is None:
        st.error(
            "🔢 Embeddings need an OpenAI API key. Anthropic has **no embeddings API**, "
            "so the RAG demos use OpenAI embeddings even when chat runs on Claude — set "
            "`OPENAI_API_KEY` (or paste an OpenAI key with the provider set to OpenAI)."
        )
        st.stop()
    try:
        r = client.embed_raw.embeddings.create(model=client.embed_model, input=texts)
    except Exception as e:
        api_guard(e)  # friendly message + st.stop()
    m = np.array([d.embedding for d in r.data], dtype=np.float32)
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


def build_index(client, docs: dict[str, str], size: int = 600, overlap: int = 100) -> dict:
    items = []
    for name, text in docs.items():
        for c in chunk(text, size, overlap):
            items.append({"doc": name, "text": c})
    if not items:
        return {"items": [], "matrix": np.zeros((0, 1), dtype=np.float32)}
    return {"items": items, "matrix": embed(client, [it["text"] for it in items])}


def render_doc_viewer(docs: dict[str, str], *, label: str = "📄 View the documents in the store") -> None:
    """Click-to-expand panel: the full source text the model grounds on.

    Participants ground answers on these docs but otherwise can't read them, so
    they can't check a "cited" answer against its source. This shows them.
    """
    if not docs:
        return
    n = len(docs)
    with st.expander(f"{label}  ·  {n} document{'s' if n != 1 else ''}"):
        st.caption(
            "This is the model's **only** source of truth. A grounded answer must trace "
            "back to text you can read right here — that's what makes it checkable."
        )
        for name, text in docs.items():
            restricted = "RESTRICTED" in name
            st.markdown(
                f"**📄 `{name}.md`**"
                + ("  🔒 *restricted — normally should never reach a user*" if restricted else "")
            )
            st.code(text.strip(), language="markdown", wrap_lines=True)


def search(client, index: dict, query: str, k: int = 4) -> list[tuple[dict, float]]:
    if not index.get("items"):
        return []
    v = embed(client, [query])[0]
    scores = index["matrix"] @ v
    order = np.argsort(-scores)[:k]
    return [(index["items"][i], float(scores[i])) for i in order]
