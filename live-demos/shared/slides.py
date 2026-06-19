"""Embed a demo's interactive concept deck inside its Streamlit page.

Each demo has a self-contained React (via CDN) deck under ``decks/<topic>.html`` —
title, an architecture diagram, the key concepts, an interactive widget, and a
"what this can't do yet" slide that sets up the next demo. Shown inline in an
expander, with a link to the full-screen GitHub Pages copy.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_DECKS = Path(__file__).resolve().parents[1] / "decks"
PAGES_BASE = "https://prof-tcsmith.github.io/genai-workshop-labs/decks/live"


def render_slides(topic: str, label: str = "📊 Concept slides (interactive)") -> None:
    deck = _DECKS / f"{topic}.html"
    try:
        html = deck.read_text(encoding="utf-8")
    except Exception:
        return
    with st.expander(label, expanded=False):
        components.html(html, height=540, scrolling=False)
        st.markdown(f"[↗ Open these slides full-screen in a new tab]({PAGES_BASE}/{topic}.html)")
