# Tools, the Agent Loop, and the Model Context Protocol (MCP)

A bare language model can only produce text. To let it *act*, you give it **tools** —
functions it can call, such as looking up an order or issuing a refund. The model runs
an **agent loop**: plan → call a tool → observe the result → repeat, until the goal is
met or a step limit is reached.

Naively, the app imports each tool's SDK directly (the vector database client, the
payments client, and so on) and holds all of their credentials. This **couples** the
app to every backend.

The **Model Context Protocol (MCP)** decouples the tools. The app no longer imports
those SDKs; it speaks **one standard protocol** to an MCP server that owns the tools
and their credentials. The model is the MCP **client**; the tool server advertises a
catalog of named tools, and the client calls them by name.

Decoupling delivers three benefits:

- **Reuse** — any agent or app that speaks MCP can call the same tools.
- **Credential isolation** — secrets live in the tool server, not in every app.
- **Swappability** — the same app code can talk to an in-process server or a networked
  one with no change.

Crucially, **exposing a capability over MCP is not the same as authorizing a caller to
use it.** The MCP server makes a tool available; deciding *who* may call it is the job
of the orchestrator's access-control rules, not the server.
