from __future__ import annotations

import streamlit as st

from st_error_boundary import ErrorBoundary


def audit(_: Exception) -> None:
    # Replace with actual audit logging/metrics in production
    st.session_state["last_error"] = "unhandled"


def fallback_ui(_: Exception) -> None:
    st.error("An unexpected error occurred. Please contact support.")
    st.link_button("Contact Support", "https://example.com/support")
    if st.button("Retry"):
        st.rerun()


# Create ErrorBoundary instance with shared configuration
boundary = ErrorBoundary(on_error=audit, fallback=fallback_ui)


def trigger_error_callback() -> None:
    """Callback that raises an error - protected by wrap_callback."""
    _ = 1 / 0


@boundary.decorate
def main() -> None:
    st.title("st-error-boundary demo")

    st.subheader("Protected button click (if statement)")
    if st.button("Trigger Error (Direct)"):
        # This error is caught by @boundary.decorate
        _ = 1 / 0

    st.subheader("Protected callback (on_click)")
    # This error is caught by boundary.wrap_callback
    st.button("Trigger Error (Callback)", on_click=boundary.wrap_callback(trigger_error_callback))


if __name__ == "__main__":
    main()
