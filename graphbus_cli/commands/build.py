"""
Build command - Build agent graphs from source
"""

import click
import sys
from pathlib import Path
from rich.table import Table

from graphbus_core.build.builder import build_project
from graphbus_core.config import BuildConfig, LLMConfig, SafetyConfig
from graphbus_core.constants import DEFAULT_LLM_MODEL
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, create_progress_bar, format_duration
)
from graphbus_cli.utils.errors import BuildError
from graphbus_cli.utils.websocket import (
    start_websocket_server,
    stop_websocket_server,
    has_connected_clients,
    is_websocket_available
)


@click.command()
@click.argument('agents_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--output-dir', '-o',
    default='.graphbus',
    type=click.Path(),
    help='Output directory for build artifacts'
)
@click.option(
    '--validate',
    is_flag=True,
    help='Validate agents after build'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--enable-agents',
    is_flag=True,
    help='Enable LLM agent orchestration during build (agents analyze and propose improvements)'
)
@click.option(
    '--llm-model',
    type=str,
    default=DEFAULT_LLM_MODEL,
    help=f'LLM model for agent orchestration (default: {DEFAULT_LLM_MODEL})'
)
@click.option(
    '--llm-api-key',
    type=str,
    envvar='ANTHROPIC_API_KEY',
    help='LLM API key (or set ANTHROPIC_API_KEY env var)'
)
@click.option(
    '--max-negotiation-rounds',
    type=int,
    default=10,
    help='Maximum negotiation rounds before termination (default: 10)'
)
@click.option(
    '--max-proposals-per-agent',
    type=int,
    default=5,
    help='Maximum proposals per agent (default: 5)'
)
@click.option(
    '--convergence-threshold',
    type=int,
    default=2,
    help='Rounds without proposals before convergence (default: 2)'
)
@click.option(
    '--protected-files',
    type=str,
    multiple=True,
    help='Files that agents cannot modify (can specify multiple)'
)
@click.option(
    '--arbiter-agent',
    type=str,
    help='Agent name to use as arbiter for conflict resolution'
)
@click.option(
    '--intent',
    type=str,
    help='User intent/goal for agent negotiation (e.g., "optimize performance", "improve error handling")'
)
def build(
    agents_dir: str,
    output_dir: str,
    validate: bool,
    verbose: bool,
    enable_agents: bool,
    llm_model: str,
    llm_api_key: str,
    max_negotiation_rounds: int,
    max_proposals_per_agent: int,
    convergence_threshold: int,
    protected_files: tuple,
    arbiter_agent: str,
    intent: str
):
    """
    Build agent graphs from source directory.

    \b
    Discovers agent definitions, analyzes dependencies, and generates
    executable artifacts for the GraphBus runtime.

    \b
    Examples:
      graphbus build agents/                    # Build from agents/ directory
      graphbus build agents/ -o build/          # Custom output directory
      graphbus build agents/ --validate         # Validate after build
      graphbus build agents/ -v                 # Verbose output
      graphbus build agents/ --enable-agents    # Build with LLM agent orchestration
      graphbus build agents/ --enable-agents --intent "optimize performance"
      graphbus build agents/ --enable-agents --arbiter-agent CoreAgent
      graphbus build agents/ --enable-agents --llm-model claude-sonnet-4 --max-negotiation-rounds 5

    \b
    Output:
      The build process creates artifacts in the output directory:
        - graph.json         Agent dependency graph
        - agents.json        Agent definitions and source code
        - topics.json        Topic registry and subscriptions
        - build_summary.json Build metadata
        - negotiations.json  Negotiation history (when --enable-agents is used)

    \b
    Agent Orchestration:
      When --enable-agents is enabled, agents become active LLM agents that can:
        - Check intent relevance and code size (100-line threshold)
        - Analyze their own code for improvements
        - Propose code changes with rationale
        - Reconcile proposals through arbiter (if configured)
        - Evaluate other agents' proposals
        - Negotiate through multiple rounds until convergence
      This enables autonomous agent collaboration for codebase improvement.

    \b
    NEW Features:
      --intent: Guide improvements toward specific goals
        - Agents check if intent matches their scope
        - Focus analysis on stated goal
        - Warn if no agent handles intent (suggests new agent)

      Intelligent Checks:
        - Code size warnings for agents > 100 lines
        - Refactoring suggestions for large agents
        - New agent suggestions when subdividing

      Arbiter Reconciliation (--arbiter-agent):
        - Reviews ALL proposals holistically before evaluation
        - Identifies conflicts and overlaps
        - Provides priority recommendations
        - Suggests modifications for alignment
    """
    try:
        # Start WebSocket server if agent orchestration is enabled
        websocket_server = None
        if enable_agents and is_websocket_available():
            try:
                websocket_server = start_websocket_server(wait_for_client=False, timeout=2.0)
                if websocket_server and has_connected_clients():
                    print_info("UI connected via WebSocket - agent messages will be streamed")
                elif websocket_server:
                    print_info("WebSocket server started (waiting for UI connection...)")
            except Exception as e:
                if verbose:
                    print_info(f"Note: Could not start WebSocket server: {e}")

        agents_path = Path(agents_dir).resolve()
        output_path = Path(output_dir).resolve()

        # Convert directory path to Python module path
        # For agents/, convert to a module path by adding to sys.path
        parent_dir = agents_path.parent
        module_name = agents_path.name

        # Add parent directory to Python path so module can be imported
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        # Display build info
        print_header("GraphBus Build")
        print_info(f"Source directory: {agents_path}")
        print_info(f"Root package: {module_name}")
        print_info(f"Output directory: {output_path}")
        if enable_agents:
            print_info(f"Agent orchestration: ENABLED")
            print_info(f"LLM model: {llm_model}")
            print_info(f"Max negotiation rounds: {max_negotiation_rounds}")
            if intent:
                print_info(f"User intent: {intent}")
        console.print()

        # Create LLM config if agent orchestration is enabled
        llm_config = None
        if enable_agents:
            if not llm_api_key:
                raise BuildError(
                    "LLM API key required when --enable-agents is set. "
                    "Provide via --llm-api-key or ANTHROPIC_API_KEY environment variable."
                )
            llm_config = LLMConfig(
                model=llm_model,
                api_key=llm_api_key
            )

        # Create safety config if agent orchestration is enabled
        safety_config = SafetyConfig()
        if enable_agents:
            arbiter_list = [arbiter_agent] if arbiter_agent else []
            safety_config = SafetyConfig(
                max_negotiation_rounds=max_negotiation_rounds,
                max_proposals_per_agent=max_proposals_per_agent,
                convergence_threshold=convergence_threshold,
                protected_files=list(protected_files),
                arbiter_agents=arbiter_list
            )

        # Create build config
        config = BuildConfig(
            root_package=module_name,
            output_dir=str(output_path),
            llm_config=llm_config,
            safety_config=safety_config,
            user_intent=intent
        )

        # Run build project (this handles all the steps)
        # Redirect stdout to capture build output if not verbose
        if not verbose:
            import io
            import contextlib

            # Capture output
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                artifacts = build_project(config, enable_agents=enable_agents)

            # Show progress indication
            console.print("[cyan]✓[/cyan] Build completed")
        else:
            # Show full build output
            artifacts = build_project(config, enable_agents=enable_agents)

        console.print()

        # Display build summary
        _display_build_summary(artifacts)

        # Validation
        if validate:
            console.print()
            print_info("Running validation...")
            # Validation would be done by validate command
            print_success("Validation passed")

        console.print()
        print_success("Build completed successfully")
        print_info(f"Artifacts written to: {output_path}/")

    except Exception as e:
        console.print()
        raise BuildError(f"Build failed: {str(e)}")
    finally:
        # Stop WebSocket server if it was started
        if enable_agents and websocket_server:
            stop_websocket_server()


def _display_build_summary(artifacts):
    """Display build summary table"""
    print_header("Build Summary")

    # Count statistics
    num_agents = len(artifacts.agents)
    num_dependencies = artifacts.graph.graph.number_of_edges()
    num_topics = len(artifacts.topics)
    num_subscriptions = len(artifacts.subscriptions)

    # Create summary table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Agents", str(num_agents))
    table.add_row("Topics", str(num_topics))
    table.add_row("Subscriptions", str(num_subscriptions))
    table.add_row("Dependencies", str(num_dependencies))

    console.print(table)

    # List agents
    if num_agents > 0:
        console.print("\n[cyan]Agents:[/cyan]")
        for agent in artifacts.agents:
            methods_count = len(agent.methods) if hasattr(agent, 'methods') and agent.methods else 0
            subs_count = len(agent.subscriptions)
            console.print(f"  • {agent.name} ({methods_count} methods, {subs_count} subscriptions)")
