"""Integration tests for ErrorBoundary using Streamlit AppTest."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_error_boundary_catches_exception_and_shows_fallback() -> None:
    """Test that error boundary catches exceptions and displays fallback UI."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

boundary = ErrorBoundary(
    on_error=lambda _: None,
    fallback="An error occurred. Please try again.",
)

@boundary.decorate
def main() -> None:
    st.title("Test App")
    if st.button("Trigger Error"):
        raise RuntimeError("test error")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially no error
    assert not at.exception
    assert len(at.error) == 0

    # Click the button to trigger error
    at.button[0].click()
    at.run()

    # Error should be caught and fallback displayed
    assert not at.exception  # No unhandled exception
    assert len(at.error) == 1
    assert at.error[0].value == "An error occurred. Please try again."


def test_error_boundary_with_custom_fallback_ui() -> None:
    """Test error boundary with custom fallback UI renderer."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

def custom_fallback(_: Exception) -> None:
    st.error("Custom error message")
    st.warning("Additional context")

boundary = ErrorBoundary(on_error=lambda _: None, fallback=custom_fallback)

@boundary.decorate
def main() -> None:
    st.title("Test App")
    if st.button("Trigger Error"):
        raise RuntimeError("test error")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Click button to trigger error
    at.button[0].click()
    at.run()

    # Check custom fallback UI is rendered
    assert not at.exception
    assert len(at.error) == 1
    assert at.error[0].value == "Custom error message"
    assert len(at.warning) == 1
    assert at.warning[0].value == "Additional context"


def test_error_boundary_hook_is_called() -> None:
    """Test that error hooks are called when exception occurs."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_called" not in st.session_state:
    st.session_state.hook_called = False

def hook(_: Exception) -> None:
    st.session_state.hook_called = True

boundary = ErrorBoundary(on_error=hook, fallback="Error occurred")

@boundary.decorate
def main() -> None:
    st.title("Test App")
    if st.button("Trigger Error"):
        raise RuntimeError("test error")
    st.write(f"Hook called: {st.session_state.hook_called}")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially hook not called
    assert "Hook called: False" in at.markdown[0].value

    # Trigger error
    at.button[0].click()
    at.run()

    # Hook should have been called
    assert at.session_state.hook_called is True


def test_error_boundary_normal_execution() -> None:
    """Test that error boundary doesn't interfere with normal execution."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

boundary = ErrorBoundary(on_error=lambda _: None, fallback="Error occurred")

@boundary.decorate
def main() -> None:
    st.title("Test App")
    st.write("Normal execution")
    if st.button("Click Me"):
        st.success("Button clicked!")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Check normal rendering
    assert not at.exception
    assert len(at.error) == 0
    assert "Normal execution" in at.markdown[0].value

    # Click button (normal operation)
    at.button[0].click()
    at.run()

    # Check success message appears
    assert len(at.success) == 1
    assert at.success[0].value == "Button clicked!"
    assert len(at.error) == 0


def test_error_boundary_with_retry_button() -> None:
    """Test error boundary with retry functionality in fallback."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "attempts" not in st.session_state:
    st.session_state.attempts = 0

def fallback_with_retry(_: Exception) -> None:
    st.error("An error occurred")
    if st.button("Retry"):
        st.session_state.attempts = 0
        st.rerun()

boundary = ErrorBoundary(on_error=lambda _: None, fallback=fallback_with_retry)

@boundary.decorate
def main() -> None:
    st.title("Test App")
    st.write(f"Attempts: {st.session_state.attempts}")
    if st.button("Trigger Error"):
        st.session_state.attempts += 1
        raise RuntimeError("test error")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Trigger error
    at.button[0].click()
    at.run()

    # Error UI with retry button should appear
    assert len(at.error) == 1
    # Both Trigger Error and Retry buttons are present
    assert len(at.button) >= 1
    assert at.button[1].label == "Retry"


def test_multiple_hooks_in_integration() -> None:
    """Test that multiple hooks are executed in order during integration."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_order" not in st.session_state:
    st.session_state.hook_order = []

def hook1(_: Exception) -> None:
    st.session_state.hook_order.append("hook1")

def hook2(_: Exception) -> None:
    st.session_state.hook_order.append("hook2")

boundary = ErrorBoundary(on_error=[hook1, hook2], fallback="Error")

@boundary.decorate
def main() -> None:
    if st.button("Trigger"):
        raise RuntimeError("error")
    st.write(f"Order: {st.session_state.hook_order}")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Trigger error
    at.button[0].click()
    at.run()

    # Both hooks should have executed in order
    assert at.session_state.hook_order == ["hook1", "hook2"]


def test_hook_receives_exception_message() -> None:
    """Test that hooks receive the actual exception with its message."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "error_message" not in st.session_state:
    st.session_state.error_message = ""

def capture_error(exc: Exception) -> None:
    st.session_state.error_message = str(exc)

boundary = ErrorBoundary(on_error=capture_error, fallback="Error occurred")

@boundary.decorate
def main() -> None:
    st.title("Test App")
    if st.button("Trigger"):
        raise ValueError("Custom error message from test")
    st.write(f"Captured: {st.session_state.error_message}")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Trigger error
    at.button[0].click()
    at.run()

    # Hook should have captured the exception message
    assert at.session_state.error_message == "Custom error message from test"


def test_failing_hook_suppressed_in_integration() -> None:
    """Test that failing hooks are suppressed and subsequent hooks still run."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_results" not in st.session_state:
    st.session_state.hook_results = []

def failing_hook(_: Exception) -> None:
    st.session_state.hook_results.append("failing_executed")
    raise RuntimeError("hook failed")

def success_hook(_: Exception) -> None:
    st.session_state.hook_results.append("success_executed")

boundary = ErrorBoundary(
    on_error=[failing_hook, success_hook],
    fallback="Main error handled"
)

@boundary.decorate
def main() -> None:
    st.title("Test App")
    if st.button("Trigger"):
        raise ValueError("main error")
    st.write(f"Results: {st.session_state.hook_results}")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Trigger error
    at.button[0].click()
    at.run()

    # Both hooks should have been attempted
    assert at.session_state.hook_results == ["failing_executed", "success_executed"]
    # Fallback should still render despite hook failure
    assert len(at.error) == 1
    assert at.error[0].value == "Main error handled"
