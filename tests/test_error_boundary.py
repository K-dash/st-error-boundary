from __future__ import annotations

import sys
from unittest.mock import Mock

import pytest

from st_error_boundary import ErrorBoundary


def test_error_boundary_class_exists() -> None:
    """Verify ErrorBoundary class exists."""
    assert ErrorBoundary is not None


def test_single_hook_is_called() -> None:
    """Test that a single error hook is executed when exception occurs."""
    called: list[str] = []

    def hook(_: Exception) -> None:
        called.append("x")

    boundary = ErrorBoundary(on_error=hook, fallback="error")

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    assert called == ["x"]


def test_multiple_hooks_executed_in_order() -> None:
    """Test that multiple hooks are executed in order."""
    execution_order: list[str] = []

    def hook1(_: Exception) -> None:
        execution_order.append("hook1")

    def hook2(_: Exception) -> None:
        execution_order.append("hook2")

    def hook3(_: Exception) -> None:
        execution_order.append("hook3")

    boundary = ErrorBoundary(on_error=[hook1, hook2, hook3], fallback="error")

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    assert execution_order == ["hook1", "hook2", "hook3"]


def test_string_fallback_renders(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that string fallback is rendered via render_string_fallback."""
    mock_render = Mock()
    # Patch at the module level where render_string_fallback is imported
    monkeypatch.setattr(sys.modules["st_error_boundary.error_boundary"], "render_string_fallback", mock_render)

    boundary = ErrorBoundary(on_error=lambda _: None, fallback="Error message")

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    mock_render.assert_called_once_with("Error message")


def test_callable_fallback_renders() -> None:
    """Test that callable fallback is executed."""
    fallback_called: list[bool] = []

    def custom_fallback(_: Exception) -> None:
        fallback_called.append(True)

    boundary = ErrorBoundary(on_error=lambda _: None, fallback=custom_fallback)

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    assert fallback_called == [True]


def test_keyboard_interrupt_passes_through() -> None:
    """Test that KeyboardInterrupt is re-raised."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def interrupted() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        interrupted()


def test_system_exit_passes_through() -> None:
    """Test that SystemExit is re-raised."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def exit_func() -> None:
        raise SystemExit(1)

    with pytest.raises(SystemExit):
        exit_func()


def test_generator_exit_passes_through() -> None:
    """Test that GeneratorExit (BaseException) is re-raised."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def gen_exit() -> None:
        raise GeneratorExit

    with pytest.raises(GeneratorExit):
        gen_exit()


def test_hook_failure_suppressed() -> None:
    """Test that exception in hook doesn't crash the boundary."""
    hooks_executed: list[str] = []

    def failing_hook(_: Exception) -> None:
        hooks_executed.append("failing")
        msg = "hook failed"
        raise RuntimeError(msg)

    def success_hook(_: Exception) -> None:
        hooks_executed.append("success")

    boundary = ErrorBoundary(on_error=[failing_hook, success_hook], fallback="error")

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    # Both hooks should have been attempted
    assert hooks_executed == ["failing", "success"]


def test_normal_return_value_preserved() -> None:
    """Test that normal execution returns the original value."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def success() -> str:
        return "success"

    result = success()
    assert result == "success"


def test_exception_returns_none() -> None:
    """Test that exception returns None."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def boom() -> str:
        msg = "error"
        raise RuntimeError(msg)

    result = boom()
    assert result is None


def test_function_metadata_preserved() -> None:
    """Test that @wraps preserves function metadata."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def my_function() -> None:
        """My docstring."""

    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "My docstring."


def test_wrap_callback_returns_original_value() -> None:
    """Test that wrap_callback returns the original callback's return value."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    def callback() -> str:
        return "callback_result"

    wrapped = boundary.wrap_callback(callback)
    result = wrapped()
    assert result == "callback_result"


def test_wrap_callback_returns_none_on_exception() -> None:
    """Test that wrap_callback returns None when an exception occurs."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    def callback() -> str:
        msg = "error"
        raise RuntimeError(msg)

    wrapped = boundary.wrap_callback(callback)
    result = wrapped()
    assert result is None


def test_wrap_callback_baseexception_passes_through() -> None:
    """Test that wrap_callback re-raises BaseException (SystemExit)."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    def callback() -> None:
        raise SystemExit(1)

    wrapped = boundary.wrap_callback(callback)
    with pytest.raises(SystemExit):
        wrapped()


def test_wrap_callback_keyboard_interrupt_passes_through() -> None:
    """Test that wrap_callback re-raises KeyboardInterrupt."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    def callback() -> None:
        raise KeyboardInterrupt

    wrapped = boundary.wrap_callback(callback)
    with pytest.raises(KeyboardInterrupt):
        wrapped()


def test_wrap_callback_hook_failure_suppressed() -> None:
    """Test that wrap_callback suppresses hook exceptions."""
    hooks_executed: list[str] = []

    def failing_hook(_: Exception) -> None:
        hooks_executed.append("failing")
        msg = "hook failed"
        raise RuntimeError(msg)

    def success_hook(_: Exception) -> None:
        hooks_executed.append("success")

    boundary = ErrorBoundary(on_error=[failing_hook, success_hook], fallback="error")

    def callback() -> None:
        msg = "callback error"
        raise RuntimeError(msg)

    wrapped = boundary.wrap_callback(callback)
    wrapped()

    # Both hooks should have been attempted
    assert hooks_executed == ["failing", "success"]


def test_wrap_callback_executes_hooks() -> None:
    """Test that wrap_callback executes all hooks in order."""
    hook_order: list[str] = []

    def hook1(_: Exception) -> None:
        hook_order.append("hook1")

    def hook2(_: Exception) -> None:
        hook_order.append("hook2")

    boundary = ErrorBoundary(on_error=[hook1, hook2], fallback="error")

    def callback() -> None:
        msg = "error"
        raise RuntimeError(msg)

    wrapped = boundary.wrap_callback(callback)
    wrapped()

    assert hook_order == ["hook1", "hook2"]


def test_wrap_callback_renders_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that wrap_callback renders fallback UI."""
    mock_render = Mock()
    monkeypatch.setattr(sys.modules["st_error_boundary.error_boundary"], "render_string_fallback", mock_render)

    boundary = ErrorBoundary(on_error=lambda _: None, fallback="Callback error")

    def callback() -> None:
        msg = "error"
        raise RuntimeError(msg)

    wrapped = boundary.wrap_callback(callback)
    wrapped()

    mock_render.assert_called_once_with("Callback error")


def test_wrap_callback_preserves_metadata() -> None:
    """Test that wrap_callback preserves function metadata."""
    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    def my_callback() -> None:
        """Callback docstring."""

    wrapped = boundary.wrap_callback(my_callback)
    assert wrapped.__name__ == "my_callback"
    assert wrapped.__doc__ == "Callback docstring."


# ============================================================================
# Runtime validation tests
# ============================================================================


def test_on_error_rejects_str_iterable() -> None:
    """Test that str is rejected as on_error to prevent list('abc') issue."""
    with pytest.raises(TypeError, match="str/bytes are not accepted"):
        ErrorBoundary(on_error="not-a-hook", fallback="error")  # type: ignore[arg-type]


def test_on_error_rejects_bytes_iterable() -> None:
    """Test that bytes is rejected as on_error."""
    with pytest.raises(TypeError, match="str/bytes are not accepted"):
        ErrorBoundary(on_error=b"not-a-hook", fallback="error")  # type: ignore[arg-type]


def test_on_error_rejects_noncallable_in_iterable() -> None:
    """Test that non-callable elements in iterable are detected."""
    with pytest.raises(TypeError, match=r"on_error\[1\] is not callable: 123"):
        ErrorBoundary(on_error=[lambda _: None, 123], fallback="error")  # type: ignore[list-item]


def test_on_error_rejects_non_iterable() -> None:
    """Test that non-iterable, non-callable on_error is rejected."""
    with pytest.raises(TypeError, match="must be callable or an iterable"):
        ErrorBoundary(on_error=123, fallback="error")  # type: ignore[arg-type]


def test_fallback_rejects_invalid_type() -> None:
    """Test that fallback rejects non-str, non-callable values."""
    with pytest.raises(TypeError, match="fallback must be either a string or a callable"):
        ErrorBoundary(on_error=lambda _: None, fallback=123)  # type: ignore[arg-type]


def test_on_error_accepts_empty_iterable() -> None:
    """Test that empty iterable is accepted for on_error."""
    # Should not raise TypeError
    boundary = ErrorBoundary(on_error=[], fallback="error")

    # Verify it works by decorating a function
    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    # Should execute without errors (no hooks to call)
    boom()


def test_on_error_accepts_generator() -> None:
    """Test that generator expressions are accepted for on_error."""
    called: list[str] = []

    def hook1(_: Exception) -> None:
        called.append("hook1")

    def hook2(_: Exception) -> None:
        called.append("hook2")

    # Use generator expression
    hooks = (h for h in [hook1, hook2])
    boundary = ErrorBoundary(on_error=hooks, fallback="error")

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    # Verify both hooks were called
    assert called == ["hook1", "hook2"]


# ============================================================================
# Control flow exception tests
# ============================================================================


def test_unknown_baseexception_is_reraised_in_decorate() -> None:
    """Test that unknown BaseException is re-raised without handling."""

    class UnknownBaseException(BaseException):
        """Custom BaseException for testing."""

    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def raise_unknown_baseexception() -> None:
        msg = "test"
        raise UnknownBaseException(msg)

    # Unknown BaseException should be re-raised
    with pytest.raises(UnknownBaseException):
        raise_unknown_baseexception()


def test_unknown_baseexception_is_reraised_in_callback() -> None:
    """Test that unknown BaseException is re-raised in callbacks."""

    class UnknownBaseException(BaseException):
        """Custom BaseException for testing."""

    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    def callback() -> None:
        msg = "test"
        raise UnknownBaseException(msg)

    wrapped = boundary.wrap_callback(callback)

    # Unknown BaseException should be re-raised
    with pytest.raises(UnknownBaseException):
        wrapped()


def test_unknown_baseexception_does_not_call_hook() -> None:
    """Test that hooks are not called for unknown BaseException."""
    hook_called: list[bool] = []

    class UnknownBaseException(BaseException):
        """Custom BaseException for testing."""

    def hook(_: Exception) -> None:
        hook_called.append(True)

    boundary = ErrorBoundary(on_error=hook, fallback="error")

    @boundary.decorate
    def raise_unknown_baseexception() -> None:
        msg = "test"
        raise UnknownBaseException(msg)

    # Unknown BaseException should be re-raised without calling hooks
    with pytest.raises(UnknownBaseException):
        raise_unknown_baseexception()

    # Hook should not have been called
    assert hook_called == []


def test_hook_raising_baseexception_is_propagated() -> None:
    """Test that BaseException raised in hook is propagated (not suppressed).

    Hooks that raise Exception are suppressed to prevent cascading errors,
    but BaseException (like SystemExit) should propagate to allow proper
    application shutdown.
    """

    def hook_raises_systemexit(_: Exception) -> None:
        raise SystemExit(0)

    boundary = ErrorBoundary(on_error=hook_raises_systemexit, fallback="error")

    @boundary.decorate
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    # SystemExit from hook should propagate
    with pytest.raises(SystemExit):
        boom()


def test_fallback_exception_is_propagated() -> None:
    """Test that exceptions in fallback renderer are propagated (not suppressed).

    This ensures that bugs in fallback UI code are not silently ignored.
    """

    def bad_fallback(_: Exception) -> None:
        msg = "fallback failed"
        raise RuntimeError(msg)

    boundary = ErrorBoundary(on_error=lambda _: None, fallback=bad_fallback)

    @boundary.decorate
    def boom() -> None:
        msg = "original error"
        raise ValueError(msg)

    # RuntimeError from fallback should propagate
    with pytest.raises(RuntimeError, match="fallback failed"):
        boom()


def test_passthrough_without_internal_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that control flow exceptions pass through even if import fails.

    If _is_streamlit_control_flow returns False (e.g., due to import failure),
    control flow exceptions should still be re-raised via the "unknown BaseException"
    path, ensuring st.rerun()/st.stop() don't break.
    """

    # Get the actual module object (not the function with the same name)
    eb_module = sys.modules["st_error_boundary.error_boundary"]

    # Simulate import failure - _is_streamlit_control_flow always returns False
    def always_false(_exc: BaseException) -> bool:
        return False

    monkeypatch.setattr(eb_module, "_is_streamlit_control_flow", always_false)

    class ControlFlowException(BaseException):
        """Simulates a control flow exception like RerunException."""

    boundary = ErrorBoundary(on_error=lambda _: None, fallback="error")

    @boundary.decorate
    def raise_control_flow() -> None:
        raise ControlFlowException

    # Control flow exception should still be re-raised via unknown BaseException path
    with pytest.raises(ControlFlowException):
        raise_control_flow()
