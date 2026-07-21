# Participant Guide — GenAI Workshop Labs

**(c) Dr. Tim Smith, 2026**

## Overview

In this hands-on portion you'll run a set of small AI applications on **your own laptop**
and watch how an AI system grows, one capability at a time, from a bare chatbot to a
governed multi-agent system. Everything runs in Docker containers that you pull with one
command — no coding required, and nothing is installed permanently except the tools below.

You'll need a **model API key**. You can run on **OpenAI** *or* **Anthropic (Claude)** —
pick the provider in the app's sidebar. The facilitator will provide a key at the session
(or use your own). **The key is never stored in this repository** — you paste it in the
sidebar, or put it in a gitignored local file.

## Summary — the seven labs

Each lab breaks the one before it — a working system, then the failure that forces the next piece. A **lab** is one app page (the sidebar's own numbering), and each lab has its own two-page sheet in the handout.

| Lab | What you'll see |
|---|---|
| 1 · A model becomes an app | a system prompt + one message — the whole app is two messages; behavior lives in the context, and the model sees one token stream, not your JSON |
| 2 · It forgets your last sentence | the same bot with memory: the history replayed each turn — follow-ups work, and the prompt grows every turn |
| 3 · It will answer anything | a support bot with a fail-closed scope check you can watch fire; guardrails |
| 4 · Ground it in your documents | model-alone vs. grounded + cited answers over a small corpus — or an honest abstain |
| 5 · Then break it | sabotage chunking / staleness / permissions and watch quality collapse, model untouched |
| 6 · It knows, but can't act | an agent calls tools in a plan→act→observe loop, with a human approval gate |
| 7 · Agents over MCP + A2A | agents collaborate under RBAC, an approval gate, and an audit log |

**Take-home deeper labs** (run these after the session):

| Lab | What you'll see |
|---|---|
| 8 · Red-team & govern | run injection / exfiltration / unauthorized-write attacks, then enable controls |
| 9 · Evaluate & validate | run a golden-set eval + LLM-as-judge + abstention check → a go/no-go |

---

## Before the session — install these

You need four things. Install them **before** the session and verify them (commands below).

1. **A terminal running bash.**
   - **macOS:** the built-in *Terminal* app (zsh is fine; `bash` is available).
   - **Windows:** install **WSL2** (Ubuntu) — open *PowerShell* as admin and run `wsl --install`, then use the Ubuntu terminal.
   - **Linux:** your usual terminal.

2. **Docker + Docker Compose.** Either:
   - **Docker Desktop** — https://www.docker.com/products/docker-desktop/ (Mac/Windows/Linux), **or**
   - **OrbStack** (macOS, lightweight) — https://orbstack.dev/
   Compose is included with both. **Start Docker Desktop / OrbStack so the engine is running.**

3. **git** — https://git-scm.com/downloads (macOS: `git` ships with the Xcode command-line tools).

### Verify everything (paste into your terminal)
Run these **one line at a time** (each should print a version; `docker info` should print engine details):
```bash
bash --version
git --version
docker --version
docker compose version
docker info
```
Notes:
- `bash` 3.2+ is fine. If `docker info` shows *"Cannot connect to the Docker daemon,"* your Docker
  engine isn't running — open **Docker Desktop** (or **OrbStack**), wait a few seconds, and retry.
- Don't paste a `#` comment after a command — some shells pass the comment to the program as
  arguments (e.g. `docker info  # note` can error with *"accepts no arguments"*). Just run the bare command.

---

## Step-by-step

### 1. Get the code
```bash
git clone https://github.com/prof-tcsmith/genai-workshop-labs.git
cd genai-workshop-labs
```

### 2. Provide the model key (two options)
- **Easiest:** skip this step and, when the app opens, **pick a provider (OpenAI or
  Anthropic) in the sidebar and paste the matching key.** It's held in your browser
  session only.
- **Or set it once:** copy the example env file and fill it in:
  ```bash
  cp .env.example .env
  ```
  Then open `.env` and set `LLM_PROVIDER` (`openai` or `anthropic`) and the matching
  key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`). (`.env` is git-ignored, so your key
  won't be committed.)

### 3. Start the demos
```bash
docker compose up
```
The first run pulls the images from Docker Hub (a minute or two). When it's ready you'll see
a copyright banner and a line like `You can now view your Streamlit app … :8501`.

### 4. Open the apps in your browser
- **Live demos:** http://localhost:8501
- **MCP lab (advanced):** http://localhost:8000

In the live demos, **pick a provider and paste the key** in the left sidebar (unless you set
`.env`), then use the sidebar to work through the **seven labs in order** — each stage breaks the one before.

### 5. What to try in each lab
- **Lab 1 — A model becomes an app (Chatbot):** change the system prompt (e.g., "answer only in haiku") and resend — same model, new behavior. Compare the two Under-the-hood panels: JSON to the API vs. the one token stream the model continues.
- **Lab 2 — It forgets your last sentence (Memory):** ask a question, then a follow-up that depends on it — now it remembers; watch the memory panel grow each turn.
- **Lab 3 — It will answer anything (Guardrails):** ask an on-topic question, then something off-topic with the guardrail ON vs OFF.
- **Lab 4 — Ground it in your documents (Grounding & RAG):** ask a policy question; compare the model-alone answer with the grounded, cited one — then ask something the corpus can't answer and watch it abstain.
- **Lab 5 — Then break it (Build & break a RAG):** flip the sabotage switches (tiny chunks / stale doc / restricted doc) and watch quality fall with the model untouched.
- **Lab 6 — It knows, but can't act (Tools & the agent loop):** run a task that needs a tool; watch the plan→call→observe trace and the approval gate.
- **Lab 7 — Agents over MCP + A2A (Multi-agent & governance):** run the refund workflow; approve/deny the gated action; read the audit log.
- **Take-home — Red-team & govern:** run an attack preset, then enable controls one at a time and watch defense-in-depth hold.

### 6. (Optional) The Case — the seven labs, assembled
The **Prior-Authorization Triage** Case (`prior-auth-agent/`) puts all seven labs together into one
agentic workflow: specialist agents over **A2A** reach tools through a **real MCP server**, decide a
*synthetic* coverage request grounded in retrieved policy, an **LLM critic** checks the draft, and a
**human approves** before anything is finalized — with a full audit log. Run it with Docker (OpenAI key only):
```bash
cd prior-auth-agent
docker compose up
```
*Synthetic data — a demonstration of AI system architecture, not medical advice.*

### 7. Stop and clean up
- Stop: press **Ctrl-C** in the terminal.
- Remove the containers: `docker compose down`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker info` errors | Start Docker Desktop / OrbStack and retry. |
| "port is already allocated" | Something else uses 8501/8000 — stop it, or ask the facilitator. |
| "The API key was rejected" | Re-paste the key in the sidebar (check for stray spaces; match the provider). |
| First answer is slow | Normal cold start; later calls are quick. |
| `git: command not found` | Install git (see prerequisites). |

---

## Notes
- Your API key (OpenAI or Anthropic) stays in your browser session (or your local `.env`); it is never committed or logged.
- Please don't paste sensitive data — this is a teaching environment, often on a shared key.
- Images: `proftsmith/genai-live-demos` and `proftsmith/genai-mcp-lab` on Docker Hub. **(c) Dr. Tim Smith, 2026.**
