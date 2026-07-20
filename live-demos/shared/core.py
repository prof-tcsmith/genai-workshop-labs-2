"""Shared infrastructure for the 8 progressive building blocks.

Provider-configurable: chat runs on **OpenAI** or **Anthropic (Claude)**, chosen
in the sidebar (or via the ``LLM_PROVIDER`` secret/env var). Embeddings always go
through an OpenAI-compatible embeddings provider, because Anthropic has no
embeddings API — a real enterprise lesson: chat and embeddings can be different
vendors, so design to avoid lock-in.

Design:
- One key per provider, pasted in the sidebar, held in session memory only.
- Cheap model defaults + a per-session request cap (shared-key safety).
- Pages stay provider-agnostic: ``chat()`` / ``stream_assistant()`` return the
  same OpenAI-shaped objects regardless of provider — the Anthropic backend
  translates to/from that shape using the official ``anthropic`` SDK.
"""
from __future__ import annotations

import hashlib
import json
import os

import streamlit as st

# --- OpenAI (default chat provider) + embeddings ---
CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
# --- Anthropic (Claude) chat provider — Haiku is the cheap/fast peer of gpt-4o-mini ---
ANTHROPIC_CHAT_MODEL = "claude-haiku-4-5"

MAX_TOKENS = 700
REQ_CAP = 120  # soft per-session cap to protect the shared key

STACK = {
    1: "Experience", 2: "Orchestration", 3: "Model", 4: "Retrieval & context",
    5: "Enterprise systems", 6: "Data foundation", 7: "Governance",
}

PROVIDERS = {"openai": "OpenAI", "anthropic": "Anthropic (Claude)"}


def _secret(name: str):
    try:
        return st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        return None


# --------------------------------------------------------------- provider choice
def provider() -> str:
    """Active chat provider: a per-session sidebar choice, else the configured default."""
    sess = st.session_state.get("llm_provider")
    if sess in PROVIDERS:
        return sess
    cfg = (_secret("llm_provider") or os.environ.get("LLM_PROVIDER") or "openai").lower()
    return cfg if cfg in PROVIDERS else "openai"


def chat_model() -> str:
    return ANTHROPIC_CHAT_MODEL if provider() == "anthropic" else CHAT_MODEL


def default_key(prov: str | None = None) -> str | None:
    """A workshop default key for ``prov``, from Streamlit secrets or env.
    Never hard-coded in source — set it in a gitignored secrets.toml or .env."""
    prov = prov or provider()
    if prov == "anthropic":
        return _secret("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
    return _secret("openai_api_key") or os.environ.get("OPENAI_API_KEY")


def _openai_embed_key() -> str | None:
    """Key for embeddings — always OpenAI, even when chat runs on Claude."""
    pasted = st.session_state.get("user_key_openai")
    return pasted or _secret("openai_api_key") or os.environ.get("OPENAI_API_KEY")


# Today's route: the seven labs of the 60-minute hands-on hour, in five groups.
# This is the ONLY
# navigation shown (auto page nav is off in .streamlit/config.toml); other levels
# stay deployed but unlisted.
ROUTE_NAV = [
    ("Labs 1–2 · A model becomes an app",
     [("pages/1_1._Chatbot.py", "1 · Chatbot"), ("pages/2_2._Memory.py", "2 · Memory")]),
    ("Lab 3 · It will answer anything",
     [("pages/3_3._Guardrails.py", "3 · Guardrails")]),
    ("Labs 4–5 · Ground it — then break it",
     [("pages/4_4._Grounding_and_RAG.py", "4 · Grounding & RAG"),
      ("pages/5_5._Build_and_break_a_RAG.py", "5 · Build & break a RAG")]),
    ("Lab 6 · It knows, but can't act",
     [("pages/6_6._Tools_and_the_agent_loop.py", "6 · Tools & the agent loop")]),
    ("Lab 7 · Agents over MCP + A2A",
     [("pages/7_7._Multi-agent_and_governance.py", "7 · Multi-agent & governance")]),
]


def render_route_sidebar() -> None:
    """Sidebar nav: home + the seven labs (grouped by sheet), nothing else."""
    with st.sidebar:
        st.page_link("app.py", label="🧱 Home — today's route")
        for stop, pages in ROUTE_NAV:
            st.markdown(f"**{stop}**")
            for path, label in pages:
                st.page_link(path, label=label)
        st.divider()


def render_key_sidebar() -> str | None:
    st.sidebar.header("🔑 Model provider")
    prov = st.sidebar.radio(
        "Chat provider", list(PROVIDERS), index=list(PROVIDERS).index(provider()),
        format_func=lambda p: PROVIDERS[p], horizontal=False,
        help="Switch the chat model between vendors — same demo, no code change. "
             "Embeddings (RAG demos) always use OpenAI; Anthropic has no embeddings API.",
    )
    st.session_state["llm_provider"] = prov

    dflt = default_key(prov)
    label = "Your Anthropic key (optional)" if prov == "anthropic" else "Your OpenAI key (optional)"
    placeholder = ("sk-ant-..." if prov == "anthropic" else "sk-...")
    if dflt:
        placeholder = "workshop default active — paste to override"
    sess_key = f"user_key_{prov}"
    entered = st.sidebar.text_input(
        label, type="password", value=st.session_state.get(sess_key, ""),
        placeholder=placeholder,
        help="A workshop default may be configured. Paste your own to use it instead. "
             "Held in this browser session only — never stored or logged.",
    ).strip()
    st.session_state[sess_key] = entered
    eff = entered if entered else dflt
    st.session_state["key"] = eff
    if entered:
        st.sidebar.caption(f"✅ Using **your** {PROVIDERS[prov]} key (entered).")
    elif dflt:
        st.sidebar.caption(f"Using the **workshop default** {PROVIDERS[prov]} key.")
    else:
        st.sidebar.caption("No key yet — paste one above.")
    st.sidebar.caption(f"Model `{chat_model()}` · shared key — please be gentle.")
    return eff


def api_guard(e: Exception) -> None:
    """Turn an API exception into a friendly message and stop — never a raw traceback."""
    msg = str(e)
    low = msg.lower()
    if any(s in low for s in ("invalid_api_key", "incorrect api key", "authentication", "no api key", "x-api-key")) or "401" in msg:
        st.error("🔑 The API key was rejected (invalid or expired). Paste a valid key in the sidebar.")
    elif any(s in low for s in ("rate limit", "quota", "insufficient_quota", "overloaded")) or "429" in msg:
        st.error("⏳ The key hit a rate or quota limit. Wait a moment, or paste a different key.")
    else:
        st.error(f"Model request failed: {e}")
    st.stop()


# Back-compat alias (store.py and older imports used this name).
openai_guard = api_guard


# --------------------------------------------------------------- client wrapper
class LLMClient:
    """Provider-neutral handle: a chat backend (OpenAI or Anthropic) plus an
    OpenAI client for embeddings (shared by both, since Anthropic has none)."""

    def __init__(self, prov, raw, chat_model, embed_raw, embed_model):
        self.provider = prov
        self.raw = raw
        self.chat_model = chat_model
        self.embed_raw = embed_raw
        self.embed_model = embed_model


def _build_chat_raw(prov: str, key: str):
    if prov == "anthropic":
        try:
            from anthropic import Anthropic
        except Exception:
            st.error("The `anthropic` package is not installed. Add `anthropic` to requirements.txt.")
            st.stop()
        return Anthropic(api_key=key)
    try:
        from openai import OpenAI
    except Exception:
        st.error("The `openai` package is not installed.")
        st.stop()
    return OpenAI(api_key=key)


def _build_embed_raw():
    key = _openai_embed_key()
    if not key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    return OpenAI(api_key=key)


def get_client():
    k = st.session_state.get("key")
    if not k:
        return None
    prov = provider()
    return LLMClient(prov, _build_chat_raw(prov, k), chat_model(), _build_embed_raw(), EMBED_MODEL)


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
    st.title("🔒 Enterprise AI — the building blocks")
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
    """Top of every demo page: config, gate, nav, key entry, return a ready client (or stop)."""
    st.set_page_config(page_title=title, page_icon="🎬", layout="wide")
    ensure_access()
    render_route_sidebar()
    render_key_sidebar()
    client = get_client()
    if client is None:
        st.title(title)
        st.info(f"⬅️ Paste the {PROVIDERS[provider()]} key in the sidebar to run this demo.")
        st.stop()
    return client


def layer_badge(layers: list[int]) -> None:
    # Retained as a no-op so existing page imports/calls keep working. The
    # layer/dimension framing was dropped for the GenAI Day edition
    # (the intro deck no longer introduces it), so nothing is rendered.
    return None


def try_this(*items: str, title: str = "✋ Try this") -> None:
    """Hands-on experiments, rendered in a box directly beneath a lab's app.

    These labs are a bench, not a lecture: every item names an ACTION to take in
    the app above and the thing to NOTICE when you do. Keep them short enough to
    run in seconds, and ordered so each one builds on the last.
    """
    with st.container(border=True):
        st.markdown(f"##### {title}")
        st.caption("Run these in the app above — each takes seconds, and each shows you something.")
        for i, item in enumerate(items, start=1):
            st.markdown(f"**{i}.** {item}")


def _bump() -> None:
    n = st.session_state.get("_reqs", 0) + 1
    st.session_state["_reqs"] = n
    if n > REQ_CAP:
        st.error("Per-session request limit reached (protects the shared key). Refresh to reset.")
        st.stop()


# --------------------------------------------------- OpenAI <-> Anthropic shims
# Pages consume an OpenAI-shaped response (resp.choices[0].message.content /
# .tool_calls). These tiny classes let the Anthropic backend return that same
# shape, so no page code is provider-specific.
class _FnCall:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments  # JSON string, like OpenAI


class _ToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.type = "function"
        self.function = _FnCall(name, arguments)

    def model_dump(self):
        return {"id": self.id, "type": "function",
                "function": {"name": self.function.name, "arguments": self.function.arguments}}


class _Msg:
    def __init__(self, content, tool_calls):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or None


class _Choice:
    def __init__(self, message):
        self.message = message


class _Resp:
    def __init__(self, message):
        self.choices = [_Choice(message)]


def _to_anthropic_messages(messages):
    """OpenAI-style messages -> (system_str, anthropic_messages)."""
    system_parts, out = [], []
    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(m["content"])
        elif role == "tool":
            content = m.get("content")
            out.append({"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id"),
                "content": content if isinstance(content, str) else json.dumps(content),
            }]})
        elif role == "assistant":
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in (m.get("tool_calls") or []):
                fn = tc["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}
                blocks.append({"type": "tool_use", "id": tc["id"], "name": fn["name"], "input": args})
            out.append({"role": "assistant", "content": blocks if blocks else ""})
        else:  # user
            out.append({"role": "user", "content": m.get("content", "")})
    system = "\n\n".join(p for p in system_parts if p) or None
    return system, out


def _tools_to_anthropic(tools):
    out = []
    for t in tools or []:
        fn = t["function"]
        out.append({"name": fn["name"], "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}})})
    return out


def _tool_choice_to_anthropic(tc):
    if tc in (None, "auto"):
        return None
    if tc in ("required", "any"):
        return {"type": "any"}
    if isinstance(tc, dict) and tc.get("type") == "function":
        return {"type": "tool", "name": tc["function"]["name"]}
    return None


def _anthropic_kwargs(client, messages, tools, tool_choice, model, max_tokens):
    system, msgs = _to_anthropic_messages(messages)
    # Anthropic Opus-tier models reject `temperature`; omit it everywhere for safety.
    kw = dict(model=model or client.chat_model, max_tokens=max_tokens, messages=msgs)
    if system:
        kw["system"] = system
    if tools:
        kw["tools"] = _tools_to_anthropic(tools)
    ac = _tool_choice_to_anthropic(tool_choice)
    if ac:
        kw["tool_choice"] = ac
    return kw


# ----------------------------------------------------------------- chat helpers
def chat(client, messages, tools=None, tool_choice=None, model: str | None = None,
         max_tokens: int = MAX_TOKENS, temperature: float = 0.3):
    """Non-streaming completion. Returns an OpenAI-shaped response for both providers."""
    _bump()
    if client.provider == "anthropic":
        kw = _anthropic_kwargs(client, messages, tools, tool_choice, model, max_tokens)
        try:
            resp = client.raw.messages.create(**kw)
        except Exception as e:
            api_guard(e)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [_ToolCall(b.id, b.name, json.dumps(b.input)) for b in resp.content if b.type == "tool_use"]
        return _Resp(_Msg(text, calls))

    kw = dict(model=model or client.chat_model, messages=messages, max_tokens=max_tokens, temperature=temperature)
    if tools:
        kw["tools"] = tools
    if tool_choice:
        kw["tool_choice"] = tool_choice
    try:
        return client.raw.chat.completions.create(**kw)
    except Exception as e:
        api_guard(e)


def stream_assistant(client, messages, *, tools=None, tool_choice=None, model: str | None = None,
                     max_tokens: int = MAX_TOKENS, temperature: float = 0.3, placeholder=None):
    """Stream a completion, rendering text live into `placeholder` (an st.empty()).

    Returns (content_text, tool_calls) where tool_calls is a list of
    {"id","name","args"} dicts — same shape for OpenAI and Anthropic.
    """
    _bump()
    if client.provider == "anthropic":
        kw = _anthropic_kwargs(client, messages, tools, tool_choice, model, max_tokens)
        content = ""
        try:
            with client.raw.messages.stream(**kw) as stream:
                for text in stream.text_stream:
                    content += text
                    if placeholder is not None:
                        placeholder.markdown(content + "▌")
                final = stream.get_final_message()
        except Exception as e:
            api_guard(e)
            return "", []
        if placeholder is not None and content:
            placeholder.markdown(content)
        calls = [{"id": b.id, "name": b.name, "args": json.dumps(b.input)}
                 for b in final.content if b.type == "tool_use"]
        return content, calls

    kw = dict(model=model or client.chat_model, messages=messages, max_tokens=max_tokens,
              temperature=temperature, stream=True)
    if tools:
        kw["tools"] = tools
    if tool_choice:
        kw["tool_choice"] = tool_choice
    try:
        stream = client.raw.chat.completions.create(**kw)
    except Exception as e:
        api_guard(e)
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
    """Rebuild the assistant message (with tool_calls) from stream_assistant output.

    OpenAI-shaped; the Anthropic backend translates it back on the next call.
    """
    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"]}}
            for c in calls
        ],
    }
