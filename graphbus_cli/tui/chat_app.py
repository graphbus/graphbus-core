"""Chat-based TUI for GraphBus — natural language interface to CLI commands."""

import re
import subprocess
import shlex
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Header, Footer, Input, Static, RichLog
from textual.binding import Binding


# Maps natural-language intents to graphbus CLI commands.
COMMAND_PATTERNS = [
    # Project init
    (r"(?:create|init|start|new)\s+(?:a\s+)?(?:new\s+)?(?:(\w+)\s+)?project\s+(?:called|named)\s+(\S+)",
     lambda m: _init_cmd(m.group(2), m.group(1))),
    (r"(?:create|init|start|new)\s+(?:a\s+)?(?:new\s+)?project\s+(\S+)",
     lambda m: f"graphbus init {m.group(1)}"),
    # Build
    (r"(?:build|compile)\s+(?:agents?\s+)?(?:from\s+|in\s+)?(\S+)(?:\s+with\s+validation|\s+--validate)?",
     lambda m: f"graphbus build {m.group(1)}" + (" --validate" if "valid" in m.group(0).lower() else "")),
    (r"(?:build|compile)\b",
     lambda m: "graphbus build ."),
    # Run
    (r"(?:run|start|execute)\s+(?:the\s+)?(?:runtime|agents?)?(?:\s+.*)?",
     lambda m: _run_cmd(m.group(0))),
    # Inspect
    (r"(?:show|list|display|view)\s+(?:me\s+)?(?:the\s+)?(?:agent\s+)?graph",
     lambda m: "graphbus inspect .graphbus --format graph"),
    (r"(?:show|list|display|view)\s+(?:me\s+)?(?:all\s+)?agents?",
     lambda m: "graphbus inspect .graphbus --format agents"),
    (r"(?:show|list|display|view)\s+(?:me\s+)?(?:all\s+)?topics?",
     lambda m: "graphbus inspect .graphbus --format topics"),
    (r"inspect\s+(?:the\s+)?artifacts?",
     lambda m: "graphbus inspect .graphbus"),
    # Generate
    (r"(?:generate|gen|create)\s+agent\s+(\w+)(?:\s+with\s+tests)?",
     lambda m: f"graphbus generate agent {m.group(1)}" + (" --with-tests" if "test" in m.group(0).lower() else "")),
    # Validate
    (r"validate\s+(?:agents?\s+)?(?:in\s+)?(?:strict\s+mode|--strict)?",
     lambda m: "graphbus validate ." + (" --strict" if "strict" in m.group(0).lower() else "")),
    # Profile
    (r"profile\s+(?:performance)?",
     lambda m: "graphbus profile .graphbus"),
    # Dashboard
    (r"(?:launch|open|start)\s+dashboard",
     lambda m: "graphbus dashboard .graphbus"),
    # Docker
    (r"(?:deploy|generate)\s+(?:to\s+)?docker(?:\s+files)?",
     lambda m: "graphbus docker generate"),
    # Kubernetes
    (r"(?:deploy|generate)\s+(?:to\s+)?(?:kubernetes|k8s)(?:\s+manifests)?",
     lambda m: "graphbus k8s generate"),
    # Negotiate
    (r"negotiate\s+(.+)",
     lambda m: f'graphbus negotiate .graphbus --intent "{m.group(1)}"'),
    # Ingest
    (r"ingest\s+(\S+)",
     lambda m: f"graphbus ingest {m.group(1)}"),
]


def _init_cmd(name, template=None):
    """Build an init command with optional template."""
    cmd = f"graphbus init {name}"
    if template:
        tpl = template.lower()
        known = {"microservices", "etl", "chatbot", "workflow", "basic"}
        if tpl in known:
            cmd += f" --template {tpl}"
    return cmd


def _run_cmd(text):
    """Build a run command from natural language."""
    cmd = "graphbus run .graphbus"
    lower = text.lower()
    if "state" in lower or "persist" in lower:
        cmd += " --enable-state-persistence"
    if "hot" in lower or "reload" in lower:
        cmd += " --enable-hot-reload"
    if "health" in lower or "monitor" in lower:
        cmd += " --health-check"
    if "debug" in lower:
        cmd += " --debug"
    if "repl" in lower or "interactive" in lower:
        cmd += " --repl"
    return cmd


def parse_intent(text):
    """Match user text against known command patterns."""
    text = text.strip()
    for pattern, builder in COMMAND_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return builder(m)
    return None


HELP_TEXT = """\
[bold]GraphBus Chat TUI[/bold]

Just type what you want to do in plain English. Examples:

  [cyan]create a new microservices project called my-api[/cyan]
  [cyan]build agents from ./agents[/cyan]
  [cyan]run the runtime with hot reload[/cyan]
  [cyan]show me the agent graph[/cyan]
  [cyan]generate agent PaymentService with tests[/cyan]
  [cyan]deploy to docker[/cyan]
  [cyan]validate agents in strict mode[/cyan]

Special commands:
  [yellow]help[/yellow]      — show this help
  [yellow]examples[/yellow]  — show more examples
  [yellow]clear[/yellow]     — clear the chat
  [yellow]quit[/yellow]      — exit
"""

EXAMPLES_TEXT = """\
[bold]More Examples[/bold]

[underline]Projects[/underline]
  create a new chatbot project called support-bot
  init my-project

[underline]Build & Validate[/underline]
  build agents from src/agents with validation
  validate agents in strict mode

[underline]Runtime[/underline]
  run with state persistence and hot reload
  start interactive REPL

[underline]Inspection[/underline]
  show all agents
  show all topics
  inspect the artifacts

[underline]Development[/underline]
  generate agent OrderProcessor with tests
  profile performance
  launch dashboard

[underline]Deployment[/underline]
  deploy to docker
  deploy to kubernetes

[underline]Advanced[/underline]
  negotiate add retry logic to all agents
  ingest ./existing-code
"""


class ChatTUI(App):
    """GraphBus chat-based TUI application."""

    TITLE = "GraphBus"
    SUB_TITLE = "Chat Interface"

    CSS = """
    #chat-log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    #input-box {
        dock: bottom;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            RichLog(id="chat-log", highlight=True, markup=True, wrap=True),
        )
        yield Input(placeholder="Tell GraphBus what you want to do...", id="input-box")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold green]Welcome to GraphBus![/bold green]")
        log.write("Type what you want to do, or [yellow]help[/yellow] for options.\n")
        self.query_one("#input-box", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        inp = self.query_one("#input-box", Input)
        inp.value = ""

        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold cyan]You:[/bold cyan] {text}")

        lower = text.lower()

        if lower in ("quit", "exit", "q"):
            self.exit()
            return

        if lower == "help":
            log.write(HELP_TEXT)
            return

        if lower in ("examples", "example"):
            log.write(EXAMPLES_TEXT)
            return

        if lower == "clear":
            log.clear()
            log.write("[dim]Chat cleared.[/dim]\n")
            return

        cmd = parse_intent(text)
        if cmd is None:
            log.write(
                f"[yellow]I'm not sure what you mean.[/yellow] "
                f"Type [bold]help[/bold] to see what I can do."
            )
            return

        log.write(f"[dim]$ {cmd}[/dim]")
        self._run_command(cmd)

    def _run_command(self, cmd: str) -> None:
        """Execute a graphbus command and display the output."""
        log = self.query_one("#chat-log", RichLog)
        try:
            result = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                log.write(result.stdout.rstrip())
            if result.stderr:
                log.write(f"[red]{result.stderr.rstrip()}[/red]")
            if result.returncode == 0:
                log.write("[green]Done.[/green]\n")
            else:
                log.write(f"[red]Command exited with code {result.returncode}[/red]\n")
        except subprocess.TimeoutExpired:
            log.write("[red]Command timed out after 60 seconds.[/red]\n")
        except FileNotFoundError:
            log.write("[red]graphbus command not found. Is it installed?[/red]\n")
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]\n")

    def action_clear_chat(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        log.write("[dim]Chat cleared.[/dim]\n")
