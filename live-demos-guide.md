# Live Demos — Facilitator Guide

**For:** Tim Smith · Companion to the five live-demo labs (`live-demos/`)

This guide is for **setting up and running the live-demo portion** of the workshop. The demos are the "do/observe" counterpart to the deck: nine pages — **seven labs** in the hour (grouped onto five handout sheets) plus two take-home labs — each adding one capability, assembling a GenAI system one building block at a time. Attendees paste a shared OpenAI key and watch (or drive) each lab.

---

## 1. What you're running

One Streamlit app — **nine demo pages: seven labs in the hour plus two take-home labs** (a lab = one page, the sidebar's numbering) — in a single Docker container. Each stage breaks the one before it: it forgets → it answers anything → it can't prove it → it can't act → nobody governs the actor.

| Lab | Pages | Demonstrates | New vs. previous lab |
|---|---|---|---|
| 1 · A model becomes an app | Chatbot · Memory | system prompt + message; then conversation history replayed each turn | the baseline, then memory |
| 2 · It will answer anything | Guardrails | a scoped support bot **plus** an independent pre-flight check | layered guardrails |
| 3 · Ground it — then break it | Grounding & RAG · Build & break a RAG | retrieval + assembled context, grounded/cited answers; then sabotage the pipeline | an information store (RAG) |
| 4 · It knows, but can't act | Tools & the agent loop | a tool-using agent (plan → call → observe) with a human approval gate | tools / the ability to act |
| 5 · Agents over MCP + A2A | Multi-agent & governance | specialist agents over A2A, tools via a **real MCP server**, under RBAC + approval + audit | multiple agents + MCP + governance |

**Take-home (not walked live):** *Red-team & govern* (attack the controls, then switch them on) and *Evaluate & validate* (release readiness). Both stay live for attendees to explore.

Architecture, kept deliberately simple: a single container; retrieval uses an **in-memory** index over OpenAI embeddings (no external database); the MCP server and the multiple agents run **in-process** (the standalone real-protocol MCP server is in `mcp-lab/`). The only external dependency is the OpenAI API.

---

## 2. Prerequisites

- **Docker Desktop** (Mac/Windows/Linux) — https://www.docker.com/products/docker-desktop/
- **One OpenAI API key** that you provision and hand out (see §5).
- That's it for attendees who run it themselves. If they'd rather just watch, you run it and screen-share.

---

## 3. Run it (one command)

```bash
cd live-demos
docker compose up --build       # first build ~1–2 min; later runs are instant
```

Open **http://localhost:8501**, paste the OpenAI key in the sidebar, and walk Labs 1 → 7.

- Stop: `Ctrl-C`. Remove the container: `docker compose down`.
- No Docker? `pip install -r requirements.txt && streamlit run app.py`.
- Port 8501 busy? Edit the port mapping in `docker-compose.yml` (e.g., `"8600:8501"`).

---

## 4. Running each lab live (what to point out)

**Labs 1–2 — A model becomes an app (Chatbot → Memory).** On *Chatbot*, send a message; the **Under the hood** panel shows the two views side by side — (1) the JSON `messages[]` your app sends to the API vs. (2) the single flattened token stream the model actually continues. Change the system prompt ("answer only in haiku") and resend; then send a follow-up and note it has *no memory*. On *Memory*, the same idea plus the conversation history replayed each turn — a follow-up like "and how do I undo that?" now works (point at the Memory panel below the app). Takeaway: an app is configuration over a model call; memory is that history, re-sent every turn (and it isn't free).

**Lab 3 — It will answer anything (Guardrails).** The bot is scoped to Northwind support. Ask a Northwind question, then ask something off-topic ("write me a poem") with **guardrails ON** (an independent pre-flight check blocks it) vs **OFF** (it wanders). Invite attendees to sneak past it. Takeaway: a scoped prompt isn't enough — you add a separate check, and governance starts here.

**Labs 4–5 — Ground it, then break it (Grounding & RAG → Build & break a RAG).** On *Grounding & RAG*, ask "how long do enterprise customers have for a refund?" Show the retrieved chunks, then the **assembled prompt** (the engineered context), then the grounded, cited answer; tick "show the ungrounded answer" to contrast. On *Build & break a RAG*, use the sliders to sabotage chunking / stale docs / a permission leak and watch quality collapse with the model untouched. Takeaway: most RAG failures are **data** failures.

**Lab 6 — It knows, but can't act (Tools & the agent loop).** Run "Is order 4471 within the refund window?" Watch the agent loop (plan → call a tool → observe), then the irreversible write held at a **human approval gate** — approve, deny, or let it run autonomously. Takeaway: adding a capability is adding a *tool*, with the risky action gated by a human.

**Lab 7 — Agents over MCP + A2A (Multi-agent & governance).** Run the refund workflow for order 4471. Show the A2A message timeline, the tools reaching a **real MCP server**, the RBAC table (only the action agent may issue a refund — expand "prove RBAC" to see a read-side write blocked), the **approval gate** (nothing executes until you click Approve), and the audit log. Takeaway: capability is not authorization — autonomy made safe with governance controls.

---

## 5. The OpenAI key — setup & safety

- Create a **dedicated, project-scoped key** with a **hard budget cap** ($25–50 is plenty).
- The demos default to **`gpt-4o-mini`**, cap output tokens, and enforce a **per-session request limit** — so a shared key can't run up a surprise bill.
- The key is entered in the sidebar and held **in browser session memory only** — never written to disk or logged.
- **Revoke the key right after the workshop.**
- Optional: to skip the paste, set `openai_api_key` in `.streamlit/secrets.toml` (see `live-demos/.streamlit` patterns), but pasting is the default.

Rough cost: each lab is a handful of small `gpt-4o-mini` calls; a room of faculty clicking through all seven labs is typically a few dollars, not tens.

---

## 6. Distributing to attendees

Three options, easiest first:

1. **You drive, they watch** (screen-share) — zero attendee setup; best for the live session.
2. **Attendees run locally** — they need Docker Desktop + the key; hand out the repo URL and §3.
3. **One shared instance** — run the container on a laptop/VM and share the URL on the room network (it's a plain Streamlit app on a port). Add a passphrase if you expose it widely.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| "OpenAI call failed: …auth…" | Wrong/empty key — re-paste in the sidebar. |
| First model reply is slow | Normal cold start; subsequent calls are quick. |
| "Per-session request limit reached" | A safety cap — refresh the page to reset. |
| Port 8501 in use | Change the mapping in `docker-compose.yml`. |
| Build is slow the first time | One-time image build; cached afterward. |

---

## 8. How this fits the rest of the kit

- **Deck** — the live-demos slide points here.
- **`prior-auth-agent/`** — the applied **Case**: the seven labs assembled into one agentic workflow (Prior-Authorization Triage) — specialist agents over A2A + a real MCP server, RAG-grounded, LLM-critic evaluation, human approval gate + audit. Runs via Docker; synthetic data.
- **`course-content-studio/`** — a larger applied build (vector DB + database + MCP) that turns course materials into a Canvas quiz.
- **`mcp-lab/`** — the real MCP protocol over Docker, for anyone who wants Lab 7's tools/MCP at protocol depth.
