"""Local in-memory vector store over the seeded course materials.

The local-backed replacement for a cloud vector DB (Pinecone): it embeds the
material chunks with OpenAI and ranks them by cosine similarity in numpy. Built
once, lazily, and cached in the server process.
"""
from __future__ import annotations

import glob
import os

import numpy as np

from lib import keys

_MATERIALS = os.path.join(os.path.dirname(__file__), "..", "seed", "materials")
_index = None  # {"chunks": [{id, doc, text}], "matrix": np.ndarray}


def _chunk(text: str, size: int = 700, overlap: int = 120) -> list[str]:
    text = text.strip()
    step = size - overlap
    out, i = [], 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            out.append(piece)
        i += step
    return out


def _embed(texts: list[str]) -> np.ndarray:
    resp = keys.client().embeddings.create(model=keys.EMBED_MODEL, input=texts)
    m = np.array([d.embedding for d in resp.data], dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def _build() -> None:
    global _index
    chunks = []
    for path in sorted(glob.glob(os.path.join(_MATERIALS, "*.md"))):
        doc = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for j, c in enumerate(_chunk(text)):
            chunks.append({"id": f"{doc}#{j}", "doc": doc, "text": c})
    matrix = _embed([c["text"] for c in chunks]) if chunks else np.zeros((0, 1), dtype=np.float32)
    _index = {"chunks": chunks, "matrix": matrix}


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return the top_k most similar material chunks to ``query``."""
    global _index
    if _index is None:
        _build()
    if not _index["chunks"]:
        return []
    qv = _embed([query])[0]
    scores = _index["matrix"] @ qv
    order = np.argsort(-scores)[:max(1, int(top_k))]
    return [{"id": _index["chunks"][i]["id"], "doc": _index["chunks"][i]["doc"],
             "text": _index["chunks"][i]["text"], "score": round(float(scores[i]), 3)}
            for i in order]
