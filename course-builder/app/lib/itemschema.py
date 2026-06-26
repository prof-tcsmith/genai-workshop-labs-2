"""Assessment-item JSON schema + light validation.

The shape matches what the reused ``qti.py`` consumes, so validated items export to
a Canvas QTI package unchanged. ``correct`` is an array of strings at the schema
level (OpenAI strict mode needs one concrete type) and interpreted per ``type``:
choice items use it as option indices ("0","2"); short-answer uses accepted strings.
"""
from __future__ import annotations

ITEM_TYPES = ["mcq", "true_false", "short_answer"]
CONFIDENCE = ["high", "medium", "low"]

_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "type": {"type": "string", "enum": ITEM_TYPES},
        "stem": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
        "correct": {"type": "array", "items": {"type": "string"}},
        "points": {"type": "number"},
        "rationale": {"type": "string"},
        "citation": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"source": {"type": "string"}, "loc": {"type": "string"}},
            "required": ["source", "loc"],
        },
        "objective_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "confidence": {"type": "string", "enum": CONFIDENCE},
    },
    "required": ["type", "stem", "options", "correct", "points", "rationale",
                 "citation", "objective_id", "confidence"],
}

# A batch of items (the Item-writer's output).
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"items": {"type": "array", "items": _ITEM}},
    "required": ["items"],
}

# A single item (the revise step's output).
ITEM_SCHEMA = _ITEM


def validate(item: dict) -> dict | None:
    """Return a cleaned, QTI-safe item, or None if it's malformed."""
    if not isinstance(item, dict):
        return None
    t = item.get("type")
    stem = (item.get("stem") or "").strip()
    if t not in ITEM_TYPES or not stem:
        return None
    options = item.get("options") or []
    if t in ("mcq", "true_false") and len(options) < 2:
        return None
    correct = item.get("correct")
    if not isinstance(correct, list) or not correct:
        return None
    out = {
        "type": t,
        "stem": stem,
        "options": [str(o) for o in options],
        "correct": [str(c) for c in correct],
        "points": float(item.get("points") or 1),
        "rationale": (item.get("rationale") or "").strip(),
        "citation": item.get("citation") if isinstance(item.get("citation"), dict)
        else {"source": "", "loc": ""},
        "objective_id": item.get("objective_id"),
        "confidence": item.get("confidence") if item.get("confidence") in CONFIDENCE else "medium",
    }
    return out
