"""Small reusable components used by KavachED pages."""

from __future__ import annotations

import html

import streamlit as st


def hero(title: str, description: str, action: str | None = None) -> bool:
    """Render a page heading and optionally return the primary action result."""
    st.markdown(
        f'<div class="hero-shell"><div class="eyebrow">KavachED · Student success</div><h1>{html.escape(title)}</h1><p>{html.escape(description)}</p></div>',
        unsafe_allow_html=True,
    )
    return st.button(action, type="primary") if action else False


def render_theme_toggle(key: str = "theme-toggle") -> None:
    """Render a compact toggle that preserves the selected theme in session state."""
    is_dark = st.session_state.get("theme", "dark") == "dark"
    if st.button(
        " ",
        icon=":material/light_mode:" if is_dark else ":material/dark_mode:",
        help=f"Switch to {'light' if is_dark else 'dark'} mode",
        key=key,
    ):
        st.session_state["theme"] = "light" if is_dark else "dark"
        st.rerun()
def render_theme_toggle(key: str = "theme_toggle") -> None:
    """Sun/moon button: flips light/dark and reruns the app."""
    current = st.session_state.get("theme", "dark")
    label = "☀️" if current == "dark" else "🌙"
    tip = "Switch to light mode" if current == "dark" else "Switch to dark mode"
    if st.button(label, key=key, help=tip):
        st.session_state["theme"] = "light" if current == "dark" else "dark"
        st.rerun()