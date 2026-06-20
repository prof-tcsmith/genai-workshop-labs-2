"""Lab · MCP — decouple the tools.

The same two capabilities from the previous labs (vector search + structured
lookup), now behind ONE MCP server. The app no longer imports ``pinecone`` or
``psycopg`` — it calls named tools over a standard protocol via
``lib.mcp_client``. An agent could call these exact same tools.

By default the MCP server runs **in-process** (in memory) over a real MCP client
session — nothing to host. Set the ``mcp_server_url`` secret to a hosted URL to
switch to a networked (streamable-http) server with no other code change.
"""
import json

import streamlit as st

st.set_page_config(page_title="MCP — decouple the tools", page_icon="🔌", layout="wide")

from lib.config import gate
gate()

from lib import config
from lib.ui import render_deck
from lib import mcp_client


st.title("Lab · MCP — decouple the tools")
st.caption(
    "Same two capabilities — vector search + structured lookup — but now behind "
    "ONE MCP server, reached over one standard protocol. The app calls named "
    "tools; it no longer imports the SDKs or holds their credentials."
)

render_deck("mcp-real")

MODE = mcp_client.mode()
if MODE == "in-process":
    st.success(
        "**MCP mode: in-process.** The app runs the MCP server (from "
        "`lib/mcp_tools.py`) **in memory** and calls it over a real MCP client "
        "session — a genuine client→server→tool round-trip, no host required. "
        "Set the `mcp_server_url` secret to a hosted URL to switch to a networked "
        "server (same app code).",
        icon="🔌",
    )
else:
    st.success(
        f"**MCP mode: remote.** Connected over streamable-http to "
        f"`{config.MCP_SERVER_URL}`.",
        icon="🔌",
    )


# --- The before/after framing ---------------------------------------------
left, right = st.columns(2)
with left:
    st.markdown(
        "#### Before — direct SDK imports\n"
        "- `from lib import vectors` → Pinecone SDK + key\n"
        "- `from lib import db` → psycopg + PG creds\n"
        "- Two SDKs, two cred sets, two shapes **in the app**."
    )
with right:
    st.markdown(
        "#### After — one MCP server\n"
        "- `mcp_client.call_tool('vector_search', …)`\n"
        "- `mcp_client.call_tool('course_lookup', …)`\n"
        "- One protocol; creds + SDKs live **behind the server**."
    )

st.divider()


def _remote_help(msg: str) -> None:
    st.error(msg)
    st.info(
        "A hosted MCP URL is set but unreachable. Either fix the `mcp_server_url` "
        "secret, **or remove it** to use the built-in in-process server. To run "
        "the networked server yourself, see **`mcp-server/README.md`**.",
        icon="🔌",
    )


# --- The server's advertised tool catalog ----------------------------------
st.subheader("🧰 The server's tool catalog")
st.caption(
    "`list_tools()` over MCP — the same catalog a model would see. The app "
    "discovers tools; it doesn't hard-code SDK calls."
)
try:
    tools = mcp_client.list_tools()
    for t in tools:
        with st.expander(f"🔧 {t['name']} — {t.get('description', '')[:80]}"):
            st.markdown(t.get("description") or "_(no description)_")
            if t.get("input_schema"):
                st.markdown("**Input schema** (typed parameters):")
                st.json(t["input_schema"])
except mcp_client.MCPUnavailable as e:
    _remote_help(str(e))

st.divider()


# --- Call a tool via MCP ---------------------------------------------------
st.subheader("📡 Call a tool via MCP")
st.caption(
    "Pick a tool, fill the arguments, and the app sends an MCP `call_tool` "
    "request — no `import pinecone`, no `import psycopg`."
)

tool = st.radio("Tool", ["course_lookup", "vector_search"], horizontal=True)

if tool == "course_lookup":
    st.caption("Returns exact rows from Postgres — try `kind = courses` for live data.")
    c1, c2, c3 = st.columns(3)
    with c1:
        kind = st.selectbox("kind", ["courses", "objectives", "rubric", "bank"])
    with c2:
        course_id_raw = st.text_input("course_id (int, optional)", value="1")
    with c3:
        objective_id_raw = st.text_input("objective_id (int, optional)", value="")
    args = {"kind": kind}
    if course_id_raw.strip():
        try:
            args["course_id"] = int(course_id_raw)
        except ValueError:
            st.warning("course_id must be an integer — ignoring it.")
    if objective_id_raw.strip():
        try:
            args["objective_id"] = int(objective_id_raw)
        except ValueError:
            st.warning("objective_id must be an integer — ignoring it.")
else:
    st.caption(
        "Searches the same Pinecone index as the RAG lab (namespace `lab`) — "
        "ingest content there first, or this returns an empty list."
    )
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        query = st.text_input("query", value="normalization and 3NF")
    with c2:
        top_k = st.number_input("top_k", min_value=1, max_value=20, value=5)
    with c3:
        namespace = st.text_input("namespace", value="lab")
    args = {"query": query, "top_k": int(top_k), "namespace": namespace}

# Show the exact MCP request the app will send.
st.markdown("**➡️ MCP REQUEST** (client → server: `call_tool`)")
st.code(
    "session.call_tool(\n"
    f"    {tool!r},\n"
    f"    {json.dumps(args, indent=4)},\n"
    ")",
    language="python",
)

if st.button("Call tool via MCP", type="primary"):
    try:
        with st.spinner(f"Calling {tool} over MCP ({MODE})…"):
            result = mcp_client.call_tool(tool, args)
        st.markdown("**⬅️ MCP RESPONSE** (server → client: parsed result)")
        st.json(result)
    except mcp_client.MCPUnavailable as e:
        _remote_help(str(e))
    except Exception as e:  # tool ran but errored (e.g. Pinecone/Postgres not set)
        st.error(
            "The MCP call reached the server but the tool failed — usually a "
            "missing credential or unseeded data.\n\n"
            f"```\n{e}\n```"
        )

st.divider()


# --- Teaching note ---------------------------------------------------------
with st.expander("What just happened? (and why an agent could do the same)"):
    st.markdown(
        "1. **One protocol** — the app opened an MCP session and called a "
        "**named tool**. No `pinecone` or `psycopg` import lives in the app.\n"
        "2. **The server owns the tools** — `vector_search` uses `lib.vectors` "
        "and `course_lookup` uses `lib.db`, but that code (and its credentials) "
        "lives behind the server, defined once in `lib/mcp_tools.py`.\n"
        "3. **Decoupled** — swap a tool's implementation, rotate a credential, or "
        "add a third app, and the **contract is unchanged**. The same module runs "
        "in-process here OR as a networked service (just set `mcp_server_url`).\n"
        "4. **An agent could call these same tools.** `list_tools` advertises "
        "names + typed schemas — exactly what a model needs. Next: **assemble a "
        "real app on these tools** (the capstone)."
    )
