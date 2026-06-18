import json

import streamlit as st

from lib.llm import boot, chat
from lib import rag

client = boot("Grounding: prompt → retrieval → tool")

st.title("Grounding: prompt → retrieval → tool-use")
st.caption("Layers 3–4 · Same question, three levels of grounding. Watch the answer become verifiable.")

# A mock enterprise system (Layer 5) the tool reads from.
ORDERS = {
    "4471": {"order_id": "4471", "placed_days_ago": 12, "status": "delivered", "amount": 240.0, "customer_type": "enterprise"},
    "5012": {"order_id": "5012", "placed_days_ago": 60, "status": "delivered", "amount": 90.0, "customer_type": "standard"},
}


def get_order(order_id: str):
    return ORDERS.get(str(order_id).strip(), {"error": f"order {order_id} not found"})


# Build (and cache) the in-memory index over the refund policy.
if "ground_index" not in st.session_state:
    with st.spinner("Embedding the refund policy…"):
        st.session_state["ground_index"] = rag.build_index(client, rag.load_corpus(["refund_policy"]))
index = st.session_state["ground_index"]

q = st.text_input("Question", "What is our refund window for enterprise customers, and is order #4471 eligible?")
mode = st.radio("Mode", ["Prompt only", "+ Retrieval", "+ Tool use"], horizontal=True)
st.caption("Known orders: 4471 (enterprise, 12 days ago) · 5012 (standard, 60 days ago)")

if st.button("Run", type="primary"):
    if mode == "Prompt only":
        msgs = [
            {"role": "system", "content": "You are a customer-support assistant. Answer concisely."},
            {"role": "user", "content": q},
        ]
        ans = chat(client, msgs).choices[0].message.content
        st.subheader("Answer")
        st.write(ans)
        st.warning("**Prompt only** — fluent but *unverifiable*. The model is guessing from training data, with no link to your policy or this order.")

    elif mode == "+ Retrieval":
        hits = rag.search(client, index, q, k=3)
        context = "\n\n".join(f"[{d['doc']}] {d['text']}" for d, _ in hits)
        msgs = [
            {"role": "system", "content": "Answer ONLY using the policy context provided. Quote the relevant rule. If the answer is not in the context, say so."},
            {"role": "user", "content": f"Policy context:\n{context}\n\nQuestion: {q}"},
        ]
        ans = chat(client, msgs).choices[0].message.content
        st.subheader("Answer")
        st.write(ans)
        with st.expander("What the model saw (retrieved context)"):
            for d, s in hits:
                st.markdown(f"**{d['doc']}** · score {s:.2f}\n\n> {d['text']}")
        st.info("**+ Retrieval** — grounded in your policy and quotable. But still blind to live order data.")

    else:  # + Tool use
        hits = rag.search(client, index, q, k=3)
        context = "\n\n".join(f"[{d['doc']}] {d['text']}" for d, _ in hits)
        tools = [{
            "type": "function",
            "function": {
                "name": "get_order",
                "description": "Look up an order by id. Returns days since placed, status, amount, customer_type.",
                "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
            },
        }]
        msgs = [
            {"role": "system", "content": "Use the policy context AND live order data. Call get_order for any order mentioned. Cite the policy rule and the order facts, then give a clear yes/no."},
            {"role": "user", "content": f"Policy context:\n{context}\n\nQuestion: {q}"},
        ]
        trace = []
        ans = "(no answer)"
        for _ in range(4):
            resp = chat(client, msgs, tools=tools, tool_choice="auto")
            m = resp.choices[0].message
            if m.tool_calls:
                msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
                for tc in m.tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    result = get_order(**args) if tc.function.name == "get_order" else {"error": "unknown tool"}
                    trace.append((tc.function.name, args, result))
                    msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
                continue
            ans = m.content
            break
        st.subheader("Answer")
        st.write(ans)
        if trace:
            with st.expander("Tool calls (live data)", expanded=True):
                for name, args, res in trace:
                    st.markdown(f"`{name}({args})` → `{res}`")
        st.success("**+ Tool use** — grounded, *current, and traceable*: a cited policy plus a live, logged tool call you can audit.")

st.divider()
st.caption("Try the same question in each mode. Notice how only the last one can actually answer 'is #4471 eligible?'.")
