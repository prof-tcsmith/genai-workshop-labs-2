# Deploying / hosting the workshop material

Repo: **https://github.com/prof-tcsmith/genai-workshop-labs** (public, no keys inside).
Provide the OpenAI key at runtime — never commit it.

## Layout
```
live-demos/      # 5 progressive demos (Docker)         → run locally
workshop-labs/   # Streamlit hands-on labs              → Streamlit Community Cloud
docs/            # slide deck + browser prompt lab      → GitHub Pages (/docs)
mcp-lab/         # MCP tool server (advanced)           → Cloud Run / local Docker
```

## live-demos (local Docker — the headline)
```bash
cd live-demos
cp .env.example .env          # paste the key into .env (gitignored)
docker compose up --build     # http://localhost:8501
```
No `.env`? Attendees can paste the key in the sidebar instead.

## workshop-labs → Streamlit Community Cloud (free)
1. https://share.streamlit.io → New app → repo `prof-tcsmith/genai-workshop-labs`.
2. **Main file path:** `workshop-labs/streamlit_app.py` · Branch `main`.
3. **Settings → Secrets:**
   ```toml
   openai_api_key = "sk-..."          # the workshop key (only lives here, not in git)
   workshop_passphrase = "muma-genai-2026"   # gates the public URL to attendees
   ```
4. Deploy; **pre-warm** it right before the session (free apps sleep when idle).

## docs → GitHub Pages (free)
1. Repo **Settings → Pages → Deploy from a branch** → branch `main`, folder **`/docs`**.
2. Site: **https://prof-tcsmith.github.io/genai-workshop-labs/**
3. Edit `docs/index.html`: replace `REPLACE_WITH_STREAMLIT_URL` with the Streamlit app URL above.

## mcp-lab (optional, advanced)
```bash
cd mcp-lab
docker build -t mcp-lab . && docker run -p 8000:8000 mcp-lab     # or:
gcloud run deploy mcp-lab --source . --region us-central1 --allow-unauthenticated
```

## OpenAI key — safety
- The key is **never in this repo**. Supply it via `.env`, Streamlit Secrets, or pasting in the UI.
- Use a **dedicated, budget-capped** key (apps default to `gpt-4o-mini` with caps), and **revoke it after** the workshop.
