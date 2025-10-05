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
