# Prior-Authorization Triage — the applied Case

The single **applied Case** for GenAI Day: an **agentic system** that assembles every
lab concept end-to-end, in a healthcare setting. An orchestrator coordinates
specialist agents that triage a **prior-authorization request** against a **coverage
policy** — grounded in retrieval, governed by a human, over a real MCP server.

> ⚕️ **Synthetic teaching data only** — fictional members, fictional policies. This is
> a demonstration of AI **system architecture**, not a medical device, and not medical
> advice.

## What it demonstrates (the seven labs, assembled)

| Lab | Concept | Where it shows up here |
|---|---|---|
| 1 | context + memory | each agent is an LLM steered by a role prompt; the case context is replayed to each |
| 2 | guardrails | the review is scoped to the retrieved policy; the critic screens the output |
| 3 | RAG | `policy_search` retrieves the coverage criteria; decisions cite the policy or **pend** when the note is silent |
| 4 | the agent loop | Reviewer ⇄ Critic critique→revise loop; the **LLM is the evaluator** of "goal met?" |
| 5 | MCP + A2A + governance | specialists pass work over **A2A**; tools are reached over a **networked MCP server**; **RBAC** on the write + a **human approval gate** + an **audit log** |

## The agents

- **Researcher** — calls `member_lookup` + `policy_search` (over MCP); never writes.
- **Reviewer** — drafts a determination (**approve / deny / pend**) grounded ONLY in the
  retrieved criteria, assessing each criterion and citing the policy.
- **Critic** — an **LLM as evaluator**: is the determination grounded and consistent?
  failures go back to the Reviewer (a capped critique→revise loop).
- **Case-worker** — calls `submit_determination` (the write) — but **only after a human
  approves** at the governance gate.

The three seeded requests are designed to span the outcomes: a clear **approve**
(criteria met), a clear **deny** (step therapy skipped), and a **pend** (progress not
documented) — plus a red-flag case that should expedite.

## Run it (Docker — the only dependency is an OpenAI key)

```bash
export OPENAI_API_KEY=sk-...          # or put it in a .env file beside this one
docker compose up --build
open http://localhost:8501
```

if 8501 is taken, add the line `APP_PORT=8502` to your `.env` and re-run (on macOS/Linux you can instead prefix: `APP_PORT=8502 docker compose up`). Two containers come up: the
`mcp-server` (tool catalog, internal network only) and the `app` (agents + UI).

## Run without Docker (dev)

```bash
pip install -r mcp-server/requirements.txt -r app/requirements.txt
OPENAI_API_KEY=sk-... python mcp-server/server.py          # terminal 1
cd app && OPENAI_API_KEY=sk-... MCP_SERVER_URL=http://127.0.0.1:8000/mcp \
  streamlit run streamlit_app.py                            # terminal 2
```

## Layout

```
prior-auth-agent/
  docker-compose.yml            # app + mcp-server, OpenAI key only
  app/                          # the agentic app (orchestrator + agents + Streamlit UI)
    lib/{agents,determination,llm,mcp_client}.py
  mcp-server/                   # the networked MCP tool server (local backends)
    mcp_tools.py server.py
    lib/{policystore,memberdb,keys}.py
    seed/policies/*.md          # synthetic coverage policies (the RAG corpus)
```

(c) Dr. Tim Smith, 2026 · USF Muma College of Business
