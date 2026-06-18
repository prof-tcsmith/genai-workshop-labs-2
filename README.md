# GenAI Workshop — labs & live demos

Hands-on material for the *Enterprise AI for Information Systems Faculty* workshop.
Everything runs in your browser or in Docker. **You supply your own OpenAI API key** —
no key is included in this repository. The facilitator will hand one out at the session
(or use your own); paste it where prompted, or set it locally as described below.

Everything is organized around one map: the **7-layer enterprise AI stack**.

## What's here

| Folder | What it is | Run it |
|---|---|---|
| **`live-demos/`** | Five progressive live demos (chatbot → memory+guardrails → context → MCP+tools → A2A+governance) | `cd live-demos && docker compose up` |
| **`workshop-labs/`** | Self-driven Streamlit hands-on labs (grounding, build-and-break RAG, agent loop, red-team) | `streamlit run workshop-labs/streamlit_app.py` or host it |
| **`mcp-lab/`** | An MCP tool server (advanced) | see `mcp-lab/README.md` |
| **`docs/`** | The slide deck + a browser prompt lab (served via GitHub Pages) | open `docs/index.html` |

## Quick start (participants)

You need a terminal, **Docker** (Docker Desktop or OrbStack, running), and **git**.
Full step-by-step with prerequisites: see **`PARTICIPANT-GUIDE.md`**.

```bash
git clone https://github.com/prof-tcsmith/genai-workshop-labs.git
cd genai-workshop-labs
cp .env.example .env        # paste your OpenAI key into .env (or paste it in the app sidebar later)
docker compose up           # pulls the prebuilt images from Docker Hub
```

Then open **http://localhost:8501** (live demos) and **http://localhost:8000** (MCP lab).
Walk Levels 1 → 5; each adds one capability and lights up more of the stack.
Stop with **Ctrl-C**; `docker compose down` to remove the containers.

## Your OpenAI key

- **It is not in this repo.** Provide it one of three ways: paste it into any app's sidebar,
  put it in `live-demos/.env` (gitignored), or — for hosted Streamlit — set it in the
  app's Secrets. The browser prompt lab takes the key on the page.
- Please be gentle: it may be a shared, budget-capped key. Don't paste sensitive data.

## Guides

- `attendee-guide.pdf` — one-pager for participants.
- `live-demos-guide.pdf` — facilitator setup & management for the live demos.
- `workshop-companion.pdf` — expanded notes for every slide in the deck.
- `DEPLOY.md` — how to host the labs (Streamlit Community Cloud + GitHub Pages).
