"""
graphbus auth — API key management commands.

  graphbus auth login    → interactive onboarding / key setup
  graphbus auth logout   → remove stored key
  graphbus auth status   → show which key is active and where it came from
  graphbus auth whoami   → alias for status
"""

from __future__ import annotations

import os

import click
from rich.console import Console
from rich.table import Table

from graphbus_core.auth import (
    CREDENTIALS_PATH,
    ONBOARDING_URL,
    _load_stored_key,
    _print_banner,
    _prompt_for_key,
    _save_key,
    _print_success,
    get_api_key,
)

console = Console()


@click.group()
def auth() -> None:
    """Manage your GraphBus API key."""


# ---------------------------------------------------------------------------
# graphbus auth login
# ---------------------------------------------------------------------------

@auth.command("login")
def login() -> None:
    """Set or update your GraphBus API key."""
    _print_banner()
    key = _prompt_for_key(console=console)
    if not key:
        console.print(
            f"\n[yellow]⚠[/yellow]  No key entered. "
            f"Get yours at [cyan]{ONBOARDING_URL}[/cyan]\n"
        )
        return
    _save_key(key)
    os.environ["GRAPHBUS_API_KEY"] = key
    _print_success(key)


# ---------------------------------------------------------------------------
# graphbus auth logout
# ---------------------------------------------------------------------------

@auth.command("logout")
def logout() -> None:
    """Remove the stored GraphBus API key."""
    if not CREDENTIALS_PATH.exists():
        console.print("[dim]No stored key found — nothing to remove.[/dim]")
        return

    import json
    try:
        data = json.loads(CREDENTIALS_PATH.read_text())
    except Exception:
        data = {}

    if "api_key" not in data:
        console.print("[dim]No api_key in credentials file — nothing to remove.[/dim]")
        return

    old_key = data.pop("api_key", "")
    CREDENTIALS_PATH.write_text(json.dumps(data, indent=2))
    CREDENTIALS_PATH.chmod(0o600)

    masked = old_key[:8] + "…" if old_key else "?"
    console.print(
        f"\n[green]✓[/green]  Removed stored key ([dim]{masked}[/dim])\n"
        f"   GRAPHBUS_API_KEY env var (if set) is unaffected.\n"
    )


# ---------------------------------------------------------------------------
# graphbus auth status / whoami
# ---------------------------------------------------------------------------

def _status() -> None:
    env_key = os.getenv("GRAPHBUS_API_KEY", "").strip()
    file_key = _load_stored_key()
    active_key = env_key or file_key

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold dim")
    table.add_column("Value")

    if active_key:
        table.add_row("Status", "[green]Authenticated[/green]")
        table.add_row("Key", f"[cyan]{active_key[:8]}…[/cyan]")
    else:
        table.add_row("Status", "[yellow]No API key configured[/yellow]")
        table.add_row("Get yours", f"[cyan]{ONBOARDING_URL}[/cyan]")

    if env_key:
        table.add_row("Source", "environment variable (GRAPHBUS_API_KEY)")
    elif file_key:
        table.add_row("Source", f"credentials file ({CREDENTIALS_PATH})")

    console.print()
    console.print(table)
    console.print()


@auth.command("status")
def status() -> None:
    """Show the active GraphBus API key and its source."""
    _status()


@auth.command("whoami")
def whoami() -> None:
    """Alias for 'graphbus auth status'."""
    _status()
