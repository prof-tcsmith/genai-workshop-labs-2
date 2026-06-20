"""Canonical MCP tool definitions for Course Content Studio.

Defines ONE FastMCP server with the two tools that re-expose the app's
capabilities over the MCP protocol:

  - ``vector_search``  → semantic (cosine) search over ingested content (Pinecone)
  - ``course_lookup``  → exact, structured rows from cloud Postgres

This module is imported by BOTH:
  - ``mcp-server/server.py`` — runs it as a standalone, networked service
    (streamable-http) for Docker / a hosted endpoint, and
  - ``lib.mcp_client`` — runs it **in-memory** so the Cloud lab can call the
    tools over a real MCP client session with no server to host.

Credentials are read (via :mod:`lib.config`) from Streamlit Secrets or, when
Streamlit isn't present (the standalone container), from environment variables.

(c) Dr. Tim Smith, 2026
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8000"))

# host/port matter only for the networked (streamable-http) mode; the in-memory
# mode ignores them. "/mcp" is the default FastMCP endpoint path.
mcp = FastMCP("course-tools", host="0.0.0.0", port=PORT)


@mcp.tool()
def vector_search(query: str, top_k: int = 5, namespace: str = "lab") -> dict:
    """Semantic (cosine) search over ingested course content.

    Returns ``{"result": [{id, score, text, metadata}, ...]}`` (the envelope keeps
    the MCP output schema a stable object regardless of how many hits there are).
    """
    from lib import vectors
    return {"result": vectors.query(namespace, query, top_k)}


@mcp.tool()
def course_lookup(
    kind: str,
    course_id: int | None = None,
    objective_id: int | None = None,
) -> dict:
    """Structured lookup against Postgres. Returns ``{"result": <rows or row>}``.

    ``kind`` is one of: ``courses``, ``objectives`` (needs ``course_id``),
    ``rubric`` (needs ``course_id``), ``bank`` (``course_id`` + optional
    ``objective_id``).
    """
    from lib import db
    if kind == "courses":
        value = db.list_courses()
    elif kind == "objectives":
        value = db.list_objectives(course_id)
    elif kind == "rubric":
        value = db.get_rubric(course_id)
    elif kind == "bank":
        value = db.list_bank(course_id, objective_id)
    else:
        return {"error": f"unknown kind {kind!r}"}
    return {"result": value}
