# Workshop labs (Streamlit)

Hands-on companion labs to the *Enterprise AI for IS Faculty* deck. One multipage
Streamlit app:

- **1 · Grounding** — prompt → retrieval → tool-use (Layers 3–4)
- **2 · Build & break a RAG** — chunking, stale docs, permission leaks (Layers 4 & 6)
- **3 · Agent loop with tools** — plan → tool → observe, with an approval gate (Layer 2)
- **4 · Red-team & govern an agent** — prompt injection vs. controls (Layer 7)

A browser-only **prompt lab** plus the **hub** and a copy of the **deck** live in `docs/`,
served by GitHub Pages (Settings → Pages → Deploy from branch → `/docs`). See `../DEPLOY.md`.

## What attendees need
Just a browser and the **OpenAI key Tim hands out** — paste it in the sidebar. The key
stays in the browser session only. Retrieval uses an in-memory index (no external DB).

## Run locally
```bash
cd workshop-labs
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```
Open http://localhost:8501 and paste a key in the sidebar.

## Configuration (optional) — `.streamlit/secrets.toml`
Copy `.streamlit/secrets.toml.example`:
- `workshop_passphrase` — gate the public app to attendees (recommended for the hosted URL).
- `openai_api_key` — pre-load the key so attendees don't paste it (default: leave unset).

## Deploy free — Streamlit Community Cloud
1. Push this folder to a GitHub repo.
2. share.streamlit.io → New app → point at `workshop-labs/streamlit_app.py`.
3. Paste the same secrets into the app's **Settings → Secrets**.
4. **Pre-warm** the app right before the session (free apps sleep when idle).

## Deploy as a container — Google Cloud Run (or local Docker)
```bash
# local
docker build -t workshop-labs .
docker run -p 8501:8501 workshop-labs

# Cloud Run
gcloud run deploy workshop-labs --source . --region us-central1 \
  --allow-unauthenticated --set-env-vars=PORT=8080
# add the passphrase as a Cloud Run env/secret if you want the gate
```

## Cost & safety
- Defaults to the cheap `gpt-4o-mini` model with capped output and a per-session
  request limit.
- Use a **dedicated, budget-capped OpenAI key** and **revoke it after** the workshop.
- The passphrase gate keeps the public URL (and the shared key) attendee-only.
