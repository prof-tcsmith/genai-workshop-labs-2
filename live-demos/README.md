# Live demos — five progressive levels

Companion live demos to the *Enterprise AI for IS Faculty* deck. One Streamlit app,
five levels, each adding one capability and lighting up more of the 7-layer stack.
Participants paste the workshop **OpenAI key** in the sidebar and watch.

| Level | Shows | Layers |
|---|---|---|
| 1 · Chatbot | system prompt + one message; no memory, no guardrails | 1, 3 |
| 2 · Memory + guardrails | conversation memory; a narrow support bot with guardrails you can watch fire | 1, 3, 7 |
| 3 · Context engineering | retrieval over an info store; grounded, cited answers | 4, 6 |
| 4 · MCP + tools | a tool-using agent over an MCP-style server (real protocol: `../mcp-lab/`) | 2, 5 |
| 5 · A2A + governance | specialist agents collaborate under RBAC, an approval gate, and an audit log | 2, 7 |

## Run it (Docker — one command)
```bash
cd live-demos
docker compose up --build
# open http://localhost:8501 and paste the OpenAI key in the sidebar
```

Stop with `Ctrl-C`; `docker compose down` to remove the container.

## Run it (without Docker)
```bash
cd live-demos
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- The key stays in the browser session only; demos use the cheap `gpt-4o-mini` model
  with capped output and a per-session request limit.
- Retrieval (Levels 3–4) uses an in-memory index over OpenAI embeddings — no external DB.
- See `../live-demos-guide.md` for facilitation notes (what to point out at each level)
  and `../DEPLOY.md` for the broader hosting picture.
