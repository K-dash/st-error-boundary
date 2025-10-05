from __future__ import annotations

import streamlit as st

from st_error_boundary import error_boundary


def audit(_: Exception) -> None:
    # Replace with actual audit logging/metrics in production
    st.session_state["last_error"] = "unhandled"


def fallback_ui(_: Exception) -> None:
    st.error("An unexpected error occurred. Please contact support.")
    st.link_button("Contact Support", "https://example.com/support")
    if st.button("Retry"):
        st.rerun()


@error_boundary(on_error=audit, fallback=fallback_ui)
def main() -> None:
    st.title("st-error-boundary demo")

    def trigger_error() -> None:
        _ = 1 / 0

    st.button("Trigger Error", on_click=trigger_error)


if __name__ == "__main__":
    main()
