"""The determination schema — the structured output the Reviewer agent must
produce, and a small validator. Analogous to the Course-Builder's item schema.

A determination is grounded ONLY in the retrieved policy criteria: a decision
(approve / deny / pend), a per-criterion assessment, a rationale, and a citation
to the policy it came from.
"""
from __future__ import annotations

# Strict JSON schema for structured output (OpenAI json_schema, strict=True).
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["approve", "deny", "pend"]},
        "rationale": {"type": "string"},
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "criterion": {"type": "string"},
                    "met": {"type": "string", "enum": ["yes", "no", "unknown"]},
                    "evidence": {"type": "string"},
                },
                "required": ["criterion", "met", "evidence"],
            },
        },
        "citation": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"source": {"type": "string"}},
            "required": ["source"],
        },
    },
    "required": ["decision", "rationale", "criteria", "citation"],
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "grounded": {"type": "boolean"},   # decision + criteria supported by the policy passages
        "consistent": {"type": "boolean"},  # decision follows from the criteria assessment
        "ok": {"type": "boolean"},          # grounded AND consistent
        "notes": {"type": "string"},
    },
    "required": ["grounded", "consistent", "ok", "notes"],
}

_DECISIONS = {"approve", "deny", "pend"}


def validate(d: dict) -> dict | None:
    """Light structural check; returns the determination or None if unusable."""
    if not isinstance(d, dict):
        return None
    if d.get("decision") not in _DECISIONS:
        return None
    if not (d.get("rationale") or "").strip():
        return None
    d.setdefault("criteria", [])
    d.setdefault("citation", {"source": ""})
    return d
