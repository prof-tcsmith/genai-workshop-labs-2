"""FastMCP server for the Autonomous Course-Builder — local-backed tools.

ONE MCP server exposing the three capabilities the agents orchestrate, all backed
by LOCAL implementations so the whole system runs with only an OpenAI key (no
Pinecone, no cloud Postgres):

  vector_search(query, top_k)   -> grounded passages from the course materials
  course_lookup(kind, course_id)-> course / objectives / rubric (local SQLite)
  export_qti(title, items)      -> a Canvas-importable QTI .zip (base64)

Each tool returns a ``{"result": ...}`` envelope so the MCP output schema stays a
stable object; the app's client unwraps it. The agents reach these tools over the
network (streamable-http) — exactly the decoupling the workshop teaches.

(c) Dr. Tim Smith, 2026
"""
from __future__ import annotations

import base64
import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8000"))
mcp = FastMCP("course-builder-tools", host="0.0.0.0", port=PORT)


@mcp.tool()
def vector_search(query: str, top_k: int = 5) -> dict:
    """Semantic search over the course materials. Returns {"result": [passages]}."""
    from lib import localstore
    return {"result": localstore.search(query, top_k)}


@mcp.tool()
def course_lookup(kind: str, course_id: int = 1) -> dict:
    """Structured lookup. ``kind`` is one of: courses, objectives, rubric.

    Returns {"result": <rows or rubric dict>} or {"error": ...}.
    """
    from lib import coursedb
    if kind == "courses":
        value = coursedb.list_courses()
    elif kind == "objectives":
        value = coursedb.list_objectives(course_id)
    elif kind == "rubric":
        value = coursedb.get_rubric(course_id)
    else:
        return {"error": f"unknown kind {kind!r}"}
    return {"result": value}


@mcp.tool()
def export_qti(title: str, items: list) -> dict:
    """Build a Canvas QTI .zip from reviewed items.

    Returns {"result": {"filename", "base64", "answer_key"}}.
    """
    from lib import qti
    pkg = qti.build_qti_package(title, items or [])
    answer_key = qti.build_answer_key(title, items or [])
    return {"result": {
        "filename": "quiz_qti.zip",
        "base64": base64.b64encode(pkg).decode("ascii"),
        "answer_key": answer_key,
    }}
