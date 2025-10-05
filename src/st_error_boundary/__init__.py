"""Streamlit error boundary with pluggable hooks and safe fallback UI."""

from __future__ import annotations

from .error_boundary import (
    ErrorBoundary,
    ErrorHook,
    FallbackRenderer,
    error_boundary,
)

__all__ = [
    "ErrorBoundary",
    "ErrorHook",
    "FallbackRenderer",
    "error_boundary",
]
