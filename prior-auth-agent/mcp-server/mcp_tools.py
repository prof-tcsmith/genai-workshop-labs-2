"""FastMCP server for the Prior-Authorization triage Case — local-backed tools.

ONE MCP server exposing the four capabilities the agents orchestrate, all backed
by LOCAL implementations so the whole system runs with only an OpenAI key (no
Pinecone, no cloud database):

  policy_search(query, top_k)          -> grounded chunks of the coverage policies
  member_lookup(member_id)             -> a member's plan + benefits (local SQLite)
  list_requests()                      -> the queue of pending PA requests (SQLite)
  submit_determination(request_id, decision, rationale)
                                       -> record the determination (the WRITE)

Each tool returns a ``{"result": ...}`` envelope so the MCP output schema stays a
stable object; the app's client unwraps it. The agents reach these tools over the
network (streamable-http) — exactly the decoupling the workshop teaches.

SYNTHETIC teaching data only. Not real patients. Not medical advice.
(c) Dr. Tim Smith, 2026
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8000"))
mcp = FastMCP("prior-auth-tools", host="0.0.0.0", port=PORT)


@mcp.tool()
def policy_search(query: str, top_k: int = 6) -> dict:
    """Semantic search over the coverage policies + clinical criteria.

    Returns {"result": [passages]}.
    """
    from lib import policystore
    return {"result": policystore.search(query, top_k)}


@mcp.tool()
def member_lookup(member_id: str) -> dict:
    """Structured lookup of a member's plan and benefits. Returns {"result": {...}}."""
    from lib import memberdb
    return {"result": memberdb.member_lookup(member_id)}


@mcp.tool()
def list_requests() -> dict:
    """The queue of pending prior-authorization requests. Returns {"result": [rows]}."""
    from lib import memberdb
    return {"result": memberdb.list_requests()}


@mcp.tool()
def submit_determination(request_id: str, decision: str, rationale: str) -> dict:
    """Record a determination for a request — the irreversible WRITE.

    ``decision`` is one of: approve, deny, pend. Returns {"result": {...}}.
    """
    from lib import memberdb
    return {"result": memberdb.submit_determination(request_id, decision, rationale)}
