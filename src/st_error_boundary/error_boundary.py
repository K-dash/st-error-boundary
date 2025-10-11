"""Error boundary for Streamlit applications."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from functools import wraps
from typing import Protocol, cast

from .plugins import render_string_fallback


def _is_streamlit_control_flow(exc: BaseException) -> bool:
    """Return True if exc is Streamlit's control-flow exception.

    Streamlit uses RerunException and StopException for st.rerun() and st.stop().
    These must be allowed to propagate to work correctly.

    Args:
        exc: Exception to check.

    Returns:
        True if the exception is a Streamlit control flow exception.

    """
    try:
        # v1.3x+ stable import path
        from streamlit.runtime.scriptrunner_utils.exceptions import (  # noqa: PLC0415
            RerunException,
            StopException,
        )

        return isinstance(exc, (RerunException, StopException))
    except Exception:  # noqa: BLE001
        # Older Streamlit versions or import failures - fail safe
        return False


def _should_passthrough(exc: BaseException) -> bool:
    """Return True if exception should pass through without handling.

    Args:
        exc: Exception to check.

    Returns:
        True if the exception should be re-raised without handling.

    """
    return isinstance(exc, (KeyboardInterrupt, SystemExit)) or _is_streamlit_control_flow(exc)


class ErrorHook(Protocol):
    """Protocol for error hooks that execute side effects on exceptions.

    Used for audit logging, notifications, metrics collection, etc.
    """

    def __call__(self, exc: Exception, /) -> None:
        """Handle exception with side effects."""
        ...


class FallbackRenderer(Protocol):
    """Protocol for custom fallback UI renderers.

    Allows rendering custom UI layouts when an exception occurs.
    """

    def __call__(self, exc: Exception, /) -> None:
        """Render fallback UI for the exception."""
        ...


class ErrorBoundary:
    """Error boundary with pluggable hooks and safe fallback UI.

    This class provides a centralized way to handle errors in Streamlit applications,
    supporting both decorated functions and widget callbacks (on_click, on_change, etc.).

    Args:
        on_error: Single hook or iterable of hooks for side effects (audit logging,
            notifications, metrics, etc.). Hooks are executed in order.
        fallback: Either a string (displayed via `st.error()` by default) or a
            custom callable that renders arbitrary UI. When a string is provided,
            it will be automatically passed to Streamlit's `st.error()` function
            to display the error message.

    Example:
        >>> boundary = ErrorBoundary(
        ...     on_error=lambda e: print(f"Error: {e}"),
        ...     fallback="An error occurred.",
        ... )
        >>> @boundary.decorate
        ... def main():
        ...     st.button("Click", on_click=boundary.wrap_callback(handler))

    """

    def __init__(
        self,
        on_error: ErrorHook | Iterable[ErrorHook],
        fallback: str | FallbackRenderer,
    ) -> None:
        """Initialize error boundary with hooks and fallback.

        Args:
            on_error: Single hook or iterable of hooks. str/bytes are rejected.
            fallback: String or custom renderer for fallback UI.

        Raises:
            TypeError: If on_error is str/bytes, or contains non-callable elements,
                or if fallback is neither str nor callable.

        """
        self._hooks = self._normalize_hooks(on_error)
        self._fallback = self._normalize_fallback(fallback)

    @staticmethod
    def _normalize_hooks(on_error: object) -> Sequence[ErrorHook]:
        """Normalize hook input into a validated sequence."""
        if isinstance(on_error, (str, bytes)):
            msg = "on_error must be a hook or an iterable of hooks; str/bytes are not accepted."
            raise TypeError(msg)

        if callable(on_error):
            return (cast("ErrorHook", on_error),)

        if not isinstance(on_error, Iterable):
            msg = "on_error must be callable or an iterable of callables."
            raise TypeError(msg)

        iterable_hooks = cast("Iterable[object]", on_error)

        validated: list[ErrorHook] = []
        for index, hook in enumerate(iterable_hooks):
            if not callable(hook):
                msg = f"on_error[{index}] is not callable: {hook!r}"
                raise TypeError(msg)
            validated.append(cast("ErrorHook", hook))

        return tuple(validated)

    @staticmethod
    def _normalize_fallback(fallback: object) -> str | FallbackRenderer:
        """Normalize fallback into a validated handler."""
        if isinstance(fallback, str):
            return fallback

        if callable(fallback):
            return cast("FallbackRenderer", fallback)

        msg = "fallback must be either a string or a callable (FallbackRenderer)."
        raise TypeError(msg)

    def _handle_error(self, exc: Exception) -> None:
        """Execute hooks and render fallback UI for an exception.

        Args:
            exc: The exception to handle.

        """
        # Execute all hooks, suppressing their exceptions
        for hook in self._hooks:
            try:
                hook(exc)
            except Exception:  # noqa: S110, BLE001
                # Suppress hook failures to prevent cascading errors
                pass

        # Render fallback UI
        if callable(self._fallback):
            self._fallback(exc)
        else:
            render_string_fallback(self._fallback)

    def decorate[**P, R](self, func: Callable[P, R]) -> Callable[P, R | None]:
        """Wrap a function with error boundary.

        Args:
            func: Function to wrap with error handling.

        Returns:
            Wrapped function that returns the original result on success,
            or None when an exception occurs.

        """

        @wraps(func)
        def _wrapped(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return func(*args, **kwargs)
            except BaseException as exc:
                # Pass through control flow exceptions
                if _should_passthrough(exc):
                    raise
                # Handle normal exceptions only
                if isinstance(exc, Exception):
                    self._handle_error(exc)
                    return None
                # Unknown BaseException - re-raise for safety
                raise

        return _wrapped

    def wrap_callback[**P, R](self, callback: Callable[P, R]) -> Callable[P, R | None]:
        """Wrap a widget callback with error boundary.

        This method is designed for Streamlit widget callbacks (on_click, on_change, etc.).
        Returns the original callback's return value on success, or None if an exception
        was caught.

        Args:
            callback: Widget callback to wrap with error handling.

        Returns:
            Wrapped callback that returns the original result on success,
            or None when an exception occurs.

        """

        @wraps(callback)
        def _wrapped(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return callback(*args, **kwargs)  # Return original value
            except BaseException as exc:
                # Pass through control flow exceptions
                if _should_passthrough(exc):
                    raise
                # Handle normal exceptions only
                if isinstance(exc, Exception):
                    self._handle_error(exc)
                    return None  # Only None on exception
                # Unknown BaseException - re-raise for safety
                raise

        return _wrapped


def error_boundary[**P, R](
    on_error: ErrorHook | Iterable[ErrorHook],
    fallback: str | FallbackRenderer,
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Create error boundary decorator (legacy API).

    .. deprecated::
        Use ErrorBoundary class instead for better callback support.
        This function only protects the decorated function,
        not widget callbacks (on_click, on_change, etc.).

    Args:
        on_error: Single hook or iterable of hooks for side effects.
        fallback: String or custom renderer for fallback UI.

    Returns:
        Decorator function that returns the original result on success,
        or None when an exception occurs.

    Example:
        >>> @error_boundary(
        ...     on_error=lambda e: print(f"Error: {e}"),
        ...     fallback="An error occurred.",
        ... )
        ... def my_func():
        ...     pass

    """
    return ErrorBoundary(on_error, fallback).decorate
