[![PyPI version](https://img.shields.io/pypi/v/st-error-boundary.svg)](https://pypi.org/project/st-error-boundary/)
[![Python versions](https://img.shields.io/pypi/pyversions/st-error-boundary.svg)](https://pypi.org/project/st-error-boundary/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/st-error-boundary?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/st-error-boundary)
[![codecov](https://codecov.io/gh/K-dash/st-error-boundary/graph/badge.svg?token=nhDsSbTkaJ)](https://codecov.io/gh/K-dash/st-error-boundary)

# st-error-boundary

English | [日本語](README.ja.md)

A minimal, type-safe error boundary library for Streamlit applications with pluggable hooks and safe fallback UI.

## Motivation

Streamlit's default behavior displays detailed stack traces in the browser when exceptions occur. While `client.showErrorDetails = "none"` prevents information leakage, it shows only generic error messages, leaving users confused. The typical solution—scattering `st.error()` and `st.stop()` calls throughout your code—**severely degrades readability and maintainability**, and creates a risk of **forgetting exception handling** in critical places.

This library solves the problem with the **decorator pattern**: a single "last line of defense" decorator that separates exception handling (cross-cutting concern) from business logic. Just decorate your main function, and all unhandled exceptions are caught and displayed with user-friendly messages—no need to pollute your code with error handling boilerplate everywhere.

This pattern is extracted from production use and open-sourced to help others build robust Streamlit applications without sacrificing code clarity. For the full architectural context, see the [PyConJP 2025 presentation](https://speakerdeck.com/kdash/streamlit-hashe-nei-turudakeziyanai-poc-nosu-sadeshi-xian-surushang-yong-pin-zhi-nofen-xi-saas-akitekutiya).

In **customer-facing and regulated** environments, an unhandled exception that leaks internals isn’t just noisy—it can be a business incident. You want **no stack traces in the UI**, but **rich, sanitized telemetry** behind the scenes.

## Who is this for?

Teams shipping **customer-facing** Streamlit apps (B2B/B2C, regulated or enterprise settings) where you want **no stack traces in the UI**, but **rich telemetry** in your logs/alerts. The boundary provides a **consistent, user-friendly fallback** while `on_error` sends **sanitized** details to your observability stack.


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

## Comparison: Traditional try/except vs ErrorBoundary (raise-only)

### Traditional: scatter try/except + `st.error()` / `st.stop()` in each screen

```python
from __future__ import annotations
import streamlit as st

def save_profile(name: str) -> None:
    if not name:
        raise ValueError("Name is required")
    # ... persist ...

def main() -> None:
    st.title("Profile")
    name: str = st.text_input("Name", "")
    if st.button("Save"):
        try:
            save_profile(name)
            st.success("Saved!")
        except ValueError as exc:
            st.error(f"Input error: {exc}")
            st.stop()  # stop to avoid broken UI after errors

if __name__ == "__main__":
    main()
```

* Drawbacks: exception handling is **duplicated and easy to forget**, readability suffers, and a cross-cutting concern leaks into business logic.

### ErrorBoundary: just **raise**, and let the boundary handle UI + hooks

```python
from __future__ import annotations
import streamlit as st
from st_error_boundary import ErrorBoundary

def audit_log(exc: Exception) -> None:
    # send to your telemetry/metrics
    print(f"[audit] {exc!r}")

def fallback_ui(exc: Exception) -> None:
    st.error("An unexpected error occurred. Please try again later.")
    if st.button("Retry"):
        st.rerun()

boundary: ErrorBoundary = ErrorBoundary(
    on_error=audit_log,
    fallback=fallback_ui,  # string is also allowed; it is rendered via st.error() internally
)

def save_profile(name: str) -> None:
    if not name:
        raise ValueError("Name is required")
    # ... persist ...

@boundary.decorate
def main() -> None:
    st.title("Profile")
    name: str = st.text_input("Name", "")
    if st.button("Save"):
        # No local try/except: domain errors bubble to the boundary
        save_profile(name)

if __name__ == "__main__":
    main()
```

* Benefits: **single place** for error UI and side effects; business code stays clean. When `fallback` is a string, it is shown with `st.error()` internally (use a callable for custom UI).
* Callbacks (`on_click` / `on_change`) run outside the decorated scope—wrap them with `boundary.wrap_callback(...)`.
* Control-flow exceptions (`st.rerun()`, `st.stop()`) **pass through** boundaries; keep using them intentionally as needed (you don't need `st.stop()` as error handling boilerplate).

### When to still use local try/except

* You want to **recover inline** (e.g., fix input and continue).
* You need **fine-grained branching UI** for a specific, expected exception.
* You implement a **local retry** for an external API and intentionally swallow the exception.

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

### Nested ErrorBoundary Behavior

When `ErrorBoundary` instances are nested (hierarchical), the following rules apply:

1. **Inner boundary handles first** (first-match wins)
    - The innermost boundary that catches the exception handles it.

2. **Only inner hooks execute**
    - When the inner boundary handles an exception, **only the inner boundary's hooks are called**. Outer boundary hooks are NOT executed.

3. **Fallback exceptions bubble up**
    - If the inner boundary's fallback raises an exception, that exception propagates to the outer boundary. The outer boundary then handles it (by design, fallback bugs are not silently ignored).

4. **Control flow exceptions pass through**
    - Streamlit control flow exceptions (`st.rerun()`, `st.stop()`) pass through **all** boundaries without being caught.

5. **Same rules for callbacks**
    - `wrap_callback()` follows the same nesting rules—the innermost boundary wrapping the callback handles exceptions.

#### Example: Inner Boundary Handles

```python
outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback="INNER")

@outer.decorate
def main():
    @inner.decorate
    def section():
        raise ValueError("boom")
    section()
```

**Result**:
- `INNER` fallback is displayed
- Only `inner_hook` is called (not `outer_hook`)

#### Example: Fallback Exception Bubbles

```python
def bad_fallback(exc: Exception):
    raise RuntimeError("fallback failed")

outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback=bad_fallback)

@outer.decorate
def main():
    @inner.decorate
    def section():
        raise ValueError("boom")
    section()
```

**Result**:
- `OUTER` fallback is displayed (inner fallback raised exception)
- Both `inner_hook` and `outer_hook` are called (inner first, then outer)

#### Best Practice

- **Inner fallback**: Render UI and finish (don't raise). This keeps errors isolated.
- **Outer fallback**: If you want outer boundaries to handle certain errors, explicitly `raise` from the inner fallback.

#### Test Coverage

All nested boundary behaviors are verified by automated tests.
See [`tests/test_integration.py`](tests/test_integration.py) for implementation details.

## Development

```bash
# Install dependencies
make install

# Install pre-commit hooks (recommended)
make install-hooks

# Run linting and type checking
make

# Run tests
make test

# Run example app
make example

# Run demo
make demo
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to automatically run code quality checks before each commit:

- **Code Formatting**: ruff format
- **Linting**: ruff check
- **Type Checking**: mypy and pyright
- **Tests**: pytest
- **Other Checks**: trailing whitespace, end-of-file, YAML/TOML validation

**Setup:**

```bash
# Install pre-commit hooks (one-time setup)
make install-hooks
```

After installation, the hooks will run automatically on `git commit`. To run manually:

```bash
# Run on all files
uv run pre-commit run --all-files

# Skip hooks for a specific commit (not recommended)
git commit --no-verify
```

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
