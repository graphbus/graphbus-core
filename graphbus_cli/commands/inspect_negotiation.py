"""
Inspect negotiation command - View agent negotiation history
"""

import click
import json
from pathlib import Path
from rich.table import Table

from graphbus_cli.utils.output import (
    console, print_error, print_info,
    print_header, print_json
)
from graphbus_cli.utils.errors import CLIError


@click.command(name='inspect-negotiation')
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--format',
    type=click.Choice(['table', 'json', 'timeline']),
    default='table',
    help='Output format: table (summary), timeline (chronological), json (complete data)'
)
@click.option(
    '--round',
    'round_num',
    type=int,
    help='Show specific negotiation round (omit for all rounds)'
)
@click.option(
    '--agent',
    'agent_name',
    type=str,
    help='Filter to specific agent\'s proposals and evaluations'
)
def inspect_negotiation(artifacts_dir: str, format: str, round_num: int, agent_name: str):
    """
    Inspect negotiation history from previous agent orchestration.

    \b
    Shows all proposals, evaluations, conflicts, and commits from
    multi-round agent collaboration. Use this to understand agent
    decision-making and debug negotiation outcomes.

    \b
    Examples:
      graphbus inspect-negotiation .graphbus
      graphbus inspect-negotiation .graphbus --format timeline
      graphbus inspect-negotiation .graphbus --format json > negotiation.json
      graphbus inspect-negotiation .graphbus --round 2
      graphbus inspect-negotiation .graphbus --agent OrderService

    \b
    Output Formats:
      table    - Summary table (default)
      timeline - Chronological event flow
      json     - Complete data export
    """
    try:
        artifacts_path = Path(artifacts_dir).resolve()

        # Find negotiations.json file
        graphbus_dir = artifacts_path if artifacts_path.name == '.graphbus' else artifacts_path / '.graphbus'
        negotiations_file = graphbus_dir / 'negotiations.json'

        if not negotiations_file.exists():
            print_error(f"Negotiation history not found: {negotiations_file}")
            console.print()
            print_info("No negotiation history found. This file is created when you run:")
            console.print("  • graphbus build --enable-agents")
            console.print("  • graphbus negotiate .graphbus")
            return

        # Load negotiation history
        with open(negotiations_file, 'r') as f:
            negotiations = json.load(f)

        # Display header
        print_header("Negotiation History")
        print_info(f"Source: {negotiations_file}")
        console.print()

        # JSON format - just dump everything
        if format == 'json':
            print_json(negotiations)
            return

        # Apply filters
        # Handle both old format (list) and new format (dict)
        if isinstance(negotiations, list):
            proposals = negotiations  # Old format - list of proposals
            evaluations = []
            commits = []
        elif isinstance(negotiations, dict):
            proposals = negotiations.get('proposals', [])  # New format
            evaluations = negotiations.get('evaluations', [])
            commits = negotiations.get('commits', [])
        else:
            proposals = []
            evaluations = []
            commits = []

        if round_num is not None:
            proposals = [p for p in proposals if p.get('round') == round_num]
            evaluations = [e for e in evaluations if e.get('round') == round_num]
            commits = [c for c in commits if c.get('round') == round_num]

        if agent_name:
            proposals = [p for p in proposals if p.get('agent') == agent_name]
            evaluations = [e for e in evaluations if e.get('agent') == agent_name or e.get('proposal_agent') == agent_name]
            commits = [c for c in commits if c.get('agent') == agent_name]

        # Timeline format
        if format == 'timeline':
            _display_negotiation_timeline(proposals, evaluations, commits)
        else:
            # Table format (default)
            _display_negotiation_table(proposals, evaluations, commits, negotiations)

    except Exception as e:
        console.print()
        raise CLIError(f"Failed to inspect negotiation: {str(e)}")


def _display_negotiation_table(proposals, evaluations, commits, negotiations):
    """Display negotiation summary as tables"""

    # Summary stats
    num_rounds = negotiations.get('rounds_completed', 0)
    num_proposals = len(proposals)
    num_accepted = len([p for p in proposals if p.get('status') == 'accepted'])
    num_rejected = len([p for p in proposals if p.get('status') == 'rejected'])
    num_conflicts = negotiations.get('conflicts_resolved', 0)

    console.print(f"[cyan]Rounds:[/cyan] {num_rounds}")
    console.print(f"[cyan]Total proposals:[/cyan] {num_proposals}")
    console.print(f"[cyan]Accepted:[/cyan] {num_accepted}")
    console.print(f"[cyan]Rejected:[/cyan] {num_rejected}")
    console.print(f"[cyan]Conflicts resolved:[/cyan] {num_conflicts}")
    console.print()

    # Proposals table
    if proposals:
        print_header("Proposals")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan")
        table.add_column("Round", justify="right")
        table.add_column("Agent")
        table.add_column("Intent")
        table.add_column("Status")

        for proposal in proposals:
            status_color = "green" if proposal.get('status') == 'accepted' else "red" if proposal.get('status') == 'rejected' else "yellow"
            table.add_row(
                proposal.get('id', 'N/A'),
                str(proposal.get('round', 'N/A')),
                proposal.get('agent', 'N/A'),
                proposal.get('intent', 'N/A')[:50] + ('...' if len(proposal.get('intent', '')) > 50 else ''),
                f"[{status_color}]{proposal.get('status', 'pending')}[/{status_color}]"
            )

        console.print(table)
        console.print()

    # Evaluations table
    if evaluations:
        print_header("Evaluations")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Proposal", style="cyan")
        table.add_column("Evaluator")
        table.add_column("Decision")
        table.add_column("Rationale")

        for evaluation in evaluations:
            decision = evaluation.get('decision', 'unknown')
            decision_color = "green" if decision == 'approve' else "red" if decision == 'reject' else "yellow"
            table.add_row(
                evaluation.get('proposal_id', 'N/A'),
                evaluation.get('agent', 'N/A'),
                f"[{decision_color}]{decision}[/{decision_color}]",
                evaluation.get('rationale', 'N/A')[:40] + ('...' if len(evaluation.get('rationale', '')) > 40 else '')
            )

        console.print(table)
        console.print()

    # Commits table
    if commits:
        print_header("Commits Applied")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Round", justify="right")
        table.add_column("Proposal", style="cyan")
        table.add_column("Files Modified")
        table.add_column("Agent")

        for commit in commits:
            table.add_row(
                str(commit.get('round', 'N/A')),
                commit.get('proposal_id', 'N/A'),
                str(commit.get('files_modified', 0)),
                commit.get('agent', 'N/A')
            )

        console.print(table)


def _display_negotiation_timeline(proposals, evaluations, commits):
    """Display negotiation as chronological timeline"""
    print_header("Negotiation Timeline")

    # Combine all events with timestamps
    events = []

    for proposal in proposals:
        events.append({
            'type': 'proposal',
            'round': proposal.get('round', 0),
            'timestamp': proposal.get('timestamp', 0),
            'data': proposal
        })

    for evaluation in evaluations:
        events.append({
            'type': 'evaluation',
            'round': evaluation.get('round', 0),
            'timestamp': evaluation.get('timestamp', 0),
            'data': evaluation
        })

    for commit in commits:
        events.append({
            'type': 'commit',
            'round': commit.get('round', 0),
            'timestamp': commit.get('timestamp', 0),
            'data': commit
        })

    # Sort by timestamp
    events.sort(key=lambda e: (e['round'], e['timestamp']))

    # Display timeline
    current_round = None
    for event in events:
        if event['round'] != current_round:
            current_round = event['round']
            console.print(f"\n[bold cyan]Round {current_round}[/bold cyan]")

        data = event['data']
        if event['type'] == 'proposal':
            console.print(f"  [yellow]PROPOSE[/yellow] {data.get('agent')} → {data.get('id')}: {data.get('intent')[:60]}")
        elif event['type'] == 'evaluation':
            decision = data.get('decision', 'unknown')
            color = "green" if decision == 'approve' else "red" if decision == 'reject' else "yellow"
            console.print(f"  [{color}]{decision.upper()}[/{color}] {data.get('agent')} evaluates {data.get('proposal_id')}")
        elif event['type'] == 'commit':
            console.print(f"  [green]COMMIT[/green] Applied {data.get('proposal_id')} ({data.get('files_modified', 0)} files)")

    console.print()
