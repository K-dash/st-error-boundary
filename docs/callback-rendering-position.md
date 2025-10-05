# Callback Error Rendering Position

## Problem

When using `wrap_callback()` to protect widget callbacks (e.g., `on_click`, `on_change`), errors caught in callbacks are rendered at the **top of the page** instead of near the widget that triggered them.

### Example

```python
boundary = ErrorBoundary(
    on_error=lambda exc: print(f"Error: {exc}"),
    fallback=lambda _: st.error("An error occurred")
)

def trigger_error():
    raise ValueError("Error!")

st.button("Click me", on_click=boundary.wrap_callback(trigger_error))
```

**Result**: The error message appears at the top of the page, not below the button.

## Why This Happens

This is a Streamlit architectural limitation:

1. **Callbacks execute BEFORE script rerun**: When you click a button with `on_click`, Streamlit executes the callback first
2. **Page structure doesn't exist yet**: At callback execution time, the page layout (containers, widgets, etc.) hasn't been rendered yet
3. **Default rendering position**: Therefore, any UI rendered in the callback (like `st.error`) appears at the default location (top of page)

### Execution Order

```
User clicks button
    ↓
1. Callback executes (page structure doesn't exist)
    ↓
2. Script reruns (page structure is created)
    ↓
3. Widgets are rendered
```

## Solution: Deferred Rendering Pattern

Instead of rendering UI in the callback, **store error information in `session_state`** and render it during the main script execution.

### Implementation

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# Initialize session state
if "callback_error" not in st.session_state:
    st.session_state.callback_error = None

def store_error(exc: Exception) -> None:
    """Store error in session_state instead of rendering."""
    st.session_state.callback_error = str(exc)

def silent_fallback(_: Exception) -> None:
    """Don't render anything in callback - just store the error."""
    pass

# Create boundary with deferred rendering
boundary = ErrorBoundary(on_error=store_error, fallback=silent_fallback)

def trigger_error():
    raise ValueError("Error in callback!")

# Main app
st.title("My App")

st.button("Click me", on_click=boundary.wrap_callback(trigger_error))

# Render error AFTER the button (during script rerun)
if st.session_state.callback_error:
    st.error(f"Error: {st.session_state.callback_error}")
    if st.button("Clear Error"):
        st.session_state.callback_error = None
        st.rerun()
```

### How It Works

1. **Callback execution**: `store_error` saves the exception to `session_state`, `silent_fallback` does nothing
2. **Script rerun**: The button is rendered first
3. **Error rendering**: After the button, we check `session_state.callback_error` and render the error message

**Result**: The error message appears **below the button**, in the correct position.

## Complete Example

See [`examples/demo.py`](../examples/demo.py) for a complete working example comparing direct errors and callback errors.

## Benefits

- Full control over error message position
- Consistent with Streamlit's execution model
- Can customize error UI per widget/section

## Limitations

- This pattern requires manual error rendering code
- Adds boilerplate compared to simple `fallback` usage
- Error state persists across reruns until explicitly cleared

## When to Use This Pattern

**Use deferred rendering when:**
- Error position is important for UX
- You have multiple widgets and need errors to appear near each widget
- You want to customize error UI per section

**Use standard `wrap_callback()` when:**
- Error position doesn't matter
- You want simple, minimal code
- Errors are rare edge cases

## Alternative: Avoid Callbacks

If possible, restructure your code to avoid `on_click`/`on_change` callbacks:

```python
# Instead of:
st.button("Click", on_click=handle_click)

# Use:
if st.button("Click"):
    handle_click()
```

This way, errors occur during main script execution and are naturally rendered in the correct position by the `@boundary.decorate` decorator.
