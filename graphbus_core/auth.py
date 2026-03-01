"""
graphbus_core.auth — API key management and interactive onboarding.

Onboarding flow (runs once, on first command):
  1. Show welcome banner
  2. Prompt for GRAPHBUS_API_KEY — fully blocking, no skip
  3. Prompt for preferred LLM model (model choice saved; key NOT stored)
  4. Save both to ~/.graphbus/credentials.json (mode 600)

Subsequent runs:
  - Key and model preference loaded silently from credentials file or env
  - LLM provider key checked at runtime via check_llm_key()

LLM API keys (Anthropic, DeepSeek, OpenAI, etc.) are NEVER stored here.
Set them in your shell environment or .env file.
"""

from __future__ import annotations

import json
import os
import sys
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CREDENTIALS_PATH: Path = Path.home() / ".graphbus" / "credentials.json"
ONBOARDING_URL: str = "https://graphbus.com/onboarding"
_KEY_PREFIX: str = "gb_"
_KEY_MIN_LEN: int = 16  # gb_ + 13 chars minimum

# Supported LLM models: display name → (env_var, model_string)
LLM_MODELS: dict[str, tuple[str, str]] = {
    "1": ("Claude Haiku  (recommended)", "ANTHROPIC_API_KEY", "anthropic/claude-haiku-4-5"),
    "2": ("Claude Sonnet",               "ANTHROPIC_API_KEY", "anthropic/claude-sonnet-4-5"),
    "3": ("GPT-4o",                      "OPENAI_API_KEY",    "gpt-4o"),
    "4": ("DeepSeek R1",                 "DEEPSEEK_API_KEY",  "deepseek/deepseek-reasoner"),
    "5": ("OpenRouter  (any model)",     "OPENROUTER_API_KEY","openrouter/auto"),
}
DEFAULT_MODEL_KEY = "anthropic/claude-haiku-4-5"
DEFAULT_MODEL_ENV = "ANTHROPIC_API_KEY"


# ---------------------------------------------------------------------------
# Credentials file helpers
# ---------------------------------------------------------------------------

def _load_credentials() -> dict:
    """Return the full credentials dict, or {} on any error."""
    try:
        if CREDENTIALS_PATH.exists():
            return json.loads(CREDENTIALS_PATH.read_text())
    except Exception:
        pass
    return {}


def _save_credentials(data: dict) -> None:
    """Write *data* to the credentials file (mode 600)."""
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(json.dumps(data, indent=2))
    CREDENTIALS_PATH.chmod(0o600)


def _load_stored_key() -> str:
    return _load_credentials().get("api_key", "").strip()


def _load_stored_model() -> tuple[str, str]:
    """Return (model_string, env_var) from credentials, or defaults."""
    creds = _load_credentials()
    return (
        creds.get("model", DEFAULT_MODEL_KEY),
        creds.get("model_env_var", DEFAULT_MODEL_ENV),
    )


def _validate_key_format(key: str) -> bool:
    return (
        isinstance(key, str)
        and key.startswith(_KEY_PREFIX)
        and len(key) >= _KEY_MIN_LEN
        and key[len(_KEY_PREFIX):].replace("-", "").replace("_", "").isalnum()
    )


# ---------------------------------------------------------------------------
# Rich helpers (graceful plain-text fallback)
# ---------------------------------------------------------------------------

def _con():
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        return None


def _print(console, msg: str, *, plain: str | None = None) -> None:
    if console:
        console.print(msg)
    else:
        print(plain or msg)


def _print_banner(console=None) -> None:
    c = console or _con()
    if c:
        from rich.panel import Panel
        from rich.text import Text
        body = Text.assemble(
            ("Multi-agent orchestration for your codebase.\n\n", ""),
            ("To continue you need a ", ""),
            ("GraphBus API key", "bold"),
            (".\n\n", ""),
            ("  Get yours free → ", "dim"),
            (ONBOARDING_URL, "bold cyan underline"),
        )
        c.print()
        c.print(Panel(body, title="[bold cyan]GraphBus[/bold cyan]",
                      border_style="cyan", padding=(1, 3)))
        c.print()
    else:
        line = "─" * 58
        print(f"\n\033[96m{line}\033[0m")
        print("  \033[1mGraphBus\033[0m  —  multi-agent orchestration")
        print(f"\033[96m{line}\033[0m")
        print("  To continue you need a \033[1mGraphBus API key\033[0m.")
        print(f"  Get yours free → \033[96m{ONBOARDING_URL}\033[0m\n")


def _prompt_for_graphbus_key(console=None) -> str:
    """
    Blocking prompt — loops until a valid key is entered.
    No skip option. Returns the validated key.
    """
    c = console or _con()

    def _ask(text: str) -> str:
        if c:
            from rich.prompt import Prompt
            return Prompt.ask(f"[bold]{text}[/bold]")
        return input(f"{text}: ").strip()

    def _confirm(text: str) -> bool:
        if c:
            from rich.prompt import Confirm
            return Confirm.ask(f"[bold]{text}[/bold]")
        return input(f"{text} [y/N]: ").strip().lower() in ("y", "yes")

    if _confirm("Open graphbus.com/onboarding in your browser?"):
        webbrowser.open(ONBOARDING_URL)
        _print(c, "\n[dim]Sign up, copy your key, then come back here.[/dim]\n",
               plain="\nSign up, copy your key, then come back here.\n")

    while True:
        raw = _ask("Paste your GraphBus API key").strip()
        if _validate_key_format(raw):
            return raw
        _print(
            c,
            f"[yellow]⚠  Invalid key format (expected [bold]{_KEY_PREFIX}…[/bold]).[/yellow]\n"
            "   Double-check at graphbus.com/onboarding and try again.",
            plain=f"⚠  Invalid key format (expected {_KEY_PREFIX}...). Try again.",
        )


def _prompt_for_model(console=None) -> tuple[str, str]:
    """
    Let the user pick their preferred LLM model for Build Mode.
    Returns (model_string, env_var_name).
    LLM API keys are NOT requested or stored here.
    """
    c = console or _con()

    if c:
        from rich.table import Table
        c.print("\n[bold]Choose your preferred LLM model for Build Mode:[/bold]\n")
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("Num", style="bold cyan")
        t.add_column("Model")
        t.add_column("Env var needed", style="dim")
        for num, (label, env_var, _) in LLM_MODELS.items():
            t.add_row(num, label, env_var)
        c.print(t)
        c.print()
        from rich.prompt import Prompt
        choice = Prompt.ask(
            "[bold]Enter number[/bold]",
            choices=list(LLM_MODELS.keys()),
            default="1",
        )
    else:
        print("\nChoose your preferred LLM model for Build Mode:\n")
        for num, (label, env_var, _) in LLM_MODELS.items():
            print(f"  {num}. {label}  ({env_var})")
        print()
        valid = list(LLM_MODELS.keys())
        while True:
            choice = input("Enter number [1]: ").strip() or "1"
            if choice in valid:
                break
            print(f"Invalid choice. Enter one of: {', '.join(valid)}.")

    label, env_var, model_str = LLM_MODELS[choice]

    # Check if the env var already exists — inform but don't block or store the key
    if os.getenv(env_var, "").strip():
        _print(c, f"\n[green]✓[/green]  {env_var} found in environment.",
               plain=f"\n✓  {env_var} found in environment.")
    else:
        _print(
            c,
            f"\n[yellow]ℹ[/yellow]  {env_var} not set yet.\n"
            f"   Add it to your shell or .env file before running Build Mode:\n"
            f"     [dim]export {env_var}=your_key_here[/dim]",
            plain=f"\nℹ  {env_var} not set yet.\n"
                  f"   export {env_var}=your_key_here",
        )

    return model_str, env_var


def _print_success(key: str, console=None) -> None:
    c = console or _con()
    masked = key[:8] + "…"
    _print(
        c,
        f"\n[bold green]✓[/bold green]  Authenticated "
        f"([dim]{masked}[/dim])  ·  credentials saved to [dim]{CREDENTIALS_PATH}[/dim]\n",
        plain=f"\n✓  Authenticated ({masked})  ·  credentials saved to {CREDENTIALS_PATH}\n",
    )


# ---------------------------------------------------------------------------
# Runtime LLM key check (called by build.py / negotiate commands)
# ---------------------------------------------------------------------------

def check_llm_key() -> tuple[bool, str, str]:
    """
    Check whether the env var for the user's configured LLM model is set.

    Returns
    -------
    (found, env_var, model_string)
        found       — True if the key is present in the environment
        env_var     — name of the expected env var (e.g. "DEEPSEEK_API_KEY")
        model_string — litellm model string (e.g. "deepseek/deepseek-reasoner")

    LLM keys are NEVER read from credentials — only from the environment.
    """
    model_str, env_var = _load_stored_model()
    found = bool(os.getenv(env_var, "").strip())
    return found, env_var, model_str


def get_configured_model() -> str:
    """Return the litellm model string saved in credentials, or the default."""
    return _load_stored_model()[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_api_key() -> str:
    """
    Return a valid GRAPHBUS_API_KEY, running interactive onboarding if needed.

    Resolution order
    ----------------
    1. ``GRAPHBUS_API_KEY`` environment variable
    2. ``~/.graphbus/credentials.json``
    3. Interactive first-run onboarding (fully blocking — no skip option)
       a. Prompt for API key
       b. Prompt for preferred LLM model (model name saved; key NOT stored)
       c. Save to credentials file; set env var for this process

    Always returns a non-empty key string. Exits with code 1 only if stdin
    is not a TTY (non-interactive environment without a configured key).
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

    # 3. Interactive onboarding — no TTY means we can't prompt
    if not sys.stdin.isatty():
        c = _con()
        _print(
            c,
            "\n[red]✗[/red]  [bold]GRAPHBUS_API_KEY[/bold] is required.\n"
            f"   Get yours at [cyan]{ONBOARDING_URL}[/cyan]\n"
            "   Then set it:  export GRAPHBUS_API_KEY=gb_...\n",
            plain=f"\n✗  GRAPHBUS_API_KEY is required.\n"
                  f"   Get yours at {ONBOARDING_URL}\n"
                  "   Then set it:  export GRAPHBUS_API_KEY=gb_...\n",
        )
        sys.exit(1)

    c = _con()
    _print_banner(c)

    # a. API key — blocking, no skip
    key = _prompt_for_graphbus_key(c)

    # b. LLM model preference (key NOT stored — only model name + env var name)
    model_str, model_env = _prompt_for_model(c)

    # c. Persist
    creds = _load_credentials()
    creds["api_key"] = key
    creds["model"] = model_str
    creds["model_env_var"] = model_env
    _save_credentials(creds)

    os.environ["GRAPHBUS_API_KEY"] = key
    _print_success(key, c)
    return key


def get_api_key() -> str:
    """
    Return the current API key without triggering onboarding.
    Returns ``""`` if no key is configured.
    """
    return (
        os.getenv("GRAPHBUS_API_KEY", "").strip()
        or _load_stored_key()
    )
