"""OpenAI chat helpers for the Course-Builder agents (env-based key)."""
from __future__ import annotations

import json
import os

CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")


def _client():
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("openai_api_key")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set (the only required secret).")
    from openai import OpenAI
    return OpenAI(api_key=key)


def chat(messages, temperature: float = 0.3, max_tokens: int = 700) -> str:
    resp = _client().chat.completions.create(
        model=CHAT_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
    return resp.choices[0].message.content or ""


def chat_json(messages, schema: dict, temperature: float = 0.2, max_tokens: int = 1600) -> dict:
    """Structured output: the model must reply matching ``schema`` (strict)."""
    resp = _client().chat.completions.create(
        model=CHAT_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens,
        response_format={"type": "json_schema",
                         "json_schema": {"name": "out", "schema": schema, "strict": True}})
    return json.loads(resp.choices[0].message.content or "{}")
