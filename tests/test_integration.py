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


def test_wrap_callback_with_on_change() -> None:
    """Test that wrap_callback works with on_change callbacks."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "error_caught" not in st.session_state:
    st.session_state.error_caught = False

def handle_change() -> None:
    # This will raise an error
    _ = 1 / 0

boundary = ErrorBoundary(
    on_error=lambda _: st.session_state.update(error_caught=True),
    fallback="Error in on_change callback"
)

@boundary.decorate
def main() -> None:
    st.title("Test on_change")

    # Use text_input with on_change
    st.text_input(
        "Enter text",
        key="test_input",
        on_change=boundary.wrap_callback(handle_change)
    )

    st.write(f"Error caught: {st.session_state.error_caught}")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially no error
    assert at.session_state.error_caught is False
    assert len(at.error) == 0

    # Change text input to trigger on_change
    at.text_input[0].input("test").run()

    # Error should be caught by wrap_callback
    assert at.session_state.error_caught is True
    assert len(at.error) == 1  # type: ignore[unreachable]
    assert at.error[0].value == "Error in on_change callback"


def test_wrap_callback_with_selectbox_on_change() -> None:
    """Test that wrap_callback works with selectbox on_change."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "callback_executed" not in st.session_state:
    st.session_state.callback_executed = False
if "error_message" not in st.session_state:
    st.session_state.error_message = ""

def handle_selection_change() -> None:
    st.session_state.callback_executed = True
    raise ValueError("Selection error")

boundary = ErrorBoundary(
    on_error=lambda exc: st.session_state.update(error_message=str(exc)),
    fallback="Error handling selection"
)

@boundary.decorate
def main() -> None:
    st.title("Test selectbox on_change")

    st.selectbox(
        "Choose option",
        options=["A", "B", "C"],
        key="selection",
        on_change=boundary.wrap_callback(handle_selection_change)
    )

    st.write(f"Callback executed: {st.session_state.callback_executed}")
    st.write(f"Error: {st.session_state.error_message}")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially no error
    assert at.session_state.callback_executed is False
    assert at.session_state.error_message == ""

    # Change selection to trigger on_change
    at.selectbox[0].select("B").run()

    # Callback should have executed and error caught
    assert at.session_state.callback_executed is True
    assert at.session_state.error_message == "Selection error"  # type: ignore[unreachable]
    assert len(at.error) == 1
    assert at.error[0].value == "Error handling selection"


def test_rerun_passes_through_in_decorate() -> None:
    """Test that st.rerun() passes through ErrorBoundary in decorated functions."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

boundary = ErrorBoundary(on_error=lambda _: None, fallback="Error occurred")

@boundary.decorate
def main() -> None:
    st.write("before rerun")
    if st.button("Trigger Rerun"):
        st.rerun()
    st.write("after rerun")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially both texts should appear
    markdown_values = [m.value for m in at.markdown]
    assert any("before rerun" in v for v in markdown_values)
    assert any("after rerun" in v for v in markdown_values)

    # Click button to trigger rerun
    at.button[0].click()
    at.run()

    # After rerun, script should restart from beginning
    markdown_values = [m.value for m in at.markdown]
    assert any("before rerun" in v for v in markdown_values)
    # No error should be shown
    assert len(at.error) == 0


def test_stop_passes_through_in_decorate() -> None:
    """Test that st.stop() passes through ErrorBoundary in decorated functions."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

boundary = ErrorBoundary(on_error=lambda _: None, fallback="Error occurred")

@boundary.decorate
def main() -> None:
    st.write("before stop")
    if st.button("Trigger Stop"):
        st.write("stopping now")
        st.stop()
        st.write("this should never appear")
    st.write("after stop")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially "before stop" and "after stop" appear
    markdown_values = [m.value for m in at.markdown]
    assert any("before stop" in v for v in markdown_values)
    assert any("after stop" in v for v in markdown_values)

    # Click button to trigger stop
    at.button[0].click()
    at.run()

    # "stopping now" should appear, but "this should never appear" should not
    markdown_values = [m.value for m in at.markdown]
    assert any("before stop" in v for v in markdown_values)
    assert any("stopping now" in v for v in markdown_values)
    # Content after st.stop() should not appear
    assert not any("this should never appear" in v for v in markdown_values)
    # No error should be shown
    assert len(at.error) == 0


def test_rerun_passes_through_in_callback() -> None:
    """Test that st.rerun() passes through ErrorBoundary in wrapped callbacks."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "counter" not in st.session_state:
    st.session_state.counter = 0

boundary = ErrorBoundary(on_error=lambda _: None, fallback="Error occurred")

def trigger_rerun() -> None:
    st.session_state.counter += 1
    st.rerun()

@boundary.decorate
def main() -> None:
    st.write(f"Counter: {st.session_state.counter}")
    st.button("Increment and Rerun", on_click=boundary.wrap_callback(trigger_rerun))

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially counter is 0
    markdown_values = [m.value for m in at.markdown]
    assert any("Counter: 0" in v for v in markdown_values)

    # Click button to trigger rerun
    at.button[0].click()
    at.run()

    # Counter should be incremented and rerun should have occurred
    markdown_values = [m.value for m in at.markdown]
    assert any("Counter: 1" in v for v in markdown_values)
    # No error should be shown
    assert len(at.error) == 0


def test_stop_passes_through_in_callback() -> None:
    """Test that st.stop() passes through ErrorBoundary in wrapped callbacks.

    Note: When st.stop() is called in a callback, it stops the entire script execution
    immediately after the callback completes. This test verifies that st.stop() is not
    caught by the error boundary and allows Streamlit to handle it correctly.
    """
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "error_triggered" not in st.session_state:
    st.session_state.error_triggered = False

boundary = ErrorBoundary(
    on_error=lambda _: st.session_state.update(error_triggered=True),
    fallback="Error occurred"
)

def trigger_stop() -> None:
    # This should pass through without triggering error handler
    st.stop()

@boundary.decorate
def main() -> None:
    st.write("start")
    st.button("Trigger Stop", on_click=boundary.wrap_callback(trigger_stop))
    st.write("end")

main()

# Verify error was not triggered
st.write(f"Error triggered: {st.session_state.error_triggered}")
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially everything renders
    markdown_values = [m.value for m in at.markdown]
    assert any("start" in v for v in markdown_values)
    assert any("end" in v for v in markdown_values)
    assert any("Error triggered: False" in v for v in markdown_values)

    # Click button to trigger stop in callback
    at.button[0].click()
    at.run()

    # After st.stop() in callback, script execution stops
    # The key point is that error_triggered should still be False
    # (meaning st.stop() was not caught as an error)
    assert at.session_state.error_triggered is False
    # No error fallback should be shown
    assert len(at.error) == 0


# ============================================================================
# Nested boundary tests
# ============================================================================


def test_nested_inner_handles_only() -> None:
    """Test that inner boundary handles exception, not outer boundary.

    When ErrorBoundaries are nested, the innermost boundary that catches
    the exception should handle it. The outer boundary's hooks should NOT
    be executed.
    """
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

# Initialize observation flags
if "inner_hook" not in st.session_state:
    st.session_state.inner_hook = False
if "outer_hook" not in st.session_state:
    st.session_state.outer_hook = False

def inner_hook(_: Exception) -> None:
    st.session_state.inner_hook = True

def outer_hook(_: Exception) -> None:
    st.session_state.outer_hook = True

# Create nested boundaries
outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER FALLBACK")
inner = ErrorBoundary(on_error=inner_hook, fallback="INNER FALLBACK")

@outer.decorate
def main() -> None:
    st.write("start")

    @inner.decorate
    def section() -> None:
        if st.button("Boom"):
            raise ValueError("boom")

    section()
    st.write("end")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially no error
    assert at.session_state.inner_hook is False
    assert at.session_state.outer_hook is False

    # Trigger exception
    at.button[0].click()
    at.run()

    # Inner fallback should be shown, not outer
    assert len(at.error) == 1
    assert at.error[0].value == "INNER FALLBACK"

    # Inner hook should be executed, outer hook should NOT
    assert at.session_state.inner_hook is True
    assert at.session_state.outer_hook is False  # type: ignore[unreachable]


def test_nested_inner_fallback_raises_bubbles_to_outer() -> None:
    """Test that exception from inner fallback bubbles to outer boundary.

    If the inner fallback raises an exception, it should propagate to the
    outer boundary, which will handle it. Both inner and outer hooks should
    be executed (inner first, then outer).
    """
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

# Initialize observation flags
if "inner_hook" not in st.session_state:
    st.session_state.inner_hook = False
if "outer_hook" not in st.session_state:
    st.session_state.outer_hook = False

def inner_hook(_: Exception) -> None:
    st.session_state.inner_hook = True

def outer_hook(_: Exception) -> None:
    st.session_state.outer_hook = True

def bad_inner_fallback(_: Exception) -> None:
    # Intentionally raise to propagate to outer boundary
    msg = "fallback failed"
    raise RuntimeError(msg)

# Create nested boundaries
outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER FALLBACK")
inner = ErrorBoundary(on_error=inner_hook, fallback=bad_inner_fallback)

@outer.decorate
def main() -> None:
    @inner.decorate
    def section() -> None:
        if st.button("Boom"):
            msg = "boom"
            raise ValueError(msg)

    section()

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially no error
    assert at.session_state.inner_hook is False
    assert at.session_state.outer_hook is False

    # Trigger exception (inner fallback will raise)
    at.button[0].click()
    at.run()

    # Outer fallback should be shown (inner fallback raised exception)
    assert len(at.error) == 1
    assert at.error[0].value == "OUTER FALLBACK"

    # Both hooks should have been executed (inner first, then outer)
    assert at.session_state.inner_hook is True
    assert at.session_state.outer_hook is True  # type: ignore[unreachable]


def test_nested_fallback_raise_hooks_run_inner_then_outer() -> None:
    """Test that when inner fallback raises, hooks execute in order: inner then outer.

    This verifies the execution order guarantee for nested boundaries when
    the inner fallback propagates an exception to the outer boundary.
    """
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "order" not in st.session_state:
    st.session_state.order = []

def inner_hook(_: Exception) -> None:
    st.session_state.order.append("inner")

def outer_hook(_: Exception) -> None:
    st.session_state.order.append("outer")

def bad_inner_fallback(_: Exception) -> None:
    msg = "fallback failed"
    raise RuntimeError(msg)

outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback=bad_inner_fallback)

@outer.decorate
def main() -> None:
    @inner.decorate
    def section() -> None:
        if st.button("Boom"):
            msg = "boom"
            raise ValueError(msg)
    section()

main()
"""
    at = AppTest.from_string(script)
    at.run()

    # Initially no hooks called
    assert at.session_state.order == []

    # Trigger exception
    at.button[0].click()
    at.run()

    # Outer fallback shown (inner fallback raised)
    assert len(at.error) == 1
    assert at.error[0].value == "OUTER"

    # Hooks executed in order: inner first, then outer
    assert at.session_state.order == ["inner", "outer"]


def test_nested_with_callback_inner_handles_only() -> None:
    """Test that nested boundaries with wrap_callback follow the same rules.

    Verifies that when a callback raises an exception within nested boundaries,
    only the innermost boundary's hooks are called (same as decorate behavior).
    """
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "inner" not in st.session_state:
    st.session_state.inner = False
if "outer" not in st.session_state:
    st.session_state.outer = False

def inner_hook(_: Exception) -> None:
    st.session_state.inner = True

def outer_hook(_: Exception) -> None:
    st.session_state.outer = True

outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback="INNER")

def cb() -> None:
    msg = "cb error"
    raise RuntimeError(msg)

@outer.decorate
def main() -> None:
    @inner.decorate
    def section() -> None:
        st.button("Boom", on_click=inner.wrap_callback(cb))
    section()

main()
"""
    at = AppTest.from_string(script)
    at.run()

    # Initially no hooks called
    assert at.session_state.inner is False
    assert at.session_state.outer is False

    # Trigger callback exception
    at.button[0].click()
    at.run()

    # Inner fallback shown (callback error caught by inner boundary)
    assert len(at.error) == 1
    assert at.error[0].value == "INNER"

    # Only inner hook called, outer hook NOT called
    assert at.session_state.inner is True
    assert at.session_state.outer is False  # type: ignore[unreachable]


def test_rerun_does_not_call_hook_in_decorate() -> None:
    """Test that st.rerun() does not trigger error hooks in decorated functions."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_called" not in st.session_state:
    st.session_state.hook_called = False

def hook(_: Exception) -> None:
    st.session_state.hook_called = True

boundary = ErrorBoundary(on_error=hook, fallback="fallback")

@boundary.decorate
def main() -> None:
    st.write("before rerun")
    if st.button("Rerun"):
        st.rerun()
    st.write("after rerun")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially hook not called
    assert at.session_state.hook_called is False

    # Click button to trigger rerun
    at.button[0].click()
    at.run()

    # Hook should NOT be called because st.rerun() is a control flow exception
    assert at.session_state.hook_called is False
    # No error should be shown
    assert len(at.error) == 0


def test_stop_does_not_call_hook_in_decorate() -> None:
    """Test that st.stop() does not trigger error hooks in decorated functions."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_called" not in st.session_state:
    st.session_state.hook_called = False

def hook(_: Exception) -> None:
    st.session_state.hook_called = True

boundary = ErrorBoundary(on_error=hook, fallback="fallback")

@boundary.decorate
def main() -> None:
    st.write("before stop")
    if st.button("Stop"):
        st.write("stopping now")
        st.stop()
    st.write("after stop")

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially hook not called
    assert at.session_state.hook_called is False

    # Click button to trigger stop
    at.button[0].click()
    at.run()

    # Hook should NOT be called because st.stop() is a control flow exception
    assert at.session_state.hook_called is False
    # No error should be shown
    assert len(at.error) == 0


def test_rerun_does_not_call_hook_in_callback() -> None:
    """Test that st.rerun() does not trigger error hooks in wrapped callbacks."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_called" not in st.session_state:
    st.session_state.hook_called = False
if "counter" not in st.session_state:
    st.session_state.counter = 0

def hook(_: Exception) -> None:
    st.session_state.hook_called = True

boundary = ErrorBoundary(on_error=hook, fallback="fallback")

def trigger_rerun() -> None:
    st.session_state.counter += 1
    st.rerun()

@boundary.decorate
def main() -> None:
    st.write(f"Counter: {st.session_state.counter}")
    st.button("Rerun", on_click=boundary.wrap_callback(trigger_rerun))

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially hook not called
    assert at.session_state.hook_called is False
    assert at.session_state.counter == 0

    # Click button to trigger rerun
    at.button[0].click()
    at.run()

    # Counter should be incremented and rerun should have occurred
    assert at.session_state.counter == 1
    # Hook should NOT be called because st.rerun() is a control flow exception
    assert at.session_state.hook_called is False
    # No error should be shown
    assert len(at.error) == 0


def test_stop_does_not_call_hook_in_callback() -> None:
    """Test that st.stop() does not trigger error hooks in wrapped callbacks."""
    script = """
import streamlit as st
from st_error_boundary import ErrorBoundary

if "hook_called" not in st.session_state:
    st.session_state.hook_called = False

def hook(_: Exception) -> None:
    st.session_state.hook_called = True

boundary = ErrorBoundary(on_error=hook, fallback="fallback")

def trigger_stop() -> None:
    st.stop()

@boundary.decorate
def main() -> None:
    st.button("Stop", on_click=boundary.wrap_callback(trigger_stop))

main()
"""

    at = AppTest.from_string(script)
    at.run()

    # Initially hook not called
    assert at.session_state.hook_called is False

    # Click button to trigger stop
    at.button[0].click()
    at.run()

    # Hook should NOT be called because st.stop() is a control flow exception
    assert at.session_state.hook_called is False
    # No error should be shown
    assert len(at.error) == 0
