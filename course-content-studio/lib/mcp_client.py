"""SYNC client for the Course Content Studio MCP tools.

The point of the MCP unit is *decoupling*: the app no longer imports ``pinecone``
/ ``psycopg`` (and their credentials) directly — it speaks ONE standard protocol
to a server that owns the tools. This module is that single seam, with two modes
chosen automatically:

  - **in-process** (default): runs the FastMCP server from :mod:`lib.mcp_tools`
    in memory and talks to it through a real MCP ``ClientSession`` — a genuine
    client→server→tool round-trip, with no server to host. This is what the
    Streamlit Cloud lab uses.
  - **remote**: if ``mcp_server_url`` points at a hosted server (an http(s) URL
    that isn't the localhost placeholder), connect over **streamable-http**.
    Setting that one Secret flips the whole app to a networked MCP server — the
    app code doesn't change, which is the entire lesson.

Public API:
    mode()                       -> "in-process" | "remote"
    list_tools()  -> list[dict]  # the server's advertised tool catalog
    call_tool(name, args) -> any # invoke one tool, return its parsed result
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from lib import config


class MCPUnavailable(RuntimeError):
    """Raised when a *remote* MCP server can't be reached."""


def _remote_configured() -> bool:
    u = (config.MCP_SERVER_URL or "").strip()
    return (u.startswith(("http://", "https://"))
            and "localhost" not in u and "127.0.0.1" not in u)


def mode() -> str:
    """'remote' if a hosted MCP server is configured, else 'in-process'."""
    return "remote" if _remote_configured() else "in-process"


def _run(coro):
    """Run an async coroutine from sync code, robust to an existing event loop.

    Streamlit's script thread usually has no running loop (so ``asyncio.run``
    works), but if one is present we run the coroutine in a worker thread with
    its own loop instead of raising.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(coro)).result()
    return asyncio.run(coro)


def _parse_result(result: Any) -> Any:
    """Pull the tool's return value out of an MCP ``CallToolResult``."""
    if getattr(result, "isError", False):
        blocks = getattr(result, "content", None) or []
        msg = next((getattr(b, "text", None) for b in blocks if getattr(b, "text", None)), "tool error")
        raise RuntimeError(msg)
    def _one(text):
        try:
            return json.loads(text)               # JSON output
        except Exception:
            try:
                import ast
                return ast.literal_eval(text)     # FastMCP may emit a Python repr
            except Exception:
                return text

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        value = structured
    else:
        # FastMCP may split a result across one text block per item — collect all.
        parsed = [_one(b.text) for b in (getattr(result, "content", None) or [])
                  if getattr(b, "type", None) == "text" and getattr(b, "text", None) is not None]
        if not parsed:
            return None
        value = parsed[0] if len(parsed) == 1 else parsed

    # Tools wrap their payload as {"result": <value>} for a stable schema — unwrap.
    if isinstance(value, dict) and set(value.keys()) == {"result"}:
        return value["result"]
    return value


def _tool_dicts(listing) -> list[dict]:
    out: list[dict] = []
    for t in getattr(listing, "tools", []) or []:
        out.append({
            "name": getattr(t, "name", ""),
            "description": (getattr(t, "description", "") or "").strip(),
            "input_schema": getattr(t, "inputSchema", None),
        })
    return out


# ---- in-process: in-memory MCP session against lib.mcp_tools -----------------
async def _inproc_list() -> list[dict]:
    from mcp.shared.memory import create_connected_server_and_client_session as connect
    from lib.mcp_tools import mcp
    async with connect(mcp._mcp_server) as client:
        return _tool_dicts(await client.list_tools())


async def _inproc_call(name: str, args: dict) -> Any:
    from mcp.shared.memory import create_connected_server_and_client_session as connect
    from lib.mcp_tools import mcp
    async with connect(mcp._mcp_server) as client:
        return _parse_result(await client.call_tool(name, args or {}))


# ---- remote: streamable-http -------------------------------------------------
async def _remote_list() -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(config.MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _tool_dicts(await session.list_tools())


async def _remote_call(name: str, args: dict) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(config.MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _parse_result(await session.call_tool(name, args or {}))


def _friendly(exc: Exception) -> "MCPUnavailable":
    return MCPUnavailable(
        f"Could not reach the hosted MCP server at {config.MCP_SERVER_URL!r}. "
        "Check the 'mcp_server_url' secret (or unset it to use the built-in "
        f"in-process server). [{type(exc).__name__}: {exc}]"
    )


# ---- public sync API ---------------------------------------------------------
def list_tools() -> list[dict]:
    """The MCP server's advertised tools — ``[{name, description, input_schema}]``."""
    if _remote_configured():
        try:
            return _run(_remote_list())
        except Exception as exc:
            raise _friendly(exc) from exc
    return _run(_inproc_list())


def call_tool(name: str, args: dict | None = None) -> Any:
    """Invoke one MCP tool by name and return its parsed result."""
    if _remote_configured():
        try:
            return _run(_remote_call(name, args or {}))
        except MCPUnavailable:
            raise
        except Exception as exc:
            raise _friendly(exc) from exc
    return _run(_inproc_call(name, args or {}))
