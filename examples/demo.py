"""Comprehensive demo of st-error-boundary features."""

from __future__ import annotations

import streamlit as st

from st_error_boundary import ErrorBoundary

# ============================================================================
# Initialize session state
# ============================================================================
if "callback_error" not in st.session_state:
    st.session_state.callback_error = None

if "direct_error" not in st.session_state:
    st.session_state.direct_error = None


# ============================================================================
# Example 1: Basic Usage (Standard error handling)
# ============================================================================
def audit_basic(_: Exception) -> None:
    """Log errors to session state."""
    st.session_state["last_error"] = "unhandled"


def fallback_basic(_: Exception) -> None:
    """Display user-friendly error message."""
    st.error("An unexpected error occurred. Please contact support.")
    st.link_button("Contact Support", "https://example.com/support")
    if st.button("Retry"):
        st.rerun()


boundary_basic = ErrorBoundary(on_error=audit_basic, fallback=fallback_basic)


def trigger_basic_callback() -> None:
    """Callback that raises an error."""
    _ = 1 / 0


# ============================================================================
# Example 2: Deferred Rendering (Control error position)
# ============================================================================
def store_callback_error(exc: Exception) -> None:
    """Store callback error in session_state for deferred rendering."""
    st.session_state.callback_error = str(exc)


def silent_callback_fallback(_: Exception) -> None:
    """Don't render UI here - defer to main script."""


def store_direct_error(exc: Exception) -> None:
    """Store direct error in session_state."""
    st.session_state.direct_error = str(exc)


def _raise_direct_error() -> None:
    """Helper to raise direct error."""
    msg = "ERROR FROM DIRECT"
    raise ValueError(msg)


boundary_deferred = ErrorBoundary(on_error=store_callback_error, fallback=silent_callback_fallback)


def trigger_deferred_callback() -> None:
    """Callback that raises an error for deferred rendering."""
    msg = "ERROR FROM CALLBACK"
    raise ValueError(msg)


# ============================================================================
# Main App
# ============================================================================
@boundary_basic.decorate
def main() -> None:
    st.title("🛡️ st-error-boundary Demo")

    st.markdown(
        """
    This demo shows different error boundary patterns for Streamlit apps.
    """
    )

    # ========================================================================
    # Section 1: Basic Usage
    # ========================================================================
    st.header("1️⃣ Basic Usage")
    st.markdown(
        """
    Standard error handling with `@boundary.decorate` and `wrap_callback()`.
    **Note**: Callback errors appear at the top of the page.
    """
    )

    with st.container():
        st.subheader("Direct Error (if statement)")
        if st.button("Trigger Direct Error"):
            _ = 1 / 0

        st.subheader("Callback Error (on_click)")
        st.button(
            "Trigger Callback Error",
            on_click=boundary_basic.wrap_callback(trigger_basic_callback),
        )

    # ========================================================================
    # Section 2: Deferred Rendering
    # ========================================================================
    st.markdown("---")
    st.header("2️⃣ Deferred Rendering (Correct Position)")
    st.markdown(
        """
    Control error position by storing errors in `session_state` and rendering
    them during main script execution.

    **Benefit**: Errors appear near the widget that triggered them.
    """
    )

    with st.container():
        st.subheader("Direct Error")
        if st.button("Trigger Deferred Direct Error"):
            try:
                _raise_direct_error()
            except ValueError as exc:
                store_direct_error(exc)

        # Render direct error after the button
        if st.session_state.direct_error:
            st.error(f"❌ Error: {st.session_state.direct_error}")
            if st.button("Clear Direct Error"):
                st.session_state.direct_error = None
                st.rerun()

    with st.container():
        st.subheader("Callback Error")
        st.button(
            "Trigger Deferred Callback Error",
            on_click=boundary_deferred.wrap_callback(trigger_deferred_callback),
        )

        # Render callback error after the button
        if st.session_state.callback_error:
            st.error(f"❌ Error: {st.session_state.callback_error}")
            if st.button("Clear Callback Error"):
                st.session_state.callback_error = None
                st.rerun()

    # ========================================================================
    # Footer
    # ========================================================================
    st.markdown("---")
    st.markdown(
        """
    **Documentation**: See [Callback Rendering Position Guide](../docs/callback-rendering-position.md)
    for more details on the deferred rendering pattern.
    """
    )


if __name__ == "__main__":
    main()
