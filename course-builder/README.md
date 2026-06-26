# 🤖 Autonomous Course-Builder

The **agentic "after" picture** of the Course Content Studio. Where the Studio builds
a Canvas quiz by a hand-wired pipeline, this builds it with **specialist agents** an
**orchestrator** coordinates — all calling tools over a **real MCP server**, under
**governance**.

It exists to show, in one runnable system, why **MCP + agent‑to‑agent (A2A) +
orchestrator** belong together — the combination the workshop teaches in pieces
(Lab 4 / Level 7).

## What it demonstrates

- **Orchestrator + A2A** — an Orchestrator plans the job and coordinates four
  specialists who pass work between them:
  - **Researcher** → calls `vector_search` / `course_lookup` (read‑only) to gather
    grounded evidence,
  - **Item‑writer** → drafts assessment items grounded only in that evidence,
  - **Critic** → judges each item for grounding + clarity; failures go **back** to the
    writer in a capped **critique → revise** loop,
  - **Exporter** → calls `export_qti` to build the Canvas package.
- **MCP** — the agents never import the tool backends. They call **named tools over the
  network** (streamable‑http) to a FastMCP server that owns them. Swappable, reusable,
  credential‑isolated. *Exposing a tool over MCP is a capability; the orchestrator
  decides who may call it.*
- **Governance** — a **human approval gate** before the (irreversible) export, plus an
  append‑only **audit log** of every A2A message, MCP tool call, and decision.

## Runs locally — only an OpenAI key

No Pinecone, no cloud Postgres. The MCP tools are backed locally: a **numpy cosine
store** over seeded course materials, **SQLite** for the course/objectives/rubric, and
the (pure) QTI builder. The single external dependency is the OpenAI API.

```bash
cd course-builder
cp .env.example .env          # paste your OpenAI key
docker compose up --build
open http://localhost:8501
```

## Layout

```
course-builder/
  mcp-server/        # FastMCP server (streamable-http) — local-backed tools
    mcp_tools.py     #   vector_search · course_lookup · export_qti
    lib/             #   localstore (cosine) · coursedb (SQLite) · qti (reused)
    seed/materials/  #   the seeded course (a mini-course on the workshop's topics)
  app/               # the agentic app
    streamlit_app.py #   UI: run agents → review → approve → download QTI
    lib/agents.py    #   orchestrator + Researcher/Item-writer/Critic/Exporter
    lib/mcp_client.py#   streamable-http client to the MCP server
  docker-compose.yml # mcp-server + app, wired on an internal network
```

## Run without Docker (dev)

```bash
# terminal 1 — the MCP server
cd mcp-server && PYTHONPATH=. OPENAI_API_KEY=sk-... python server.py
# terminal 2 — the app (defaults MCP_SERVER_URL to http://127.0.0.1:8000/mcp)
cd app && PYTHONPATH=. OPENAI_API_KEY=sk-... streamlit run streamlit_app.py
```

(c) Dr. Tim Smith, 2026
