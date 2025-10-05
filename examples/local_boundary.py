"""Example: Local error boundaries for isolated components.

This demonstrates how to use error boundaries for specific parts of your app
(like React's component-level error boundaries), allowing some sections to fail
gracefully while the rest of the app continues to work.
"""

from __future__ import annotations

import streamlit as st

from st_error_boundary import ErrorBoundary

# ============================================================================
# Local boundary for each component
# ============================================================================


def render_user_profile() -> None:
    """Render user profile section with its own error boundary."""

    def _fallback(_: Exception) -> None:
        st.warning("⚠️ Could not load user profile. Please try again later.")

    local_boundary = ErrorBoundary(
        on_error=lambda exc: print(f"Profile error: {exc}"),
        fallback=_fallback,
    )

    @local_boundary.decorate
    def _render() -> None:
        st.subheader("👤 User Profile")
        # Simulate an error in this component
        if st.button("Break Profile Section"):
            msg = "Profile service unavailable"
            raise ConnectionError(msg)
        st.write("Name: John Doe")
        st.write("Email: john@example.com")

    _render()


def render_analytics_dashboard() -> None:
    """Render analytics dashboard with its own error boundary."""

    def _fallback(_: Exception) -> None:
        st.warning("⚠️ Analytics data temporarily unavailable. Other features still work.")

    local_boundary = ErrorBoundary(
        on_error=lambda exc: print(f"Analytics error: {exc}"),
        fallback=_fallback,
    )

    @local_boundary.decorate
    def _render() -> None:
        st.subheader("📊 Analytics Dashboard")
        # Simulate an error in this component
        if st.button("Break Analytics Section"):
            msg = "Analytics API error"
            raise RuntimeError(msg)
        st.metric("Total Users", "1,234")
        st.metric("Revenue", "$56,789")

    _render()


def render_recent_activity() -> None:
    """Render recent activity section with its own error boundary."""

    def _fallback(_: Exception) -> None:
        st.warning("⚠️ Could not load recent activity.")

    local_boundary = ErrorBoundary(
        on_error=lambda exc: print(f"Activity error: {exc}"),
        fallback=_fallback,
    )

    @local_boundary.decorate
    def _render() -> None:
        st.subheader("🕒 Recent Activity")
        # Simulate an error in this component
        if st.button("Break Activity Section"):
            msg = "Activity feed unavailable"
            raise ValueError(msg)
        st.write("- User logged in at 10:30 AM")
        st.write("- Profile updated at 9:15 AM")
        st.write("- Password changed at 8:00 AM")

    _render()


# ============================================================================
# Main App (also has a global boundary)
# ============================================================================
def _global_fallback(_: Exception) -> None:
    st.error("🚨 Critical error - entire app failed. Please refresh the page.")


global_boundary = ErrorBoundary(
    on_error=lambda exc: print(f"Global error: {exc}"),
    fallback=_global_fallback,
)


@global_boundary.decorate
def main() -> None:
    st.title("🛡️ Local Error Boundaries Demo")

    st.markdown(
        """
    This demo shows how to use **local error boundaries** for different sections of your app.
    Each section has its own boundary, so if one fails, the others continue to work.

    **Try it**: Click any "Break" button to see that section fail while others remain functional.
    """
    )

    st.markdown("---")

    # Each component has its own error boundary
    # If one fails, the others continue to work
    col1, col2 = st.columns(2)

    with col1:
        render_user_profile()
        st.markdown("---")
        render_analytics_dashboard()

    with col2:
        render_recent_activity()

    st.markdown("---")
    st.info(
        """
    **Pattern Summary**:
    - Each component (user profile, analytics, activity) has its own `ErrorBoundary`
    - If a component fails, only that component shows the fallback UI
    - Other components continue to work normally
    - This is similar to React's component-level error boundaries

    **Benefits**:
    - **Isolation**: Errors in one component don't crash the entire app
    - **Graceful degradation**: Users can still use working features
    - **Better UX**: Clear feedback about which specific feature is broken
    """
    )


if __name__ == "__main__":
    main()
