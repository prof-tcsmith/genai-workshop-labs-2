"""Embed the interactive concept deck (slides.html) inside a lab page.

The deck is one self-contained React (via CDN) file carrying all four topics;
we inject the topic and show it in an expander, plus a full-screen link to the
GitHub Pages copy.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_SLIDES = Path(__file__).resolve().parents[1] / "slides.html"
PAGES_URL = "https://prof-tcsmith.github.io/genai-workshop-labs/decks/slides.html"


def render_slides(topic: str, label: str = "📊 Concept slides (interactive)") -> None:
    try:
        html = _SLIDES.read_text(encoding="utf-8")
    except Exception:
        return
    html = html.replace("__TOPIC_PLACEHOLDER__", topic)
    with st.expander(label, expanded=False):
        components.html(html, height=520, scrolling=False)
        st.markdown(f"[↗ Open these slides full-screen in a new tab]({PAGES_URL}?topic={topic})")
