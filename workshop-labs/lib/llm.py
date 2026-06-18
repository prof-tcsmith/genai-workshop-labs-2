"""Shared LLM access, key handling, and the passphrase gate for all labs.

Design goals:
- One pasted OpenAI key, held in session memory only (never logged or persisted).
- Optional passphrase gate so the public URL is attendee-only.
- Cheap defaults + caps so a shared key can't run up a big bill.
"""
from __future__ import annotations

import os

import streamlit as st

CHAT_MODEL_DEFAULT = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
MAX_OUTPUT_TOKENS = 700
SESSION_REQUEST_CAP = 80  # soft per-session cap to protect the shared key


def _secret(name: str):
    try:
        return st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        return None


# ---------------------------------------------------------------- access gate
def ensure_access() -> None:
    """If a workshop passphrase is configured, require it before anything else."""
    expected = _secret("workshop_passphrase")
    if not expected:
        return  # gate disabled (local/dev)
    if st.session_state.get("_pass_ok"):
        return
    st.title("🔒 Workshop labs")
    st.write("Enter the workshop passphrase to continue.")
    pw = st.text_input("Passphrase", type="password")
    if st.button("Enter"):
        if pw == expected:
            st.session_state["_pass_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect passphrase.")
    st.stop()


# ------------------------------------------------------------------- key entry
def default_key() -> str | None:
    """A workshop default key, from Streamlit secrets or the OPENAI_API_KEY env var.
    Never hard-coded in source — set it in a gitignored secrets.toml or the Cloud Secrets UI."""
    return _secret("openai_api_key") or os.environ.get("OPENAI_API_KEY")


def render_sidebar_key() -> str | None:
    """Render the OpenAI key field; effective key = user-entered, else workshop default."""
    st.sidebar.header("🔑 OpenAI key")
    dflt = default_key()
    entered = st.sidebar.text_input(
        "Your OpenAI key (optional)", type="password", key="user_key_input",
        placeholder="workshop default active — paste to override" if dflt else "sk-...",
        help="A workshop default may be configured. Paste your own to use it instead. "
             "Held in this browser session only — never stored or logged.",
    )
    eff = entered.strip() if entered and entered.strip() else dflt
    st.session_state["openai_key"] = eff
    if entered and entered.strip():
        st.sidebar.caption("Using **your** key.")
    elif dflt:
        st.sidebar.caption("Using the **workshop default** key.")
    else:
        st.sidebar.caption("No key yet — paste one above.")
    st.sidebar.caption("Model `%s` · shared key — please be gentle." % CHAT_MODEL_DEFAULT)
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
    key = st.session_state.get("openai_key")
    if not key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        st.error("The `openai` package is not installed in this environment.")
        st.stop()
    return OpenAI(api_key=key)


def boot(page_title: str):
    """Call at the top of every lab page. Returns a ready OpenAI client.

    Sets page config, enforces the gate, renders the key field, and stops with a
    friendly message until a key is present.
    """
    st.set_page_config(page_title=page_title, page_icon="🧪", layout="wide")
    ensure_access()
    render_sidebar_key()
    client = get_client()
    if client is None:
        st.title(page_title)
        st.info("⬅️ Paste the workshop OpenAI key in the sidebar to begin.")
        st.stop()
    return client


def home_setup(page_title: str) -> None:
    st.set_page_config(page_title=page_title, page_icon="🧪", layout="wide")
    ensure_access()
    render_sidebar_key()


# ----------------------------------------------------------------- chat helper
def _bump() -> None:
    n = st.session_state.get("_reqs", 0) + 1
    st.session_state["_reqs"] = n
    if n > SESSION_REQUEST_CAP:
        st.error("Per-session request limit reached (protects the shared key). Refresh the page to reset.")
        st.stop()


def chat(client, messages, model: str | None = None, tools=None, tool_choice=None,
         max_tokens: int = MAX_OUTPUT_TOKENS, temperature: float = 0.2):
    """Thin wrapper around chat.completions with caps + a session request counter."""
    _bump()
    kwargs = dict(
        model=model or CHAT_MODEL_DEFAULT,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as e:  # surface auth/rate errors cleanly to attendees
        openai_guard(e)
