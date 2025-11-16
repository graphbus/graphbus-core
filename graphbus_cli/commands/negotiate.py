"""
Negotiate command - Run agent negotiation on existing build artifacts
"""

import click
import json
from pathlib import Path

from graphbus_core.config import LLMConfig, SafetyConfig
from graphbus_core.constants import DEFAULT_LLM_MODEL
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header
)
from graphbus_cli.utils.errors import BuildError


@click.command()
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--rounds',
    type=int,
    default=5,
    help='Number of negotiation rounds to run (default: 5)'
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
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--intent',
    type=str,
    help='User intent/goal for the negotiation (e.g., "optimize performance", "improve error handling")'
)
def negotiate(
    artifacts_dir: str,
    rounds: int,
    llm_model: str,
    llm_api_key: str,
    max_proposals_per_agent: int,
    convergence_threshold: int,
    protected_files: tuple,
    arbiter_agent: str,
    verbose: bool,
    intent: str
):
    """
    Run LLM agent negotiation on existing build artifacts.

    \b
    This command runs agent negotiation on already-built artifacts, allowing
    agents to collaboratively improve the codebase through multi-round
    negotiation without rebuilding from scratch.

    \b
    Use Cases:
      - Re-run negotiation with different parameters
      - Incremental improvements after initial build
      - Experiment with agent interactions
      - Iterate on improvements after manual code changes

    \b
    Examples:
      graphbus negotiate .graphbus --rounds 5
      graphbus negotiate .graphbus --llm-model gpt-4-turbo
      graphbus negotiate .graphbus --rounds 3 --max-proposals-per-agent 3
      graphbus negotiate .graphbus --protected-files agents/core.py

    \b
    How It Works:
      1. Load agents from build artifacts
      2. Activate agents as LLM agents
      3. Each agent analyzes code and proposes improvements
      4. Agents evaluate each other's proposals
      5. Arbiter resolves conflicts if needed
      6. Accepted proposals are committed to files
      7. Repeat for N rounds or until convergence

    \b
    Output:
      The negotiation process updates:
        - Source files (agents/*.py) with accepted changes
        - .graphbus/negotiations.json with complete history
        - Build artifacts reflecting code changes
    """
    try:
        artifacts_path = Path(artifacts_dir).resolve()

        # Verify artifacts directory contains necessary files
        graphbus_dir = artifacts_path if artifacts_path.name == '.graphbus' else artifacts_path / '.graphbus'
        if not graphbus_dir.exists():
            raise BuildError(
                f"Artifacts directory not found: {graphbus_dir}\n"
                "Run 'graphbus build' first to create artifacts."
            )

        agents_json = graphbus_dir / 'agents.json'
        if not agents_json.exists():
            raise BuildError(
                f"agents.json not found in {graphbus_dir}\n"
                "The artifacts directory must contain a valid build."
            )

        # Display negotiation info
        print_header("GraphBus Agent Negotiation")
        print_info(f"Artifacts directory: {graphbus_dir}")
        print_info(f"LLM model: {llm_model}")
        print_info(f"Max rounds: {rounds}")
        print_info(f"Max proposals per agent: {max_proposals_per_agent}")
        if intent:
            print_info(f"User intent: {intent}")
        console.print()

        # Validate API key
        if not llm_api_key:
            raise BuildError(
                "LLM API key required for agent negotiation. "
                "Provide via --llm-api-key or ANTHROPIC_API_KEY environment variable."
            )

        # Create LLM config
        llm_config = LLMConfig(
            model=llm_model,
            api_key=llm_api_key
        )

        # Create safety config
        arbiter_list = [arbiter_agent] if arbiter_agent else []
        safety_config = SafetyConfig(
            max_negotiation_rounds=rounds,
            max_proposals_per_agent=max_proposals_per_agent,
            convergence_threshold=convergence_threshold,
            protected_files=list(protected_files),
            arbiter_agents=arbiter_list
        )

        # TODO: Import and call negotiation function from graphbus_core
        # This will be implemented when the orchestrator exposes a standalone negotiate function
        print_info("Loading agents from artifacts...")

        # For now, show what would happen
        console.print("[yellow]⚠[/yellow] Negotiation functionality coming soon!")
        console.print()
        print_info("This command will:")
        console.print("  1. Load agent definitions from artifacts")
        console.print("  2. Activate agents with LLM capabilities")
        console.print("  3. Run multi-round negotiation")
        console.print("  4. Apply accepted proposals")
        console.print("  5. Save negotiation history")
        console.print()

        # TODO: Once implemented:
        # from graphbus_core.build.orchestrator import run_negotiation
        # results = run_negotiation(
        #     artifacts_dir=str(graphbus_dir),
        #     llm_config=llm_config,
        #     safety_config=safety_config,
        #     user_intent=intent,
        #     verbose=verbose
        # )
        # _display_negotiation_summary(results)

        print_info(f"Would negotiate with artifacts in: {graphbus_dir}/")

    except Exception as e:
        console.print()
        raise BuildError(f"Negotiation failed: {str(e)}")


def _display_negotiation_summary(results):
    """Display negotiation summary"""
    print_header("Negotiation Summary")

    num_rounds = results.get('rounds_completed', 0)
    num_proposals = results.get('total_proposals', 0)
    num_accepted = results.get('accepted_proposals', 0)
    num_files_changed = results.get('files_changed', 0)

    console.print(f"[cyan]Rounds completed:[/cyan] {num_rounds}")
    console.print(f"[cyan]Proposals made:[/cyan] {num_proposals}")
    console.print(f"[cyan]Proposals accepted:[/cyan] {num_accepted}")
    console.print(f"[cyan]Files modified:[/cyan] {num_files_changed}")
    console.print()

    if num_accepted > 0:
        print_success(f"Negotiation completed: {num_accepted} improvements applied")
    else:
        print_info("Negotiation completed: no changes proposed")
