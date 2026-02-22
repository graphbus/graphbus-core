"""
graphbus_core.auth — API key management and interactive onboarding.

Flow (same order every time):
  1. GRAPHBUS_API_KEY environment variable
  2. ~/.graphbus/credentials.json  (written by the onboarding prompt)
  3. Interactive first-run onboarding — asks for key, optionally opens browser,
     validates format, saves to credentials file, sets env var for the process.

Usage (CLI, run.py, build.py, tests):
    from graphbus_core.auth import ensure_api_key
    api_key = ensure_api_key()   # always returns a non-empty string or sys.exit(1)
"""

from __future__ import annotations

import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CREDENTIALS_PATH: Path = Path.home() / ".graphbus" / "credentials.json"
ONBOARDING_URL: str = "https://graphbus.com/onboarding"
_KEY_PREFIX: str = "gb_"
_KEY_MIN_LEN: int = 16   # gb_ + 13 chars minimum


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_stored_key() -> str:
    """Return the key stored in ~/.graphbus/credentials.json, or ''."""
    try:
        if CREDENTIALS_PATH.exists():
            data = json.loads(CREDENTIALS_PATH.read_text())
            return data.get("api_key", "").strip()
    except Exception:
        pass
    return ""


def _save_key(api_key: str) -> None:
    """Persist *api_key* to ~/.graphbus/credentials.json (mode 600)."""
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if CREDENTIALS_PATH.exists():
        try:
            existing = json.loads(CREDENTIALS_PATH.read_text())
        except Exception:
            pass
    existing["api_key"] = api_key
    CREDENTIALS_PATH.write_text(json.dumps(existing, indent=2))
    CREDENTIALS_PATH.chmod(0o600)


def _validate_key_format(key: str) -> bool:
    """Return True if *key* looks like a GraphBus API key."""
    return (
        isinstance(key, str)
        and key.startswith(_KEY_PREFIX)
        and len(key) >= _KEY_MIN_LEN
        and key[len(_KEY_PREFIX):].replace("-", "").replace("_", "").isalnum()
    )


# ---------------------------------------------------------------------------
# Rich helpers (graceful fallback if rich is not installed)
# ---------------------------------------------------------------------------

def _print_banner() -> None:
    """Print the welcome / onboarding banner."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        title = Text("GraphBus", style="bold cyan")
        body = Text.assemble(
            ("Multi-agent orchestration for your codebase.\n\n", ""),
            ("To get started you need a ", ""),
            ("GraphBus API key", "bold"),
            (".\n\n", ""),
            ("  Get yours free → ", "dim"),
            (ONBOARDING_URL, "bold cyan underline"),
        )
        console.print()
        console.print(Panel(body, title=title, border_style="cyan", padding=(1, 3)))
        console.print()
    except ImportError:
        # Fallback: plain ANSI
        cyan = "\033[96m"
        bold = "\033[1m"
        reset = "\033[0m"
        dim = "\033[2m"
        line = "─" * 58
        print(f"\n{cyan}{line}{reset}")
        print(f"  {bold}GraphBus{reset}  —  multi-agent orchestration")
        print(f"{cyan}{line}{reset}")
        print(f"  To get started, you need a {bold}GraphBus API key{reset}.")
        print(f"  {dim}Get yours free → {reset}{cyan}{ONBOARDING_URL}{reset}\n")


def _prompt_for_key(console=None) -> Optional[str]:
    """
    Interactive prompt loop.  Returns a valid key string, or None if the
    user chose to skip.
    """
    try:
        from rich.console import Console
        from rich.prompt import Prompt, Confirm
        _con = console or Console()
    except ImportError:
        _con = None

    def _ask(prompt_text: str, default: str = "") -> str:
        if _con:
            return Prompt.ask(f"[bold]{prompt_text}[/bold]", default=default)
        return input(f"{prompt_text}: ").strip()

    def _confirm(prompt_text: str) -> bool:
        if _con:
            from rich.prompt import Confirm
            return Confirm.ask(f"[bold]{prompt_text}[/bold]")
        ans = input(f"{prompt_text} [y/N]: ").strip().lower()
        return ans in ("y", "yes")

    # Offer to open the browser first
    if _confirm("Open graphbus.com/onboarding in your browser?"):
        webbrowser.open(ONBOARDING_URL)
        if _con:
            _con.print(
                "\n[dim]Sign up, copy your API key, then come back here.[/dim]\n"
            )
        else:
            print("\nSign up, copy your API key, then come back here.\n")

    while True:
        raw = _ask("Paste your GraphBus API key (or 'skip' to continue without)")
        stripped = raw.strip()

        if stripped.lower() in ("skip", "s", ""):
            return None

        if _validate_key_format(stripped):
            return stripped

        msg = (
            f"[yellow]⚠  That doesn't look like a valid GraphBus key "
            f"(expected {_KEY_PREFIX}…).[/yellow]\n"
            "   Check your key at graphbus.com/onboarding or type 'skip'."
        )
        if _con:
            _con.print(msg)
        else:
            print(f"⚠  That doesn't look like a valid GraphBus key (expected {_KEY_PREFIX}...).")
            print("   Check your key at graphbus.com/onboarding or type 'skip'.")


def _print_success(key: str) -> None:
    masked = key[:8] + "…"
    try:
        from rich.console import Console
        Console().print(
            f"\n[bold green]✓[/bold green]  API key saved "
            f"([dim]{masked}[/dim])  →  [dim]{CREDENTIALS_PATH}[/dim]\n"
        )
    except ImportError:
        print(f"\n✓  API key saved ({masked})  →  {CREDENTIALS_PATH}\n")


def _print_skipped() -> None:
    try:
        from rich.console import Console
        Console().print(
            "\n[yellow]⚠[/yellow]  Continuing without a GraphBus API key. "
            "Some features will be unavailable.\n"
            f"   Get yours at [cyan]{ONBOARDING_URL}[/cyan]\n"
        )
    except ImportError:
        print(f"\n⚠  Continuing without a GraphBus API key. Get yours at {ONBOARDING_URL}\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_api_key(*, required: bool = True) -> str:
    """
    Return the active GraphBus API key, running interactive onboarding if needed.

    Resolution order
    ----------------
    1. ``GRAPHBUS_API_KEY`` environment variable
    2. ``~/.graphbus/credentials.json``
    3. Interactive first-run prompt (opens browser, validates, saves)

    Parameters
    ----------
    required:
        If *True* (default) and the user skips onboarding, exit with code 1.
        If *False*, return ``""`` instead of exiting so callers can degrade
        gracefully.

    Returns
    -------
    str
        A non-empty API key string (or ``""`` when *required=False* and the
        user skipped).
    """
    # 1. Environment variable
    key = os.getenv("GRAPHBUS_API_KEY", "").strip()
    if key:
        return key

    # 2. Stored credentials
    key = _load_stored_key()
    if key:
        os.environ["GRAPHBUS_API_KEY"] = key
        return key

    # 3. Interactive onboarding
    _print_banner()
    key = _prompt_for_key()

    if not key:
        _print_skipped()
        if required:
            sys.exit(1)
        return ""

    _save_key(key)
    os.environ["GRAPHBUS_API_KEY"] = key
    _print_success(key)
    return key


def get_api_key() -> str:
    """
    Return the current API key without triggering onboarding.

    Returns ``""`` if no key is configured. Useful for optional features
    (e.g. negotiation history warehousing) that should degrade gracefully.
    """
    return (
        os.getenv("GRAPHBUS_API_KEY", "").strip()
        or _load_stored_key()
    )
