# Participant Guide — GenAI Workshop Labs

**(c) Dr. Tim Smith, 2026**

## Overview

In this hands-on portion you'll run a set of small AI applications on **your own laptop**
and watch how an AI system grows, one capability at a time, from a bare chatbot to a
governed multi-agent system. Everything runs in Docker containers that you pull with one
command — no coding required, and nothing is installed permanently except the tools below.

You'll need an **OpenAI API key**; the facilitator will provide one at the session (or you
can use your own). The key is never stored in this repository.

## Summary — the five live demos

| Level | What you'll see | Stack layers |
|---|---|---|
| 1 · Chatbot | a system prompt + one message; no memory, no guardrails | 1, 3 |
| 2 · Memory + guardrails | a support bot that remembers and refuses off-topic requests | 1, 3, 7 |
| 3 · Context engineering | retrieval from an info store; grounded, cited answers | 4, 6 |
| 4 · MCP + tools | an agent that calls tools through an MCP-style server | 2, 5 |
| 5 · A2A + governance | agents collaborating under RBAC, an approval gate, and an audit log | 2, 7 |

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
```bash
bash --version      # any 3.2+ is fine
git --version
docker --version
docker compose version
docker info         # should print engine info — if it errors, start Docker Desktop / OrbStack
```
If `docker info` errors, your Docker engine isn't running yet — open Docker Desktop (or OrbStack) and wait a few seconds.

---

## Step-by-step

### 1. Get the code
```bash
git clone https://github.com/prof-tcsmith/genai-workshop-labs.git
cd genai-workshop-labs
```

### 2. Provide the OpenAI key (two options)
- **Easiest:** skip this step and paste the key into the app's sidebar when it opens.
- **Or set it once:** copy the example env file and paste the key into it:
  ```bash
  cp .env.example .env
  # open .env in any editor and replace sk-proj-your-key-here with the workshop key
  ```
  (`.env` is git-ignored — your key won't be committed.)

### 3. Start the demos
```bash
docker compose up
```
The first run pulls the images from Docker Hub (a minute or two). When it's ready you'll see
a copyright banner and a line like `You can now view your Streamlit app … :8501`.

### 4. Open the apps in your browser
- **Live demos:** http://localhost:8501
- **MCP lab (advanced):** http://localhost:8000

In the live demos, paste the OpenAI key in the left sidebar (unless you set `.env`), then use
the sidebar to walk **Level 1 → Level 5**.

### 5. What to try at each level
- **Level 1 – Chatbot:** change the system prompt (e.g., "answer only in haiku"), resend; note it has no memory.
- **Level 2 – Memory + guardrails:** ask a support question, then a follow-up; then ask something off-topic with guardrails ON vs OFF.
- **Level 3 – Context engineering:** ask a policy question; open the panels showing the retrieved chunks and the assembled context.
- **Level 4 – MCP + tools:** run a task that needs a tool; watch the request/response trace.
- **Level 5 – A2A + governance:** run the refund workflow; approve/deny the gated action; read the audit log.

### 6. Stop and clean up
- Stop: press **Ctrl-C** in the terminal.
- Remove the containers: `docker compose down`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker info` errors | Start Docker Desktop / OrbStack and retry. |
| "port is already allocated" | Something else uses 8501/8000 — stop it, or ask the facilitator. |
| "The OpenAI key was rejected" | Re-paste the key in the sidebar (check for stray spaces). |
| First answer is slow | Normal cold start; later calls are quick. |
| `git: command not found` | Install git (see prerequisites). |

---

## Notes
- Your OpenAI key stays in your browser session (or your local `.env`); it is never committed or logged.
- Please don't paste sensitive data — this is a teaching environment, often on a shared key.
- Images: `proftsmith/genai-live-demos` and `proftsmith/genai-mcp-lab` on Docker Hub. **(c) Dr. Tim Smith, 2026.**
