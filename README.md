[![codecov](https://codecov.io/gh/K-dash/st-error-boundary/graph/badge.svg?token=nhDsSbTkaJ)](https://codecov.io/gh/K-dash/st-error-boundary)

# st-error-boundary

English | [日本語](README.ja.md)

A minimal, type-safe error boundary library for Streamlit applications with pluggable hooks and safe fallback UI.

## Motivation

Streamlit's default behavior displays detailed stack traces in the browser when exceptions occur. While `client.showErrorDetails = "none"` prevents information leakage, it shows only generic error messages, leaving users confused. The typical solution—scattering `st.error()` and `st.stop()` calls throughout your code—**severely degrades readability and maintainability**, and creates a risk of **forgetting exception handling** in critical places.

This library solves the problem with the **decorator pattern**: a single "last line of defense" decorator that separates exception handling (cross-cutting concern) from business logic. Just decorate your main function, and all unhandled exceptions are caught and displayed with user-friendly messages—no need to pollute your code with error handling boilerplate everywhere.

This pattern is extracted from production use and open-sourced to help others build robust Streamlit applications without sacrificing code clarity. For the full architectural context, see the [PyConJP 2025 presentation](https://speakerdeck.com/kdash/streamlit-hashe-nei-turudakeziyanai-poc-nosu-sadeshi-xian-surushang-yong-pin-zhi-nofen-xi-saas-akitekutiya).

## Features

- **Minimal API**: Just two required arguments (`on_error` and `fallback`)
- **PEP 561 Compatible**: Ships with `py.typed` for full type checker support
- **Callback Protection**: Protect both decorated functions and widget callbacks (`on_click`, `on_change`, etc.)
- **Pluggable Hooks**: Execute side effects (audit logging, metrics, notifications) when errors occur
- **Safe Fallback UI**: Display user-friendly error messages instead of tracebacks

## Installation

```bash
pip install st-error-boundary
```

## Quick Start

### Basic Usage (Decorator Only)

For simple cases where you only need to protect the main function:

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# Create error boundary
boundary = ErrorBoundary(
    on_error=lambda exc: print(f"Error logged: {exc}"),
    fallback="An error occurred. Please try again later."
)

@boundary.decorate
def main() -> None:
    st.title("My App")

    if st.button("Trigger Error"):
        raise ValueError("Something went wrong")

if __name__ == "__main__":
    main()
```

**⚠️ Important**: The `@boundary.decorate` decorator alone does **not** protect `on_click`/`on_change` callbacks—you must use `boundary.wrap_callback()` for those (see Advanced Usage below).

### Advanced Usage (With Callbacks)

To protect both decorated functions **and** widget callbacks:

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

def audit_log(exc: Exception) -> None:
    # Log to monitoring service
    print(f"Error: {exc}")

def fallback_ui(exc: Exception) -> None:
    st.error("An unexpected error occurred.")
    st.link_button("Contact Support", "https://example.com/support")
    if st.button("Retry"):
        st.rerun()

# Single ErrorBoundary instance for DRY configuration
boundary = ErrorBoundary(on_error=audit_log, fallback=fallback_ui)

def handle_click() -> None:
    # This will raise an error
    result = 1 / 0

@boundary.decorate
def main() -> None:
    st.title("My App")

    # Protected: error in if statement
    if st.button("Direct Error"):
        raise ValueError("Error in main function")

    # Protected: error in callback
    st.button("Callback Error", on_click=boundary.wrap_callback(handle_click))

if __name__ == "__main__":
    main()
```

## Why ErrorBoundary Class?

Streamlit executes `on_click` and `on_change` callbacks **before** the script reruns, meaning they run **outside** the decorated function's scope. This is why `@boundary.decorate` alone cannot catch callback errors.

**Execution Flow:**
1. User clicks button with `on_click=callback`
2. Streamlit executes `callback()` -> **Not protected by decorator**
3. Streamlit reruns the script
4. Decorated function executes -> **Protected by decorator**

**Solution**: Use `boundary.wrap_callback()` to explicitly wrap callbacks with the same error handling logic.

## API Reference

### `ErrorBoundary`

```python
ErrorBoundary(
    on_error: ErrorHook | Iterable[ErrorHook],
    fallback: str | FallbackRenderer
)
```

**Parameters:**
- `on_error`: Single hook or list of hooks for side effects (logging, metrics, etc.)
- `fallback`: Either a string (displayed via `st.error()`) or a callable that renders custom UI
  - When `fallback` is a `str`, it is rendered using `st.error()` internally
  - To customize rendering (e.g., use `st.warning()` or custom widgets), pass a `FallbackRenderer` callable instead

**Methods:**
- `.decorate(func)`: Decorator to wrap a function with error boundary
- `.wrap_callback(callback)`: Wrap a widget callback (on_click, on_change, etc.)

### `ErrorHook` Protocol

```python
def hook(exc: Exception) -> None:
    """Handle exception with side effects."""
    ...
```

### `FallbackRenderer` Protocol

```python
def renderer(exc: Exception) -> None:
    """Render fallback UI for the exception."""
    ...
```

## Examples

### Multiple Hooks

```python
def log_error(exc: Exception) -> None:
    logging.error(f"Error: {exc}")

def send_metric(exc: Exception) -> None:
    metrics.increment("app.errors")

boundary = ErrorBoundary(
    on_error=[log_error, send_metric],  # Hooks execute in order
    fallback="An error occurred."
)
```

### Custom Fallback UI

```python
def custom_fallback(exc: Exception) -> None:
    st.error(f"Error: {type(exc).__name__}")
    st.warning("Please try again or contact support.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Retry"):
            st.rerun()
    with col2:
        st.link_button("Report Bug", "https://example.com/bug-report")

boundary = ErrorBoundary(on_error=lambda _: None, fallback=custom_fallback)
```

## Important Notes

### Callback Error Rendering Position

**TL;DR**: Errors in callbacks appear at the top of the page, not near the widget. Use the deferred rendering pattern (below) to control error position.

When using `wrap_callback()`, errors in widget callbacks (`on_click`, `on_change`) are rendered at the **top of the page** instead of near the widget. This is a Streamlit architectural limitation.

#### Deferred Rendering Pattern

Store errors in `session_state` during callback execution, then render them during main script execution:

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# Initialize session state
if "error" not in st.session_state:
    st.session_state.error = None

# Store error instead of rendering it
boundary = ErrorBoundary(
    on_error=lambda exc: st.session_state.update(error=str(exc)),
    fallback=lambda _: None  # Silent - defer to main script
)

def trigger_error():
    raise ValueError("Error in callback!")

# Main app
st.button("Click", on_click=boundary.wrap_callback(trigger_error))

# Render error after the button
if st.session_state.error:
    st.error(f"Error: {st.session_state.error}")
    if st.button("Clear"):
        st.session_state.error = None
        st.rerun()
```

**Result**: Error appears **below the button** instead of at the top.

For more details, see [Callback Rendering Position Guide](docs/callback-rendering-position.md).

## Development

```bash
# Install dependencies
make install

# Run linting and type checking
make

# Run tests
make test

# Run example app
make example
```

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
