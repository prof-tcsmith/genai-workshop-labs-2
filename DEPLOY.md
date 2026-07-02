# Deploying / hosting the workshop material

Repo: **https://github.com/prof-tcsmith/genai-workshop-labs** (public, no keys inside).
Provide the OpenAI key at runtime — never commit it.

## What participants use — two apps
1. **🧱 Building blocks** — `live-demos/app.py` — the 9 progressive steps (chatbot → memory →
   guardrails → grounding/RAG → build-and-break RAG → tools/agent loop → multi-agent+governance →
   red-team → evaluate & validate).
2. **🎓 Course Content Studio** — `course-content-studio/app.py` — the capstone (RAG + Postgres +
   MCP → a Canvas-ready quiz).

The GitHub Pages hub at **https://prof-tcsmith.github.io/genai-workshop-labs/** routes participants
to these two.

> The old `workshop-labs/` Streamlit app was **retired** — it duplicated five of the building-blocks
> levels and added no new topic. Don't redeploy it.

## Layout
```
live-demos/             # 🧱 the 9 building blocks          → Streamlit Cloud / local Docker
course-content-studio/  # 🎓 the capstone (RAG+PG+MCP)      → Streamlit Cloud / local
docs/                   # slide deck + browser prompt lab   → GitHub Pages (/docs)
mcp-lab/                # MCP tool server (advanced)        → Cloud Run / local Docker
```

## Streamlit Community Cloud (free) — both apps
For each app: https://share.streamlit.io → **New app** → repo `prof-tcsmith/genai-workshop-labs`,
branch `main`, **Main file path** = `live-demos/app.py` (building blocks) **or**
`course-content-studio/app.py` (capstone).

**Settings → Secrets** (these live only in Cloud, never in git):
```toml
openai_api_key = "sk-..."                       # the workshop key
workshop_passphrase_sha256 = "<64-char hash>"   # SHA-256 of the participant code, NOT the code
```
Generate the hash (hand the *plain* code to attendees, store only its hash):
```bash
printf '%s' 'your-participant-code' | shasum -a 256
```
The participant-code gate turns on **only** when `workshop_passphrase_sha256` is set, so local runs
stay gate-free. **Pre-warm** each app right before the session (free apps sleep when idle).

Current deployments:
- 🧱 Building blocks: https://muma-genai.streamlit.app/
- 🎓 Course Content Studio: https://genai-workshop-labs-awybgq8gnmnrevxna2ukv3.streamlit.app/

## Run locally (Docker)
```bash
cd live-demos
cp .env.example .env          # paste the key into .env (gitignored)
docker compose up --build     # http://localhost:8501
```
No `.env`? Paste the key in the sidebar instead. Course Content Studio also needs Pinecone +
Neon/Postgres — see `course-content-studio/SETUP.md`.

## docs → GitHub Pages (free)
1. Repo **Settings → Pages → Deploy from a branch** → branch `main`, folder **`/docs`**.
2. Site: **https://prof-tcsmith.github.io/genai-workshop-labs/**

## mcp-lab (optional, advanced)
```bash
cd mcp-lab
docker build -t mcp-lab . && docker run -p 8000:8000 mcp-lab     # or:
gcloud run deploy mcp-lab --source . --region us-central1 --allow-unauthenticated
```

## OpenAI key — safety
- The key is **never in this repo**. Supply it via `.env`, Streamlit Secrets, or pasting in the UI.
- Use a **dedicated, budget-capped** key (apps default to `gpt-4o-mini` with caps), and **revoke it after** the workshop.
