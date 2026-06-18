"""Level 4 · MCP + tools — an agent that can ACT.

Versus Level 3 (the model could only READ retrieved context) this page gives the
model TOOLS it can call. The tools are advertised by a small in-process
"MCP-style" server (`ToolServer`). The model plays the role of the MCP CLIENT:

    model (client)  --REQUEST-->  ToolServer  --runs-->  a tool
    model (client)  <-RESPONSE--  ToolServer  <-result--  a tool

We run an agent loop: ask the model with tools attached; when it asks to call a
tool we execute it on the server, feed the result back, and continue until the
model produces a final answer. This is exactly the MCP client/server/tool dance,
just collapsed into one process so participants can see every message.
"""
import ast
import json
import operator

import streamlit as st

from shared import store
from shared.core import boot, chat, layer_badge

client = boot("Level 4 · MCP + tools")

st.title("Level 4 · MCP + tools")
layer_badge([2, 3, 5])
st.caption(
    "An **agent that can act**. The model is the MCP **client**; a small in-process "
    "**server** advertises tools it can call. Layer 2 (orchestration) runs the loop, "
    "Layer 3 (model) decides which tool to use, Layer 5 (enterprise systems) is what "
    "the tools reach into — orders, the knowledge base, a calculator."
)

# --- Mock enterprise data the tools reach into (Layer 5) ----------------------
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
    """An in-process MCP-style tool server: advertises tools and executes them."""

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
        ]

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

    def call_tool(self, name: str, args: dict) -> dict:
        """Dispatch a tool call from the client to the right implementation."""
        if name == "get_order":
            return self._get_order(args.get("order_id", ""))
        if name == "search_kb":
            return self._search_kb(args.get("query", ""))
        if name == "calculator":
            return self._calculator(args.get("expression", ""))
        return {"error": f"unknown tool {name!r}"}


server = ToolServer(client)
TOOLS = server.list_tools()

# --- Show the server's advertised catalog (what MCP "list_tools" returns) -----
st.subheader("🧰 Tools advertised by the MCP server")
st.caption("This is the server's catalog — the model sees exactly these names + descriptions.")
for spec in TOOLS:
    fn = spec["function"]
    st.markdown(f"- **`{fn['name']}`** — {fn['description']}")

st.divider()

# --- The goal + the agent loop ------------------------------------------------
goal = st.text_area(
    "Goal for the agent (Layer 1 — what you want done)",
    "Is order 4471 within the refund window? Use the tools.",
    height=70,
)
max_steps = st.slider("Max agent steps", 1, 8, 6, help="Safety cap on the loop.")

SYSTEM_PROMPT = (
    "You are a support agent. Use the available tools to gather facts before "
    "answering. Look up orders with get_order, check policy with search_kb, and "
    "do math with calculator. Do not guess — call tools. When you have enough "
    "information, give a clear, concise final answer."
)

if st.button("Run agent", type="primary"):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]
    trace = []          # request/response pairs for the visible MCP trace
    final_answer = None

    st.subheader("🔁 Agent loop (MCP client ↔ server ↔ tool)")
    for step in range(max_steps):
        # The model acts as the MCP CLIENT: it sees the tool catalog and may
        # choose to call one or more tools, or to answer directly.
        resp = chat(client, messages, tools=TOOLS, tool_choice="auto")
        m = resp.choices[0].message

        if not m.tool_calls:
            # No more tool requests -> this is the final answer.
            final_answer = m.content or ""
            break

        # Record the assistant turn (with its tool_calls) EXACTLY as the API needs.
        messages.append({
            "role": "assistant",
            "content": m.content or "",
            "tool_calls": [tc.model_dump() for tc in m.tool_calls],
        })

        # Execute each requested tool on the server and feed results back.
        for tc in m.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            result = server.call_tool(name, args)
            trace.append({"step": step + 1, "name": name, "args": args, "result": result})

            # Render this round-trip as an MCP REQUEST + RESPONSE.
            with st.container(border=True):
                st.markdown(f"**Step {step + 1} — `{name}`**")
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("➡️ MCP REQUEST (client → server: call_tool)")
                    st.json({"tool": name, "arguments": args})
                with c2:
                    st.caption("⬅️ MCP RESPONSE (server → client: result)")
                    st.json(result)

            # The tool result goes back as a role:"tool" message keyed by call id.
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })
    else:
        # Loop exhausted without a final answer — ask once more, no tools.
        final_answer = chat(client, messages).choices[0].message.content

    # --- Results --------------------------------------------------------------
    st.subheader("✅ Final answer")
    st.write(final_answer or "_(no answer produced)_")

    with st.expander("🔎 Full trace (every request/response pair)"):
        st.json(trace)

    with st.expander("🧠 Raw message log sent to the model"):
        st.caption("Note the assistant `tool_calls` turns and the role:'tool' replies — "
                   "this is the exact transcript the MCP client and server exchanged.")
        st.json(messages)

st.divider()
st.caption(
    "This mirrors the MCP client→server→tool flow in-process; the real protocol over "
    "Docker is in the repo's `mcp-lab/`."
)
