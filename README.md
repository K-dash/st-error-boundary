# st-error-boundary

A minimal, type-safe error boundary library for Streamlit applications with pluggable hooks and safe fallback UI.

## Features

- **Minimal API**: Just two required arguments (`on_error` and `fallback`)
- **Type-safe**: Full Python 3.12+ type hints with strict mypy/pyright checking
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

**Limitation**: `on_click`/`on_change` callbacks are **not protected** with this approach.

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
2. Streamlit executes `callback()` � **Not protected by decorator**
3. Streamlit reruns the script
4. Decorated function executes � **Protected by decorator**

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
