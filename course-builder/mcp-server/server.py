"""Standalone networked MCP server (streamable-http) for the Course-Builder.

The tool definitions live in ``mcp_tools.py`` so the same server can run here as a
long-running service (Docker / a hosted endpoint), reachable at
``http://<host>:$PORT/mcp``. The Course-Builder app connects to it over the network
— the agents never import the tool backends directly.

(c) Dr. Tim Smith, 2026
"""
from mcp_tools import PORT, mcp

if __name__ == "__main__":
    print("(c) Dr. Tim Smith, 2026")
    print(f"course-builder-tools MCP server (streamable-http) on http://0.0.0.0:{PORT}/mcp")
    mcp.run(transport="streamable-http")
