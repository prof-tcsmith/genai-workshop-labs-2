# MCP tool server (advanced lab — Layer 2)

A tiny **Model Context Protocol** server that exposes mock enterprise tools
(`get_order`, `list_orders`, `search_policy`). The model lives in the *client*;
this server only holds data and tools. This is the lab that aligns with Varol's
MCP session.

> Heads-up: MCP clients and the `mcp` package evolve quickly. The code targets
> `mcp >= 1.2` and the commands below are the common path, but you may need to
> adjust a flag for your exact client/version. Verify with your MCP client.

## Option A — local, over stdio (simplest for a single laptop)

```bash
cd mcp-lab
pip install -r requirements.txt
```

Then point an MCP client at it. Two easy clients:

**MCP Inspector** (a browser UI, needs Node):
```bash
npx @modelcontextprotocol/inspector python server.py
```
It spawns the server over stdio and lets you call each tool by hand.

**Claude Desktop** — add to its MCP config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "workshop": { "command": "python", "args": ["/ABSOLUTE/PATH/mcp-lab/server.py"] }
  }
}
```
Restart Claude Desktop, then ask: *"Is order 4471 refundable? Use the tools."*

## Option B — container over HTTP (Cloud Run, or any laptop with Docker)

```bash
cd mcp-lab
docker build -t mcp-lab .
docker run -p 8000:8000 mcp-lab
# server speaks streamable-http at http://localhost:8000/mcp
```

Connect with the Inspector in HTTP mode (choose "streamable-http", URL
`http://localhost:8000/mcp`), or deploy to Google Cloud Run:

```bash
gcloud run deploy mcp-lab --source . --region us-central1 --allow-unauthenticated
# Cloud Run sets $PORT; the Dockerfile already serves streamable-http on it.
```

## The exercise (10 min)

1. Connect a client and call `get_order("4471")` and `search_policy("enterprise refund")`.
2. Ask the model a question that forces it to chain tools (e.g., *"Is 4471 within the refund window?"*).
3. **Add a tool:** uncomment `check_inventory` in `server.py` (or write your own),
   restart the server, reconnect, and ask the model to use it.

The takeaway: adding a capability to an agent is adding a *tool to a server* —
a permissioned, auditable surface, not a change to the model.
