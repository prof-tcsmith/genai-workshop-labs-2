"""In-memory retrieval: chunk -> embed (OpenAI) -> cosine search over NumPy.

No external vector DB. At workshop corpus size this fits comfortably in RAM,
which keeps the labs free to host and free of extra keys.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .llm import EMBED_MODEL, openai_guard

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_corpus(names: list[str] | None = None) -> dict[str, str]:
    """Load markdown docs from ../data. `names` filters by file stem."""
    docs: dict[str, str] = {}
    if not DATA_DIR.exists():
        return docs
    for p in sorted(DATA_DIR.glob("*.md")):
        if names and p.stem not in names:
            continue
        docs[p.stem] = p.read_text(encoding="utf-8")
    return docs


def chunk_text(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = text.strip()
    if size <= 0:
        size = 1
    overlap = max(0, min(overlap, size - 1))
    step = max(1, size - overlap)
    out = []
    i = 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            out.append(piece)
        i += step
    return out


def embed_texts(client, texts: list[str]) -> np.ndarray:
    try:
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    except Exception as e:
        openai_guard(e)  # friendly message + st.stop()
    return np.array([d.embedding for d in resp.data], dtype=np.float32)


def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


def build_index(client, docs: dict[str, str], size: int = 600, overlap: int = 100) -> dict:
    """Return {items:[{doc,text}], matrix: normalized embeddings}."""
    items = []
    for name, text in docs.items():
        for c in chunk_text(text, size, overlap):
            items.append({"doc": name, "text": c})
    if not items:
        return {"items": [], "matrix": np.zeros((0, 1), dtype=np.float32)}
    mat = _normalize(embed_texts(client, [it["text"] for it in items]))
    return {"items": items, "matrix": mat}


def search(client, index: dict, query: str, k: int = 4) -> list[tuple[dict, float]]:
    if not index.get("items"):
        return []
    q = embed_texts(client, [query])[0]
    q = q / (np.linalg.norm(q) or 1.0)
    scores = index["matrix"] @ q
    order = np.argsort(-scores)[:k]
    return [(index["items"][i], float(scores[i])) for i in order]
