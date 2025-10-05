"""Plugin helpers for Streamlit-specific integrations."""

from __future__ import annotations

import streamlit as st


def render_string_fallback(message: str) -> None:
    """Render a simple error message using Streamlit's default error widget."""
    st.error(message)


__all__ = ["render_string_fallback"]
