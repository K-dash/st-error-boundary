"""Streamlit error boundary with pluggable hooks and safe fallback UI."""

from __future__ import annotations

from .error_boundary import ErrorHook, FallbackRenderer, error_boundary

__all__ = ["ErrorHook", "FallbackRenderer", "error_boundary"]
