"""
State command - Manage agent state
"""

import click
from pathlib import Path
from rich.table import Table

from graphbus_core.runtime.state import StateManager
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header
)


@click.group()
def state():
    """
    Manage agent state persistence.

    \b
    Commands for viewing and managing persisted agent state.
    State is stored in the .graphbus/state/ directory by default.

    \b
    Examples:
      graphbus state list              # List all saved states
      graphbus state show HelloService # Show state for specific agent
      graphbus state clear HelloService # Clear state for specific agent
      graphbus state clear-all         # Clear all saved states
    """
    pass


@state.command()
@click.option(
    '--state-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='.graphbus/state',
    help='State directory location'
)
def list(state_dir: str):
    """List all saved agent states."""
    state_path = Path(state_dir).resolve()

    if not state_path.exists():
        print_info(f"No state directory found at: {str(state_path)}")
        return

    print_header("Saved Agent States")

    # Find all state files
    state_files = list(state_path.glob("*.json"))

    if not state_files:
        print_info("No saved states found")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Size", justify="right")

    for state_file in sorted(state_files):
        agent_name = str(state_file.stem)
        file_name = str(state_file.name)
        file_size = state_file.stat().st_size
        size_str = f"{file_size:,} bytes"

        table.add_row(agent_name, file_name, size_str)

    console.print(table)
    console.print(f"\n[dim]Total: {len(state_files)} state file(s)[/dim]")


@state.command()
@click.argument('agent_name')
@click.option(
    '--state-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='.graphbus/state',
    help='State directory location'
)
def show(agent_name: str, state_dir: str):
    """Show saved state for a specific agent."""
    state_path = Path(state_dir).resolve()
    state_manager = StateManager()
    state_manager.state_dir = state_path

    print_header(f"State for {agent_name}")

    state = state_manager.load_state(agent_name)

    if not state:
        print_info(f"No saved state found for agent: {agent_name}")
        return

    # Display state as JSON
    import json
    console.print_json(json.dumps(state, indent=2))


@state.command()
@click.argument('agent_name')
@click.option(
    '--state-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='.graphbus/state',
    help='State directory location'
)
@click.confirmation_option(prompt='Are you sure you want to clear this agent state?')
def clear(agent_name: str, state_dir: str):
    """Clear saved state for a specific agent."""
    state_path = Path(state_dir).resolve()
    state_manager = StateManager()
    state_manager.state_dir = state_path

    try:
        state_manager.clear_state(agent_name)
        print_success(f"Cleared state for agent: {agent_name}")
    except Exception as e:
        print_error(f"Failed to clear state: {str(e)}")


@state.command('clear-all')
@click.option(
    '--state-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='.graphbus/state',
    help='State directory location'
)
@click.confirmation_option(prompt='Are you sure you want to clear ALL agent states?')
def clear_all(state_dir: str):
    """Clear all saved agent states."""
    state_path = Path(state_dir).resolve()

    if not state_path.exists():
        print_info(f"No state directory found at: {str(state_path)}")
        return

    # Find and delete all state files
    state_files = list(state_path.glob("*.json"))

    if not state_files:
        print_info("No saved states found")
        return

    for state_file in state_files:
        state_file.unlink()

    print_success(f"Cleared {len(state_files)} state file(s)")
