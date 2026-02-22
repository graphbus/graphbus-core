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
    LLM_MODELS,
    _load_stored_key,
    _load_stored_model,
    _load_credentials,
    _save_credentials,
    _print_banner,
    _prompt_for_graphbus_key,
    _prompt_for_model,
    _print_success,
    check_llm_key,
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
    """Set or update your GraphBus API key and model preference."""
    _print_banner(console)
    key = _prompt_for_graphbus_key(console)
    model_str, model_env = _prompt_for_model(console)

    creds = _load_credentials()
    creds["api_key"] = key
    creds["model"] = model_str
    creds["model_env_var"] = model_env
    _save_credentials(creds)

    os.environ["GRAPHBUS_API_KEY"] = key
    _print_success(key, console)


# ---------------------------------------------------------------------------
# graphbus auth logout
# ---------------------------------------------------------------------------

@auth.command("logout")
def logout() -> None:
    """Remove the stored GraphBus API key (model preference is kept)."""
    creds = _load_credentials()
    if "api_key" not in creds:
        console.print("[dim]No stored key found — nothing to remove.[/dim]")
        return

    old_key = creds.pop("api_key", "")
    _save_credentials(creds)

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
    llm_found, llm_env, llm_model = check_llm_key()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold dim")
    table.add_column("Value")

    if active_key:
        table.add_row("GraphBus", "[green]Authenticated[/green]")
        table.add_row("API key", f"[cyan]{active_key[:8]}…[/cyan]")
        src = "env var (GRAPHBUS_API_KEY)" if env_key else f"credentials file ({CREDENTIALS_PATH})"
        table.add_row("Key source", src)
    else:
        table.add_row("GraphBus", "[yellow]Not authenticated[/yellow]")
        table.add_row("Get yours", f"[cyan]{ONBOARDING_URL}[/cyan]")
        table.add_row("Setup", "run:  graphbus auth login")

    table.add_row("", "")
    table.add_row("LLM model", f"[cyan]{llm_model}[/cyan]")
    if llm_found:
        table.add_row(llm_env, "[green]✓ set[/green]")
    else:
        table.add_row(llm_env, f"[yellow]not set[/yellow]  (export {llm_env}=...)")

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
