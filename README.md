# The Building Blocks of GenAI — workshop labs

GenAI Day · Dr. Tim Smith · USF Muma College of Business

Nine hands-on labs (seven in the session, two take-home), a standalone MCP lab, and one
applied Case. Everything here runs on **your machine with Docker** — or use the hosted app
at **[muma-genai.streamlit.app](https://muma-genai.streamlit.app)** (`tinyurl.com/muma-genai`).

Slides & extras: **[prof-tcsmith.github.io/genai-workshop-labs](https://prof-tcsmith.github.io/genai-workshop-labs)**
(intro + closing decks, the deep-dive deck, and the browser prompt lab).

## Run the labs (Docker)

```bash
git clone https://github.com/prof-tcsmith/genai-workshop-labs.git
cd genai-workshop-labs
docker compose up        # first run pulls two prebuilt images (~250 MB)
```

- **http://localhost:8501** — the labs app (Labs 1–7 + take-home Labs 8–9)
- **http://localhost:8000/mcp** — the standalone MCP lab server (point the MCP Inspector
  or Claude Desktop at it)

**Your OpenAI key** (never inside the images — supply it at runtime, pick one):

- *Easiest:* pick a provider in the app **sidebar** and paste the key — held in your browser
  session only; or
- `cp .env.example .env` and set `OPENAI_API_KEY` (`.env` is gitignored).

The RAG labs (4–5) need the **OpenAI** key even with Anthropic chat — embeddings are always OpenAI.
Full setup details: [PARTICIPANT-GUIDE.md](PARTICIPANT-GUIDE.md).

## The labs

| Lab | | Page |
|---|---|---|
| 1 | A model becomes an app | Chatbot |
| 2 | It forgets your last sentence | Memory |
| 3 | It will answer anything | Guardrails |
| 4 | Ground it in your documents | Grounding & RAG |
| 5 | Then break it | Build & break a RAG |
| 6 | It knows, but can't act | Tools & the agent loop |
| 7 | Agents over MCP + A2A | Multi-agent & governance |
| 8–9 | Take-home | Red-team · Evaluate & validate |

## The Case — Prior-Authorization Triage (homework)

The seven labs, assembled into one governed agentic system: specialist agents over **A2A** +
a real **MCP server**, RAG-grounded, an LLM critic, a human approval gate + audit log.

```bash
cd prior-auth-agent
docker compose up --build      # builds from source; OpenAI key via .env or env var
```

If port 8501 is taken, add `APP_PORT=8502` to your `.env`.
*Synthetic data — a demonstration of AI system architecture, not medical advice.*

## Build it yourself

[`BUILD-IT-YOURSELF.md`](BUILD-IT-YOURSELF.md) — one prompt per lab: paste into Claude Code
and it builds a bare-bones version of that lab, ready to push to your own Streamlit app.

## Key safety

The Docker images are public and contain **no keys** — verified before every push. A pasted
key lives only in your browser session; a `.env` key stays on your machine (gitignored).

---
(c) Dr. Tim Smith, 2026
