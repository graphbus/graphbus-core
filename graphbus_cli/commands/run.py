"""
Run command - Run agent graphs in runtime mode
"""

import click
import signal
import sys
from pathlib import Path
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

from graphbus_core.runtime.executor import run_runtime, RuntimeExecutor
from graphbus_core.config import RuntimeConfig
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, print_separator
)
from graphbus_cli.utils.errors import RuntimeError as CLIRuntimeError


@click.command()
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--no-message-bus',
    is_flag=True,
    help='Disable message bus (nodes only)'
)
@click.option(
    '--interactive', '-i',
    is_flag=True,
    help='Start interactive REPL'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose runtime logging'
)
@click.option(
    '--stats-interval',
    type=int,
    help='Show stats every N seconds'
)
def run(artifacts_dir: str, no_message_bus: bool, interactive: bool, verbose: bool, stats_interval: int):
    """
    Run agent graph from build artifacts.

    \b
    Loads artifacts and starts the GraphBus runtime with message bus
    coordination. Agents can be invoked via methods or events.

    \b
    Examples:
      graphbus run .graphbus                 # Run from default artifacts
      graphbus run .graphbus --interactive   # Start interactive REPL
      graphbus run build/ -v                 # Verbose runtime logging
      graphbus run .graphbus --no-message-bus # Disable event routing

    \b
    Interactive Mode:
      Use --interactive to start a REPL where you can:
        - Call agent methods
        - Publish events
        - View statistics
        - Inspect message history

    \b
    Shutdown:
      Press Ctrl+C to gracefully stop the runtime.
    """
    artifacts_path = Path(artifacts_dir).resolve()
    executor = None

    try:
        # Add parent directory to Python path so modules can be imported
        # Artifacts are typically in .graphbus/ directory, so parent is the project root
        parent_dir = artifacts_path.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        # Display startup info
        print_header("GraphBus Runtime")
        print_info(f"Loading artifacts from: {artifacts_path}")
        console.print()

        # Create runtime config
        config = RuntimeConfig(
            artifacts_dir=str(artifacts_path),
            enable_message_bus=not no_message_bus
        )

        # Start runtime
        with console.status("[cyan]Starting runtime...[/cyan]", spinner="dots"):
            executor = RuntimeExecutor(config)
            executor.start()

        console.print()
        print_success("Runtime started successfully")
        console.print()

        # Display runtime status
        _display_runtime_status(executor, verbose)

        # Interactive mode
        if interactive:
            console.print()
            print_info("Starting interactive REPL...")
            print_info("Type 'help' for available commands, 'exit' to quit")
            console.print()
            from graphbus_cli.repl.runtime_repl import start_repl
            start_repl(executor)
        else:
            # Standard mode - wait for Ctrl+C
            console.print()
            print_info("Runtime is running. Press Ctrl+C to stop...")
            console.print()

            # Set up signal handler for graceful shutdown
            def signal_handler(sig, frame):
                console.print()
                print_info("Shutting down runtime...")
                if executor:
                    executor.stop()
                print_success("Runtime stopped")
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            # Keep running
            signal.pause()

    except KeyboardInterrupt:
        console.print()
        print_info("Shutting down runtime...")
        if executor:
            executor.stop()
        print_success("Runtime stopped")
    except Exception as e:
        console.print()
        if executor:
            executor.stop()
        raise CLIRuntimeError(f"Runtime error: {str(e)}")


def _display_runtime_status(executor: RuntimeExecutor, verbose: bool):
    """Display current runtime status"""
    print_header("Runtime Status")

    # Get stats
    stats = executor.get_stats()

    # Display basic info
    console.print(f"[cyan]Status:[/cyan] {'RUNNING' if stats['is_running'] else 'STOPPED'}")
    console.print(f"[cyan]Nodes:[/cyan] {stats['nodes_count']}")

    # List agents
    console.print("\n[cyan]Agents:[/cyan]")
    nodes = executor.get_all_nodes()
    for name, node in nodes.items():
        # Show agent with type indicator
        console.print(f"  • {name}")

    # Show message bus info if enabled
    if executor.bus:
        console.print("\n[cyan]Message Bus:[/cyan] Enabled")

        # Show subscriptions
        all_topics = executor.bus.get_all_topics()
        if all_topics:
            console.print(f"\n[cyan]Topics:[/cyan] ({len(all_topics)} total)")
            for topic in sorted(all_topics)[:5]:  # Show first 5
                subscribers = executor.bus.get_subscribers(topic)
                subscriber_names = ", ".join(subscribers)
                console.print(f"  • {topic} → {subscriber_names}")

            if len(all_topics) > 5:
                console.print(f"  ... and {len(all_topics) - 5} more")
    else:
        console.print("\n[cyan]Message Bus:[/cyan] Disabled")

    # Verbose stats
    if verbose and executor.bus:
        bus_stats = stats.get("message_bus", {})
        console.print("\n[cyan]Statistics:[/cyan]")
        console.print(f"  Messages Published: {bus_stats.get('messages_published', 0)}")
        console.print(f"  Messages Delivered: {bus_stats.get('messages_delivered', 0)}")


def _display_stats_table(executor: RuntimeExecutor):
    """Display statistics in table format"""
    stats = executor.get_stats()

    table = Table(title="Runtime Statistics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Status", "RUNNING" if stats['is_running'] else "STOPPED")
    table.add_row("Active Nodes", str(stats['nodes_count']))

    if stats.get("message_bus"):
        bus_stats = stats["message_bus"]
        table.add_row("Messages Published", str(bus_stats.get('messages_published', 0)))
        table.add_row("Messages Delivered", str(bus_stats.get('messages_delivered', 0)))

    console.print(table)
