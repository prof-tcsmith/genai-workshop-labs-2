"""Shared infrastructure for the 5 progressive live demos.

- One OpenAI key, pasted in the sidebar, held in session memory only.
- Cheap model defaults + a per-session request cap (shared key safety).
- A "layers in play" badge that ties each demo to the 7-layer stack.
"""
from __future__ import annotations

import hashlib
import os

import streamlit as st

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
MAX_TOKENS = 700
REQ_CAP = 120  # soft per-session cap to protect the shared key

STACK = {
    1: "Experience", 2: "Orchestration", 3: "Model", 4: "Retrieval & context",
    5: "Enterprise systems", 6: "Data foundation", 7: "Governance",
}


def _secret(name: str):
    try:
        return st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        return None


def default_key() -> str | None:
    """A workshop default key, from Streamlit secrets or the OPENAI_API_KEY env var.
    Never hard-coded in source — set it in a gitignored secrets.toml or .env."""
    return _secret("openai_api_key") or os.environ.get("OPENAI_API_KEY")


def render_key_sidebar() -> str | None:
    st.sidebar.header("🔑 OpenAI key")
    dflt = default_key()
    # Drive the field from a plain session var via value= so it REPOPULATES on
    # every page (widget state alone doesn't reliably carry across multipage nav).
    entered = st.sidebar.text_input(
        "Your OpenAI key (optional)", type="password",
        value=st.session_state.get("user_key", ""),
        placeholder="workshop default active — paste to override" if dflt else "sk-...",
        help="A workshop default may be configured. Paste your own to use it instead. "
             "Held in this browser session only — never stored or logged.",
    ).strip()
    st.session_state["user_key"] = entered  # remember across page switches
    eff = entered if entered else dflt
    st.session_state["key"] = eff
    if entered:
        st.sidebar.caption("✅ Using **your** key (entered).")
    elif dflt:
        st.sidebar.caption("Using the **workshop default** key.")
    else:
        st.sidebar.caption("No key yet — paste one above.")
    st.sidebar.caption(f"Model `{CHAT_MODEL}` · shared key — please be gentle.")
    return eff


def openai_guard(e: Exception) -> None:
    """Turn an OpenAI exception into a friendly message and stop — never a raw traceback."""
    msg = str(e)
    low = msg.lower()
    if any(s in low for s in ("invalid_api_key", "incorrect api key", "authentication", "no api key")) or "401" in msg:
        st.error("🔑 The OpenAI key was rejected (invalid or expired). Paste a valid key in the sidebar.")
    elif any(s in low for s in ("rate limit", "quota", "insufficient_quota")) or "429" in msg:
        st.error("⏳ The key hit a rate or quota limit. Wait a moment, or paste a different key.")
    else:
        st.error(f"OpenAI request failed: {e}")
    st.stop()


def get_client():
    k = st.session_state.get("key")
    if not k:
        return None
    try:
        from openai import OpenAI
    except Exception:
        st.error("The `openai` package is not installed.")
        st.stop()
    return OpenAI(api_key=k)


def ensure_access() -> None:
    """Gate the app behind a participant code — but ONLY when one is configured.

    On Streamlit Community Cloud, set ``workshop_passphrase_sha256`` (the SHA-256
    hash of the code, never the code itself) in the app's Secrets to require it.
    When no code is configured (e.g. local Docker), the gate is disabled so there
    is zero friction running it yourself.
    """
    expected_hash = _secret("workshop_passphrase_sha256")
    expected_plain = _secret("workshop_passphrase")  # local-dev fallback only
    if not expected_hash and not expected_plain:
        return
    if st.session_state.get("_pass_ok"):
        return
    st.title("🔒 Enterprise AI — live demos")
    st.caption("Enter the participant code from the workshop to continue.")
    pw = st.text_input("Participant code", type="password")
    if st.button("Enter"):
        if expected_hash:
            ok = hashlib.sha256(pw.encode("utf-8")).hexdigest() == str(expected_hash).strip().lower()
        else:
            ok = pw == expected_plain
        if ok:
            st.session_state["_pass_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect code.")
    st.stop()


def boot(title: str):
    """Top of every demo page: config, gate, key entry, return a ready client (or stop)."""
    st.set_page_config(page_title=title, page_icon="🎬", layout="wide")
    ensure_access()
    render_key_sidebar()
    client = get_client()
    if client is None:
        st.title(title)
        st.info("⬅️ Paste the OpenAI key in the sidebar to run this demo.")
        st.stop()
    return client


def layer_badge(layers: list[int]) -> None:
    chips = " · ".join(f"**{i}** {STACK[i]}" for i in layers)
    st.caption("🧱 Layers in play: " + chips)


def _bump() -> None:
    n = st.session_state.get("_reqs", 0) + 1
    st.session_state["_reqs"] = n
    if n > REQ_CAP:
        st.error("Per-session request limit reached (protects the shared key). Refresh to reset.")
        st.stop()


def chat(client, messages, tools=None, tool_choice=None, model: str | None = None,
         max_tokens: int = MAX_TOKENS, temperature: float = 0.3):
    """chat.completions wrapper with caps + a session request counter."""
    _bump()
    kw = dict(model=model or CHAT_MODEL, messages=messages, max_tokens=max_tokens, temperature=temperature)
    if tools:
        kw["tools"] = tools
    if tool_choice:
        kw["tool_choice"] = tool_choice
    try:
        return client.chat.completions.create(**kw)
    except Exception as e:
        openai_guard(e)


def stream_assistant(client, messages, *, tools=None, tool_choice=None, model: str | None = None,
                     max_tokens: int = MAX_TOKENS, temperature: float = 0.3, placeholder=None):
    """Stream a chat completion, rendering text live into `placeholder` (an st.empty()).

    Returns (content_text, tool_calls) where tool_calls is a list of
    {"id","name","args"} dicts. Works for plain answers and for tool-using steps
    (tool-call deltas are accumulated; little/no text streams on those steps).
    """
    _bump()
    kw = dict(model=model or CHAT_MODEL, messages=messages, max_tokens=max_tokens,
              temperature=temperature, stream=True)
    if tools:
        kw["tools"] = tools
    if tool_choice:
        kw["tool_choice"] = tool_choice
    try:
        stream = client.chat.completions.create(**kw)
    except Exception as e:
        openai_guard(e)
        return "", []

    content = ""
    calls: dict[int, dict] = {}
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            content += delta.content
            if placeholder is not None:
                placeholder.markdown(content + "▌")
        if getattr(delta, "tool_calls", None):
            for tc in delta.tool_calls:
                slot = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        slot["name"] += tc.function.name
                    if tc.function.arguments:
                        slot["args"] += tc.function.arguments
    if placeholder is not None and content:
        placeholder.markdown(content)  # drop the cursor
    return content, [calls[i] for i in sorted(calls)]


def tool_calls_to_message(content: str, calls: list[dict]) -> dict:
    """Rebuild the OpenAI assistant message (with tool_calls) from stream_assistant output."""
    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"]}}
            for c in calls
        ],
    }
