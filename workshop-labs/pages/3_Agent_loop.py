import ast
import json
import operator

import streamlit as st

from lib.llm import boot, chat
from lib import rag
from lib.slides import render_slides

client = boot("Agent loop with tools")

st.title("Agent loop with tools")
st.caption("Layer 2 · Give a goal; the agent plans → calls a tool → observes → loops. Toggle the approval gate on writes.")
render_slides("agent")

# ---- mock enterprise systems (Layer 5) ----
ORDERS = {
    "4471": {"order_id": "4471", "placed_days_ago": 12, "status": "delivered", "amount": 240.0, "customer_type": "enterprise"},
    "5012": {"order_id": "5012", "placed_days_ago": 60, "status": "delivered", "amount": 90.0, "customer_type": "standard"},
}

if "agent_index" not in st.session_state:
    with st.spinner("Embedding the refund policy…"):
        st.session_state["agent_index"] = rag.build_index(client, rag.load_corpus(["refund_policy"]))
index = st.session_state["agent_index"]

# ---- tools ----
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression: str):
    try:
        return {"result": _safe_eval(ast.parse(str(expression), mode="eval").body)}
    except Exception as e:
        return {"error": f"could not evaluate: {e}"}


def get_order(order_id: str):
    return ORDERS.get(str(order_id).strip(), {"error": f"order {order_id} not found"})


def search_policy(query: str):
    hits = rag.search(client, index, query, k=2)
    return {"snippets": [d["text"] for d, _ in hits]}


def issue_refund(order_id: str, amount: float):
    return {"status": "refunded", "order_id": order_id, "amount": amount}


IMPL = {"calculator": calculator, "get_order": get_order, "search_policy": search_policy, "issue_refund": issue_refund}
WRITE = {"issue_refund"}

TOOLS = [
    {"type": "function", "function": {"name": "calculator", "description": "Evaluate an arithmetic expression.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "get_order", "description": "Look up an order's date, status, amount, customer type.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "search_policy", "description": "Search the refund policy for relevant rules.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "issue_refund", "description": "WRITE: issue a refund for an order.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order_id", "amount"]}}},
]

gate = st.toggle("Require human approval for write actions", value=True)
goal = st.text_input("Goal", "Decide whether order 4471 can be refunded under policy, and if so, issue the refund.")

if st.button("Run agent", type="primary"):
    msgs = [
        {"role": "system", "content": "You are an operations agent. Use tools to gather facts before acting. "
                                       "Check the policy and the order before issuing any refund. Be concise."},
        {"role": "user", "content": goal},
    ]
    trace, pending = [], []
    final = "(stopped after max steps)"
    for _ in range(6):
        resp = chat(client, msgs, tools=TOOLS, tool_choice="auto")
        m = resp.choices[0].message
        if not m.tool_calls:
            final = m.content
            break
        msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
        for tc in m.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            if name in WRITE and gate:
                result = {"status": "blocked", "reason": "write action requires human approval"}
                pending.append((name, args))
            else:
                result = IMPL.get(name, lambda **_: {"error": "unknown tool"})(**args)
            trace.append((name, args, result))
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    st.subheader("Trace")
    for i, (name, args, res) in enumerate(trace, 1):
        icon = "✍️" if name in WRITE else "🔧"
        st.markdown(f"{i}. {icon} `{name}({args})` → `{res}`")

    st.subheader("Final answer")
    st.write(final)

    if pending:
        st.warning("**Approval gate held.** The agent wanted to perform a write but it was blocked pending a human:")
        for name, args in pending:
            cols = st.columns([3, 1])
            cols[0].markdown(f"Proposed: `{name}({args})`")
            if cols[1].button("Approve & run", key=f"approve-{name}-{args}"):
                st.success(f"✅ Approved — executed `{name}` (mock): {IMPL[name](**args)}")
    elif not gate:
        st.info("Approval gate is **off** — the agent executed the write autonomously. Turn the gate on and re-run to see the difference.")

st.divider()
st.caption("The loop is simple. The discipline is in which actions get a gate, how many steps are allowed, and what gets logged.")
