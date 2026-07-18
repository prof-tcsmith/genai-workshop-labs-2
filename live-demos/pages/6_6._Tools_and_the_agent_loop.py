"""Tools & the agent loop — an agent that ACTS, on a leash.

This page merges two ideas:

  * the earlier **MCP-style tool server** — the model is the MCP *client*; a small
    in-process *server* (`ToolServer`) advertises tools and executes them. We can
    watch every REQUEST/RESPONSE round-trip.
  * The workshop's **agent loop** — give the agent a goal and it runs
    *plan → call a tool → observe the result → repeat* until it can answer.

The new piece is **control**: some tools only *read* (safe to run automatically),
but some *write* / are irreversible (`issue_refund`). Before any write tool runs
we stop the loop at a **human approval gate** — a real person must approve the
exact action and arguments before it executes. The whole trace is visible so
participants can see the plan, each tool call, each observation, and where the
gate caught a write.
"""
import ast
import json
import operator

import streamlit as st

from shared import store
from shared.core import boot, chat, layer_badge
from shared.slides import render_slides

client = boot("6 · Tools & the agent loop")

st.title("6 · Tools & the agent loop")
layer_badge([2, 3, 5])
st.caption("🧭 **Tool use + approvals:** the model acts — plan → call → observe, on a leash.")
st.caption(
    "The model can now **act**. It runs an **agent loop** — plan → call a tool → "
    "observe → repeat — over an MCP-style tool server, with a **human approval "
    "gate** in front of any write/irreversible action."
)
render_slides("tools-agent-loop")

# --- Mock enterprise data the tools reach into ------------------------------
MOCK_ORDERS = {
    "4471": {"placed_days_ago": 12, "status": "delivered", "amount": 240.0, "customer_type": "enterprise"},
    "5012": {"placed_days_ago": 60, "status": "delivered", "amount": 90.0, "customer_type": "standard"},
}

# Safe arithmetic: an allow-list of AST node types -> operations. No eval().
_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(node):
    """Recursively evaluate a parsed arithmetic AST. Anything unexpected raises."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    # Python 3.8+ literals are ast.Constant; we only allow numbers.
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("only numeric constants are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


class ToolServer:
    """An in-process MCP-style tool server: advertises tools and executes them.

    Tools split into two kinds:
      * READ tools (get_order, search_kb, calculator) — safe, run automatically.
      * WRITE tools (issue_refund) — irreversible; gated behind human approval.
    """

    WRITE_TOOLS = {"issue_refund"}

    def __init__(self, client):
        self.client = client

    def list_tools(self):
        """The server's catalog, in OpenAI tools (JSON-schema) format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_order",
                    "description": "Look up an order by its ID. Returns status, amount, "
                                   "how many days ago it was placed, and customer type.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "The order ID, e.g. '4471'."}
                        },
                        "required": ["order_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_kb",
                    "description": "Search the support knowledge base and refund policy for "
                                   "relevant passages. Use this for policy questions like the "
                                   "refund window.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What to look up."}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Evaluate a basic arithmetic expression (e.g. '60 - 12'). "
                                   "Supports + - * / // % ** and parentheses.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "Arithmetic expression."}
                        },
                        "required": ["expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "issue_refund",
                    "description": "WRITE / IRREVERSIBLE: issue a refund for an order. Only call "
                                   "this once you have confirmed the order and the policy allow it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "The order to refund."},
                            "amount": {"type": "number", "description": "Refund amount in dollars."},
                        },
                        "required": ["order_id", "amount"],
                    },
                },
            },
        ]

    def is_write(self, name: str) -> bool:
        return name in self.WRITE_TOOLS

    # --- The actual tool implementations -------------------------------------
    def _get_order(self, order_id: str) -> dict:
        order = MOCK_ORDERS.get(str(order_id).strip())
        if order is None:
            return {"error": f"no order found with id {order_id!r}"}
        return {"order_id": str(order_id).strip(), **order}

    def _kb_index(self):
        """Build the KB index once per session and cache it (search_kb tool)."""
        if "kb_index" not in st.session_state:
            docs = store.load_corpus(["support_kb", "refund_policy"])
            st.session_state["kb_index"] = store.build_index(self.client, docs)
        return st.session_state["kb_index"]

    def _search_kb(self, query: str) -> dict:
        hits = store.search(self.client, self._kb_index(), query, k=3)
        return {
            "query": query,
            "results": [
                {"doc": item["doc"], "score": round(score, 3), "text": item["text"]}
                for item, score in hits
            ],
        }

    def _calculator(self, expression: str) -> dict:
        try:
            value = _safe_eval(ast.parse(str(expression), mode="eval"))
            return {"expression": expression, "result": value}
        except Exception as e:  # malformed / disallowed input -> structured error
            return {"expression": expression, "error": str(e)}

    def _issue_refund(self, order_id: str, amount: float) -> dict:
        # Mock side effect — in a real system this would hit billing.
        return {"status": "refunded", "order_id": str(order_id).strip(), "amount": amount}

    def call_tool(self, name: str, args: dict) -> dict:
        """Dispatch a tool call from the client to the right implementation."""
        if name == "get_order":
            return self._get_order(args.get("order_id", ""))
        if name == "search_kb":
            return self._search_kb(args.get("query", ""))
        if name == "calculator":
            return self._calculator(args.get("expression", ""))
        if name == "issue_refund":
            return self._issue_refund(args.get("order_id", ""), args.get("amount", 0))
        return {"error": f"unknown tool {name!r}"}


server = ToolServer(client)
TOOLS = server.list_tools()

# --- Show the server's advertised catalog (what MCP "list_tools" returns) -----
st.subheader("🧰 Tools advertised by the MCP server")
st.caption("The model sees exactly these names + descriptions. **Write** tools are gated.")
for spec in TOOLS:
    fn = spec["function"]
    tag = "✍️ **write**" if server.is_write(fn["name"]) else "🔧 read"
    st.markdown(f"- {tag} · **`{fn['name']}`** — {fn['description']}")

st.divider()

SYSTEM_PROMPT = (
    "You are an operations agent. Use the tools to gather facts before you act. "
    "Look up orders with get_order, check policy with search_kb, and do math with "
    "calculator. Do NOT guess — call tools. Only call issue_refund once the order "
    "and the policy clearly justify it. When you have enough information, give a "
    "clear, concise final answer."
)

GATE_PENDING = "blocked: this write/irreversible action requires human approval"


def _parse_args(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _render_step(entry):
    """Render one plan/act/observe step as an MCP request + response round-trip."""
    with st.container(border=True):
        icon = "✍️" if server.is_write(entry["name"]) else "🔧"
        header = f"**Step {entry['step']} — {icon} `{entry['name']}`**"
        if entry.get("gated"):
            header += " ⛔ *held at approval gate*"
        st.markdown(header)
        if entry.get("plan"):
            st.caption("🧠 PLAN (the model's reasoning before this call)")
            st.markdown(f"> {entry['plan']}")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("➡️ MCP REQUEST (client → server: call_tool)")
            st.json({"tool": entry["name"], "arguments": entry["args"]})
        with col2:
            st.caption("⬅️ OBSERVED RESULT (server → client)")
            st.json(entry["result"])


def _run_loop(state):
    """Resume the agent loop until it finishes, stops, or hits the approval gate.

    Mutates `state` (kept in session_state so the approval button can resume it).
    """
    messages = state["messages"]
    while state["step"] < state["max_steps"]:
        # The model acts as the MCP CLIENT — plan + decide which tool(s) to call.
        resp = chat(client, messages, tools=TOOLS, tool_choice="auto", max_tokens=600)
        m = resp.choices[0].message
        if not m.tool_calls:
            state["final"] = m.content or "(no answer)"
            state["status"] = "done"
            return
        state["step"] += 1
        plan = (m.content or "").strip()
        # Record the assistant turn (with its tool_calls) EXACTLY as the API needs.
        messages.append({
            "role": "assistant",
            "content": m.content or "",
            "tool_calls": [tc.model_dump() for tc in m.tool_calls],
        })
        for tc in m.tool_calls:
            name = tc.function.name
            args = _parse_args(tc.function.arguments)
            if server.is_write(name) and state["gate"]:
                # HUMAN APPROVAL GATE: stop the loop and surface the proposed write.
                state["pending"] = {
                    "tool_call_id": tc.id, "name": name, "args": args,
                    "step": state["step"], "plan": plan,
                }
                result = {"status": "blocked", "reason": GATE_PENDING}
                state["trace"].append({
                    "step": state["step"], "name": name, "args": args,
                    "result": result, "plan": plan, "gated": True,
                })
                # Don't reply to this tool_call_id yet — we resume after approval.
                state["status"] = "awaiting_approval"
                return
            result = server.call_tool(name, args)
            state["trace"].append({
                "step": state["step"], "name": name, "args": args,
                "result": result, "plan": plan, "gated": False,
            })
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
            plan = ""  # only attach the plan to the first call of a multi-call turn
    state["final"] = "(stopped after the max-step safety cap)"
    state["status"] = "max_steps"


# --- The goal + controls ------------------------------------------------------
gate = st.toggle(
    "Require human approval for write / irreversible actions", value=True,
    help="When on, the loop pauses before any write tool (issue_refund) runs.",
)
goal = st.text_area(
    "Goal for the agent (what you want done)",
    "Decide whether order 4471 is within the refund window, and if so, issue the refund.",
    height=70,
)
max_steps = st.slider("Max agent steps", 1, 8, 6, help="Safety cap on the loop.")

if st.button("Run agent", type="primary"):
    st.session_state["agent6"] = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": goal},
        ],
        "trace": [],
        "pending": None,
        "step": 0,
        "max_steps": max_steps,
        "gate": gate,
        "final": None,
        "status": "running",
    }
    _run_loop(st.session_state["agent6"])

state = st.session_state.get("agent6")
if state:
    # --- The visible trace: plan → call → observe, step by step ---------------
    st.subheader("🔁 Agent loop (plan → call tool → observe → repeat)")
    if not state["trace"]:
        st.caption("No tool calls yet.")
    for entry in state["trace"]:
        _render_step(entry)

    # --- The approval gate ----------------------------------------------------
    pending = state.get("pending")
    if state["status"] == "awaiting_approval" and pending:
        st.warning(
            "**Approval gate held.** The agent planned a write/irreversible action. "
            "A human must approve the exact tool + arguments before it runs."
        )
        with st.container(border=True):
            st.markdown(f"Proposed write: `{pending['name']}({json.dumps(pending['args'])})`")
            cols = st.columns(2)
            if cols[0].button("✅ Approve & run", type="primary"):
                # Execute the held write on the server, feed the result back, resume.
                result = server.call_tool(pending["name"], pending["args"])
                # Update the gated trace entry in place to show what actually ran.
                for entry in state["trace"]:
                    if entry["step"] == pending["step"] and entry["name"] == pending["name"]:
                        entry["result"] = result
                        entry["gated"] = False
                state["messages"].append({
                    "role": "tool", "tool_call_id": pending["tool_call_id"],
                    "content": json.dumps(result),
                })
                state["pending"] = None
                state["status"] = "running"
                _run_loop(state)
                st.rerun()
            if cols[1].button("🚫 Deny"):
                # Tell the model the write was denied; let it wrap up without it.
                state["messages"].append({
                    "role": "tool", "tool_call_id": pending["tool_call_id"],
                    "content": json.dumps({"status": "denied", "reason": "human declined the write"}),
                })
                for entry in state["trace"]:
                    if entry["step"] == pending["step"] and entry["name"] == pending["name"]:
                        entry["result"] = {"status": "denied", "reason": "human declined the write"}
                        entry["gated"] = False
                state["pending"] = None
                state["status"] = "running"
                _run_loop(state)
                st.rerun()

    # --- Final answer ---------------------------------------------------------
    if state["status"] in ("done", "max_steps") and state["final"] is not None:
        st.subheader("✅ Final answer")
        st.write(state["final"])
        if state["status"] == "max_steps":
            st.info("The loop hit its step cap before finishing.")
        elif not state["gate"]:
            st.info(
                "Approval gate is **off** — any write ran autonomously. Turn the gate "
                "on and re-run to see the loop pause for a human."
            )

    # --- The transcript, for the curious -------------------------------------
    with st.expander("🔎 Full trace (every plan / call / observed result)"):
        st.json(state["trace"])
    with st.expander("🧠 Raw message log sent to the API"):
        st.caption("Note the assistant `tool_calls` turns and the role:'tool' replies — "
                   "the exact transcript the MCP client and server exchanged.")
        st.json(state["messages"])

st.divider()
st.caption(
    "The loop is simple. The discipline is in which actions get a gate, how many "
    "steps are allowed, and what gets logged. The real MCP protocol over Docker is "
    "in the repo's `mcp-lab/`."
)

st.warning(
    "**What's missing — it's a single agent with ad-hoc controls.** Real systems "
    "run multiple specialist agents and need real governance. "
    "**➡️ Next — Multi-agent & governance.**"
)
