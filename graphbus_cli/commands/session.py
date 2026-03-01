"""
Session command - Interactive terminal for guided agent negotiation.

Provides a Claude Code-like chat interface where users describe intent
and GraphBus orchestrates multi-agent negotiation in real-time.
"""

import click
import os
import sys
import json
import readline
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text

from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info, print_header
)
from graphbus_cli.utils.errors import BuildError

# Session history file
HISTORY_FILE = Path.home() / ".graphbus" / "session_history"


def _ensure_history():
    """Ensure readline history is loaded."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(HISTORY_FILE))
    except FileNotFoundError:
        pass
    readline.set_history_length(500)


def _save_history():
    """Save readline history."""
    try:
        readline.write_history_file(str(HISTORY_FILE))
    except Exception:
        pass


def _print_welcome(project_dir: Path, artifacts_dir: Path, model: str):
    """Print session welcome banner."""
    console.print()
    console.print(Panel(
        "[bold cyan]GraphBus Interactive Session[/bold cyan]\n\n"
        f"  [dim]Project:[/dim]   {project_dir}\n"
        f"  [dim]Artifacts:[/dim] {artifacts_dir}\n"
        f"  [dim]Model:[/dim]    {model}\n\n"
        "[dim]Describe what you want to improve. GraphBus agents will negotiate\n"
        "and implement changes collaboratively.[/dim]\n\n"
        "[dim]Commands:[/dim]\n"
        "  [cyan]/status[/cyan]    — Show project & agent status\n"
        "  [cyan]/agents[/cyan]    — List available agents\n"
        "  [cyan]/history[/cyan]   — Show negotiation history\n"
        "  [cyan]/diff[/cyan]      — Show uncommitted changes\n"
        "  [cyan]/undo[/cyan]      — Revert last negotiation\n"
        "  [cyan]/model[/cyan]     — Change LLM model\n"
        "  [cyan]/help[/cyan]      — Show commands\n"
        "  [cyan]/quit[/cyan]      — Exit session",
        border_style="cyan",
        padding=(1, 2)
    ))
    console.print()


def _load_agents(artifacts_dir: Path) -> list:
    """Load agent definitions from artifacts."""
    agents_json = artifacts_dir / "agents.json"
    if not agents_json.exists():
        return []
    try:
        with open(agents_json) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("agents", [])
    except Exception:
        return []


def _show_status(project_dir: Path, artifacts_dir: Path, agents: list, model: str):
    """Show project status."""
    console.print()
    print_header("Session Status")
    console.print(f"  [cyan]Project:[/cyan]    {project_dir}")
    console.print(f"  [cyan]Artifacts:[/cyan]  {artifacts_dir}")
    console.print(f"  [cyan]Model:[/cyan]      {model}")
    console.print(f"  [cyan]Agents:[/cyan]     {len(agents)}")

    # Check git status
    import subprocess
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=str(project_dir)
        )
        changes = result.stdout.strip()
        if changes:
            console.print(f"  [yellow]Git:[/yellow]       {len(changes.splitlines())} changed files")
        else:
            console.print(f"  [green]Git:[/green]       clean")
    except Exception:
        console.print(f"  [dim]Git:[/dim]       not available")
    console.print()


def _show_agents(agents: list):
    """Show available agents."""
    console.print()
    print_header("Available Agents")
    if not agents:
        console.print("  [dim]No agents found. Run 'graphbus build agents/' first.[/dim]")
    else:
        for a in agents:
            name = a.get("name", a.get("class_name", "Unknown"))
            scope = a.get("scope", a.get("description", ""))
            console.print(f"  [cyan]•[/cyan] [bold]{name}[/bold]")
            if scope:
                console.print(f"    [dim]{scope}[/dim]")
    console.print()


def _show_diff(project_dir: Path):
    """Show git diff."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, cwd=str(project_dir)
        )
        if result.stdout.strip():
            console.print()
            console.print(result.stdout)
        else:
            console.print("\n  [dim]No uncommitted changes.[/dim]\n")
    except Exception:
        console.print("\n  [dim]Git not available.[/dim]\n")


def _show_history(artifacts_dir: Path):
    """Show negotiation history."""
    negotiations_file = artifacts_dir / "negotiations.json"
    if not negotiations_file.exists():
        console.print("\n  [dim]No negotiation history yet.[/dim]\n")
        return

    try:
        with open(negotiations_file) as f:
            sessions = json.load(f)

        console.print()
        print_header("Negotiation History")
        if isinstance(sessions, list):
            for s in sessions[-10:]:  # Last 10
                sid = s.get("session_id", "?")[:8]
                intent = s.get("intent", "no intent")
                status = s.get("status", "unknown")
                console.print(f"  [cyan]{sid}[/cyan]  {intent[:60]}  [{status}]")
        console.print()
    except Exception:
        console.print("\n  [dim]Could not read negotiation history.[/dim]\n")


def _run_negotiation(intent: str, artifacts_dir: Path, project_dir: Path, model: str,
                     rounds: int, api_key: str, verbose: bool):
    """Run a negotiation with the given intent."""
    from graphbus_core.config import LLMConfig, SafetyConfig
    from graphbus_core.build.orchestrator import run_negotiation, collect_agent_questions

    llm_config = LLMConfig(model=model)
    safety_config = SafetyConfig(
        max_negotiation_rounds=rounds,
        max_proposals_per_agent=5,
        convergence_threshold=2,
    )

    # Collect clarifying questions
    try:
        questions = collect_agent_questions(
            artifacts_dir=str(artifacts_dir),
            llm_config=llm_config,
            user_intent=intent,
            project_root=str(project_dir)
        )

        enhanced_intent = intent
        if questions:
            console.print()
            console.print(f"[yellow]✨ Agents have {len(questions)} clarifying question(s):[/yellow]")
            console.print()

            answers = []
            for i, q in enumerate(questions, 1):
                agent = q.get("agent", "Agent")
                question = q.get("question", "")
                options = q.get("options", [])

                console.print(f"  [cyan][{agent}][/cyan] {question}")
                if options:
                    for j, opt in enumerate(options, 1):
                        console.print(f"    [dim]{j}.[/dim] {opt}")

                try:
                    answer = Prompt.ask("  [bold]→[/bold]", default="skip")
                    if answer.lower() != "skip":
                        answers.append({
                            "question": question,
                            "answer": answer,
                            "agent": agent
                        })
                except (EOFError, KeyboardInterrupt):
                    break

            if answers:
                enhanced_intent = f"{intent}\n\nUser Clarifications:\n"
                for a in answers:
                    enhanced_intent += f"- [{a['agent']}] {a['question']}\n  → {a['answer']}\n"

            console.print()

    except Exception as e:
        if verbose:
            print_info(f"Could not collect questions: {e}")
        enhanced_intent = intent

    # Run negotiation
    console.print("[cyan]⚡ Starting negotiation...[/cyan]")
    console.print()

    try:
        results = run_negotiation(
            artifacts_dir=str(artifacts_dir),
            llm_config=llm_config,
            safety_config=safety_config,
            user_intent=enhanced_intent,
            verbose=verbose,
            project_root=str(project_dir),
            enable_git_workflow=True
        )

        # Display results
        num_accepted = results.get("accepted_proposals", 0)
        num_files = results.get("files_changed", 0)
        session = results.get("session", {})

        console.print()
        if num_accepted > 0:
            print_success(f"✓ {num_accepted} improvements applied across {num_files} files")
            if session.get("pr_url"):
                console.print(f"  [cyan]PR:[/cyan] {session['pr_url']}")
            if session.get("branch_name"):
                console.print(f"  [cyan]Branch:[/cyan] {session['branch_name']}")
        else:
            print_info("Negotiation completed — no changes proposed.")
        console.print()

    except Exception as e:
        print_error(f"Negotiation failed: {e}")
        console.print()


@click.command()
@click.option(
    '--project-root', '-p',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default='.',
    help='Project root directory (default: current directory)'
)
@click.option(
    '--artifacts-dir', '-a',
    type=click.Path(file_okay=False, dir_okay=True),
    default='.graphbus',
    help='Artifacts directory (default: .graphbus)'
)
@click.option(
    '--llm-model', '-m',
    type=str,
    default=None,
    help='LLM model (default: from config or deepseek/deepseek-reasoner)'
)
@click.option(
    '--rounds', '-r',
    type=int,
    default=5,
    help='Max negotiation rounds per intent (default: 5)'
)
@click.option(
    '--api-key',
    type=str,
    envvar='GRAPHBUS_API_KEY',
    help='GraphBus API key (or set GRAPHBUS_API_KEY)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--namespace', '-n',
    type=str,
    default='default',
    help='Namespace for agent isolation (default: "default")'
)
def session(project_root, artifacts_dir, llm_model, rounds, api_key, verbose, namespace):
    """
    Launch an interactive session for guided agent negotiation.

    \b
    Start a conversational interface where you describe what you want
    to improve, and GraphBus agents negotiate and implement changes.

    \b
    Examples:
      graphbus session
      graphbus session --project-root ./my-project
      graphbus session --llm-model claude-sonnet-4-6
      graphbus session -m gpt-4o -r 3

    \b
    In the session, just type what you want:
      > optimize the database queries for better performance
      > add input validation to all API endpoints
      > refactor the auth module to use JWT tokens
    """
    from graphbus_core.constants import DEFAULT_LLM_MODEL

    project_dir = Path(project_root).resolve()
    art_dir = (project_dir / artifacts_dir).resolve()
    model = llm_model or os.environ.get("GRAPHBUS_LLM_MODEL", DEFAULT_LLM_MODEL)

    # Validate
    if not art_dir.exists():
        console.print(Panel(
            f"[yellow]No artifacts found at {art_dir}[/yellow]\n\n"
            "Build your project first:\n\n"
            "  [cyan]graphbus build agents/[/cyan]\n"
            "  [cyan]graphbus session[/cyan]",
            border_style="yellow",
            padding=(1, 2)
        ))
        return

    if not api_key:
        console.print(Panel(
            "[yellow]GraphBus API key required[/yellow]\n\n"
            "Get your key at [cyan]https://graphbus.com/onboarding[/cyan]\n\n"
            "Then:\n"
            "  [cyan]export GRAPHBUS_API_KEY=gb_...[/cyan]\n"
            "  [cyan]graphbus session[/cyan]",
            border_style="yellow",
            padding=(1, 2)
        ))
        return

    os.environ.setdefault("GRAPHBUS_API_KEY", api_key)

    # Load agents
    agents = _load_agents(art_dir)

    # Welcome
    _print_welcome(project_dir, art_dir, model)
    _ensure_history()

    # REPL
    while True:
        try:
            user_input = input("\033[1;36m❯\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye![/dim]")
                break
            elif cmd == "/status":
                _show_status(project_dir, art_dir, agents, model)
            elif cmd == "/agents":
                _show_agents(agents)
            elif cmd == "/history":
                _show_history(art_dir)
            elif cmd == "/diff":
                _show_diff(project_dir)
            elif cmd == "/undo":
                import subprocess
                try:
                    result = subprocess.run(
                        ["git", "log", "--oneline", "-5"],
                        capture_output=True, text=True, cwd=str(project_dir)
                    )
                    console.print(f"\n{result.stdout}")
                    if Prompt.ask("  Revert last commit?", choices=["y", "n"], default="n") == "y":
                        subprocess.run(["git", "revert", "--no-commit", "HEAD"], cwd=str(project_dir))
                        print_success("Reverted last commit (not yet committed)")
                except Exception as e:
                    print_error(f"Undo failed: {e}")
                console.print()
            elif cmd == "/model":
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    model = parts[1]
                    print_info(f"Model set to: {model}")
                else:
                    console.print(f"  [dim]Current model:[/dim] {model}")
                    new_model = Prompt.ask("  New model", default=model)
                    if new_model != model:
                        model = new_model
                        print_info(f"Model set to: {model}")
                console.print()
            elif cmd == "/help":
                _print_welcome(project_dir, art_dir, model)
            else:
                console.print(f"  [dim]Unknown command: {cmd}. Type /help for commands.[/dim]")
            continue

        # Intent — run negotiation
        _save_history()
        _run_negotiation(
            intent=user_input,
            artifacts_dir=art_dir,
            project_dir=project_dir,
            model=model,
            rounds=rounds,
            api_key=api_key,
            verbose=verbose
        )
