"""Standalone, networked MCP server for Course Content Studio.

The tool definitions live in ``lib/mcp_tools.py`` so the very same server can be
run two ways:
  - here, as a long-running **streamable-http** service (Docker / a hosted
    endpoint), reachable at ``http://<host>:$PORT/mcp``; and
  - in-memory by ``lib.mcp_client`` (what the Streamlit Cloud lab uses — no host
    required).

Credentials come from environment variables (lib.config falls back to env when
Streamlit isn't present):
  openai_api_key, pinecone_api_key, pinecone_index, and either DATABASE_URL or
  the PG_* parts (PG_HOST/PG_PORT/PG_DB/PG_USER/PG_PASSWORD/PG_SSLMODE).

Run locally:  docker build -f mcp-server/Dockerfile -t genai-course-mcp .  (from
course-content-studio/), then docker run -p 8000:8000 -e ... genai-course-mcp.

(c) Dr. Tim Smith, 2026
"""
from lib.mcp_tools import PORT, mcp

if __name__ == "__main__":
    print("(c) Dr. Tim Smith, 2026")
    print(f"course-tools MCP server (streamable-http) on http://0.0.0.0:{PORT}/mcp")
    mcp.run(transport="streamable-http")
