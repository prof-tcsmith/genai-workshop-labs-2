# Enterprise AI for IS Faculty — hands-on labs (attendee guide)

Everything runs in your browser. No install, no account — just paste the key when asked.

## Start here

- **Labs hub:** `______________________________`  ← (Tim fills in)
- **OpenAI key:** `______________________________`  ← paste this when a lab asks
- **Workshop passphrase (if asked):** `______________________________`

Paste the key in the **sidebar** of the Streamlit labs (it stays in your browser only).
If a lab is slow to load the first time, it's just waking up — give it ~30 seconds.

## The labs (pick a lane; ~5–15 min each)

| Lab | You'll… | Lane |
|---|---|---|
| **Grounding: prompt → retrieval → tool** | Ask one question three ways and watch the answer go from a guess to a cited, live, auditable result. | everyone — start here |
| **Build & break a RAG** | Tune chunking, then sabotage the pipeline (stale doc, permission leak) and watch quality collapse. | Data |
| **Agent loop with tools** | Give a goal; watch the agent plan → call tools → loop. Flip the approval gate on a write. | Builders |
| **Red-team & govern an agent** | Try to jailbreak an HR agent; then switch on controls and watch the attacks fail. | Governors |
| **Prompt & structured output** (browser-only) | Iterate a prompt; extract clean JSON. No key prompt-box — paste your key on the page. | warm-up / anyone |
| **MCP tool server** (advanced) | Run a tool server in a container and connect a client. See the repo's `mcp-lab/README.md`. | Builders |

## Tips

- Compare modes in the **Grounding** lab — only the last mode can answer "is order #4471 eligible?".
- In **Red-team**, run an attack with all controls **off** first, then turn them on one at a time.
- Please don't paste sensitive data — this is a teaching environment on a shared key.
