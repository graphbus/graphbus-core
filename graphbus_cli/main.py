"""
GraphBus CLI - Main entry point
"""

import click
from rich.console import Console

from graphbus_cli import __version__
from graphbus_cli.utils.errors import handle_cli_error

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="graphbus")
@click.pass_context
def cli(ctx):
    """
    GraphBus - Multi-Agent Orchestration Framework

    Build, run, and manage agent graphs with event-driven communication.

    \b
    Interactive UI:
      tui       - Launch interactive text-based UI (NEW!)

    \b
    Core Commands:
      build     - Build agent graphs from source
      run       - Run an agent graph runtime
      inspect   - Inspect build artifacts
      validate  - Validate agent definitions

    \b
    Development Tools:
      init      - Initialize new project from template
      generate  - Generate agent boilerplate code
      profile   - Profile runtime performance
      dashboard - Launch web-based visualization dashboard

    \b
    Deployment Tools:
      docker    - Docker containerization tools
      k8s       - Kubernetes deployment tools
      ci        - CI/CD pipeline generators

    \b
    Namespaces:
      ns create   - Create a namespace (logical isolation boundary)
      ns use      - Switch the active namespace context
      ns current  - Show the active namespace
      ns list     - List all namespaces
      ns show     - Detailed view + agent topology

    \b
    Advanced Features:
      state                - Manage agent state persistence
      negotiate            - Run LLM agent negotiation (EXPERIMENTAL)
      inspect-negotiation  - View negotiation history (EXPERIMENTAL)
      --debug              - Enable interactive debugger (use with run)
      --watch              - Enable hot reload (use with run)

    \b
    Examples:
      graphbus tui                                     # Launch interactive UI
      graphbus init my-project                         # Create new project
      graphbus generate agent OrderProcessor           # Generate agent code
      graphbus build agents/                           # Build agents
      graphbus build agents/ --enable-agents           # Build with LLM orchestration
      graphbus ns create backend-api                   # Create a namespace
      graphbus ns use backend-api                      # Switch active namespace
      graphbus ns current                              # Show active namespace
      graphbus negotiate .graphbus --intent "add retry logic"
      graphbus negotiate .graphbus -n backend-api --intent "reduce latency"
      graphbus inspect-negotiation .graphbus           # View negotiation history
      graphbus run .graphbus --debug                   # Run with debugger
      graphbus profile .graphbus                       # Profile performance
      graphbus dashboard .graphbus                     # Launch dashboard

    For more help on a specific command, use:
      graphbus COMMAND --help
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = False


# Import and register commands
from graphbus_cli.commands.build import build
from graphbus_cli.commands.run import run
from graphbus_cli.commands.inspect import inspect
from graphbus_cli.commands.inspect_negotiation import inspect_negotiation
from graphbus_cli.commands.validate import validate
from graphbus_cli.commands.state import state
from graphbus_cli.commands.negotiate import negotiate
from graphbus_cli.commands.init import init, list_templates_cmd
from graphbus_cli.commands.generate import generate
from graphbus_cli.commands.profile import profile
from graphbus_cli.commands.dashboard import dashboard
from graphbus_cli.commands.docker import docker
from graphbus_cli.commands.k8s import k8s
from graphbus_cli.commands.ci import ci
from graphbus_cli.commands.contract import contract
from graphbus_cli.commands.migrate import migrate
from graphbus_cli.commands.coherence import coherence
from graphbus_cli.commands.tui import tui
from graphbus_cli.commands.session import session
from graphbus_cli.commands.ns import ns
from graphbus_cli.commands.auth import auth
from graphbus_cli.commands.ui import ui

cli.add_command(build)
cli.add_command(run)
cli.add_command(inspect)
cli.add_command(inspect_negotiation)
cli.add_command(validate)
cli.add_command(state)
cli.add_command(negotiate)
cli.add_command(init)
cli.add_command(list_templates_cmd)
cli.add_command(generate)
cli.add_command(profile)
cli.add_command(dashboard)
cli.add_command(docker)
cli.add_command(k8s)
cli.add_command(ci)
cli.add_command(contract)
cli.add_command(migrate)
cli.add_command(coherence)
cli.add_command(tui)
cli.add_command(session)
cli.add_command(ns)
cli.add_command(auth)
cli.add_command(ui)


def main():
    """Main entry point with error handling"""
    import sys as _sys
    from graphbus_core.auth import ensure_api_key as _ensure_api_key

    # Gate: require a GraphBus API key for any real command.
    # Skip for: bare invocation, --help, --version, and `graphbus auth *`
    # (the auth subcommand IS the key-setup flow — can't gate it behind itself).
    _SKIP_FLAGS = {"--help", "-h", "--version"}
    _first_cmd = _sys.argv[1] if len(_sys.argv) > 1 else ""
    _needs_key = (
        bool(_first_cmd)
        and _first_cmd != "auth"
        and not any(f in _sys.argv for f in _SKIP_FLAGS)
    )
    if _needs_key:
        _ensure_api_key(required=True)

    try:
        # Run CLI
        cli(obj={})

    except Exception as exc:
        handle_cli_error(exc, verbose=False)


if __name__ == "__main__":
    main()
