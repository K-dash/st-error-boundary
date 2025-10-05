from __future__ import annotations

import sys
from unittest.mock import Mock

import pytest

from st_error_boundary import error_boundary


def test_error_boundary_is_callable() -> None:
    """Verify error_boundary is a callable decorator."""
    assert callable(error_boundary)


def test_single_hook_is_called() -> None:
    """Test that a single error hook is executed when exception occurs."""
    called: list[str] = []

    def hook(_: Exception) -> None:
        called.append("x")

    @error_boundary(on_error=hook, fallback="error")
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

    @error_boundary(on_error=[hook1, hook2, hook3], fallback="error")
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

    @error_boundary(on_error=lambda _: None, fallback="Error message")
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

    @error_boundary(on_error=lambda _: None, fallback=custom_fallback)
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    assert fallback_called == [True]


def test_keyboard_interrupt_passes_through() -> None:
    """Test that KeyboardInterrupt is re-raised."""

    @error_boundary(on_error=lambda _: None, fallback="error")
    def interrupted() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        interrupted()


def test_system_exit_passes_through() -> None:
    """Test that SystemExit is re-raised."""

    @error_boundary(on_error=lambda _: None, fallback="error")
    def exit_func() -> None:
        raise SystemExit(1)

    with pytest.raises(SystemExit):
        exit_func()


def test_generator_exit_passes_through() -> None:
    """Test that GeneratorExit (BaseException) is re-raised."""

    @error_boundary(on_error=lambda _: None, fallback="error")
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

    @error_boundary(on_error=[failing_hook, success_hook], fallback="error")
    def boom() -> None:
        msg = "error"
        raise RuntimeError(msg)

    boom()
    # Both hooks should have been attempted
    assert hooks_executed == ["failing", "success"]


def test_normal_return_value_preserved() -> None:
    """Test that normal execution returns the original value."""

    @error_boundary(on_error=lambda _: None, fallback="error")
    def success() -> str:
        return "success"

    result = success()
    assert result == "success"


def test_exception_returns_none() -> None:
    """Test that exception returns None."""

    @error_boundary(on_error=lambda _: None, fallback="error")
    def boom() -> str:
        msg = "error"
        raise RuntimeError(msg)

    result = boom()
    assert result is None


def test_function_metadata_preserved() -> None:
    """Test that @wraps preserves function metadata."""

    @error_boundary(on_error=lambda _: None, fallback="error")
    def my_function() -> None:
        """My docstring."""

    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "My docstring."
