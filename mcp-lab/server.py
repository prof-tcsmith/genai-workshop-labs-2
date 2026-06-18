"""Minimal MCP server for the workshop (Layer 2 — advanced lab).

It exposes a few tools over mock enterprise data. No LLM key lives here: the
*client's* model decides when to call these tools. That separation — data and
tools on the server, model on the client — is the whole point of MCP.

Run it two ways:
  - stdio  (default): an MCP client (Claude Desktop, the MCP Inspector) spawns it.
  - HTTP   (streamable-http): a long-running service for a container / Cloud Run.
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8000"))
mcp = FastMCP("Workshop Tools", host="0.0.0.0", port=PORT)

# --- mock enterprise data (a real server would query a DB / API behind here) ---
ORDERS = {
    "4471": {"order_id": "4471", "placed_days_ago": 12, "status": "delivered", "amount": 240.0, "customer_type": "enterprise"},
    "5012": {"order_id": "5012", "placed_days_ago": 60, "status": "delivered", "amount": 90.0, "customer_type": "standard"},
}

POLICY = """
Enterprise customers may request a refund within 45 days of the order date.
Standard customers have a 30-day refund window.
Refunds above $200 require manager approval before they are issued.
Digital goods are non-refundable once downloaded.
""".strip()


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Look up an order by id. Returns days since placed, status, amount, and customer type."""
    return ORDERS.get(str(order_id).strip(), {"error": f"order {order_id} not found"})


@mcp.tool()
def list_orders() -> list[str]:
    """List the known order ids."""
    return list(ORDERS.keys())


@mcp.tool()
def search_policy(query: str) -> list[str]:
    """Return refund-policy lines relevant to the query (simple keyword match)."""
    words = [w for w in str(query).lower().split() if len(w) > 2]
    hits = [ln.strip() for ln in POLICY.splitlines()
            if ln.strip() and any(w in ln.lower() for w in words)]
    return hits or ["(no matching policy lines — try different keywords)"]


# --- YOUR TASK (exercise): add a tool, restart, and ask the model to use it. ---
# @mcp.tool()
# def check_inventory(sku: str) -> dict:
#     """Return stock on hand for a SKU."""
#     return {"sku": sku, "on_hand": 42}


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")  # "stdio" | "sse" | "streamable-http"
    mcp.run(transport=transport)
