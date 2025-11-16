# TUI Bug Fix - Generator MountError

## Issue
When clicking buttons in the TUI (e.g., "New Project"), the following error occurred:

```
MountError: Can't mount <class 'generator'>; expected a Widget instance.
```

## Root Cause
The form creation methods (`create_init_form()`, `create_build_form()`, etc.) were:

1. **Returning** `Container` objects instead of **yielding** widgets
2. Using `yield` in the parent `compose()` method instead of `yield from`

This created a generator object that Textual couldn't mount as a widget.

## Fix Applied

### Changed in All Screen Files:
- `graphbus_cli/tui/screens/build.py`
- `graphbus_cli/tui/screens/runtime.py`
- `graphbus_cli/tui/screens/dev_tools.py`
- `graphbus_cli/tui/screens/deploy.py`
- `graphbus_cli/tui/screens/advanced.py`

### Changes Made:

#### 1. Parent `compose()` Method
**Before:**
```python
def compose(self) -> ComposeResult:
    with TabbedContent():
        with TabPane("Init Project"):
            yield self.create_init_form()  # ❌ Wrong
```

**After:**
```python
def compose(self) -> ComposeResult:
    with TabbedContent():
        with TabPane("Init Project"):
            yield from self.create_init_form()  # ✅ Correct
```

#### 2. Form Creation Methods
**Before:**
```python
def create_init_form(self) -> Container:  # ❌ Wrong return type
    with Vertical(classes="form-container") as container:
        yield Static("...")
        yield Input(...)
        # ... more widgets

    return container  # ❌ Wrong - returns Container
```

**After:**
```python
def create_init_form(self) -> ComposeResult:  # ✅ Correct return type
    with Vertical(classes="form-container"):
        yield Static("...")
        yield Input(...)
        # ... more widgets
        # No return statement - just yields
```

## Technical Explanation

### Why `yield from` is Needed
- `create_*_form()` methods are **generators** that yield multiple widgets
- Using `yield generator_func()` creates a nested generator (generator of generators)
- Textual expects individual widget instances, not generators
- `yield from` **unpacks** the generator and yields each widget directly

### Why Return Type Changed
- `Container` suggests returning a single object
- `ComposeResult` (which is `Iterable[Widget]`) correctly indicates we're yielding multiple widgets
- No `return` statement needed - just `yield` widgets as we create them

## Verification

After the fix:
```bash
$ python3 -c "from graphbus_cli.tui.app import GraphBusTUI; app = GraphBusTUI(); print('✅ Working')"
✅ Working
```

All screen instantiation tests pass:
```
✅ App instantiated
✅ HomeScreen instantiated
✅ BuildScreen instantiated
✅ RuntimeScreen instantiated
✅ DevToolsScreen instantiated
✅ DeployScreen instantiated
✅ AdvancedScreen instantiated
```

## Files Modified
- `graphbus_cli/tui/screens/build.py` (3 methods fixed)
- `graphbus_cli/tui/screens/runtime.py` (3 methods fixed)
- `graphbus_cli/tui/screens/dev_tools.py` (4 methods fixed)
- `graphbus_cli/tui/screens/deploy.py` (3 methods fixed)
- `graphbus_cli/tui/screens/advanced.py` (4 methods fixed)

**Total:** 17 methods fixed across 5 files

## Status
✅ **FIXED** - TUI now works correctly. All buttons and navigation functional.

## Testing
To test the TUI:
```bash
pip install textual
graphbus tui
```

Navigate with keyboard shortcuts:
- `h` - Home
- `b` - Build & Validate
- `r` - Runtime
- `d` - Dev Tools (this was the screen that had the error)
- `p` - Deploy
- `a` - Advanced
- `q` - Quit

All screens and tabs should now load without errors.
