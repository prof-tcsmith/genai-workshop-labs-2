"""SYNC client for the Level 7 refund MCP tools (``shared.mcp_tools``).

The point of MCP here is *decoupling*: the app no longer calls tool functions
directly — it speaks ONE standard protocol to a server that owns the tools. This
module is that single seam, with two modes chosen automatically:

  - **in-process** (default): runs the FastMCP server from ``shared.mcp_tools``
    in memory and talks to it through a real MCP ``ClientSession`` — a genuine
    client→server→tool round-trip, nothing to host.
  - **remote**: if an ``mcp_server_url`` secret / ``MCP_SERVER_URL`` env points at
    a hosted server, connect over **streamable-http** instead. The same app code
    runs against a networked server — that's the whole lesson.

Public API:
    mode()                       -> "in-process" | "remote"
    list_tools()  -> list[dict]  # the server's advertised tool catalog
    call_tool(name, args) -> any # invoke one tool, return its parsed result
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any


class MCPUnavailable(RuntimeError):
    """Raised when a *remote* MCP server can't be reached."""


def _server_url() -> str:
    try:
        import streamlit as st
        u = st.secrets.get("mcp_server_url")  # type: ignore[attr-defined]
    except Exception:
        u = None
    return (u or os.environ.get("MCP_SERVER_URL") or "").strip()


def _remote_configured() -> bool:
    u = _server_url()
    return (u.startswith(("http://", "https://"))
            and "localhost" not in u and "127.0.0.1" not in u)


def mode() -> str:
    """'remote' if a hosted MCP server is configured, else 'in-process'."""
    return "remote" if _remote_configured() else "in-process"


def _run(coro):
    """Run an async coroutine from sync code, robust to an existing event loop."""
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
            return json.loads(text)
        except Exception:
            try:
                import ast
                return ast.literal_eval(text)
            except Exception:
                return text

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        value = structured
    else:
        parsed = [_one(b.text) for b in (getattr(result, "content", None) or [])
                  if getattr(b, "type", None) == "text" and getattr(b, "text", None) is not None]
        if not parsed:
            return None
        value = parsed[0] if len(parsed) == 1 else parsed

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


# ---- in-process: in-memory MCP session against shared.mcp_tools --------------
async def _inproc_list() -> list[dict]:
    from mcp.shared.memory import create_connected_server_and_client_session as connect
    from shared.mcp_tools import mcp
    async with connect(mcp._mcp_server) as client:
        return _tool_dicts(await client.list_tools())


async def _inproc_call(name: str, args: dict) -> Any:
    from mcp.shared.memory import create_connected_server_and_client_session as connect
    from shared.mcp_tools import mcp
    async with connect(mcp._mcp_server) as client:
        return _parse_result(await client.call_tool(name, args or {}))


# ---- remote: streamable-http -------------------------------------------------
async def _remote_list() -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(_server_url()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _tool_dicts(await session.list_tools())


async def _remote_call(name: str, args: dict) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(_server_url()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _parse_result(await session.call_tool(name, args or {}))


def _friendly(exc: Exception) -> "MCPUnavailable":
    return MCPUnavailable(
        f"Could not reach the hosted MCP server at {_server_url()!r}. "
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
