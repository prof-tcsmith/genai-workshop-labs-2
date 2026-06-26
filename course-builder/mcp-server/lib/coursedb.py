"""Local SQLite course catalog — the cloud-free replacement for Postgres.

Holds the structured, authoritative facts the agents look up: the course, its
learning objectives, and a grading rubric. Seeded once on first use into a
writable temp file (the image stays read-only-friendly).
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile

_DB = os.environ.get("COURSE_DB") or os.path.join(tempfile.gettempdir(), "course-builder.db")

_SEED_COURSE = "Enterprise AI Foundations"
_SEED_OBJECTIVES = [
    "Explain how retrieval-augmented generation grounds an LLM in source documents.",
    "Describe how MCP decouples tools from the application and why that matters.",
    "Identify the governance controls (RBAC, approval gates, audit log) that make a multi-agent system trustworthy.",
]
_SEED_RUBRIC = {
    "grounded": "Every item is answerable from the course materials and cites its source.",
    "clarity": "Stems are unambiguous; single-answer items have exactly one defensible answer.",
    "alignment": "Each item maps to one of the course's learning objectives.",
}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE IF NOT EXISTS objectives(id INTEGER PRIMARY KEY, course_id INTEGER, text TEXT);
            CREATE TABLE IF NOT EXISTS rubric(course_id INTEGER PRIMARY KEY, json TEXT);
            """
        )
        if not conn.execute("SELECT 1 FROM courses LIMIT 1").fetchone():
            conn.execute("INSERT INTO courses(id, name) VALUES (1, ?)", (_SEED_COURSE,))
            for i, text in enumerate(_SEED_OBJECTIVES, 1):
                conn.execute("INSERT INTO objectives(id, course_id, text) VALUES (?, 1, ?)", (i, text))
            conn.execute("INSERT INTO rubric(course_id, json) VALUES (1, ?)", (json.dumps(_SEED_RUBRIC),))


def list_courses() -> list[dict]:
    init()
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT id, name FROM courses").fetchall()]


def list_objectives(course_id: int = 1) -> list[dict]:
    init()
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, text FROM objectives WHERE course_id = ?", (course_id,)).fetchall()]


def get_rubric(course_id: int = 1) -> dict:
    init()
    with _conn() as conn:
        row = conn.execute("SELECT json FROM rubric WHERE course_id = ?", (course_id,)).fetchone()
        return json.loads(row["json"]) if row else {}
