# Multi-Agent Systems and Governance

A single agent can be replaced by several **specialized agents** that collaborate. An
**orchestrator** coordinates them: it plans the work, assigns sub-tasks, and combines
the results. The agents communicate by passing messages to one another — this is
**agent-to-agent (A2A)** communication.

A common pattern is a **research agent** that gathers facts (read-only), an **action
agent** that performs changes (writes), and a **critic agent** that checks the work
before it is accepted. Splitting roles makes each agent simpler and the system easier
to govern.

Collaboration alone is not trustworthy. Trust comes from **governance**:

- **Role-based access control (RBAC)** — each agent may call only the tools its role
  permits. A read-only research agent must never be able to perform a write, even if
  it is tricked into trying.
- **Human approval gates** — no irreversible action (a refund, a publish, a delete)
  executes until a human approves it.
- **Audit log** — an append-only record of every message, tool call, access check, and
  decision, so an auditor can reconstruct exactly what happened and why.

The governing principle is **least privilege**: give each agent the smallest set of
permissions it needs. A capability that an agent never receives cannot be abused.
