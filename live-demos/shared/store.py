"""In-memory document store + retrieval (OpenAI embeddings + NumPy cosine).

Shared by Level 3 (context engineering) and Level 4 (a search_kb tool).
No external vector DB — fits in RAM at demo scale.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .core import EMBED_MODEL, openai_guard

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
    try:
        r = client.embeddings.create(model=EMBED_MODEL, input=texts)
    except Exception as e:
        openai_guard(e)  # friendly message + st.stop()
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


def search(client, index: dict, query: str, k: int = 4) -> list[tuple[dict, float]]:
    if not index.get("items"):
        return []
    v = embed(client, [query])[0]
    scores = index["matrix"] @ v
    order = np.argsort(-scores)[:k]
    return [(index["items"][i], float(scores[i])) for i in order]
