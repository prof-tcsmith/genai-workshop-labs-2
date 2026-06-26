"""MCP tool server for Level 7 — the refund tools, decoupled behind FastMCP.

The multi-agent refund demo (``pages/7``) no longer calls Python functions
directly; it speaks the **MCP protocol** to THIS server — in-process by default
(a real client→server→tool round-trip, nothing to host), or over the network
(streamable-http) if an ``mcp_server_url`` secret is set, with no app-code change.

The three tools are *capabilities*. WHO may call each one is decided by the
orchestrator's **RBAC** (in the app), not here: exposing a capability over MCP is
not the same as authorizing a caller to use it.

  get_order(order_id)             -> the order record            (read)
  search_policy(query)            -> relevant refund-policy text  (read)
  issue_refund(order_id, amount)  -> execute a refund            (write)

Each tool returns a ``{"result": ...}`` envelope so the MCP output schema stays a
stable object; ``shared.mcp_client`` unwraps it.

(c) Dr. Tim Smith, 2026
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8001"))

# host/port matter only for the networked (streamable-http) mode; the in-memory
# mode ignores them. "/mcp" is the default FastMCP endpoint path.
mcp = FastMCP("refund-tools", host="0.0.0.0", port=PORT)

# The mock enterprise "order DB" — owned by the tool server now (the app no longer
# holds it). Try 4471 (enterprise, in window) vs 5012 (standard, expired).
ORDERS = {
    "4471": {"placed_days_ago": 12, "status": "delivered", "amount": 240.0, "customer_type": "enterprise"},
    "5012": {"placed_days_ago": 60, "status": "delivered", "amount": 90.0, "customer_type": "standard"},
}

_policy_index = None  # built once, lazily, inside the server


def _get_policy_index(client):
    global _policy_index
    if _policy_index is None:
        from shared import store
        _policy_index = store.build_index(client, store.load_corpus(["refund_policy"]))
    return _policy_index


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Look up an order by id. Returns {"result": {order record} | {error}}."""
    o = ORDERS.get(str(order_id).strip())
    return {"result": o if o else {"error": f"order {order_id} not found"}}


@mcp.tool()
def search_policy(query: str) -> dict:
    """Semantic search over the refund policy. Returns {"result": {"snippets": [...]}}."""
    from shared import core, store
    client = core.get_client()
    if client is None:
        return {"result": {"error": "no model client available to embed the query"}}
    hits = store.search(client, _get_policy_index(client), query, k=3)
    return {"result": {"snippets": [
        {"doc": it["doc"], "text": it["text"], "score": round(s, 3)} for it, s in hits]}}


@mcp.tool()
def issue_refund(order_id: str, amount: float) -> dict:
    """Execute a refund (mock side effect — in real life this hits payments).

    Returns {"result": {...confirmation...}}.
    """
    return {"result": {"refunded": True, "order_id": str(order_id), "amount": float(amount),
                       "confirmation": f"RF-{order_id}"}}
