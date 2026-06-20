"""Central config, secrets, and the participant gate for Course Content Studio.

Real values come ONLY from Streamlit Secrets or environment variables — never
hard-coded here. The placeholders below are obvious "CHANGE-ME" values so you can
see exactly what to set (in .streamlit/secrets.toml locally, or Streamlit Cloud
Secrets). This module is the single place to point the app at your services.
"""
from __future__ import annotations

import hashlib
import os


def _secret(name: str, default=None):
    """Read from Streamlit Secrets if available, else env vars.

    Streamlit is imported lazily so non-Streamlit consumers (e.g. the MCP server)
    can import this module and read config from environment variables.
    """
    v = None
    try:
        import streamlit as st
        v = st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        v = None
    return v if v is not None else os.environ.get(name, default)


# --- OpenAI ---------------------------------------------------------------
OPENAI_API_KEY = _secret("openai_api_key")
CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

# --- Pinecone (vector DB) -------------------------------------------------
PINECONE_API_KEY = _secret("pinecone_api_key")
PINECONE_INDEX = _secret("pinecone_index", "course-content")

# --- Cloud Postgres (Neon / Supabase) — set these in Secrets --------------
PG_HOST = _secret("PG_HOST", "CHANGE-ME.neon.tech")     # e.g. ep-xxx.us-east-2.aws.neon.tech
PG_PORT = int(_secret("PG_PORT", "5432"))
PG_DB = _secret("PG_DB", "course")
PG_USER = _secret("PG_USER", "course_app")
PG_PASSWORD = _secret("PG_PASSWORD", "")
PG_SSLMODE = _secret("PG_SSLMODE", "require")

# Simplest setup: paste a single full connection string (Neon/Supabase give you
# one). If set, it takes precedence over the individual PG_* parts above.
DATABASE_URL = _secret("DATABASE_URL") or _secret("database_url")


def pg_dsn() -> str:
    """A psycopg-compatible connection string (a URL, or libpq keywords)."""
    if DATABASE_URL:
        return DATABASE_URL
    return (f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} "
            f"user={PG_USER} password={PG_PASSWORD} sslmode={PG_SSLMODE}")


def pg_configured() -> bool:
    if DATABASE_URL:
        return True
    return bool(PG_HOST) and not str(PG_HOST).startswith("CHANGE-ME")


# --- MCP server (local Docker for now) ------------------------------------
MCP_SERVER_URL = _secret("mcp_server_url", "http://localhost:8000/mcp")

# --- Participant code gate ------------------------------------------------
WORKSHOP_PASSPHRASE_SHA256 = _secret("workshop_passphrase_sha256")


def configured() -> dict:
    """Quick status used by the home page to show what's wired up."""
    return {
        "OpenAI": bool(OPENAI_API_KEY),
        "Pinecone": bool(PINECONE_API_KEY),
        "Postgres": pg_configured(),
        "MCP server": bool(MCP_SERVER_URL),
    }


def gate() -> None:
    """Participant-code gate — active only when ``workshop_passphrase_sha256`` is set.

    Call once at the top of every page, AFTER ``st.set_page_config(...)``.
    """
    import streamlit as st
    h = WORKSHOP_PASSPHRASE_SHA256
    if not h:
        return
    if st.session_state.get("_pass_ok"):
        return
    st.title("🔒 Course Content Studio")
    st.caption("Enter the participant code from the workshop to continue.")
    pw = st.text_input("Participant code", type="password")
    if st.button("Enter"):
        if hashlib.sha256(pw.encode("utf-8")).hexdigest() == str(h).strip().lower():
            st.session_state["_pass_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect code.")
    st.stop()


def openai_client():
    """A ready OpenAI client, or None if no key is configured."""
    if not OPENAI_API_KEY:
        return None
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)
