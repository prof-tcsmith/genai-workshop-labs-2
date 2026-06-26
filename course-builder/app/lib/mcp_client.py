"""Networked MCP client for the Course-Builder app.

The agents call tools over **streamable-http** to the ``course-builder-tools`` MCP
server — the app never imports the tool backends, which is the decoupling the
workshop teaches. The server URL comes from ``MCP_SERVER_URL`` (set by
docker-compose to the ``mcp-server`` service; defaults to localhost for dev).

Public API:
    server_url()                 -> str
    list_tools()  -> list[dict]  # the server's advertised catalog
    call_tool(name, args) -> any # invoke one tool, return its parsed result
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any


def server_url() -> str:
    return os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")


def _run(coro):
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


async def _list() -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(server_url()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _tool_dicts(await session.list_tools())


async def _call(name: str, args: dict) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(server_url()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _parse_result(await session.call_tool(name, args or {}))


def list_tools() -> list[dict]:
    """The MCP server's advertised tools — ``[{name, description, input_schema}]``."""
    return _run(_list())


def call_tool(name: str, args: dict | None = None) -> Any:
    """Invoke one MCP tool by name and return its parsed result."""
    return _run(_call(name, args or {}))
