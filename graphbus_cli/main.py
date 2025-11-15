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
    Common Commands:
      build     - Build agent graphs from source
      run       - Run an agent graph runtime
      inspect   - Inspect build artifacts
      validate  - Validate agent definitions

    \b
    Examples:
      graphbus build agents/           # Build agents from directory
      graphbus run .graphbus           # Run built artifacts
      graphbus inspect .graphbus       # Inspect artifacts
      graphbus validate agents/        # Validate agent definitions

    For more help on a specific command, use:
      graphbus COMMAND --help
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = False


# Import and register commands
from graphbus_cli.commands.build import build
from graphbus_cli.commands.run import run
from graphbus_cli.commands.inspect import inspect
from graphbus_cli.commands.validate import validate

cli.add_command(build)
cli.add_command(run)
cli.add_command(inspect)
cli.add_command(validate)


def main():
    """Main entry point with error handling"""
    try:
        # Run CLI
        cli(obj={})

    except Exception as exc:
        handle_cli_error(exc, verbose=False)


if __name__ == "__main__":
    main()
