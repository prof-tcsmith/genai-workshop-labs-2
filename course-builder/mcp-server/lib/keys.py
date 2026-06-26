"""OpenAI key resolution + client construction for the MCP tool server.

Runs in a container, so credentials come from environment variables — the OpenAI
key is the ONLY external dependency this whole system needs (no Pinecone, no
cloud Postgres).
"""
from __future__ import annotations

import os

EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")


def openai_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("openai_api_key")


def client():
    key = openai_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set (the only required secret).")
    from openai import OpenAI
    return OpenAI(api_key=key)
