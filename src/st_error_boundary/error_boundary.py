"""Error boundary decorator for Streamlit applications."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from functools import wraps
from typing import Protocol, cast

from .plugins import render_string_fallback


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


def error_boundary[**P, R](
    on_error: ErrorHook | Iterable[ErrorHook],
    fallback: str | FallbackRenderer,
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Minimal decorator that catches unhandled exceptions and displays safe fallback UI.

    This decorator acts as the "last resort" error boundary, preventing uncaught
    exceptions from exposing sensitive information in the UI.

    Args:
        on_error: Single hook or iterable of hooks for side effects (audit logging,
            notifications, metrics, etc.). Hooks are executed in order.
        fallback: Either a string (displayed via `st.error()` by default) or a
            custom callable that renders arbitrary UI. When a string is provided,
            it will be automatically passed to Streamlit's `st.error()` function
            to display the error message.

    Returns:
        Decorator function that returns the original result on success, or None
        when an exception occurs.

    Example:
        >>> @error_boundary(
        ...     on_error=lambda e: print(f"Error: {e}"),
        ...     fallback="An error occurred. Please try again later.",
        ... )
        ... def my_func():
        ...     # Your code here
        ...     pass

    """
    if not callable(on_error):
        hooks: Sequence[ErrorHook] = cast("Sequence[ErrorHook]", list(on_error))
    else:
        hooks = [on_error]

    def _render_fallback(exc: Exception) -> None:
        if callable(fallback):
            fallback(exc)
        else:
            render_string_fallback(fallback)

    def _decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        @wraps(func)
        def _wrapped(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return func(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:  # noqa: BLE001
                for hook in hooks:
                    try:
                        hook(exc)
                    except Exception:  # noqa: S110, BLE001
                        # Suppress hook failures to prevent cascading errors
                        pass
                _render_fallback(exc)
                return None

        return _wrapped

    return _decorator
