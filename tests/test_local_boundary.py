"""Integration tests for local_boundary.py example."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_local_boundary_user_profile_error_isolated() -> None:
    """Test that user profile error is isolated and doesn't crash other sections."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

def render_user_profile() -> None:
    def _fallback(_: Exception) -> None:
        st.warning("⚠️ Could not load user profile.")

    local_boundary = ErrorBoundary(
        on_error=lambda exc: print(f"Profile error: {exc}"),
        fallback=_fallback,
    )

    @local_boundary.decorate
    def _render() -> None:
        st.subheader("👤 User Profile")
        if st.button("Break Profile"):
            raise ConnectionError("Profile service unavailable")
        st.write("Name: John Doe")

    _render()

def render_analytics() -> None:
    st.subheader("📊 Analytics")
    st.write("Analytics working fine")

render_user_profile()
st.markdown("---")
render_analytics()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially both sections render normally
    assert not at.exception
    assert len(at.warning) == 0

    # Trigger error in user profile
    at.button[0].click()
    at.run()

    # Profile section shows warning, but analytics still works
    assert not at.exception
    assert len(at.warning) == 1
    assert "Could not load user profile" in at.warning[0].value
    # Analytics section still renders
    assert "Analytics working fine" in at.markdown[1].value


def test_local_boundary_multiple_sections_independent() -> None:
    """Test that multiple sections with local boundaries are independent."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

def render_section_a() -> None:
    boundary = ErrorBoundary(
        on_error=lambda _: None,
        fallback="Section A failed"
    )

    @boundary.decorate
    def _render() -> None:
        if st.button("Break A"):
            raise ValueError("A error")
        st.write("Section A OK")

    _render()

def render_section_b() -> None:
    boundary = ErrorBoundary(
        on_error=lambda _: None,
        fallback="Section B failed"
    )

    @boundary.decorate
    def _render() -> None:
        if st.button("Break B"):
            raise ValueError("B error")
        st.write("Section B OK")

    _render()

render_section_a()
render_section_b()
"""

    at = AppTest.from_string(script)
    at.run()

    # Break section A
    at.button[0].click()
    at.run()

    # Section A shows error, B still works
    assert len(at.error) == 1
    assert at.error[0].value == "Section A failed"
    assert "Section B OK" in at.markdown[0].value

    # Reset
    at = AppTest.from_string(script)
    at.run()

    # Break section B
    at.button[1].click()
    at.run()

    # Section B shows error, A still works
    assert len(at.error) == 1
    assert at.error[0].value == "Section B failed"
    assert "Section A OK" in at.markdown[0].value


def test_local_boundary_with_global_boundary() -> None:
    """Test that local boundaries work alongside a global boundary."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

def _global_fallback(_: Exception) -> None:
    st.error("🚨 Global error")

global_boundary = ErrorBoundary(
    on_error=lambda _: None,
    fallback=_global_fallback,
)

@global_boundary.decorate
def main() -> None:
    # Local boundary for a section
    def render_section() -> None:
        local_boundary = ErrorBoundary(
            on_error=lambda _: None,
            fallback="Local error"
        )

        @local_boundary.decorate
        def _render() -> None:
            if st.button("Break Local"):
                raise ValueError("local error")
            st.write("Local section OK")

        _render()

    render_section()

    # Trigger global error outside local boundary
    if st.button("Break Global"):
        raise RuntimeError("global error")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Break local section
    at.button[0].click()
    at.run()

    # Only local error appears
    assert len(at.error) == 1
    assert at.error[0].value == "Local error"

    # Reset
    at = AppTest.from_string(script)
    at.run()

    # Break global
    at.button[1].click()
    at.run()

    # Global error appears
    assert len(at.error) == 1
    assert "Global error" in at.error[0].value


def test_local_boundary_example_imports() -> None:
    """Test that the actual local_boundary.py example can be imported."""
    script = """
import sys
sys.path.insert(0, 'examples')

# Import the example module
from local_boundary import (
    render_user_profile,
    render_analytics_dashboard,
    render_recent_activity,
    main
)

# Verify functions are defined
assert callable(render_user_profile)
assert callable(render_analytics_dashboard)
assert callable(render_recent_activity)
assert callable(main)

import streamlit as st
st.write("Import successful")
"""

    at = AppTest.from_string(script)
    at.run()

    # Should run without errors
    assert not at.exception
    assert "Import successful" in at.markdown[0].value
