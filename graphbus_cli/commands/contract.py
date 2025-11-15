"""
Contract management CLI commands
"""

import click
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from graphbus_core.runtime.contracts import ContractManager, Contract
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_warning, print_info,
    print_json
)


@click.group()
def contract():
    """Manage API contracts and schema evolution"""
    pass


@contract.command()
@click.argument('agent_name')
@click.option('--version', '-v', required=True, help='Contract version (e.g., 1.0.0)')
@click.option('--schema', '-s', required=True, type=click.Path(exists=True),
              help='Path to schema JSON file')
@click.option('--contracts-dir', default='.graphbus/contracts',
              help='Directory to store contracts')
def register(agent_name: str, version: str, schema: str, contracts_dir: str):
    """
    Register an API contract for an agent

    Example:
        graphbus contract register OrderProcessor --version 2.0.0 --schema schema.json
    """
    try:
        # Load schema from file
        with open(schema, 'r') as f:
            schema_data = json.load(f)

        # Initialize contract manager
        manager = ContractManager(storage_path=contracts_dir)

        # Register contract
        contract_obj = manager.register_contract(agent_name, version, schema_data)

        print_success(f"Registered contract for {agent_name} v{version}")

        # Show contract summary
        console.print()
        console.print(Panel.fit(
            f"[bold]Agent:[/bold] {contract_obj.agent_name}\\n"
            f"[bold]Version:[/bold] {contract_obj.version}\\n"
            f"[bold]Methods:[/bold] {len(contract_obj.methods)}\\n"
            f"[bold]Publishes:[/bold] {len(contract_obj.publishes)} topics\\n"
            f"[bold]Subscribes:[/bold] {len(contract_obj.subscribes)} topics",
            title="Contract Summary",
            border_style="green"
        ))

    except ValueError as e:
        print_error(f"Invalid contract: {e}")
        raise click.Abort()
    except FileNotFoundError:
        print_error(f"Schema file not found: {schema}")
        raise click.Abort()
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in schema file: {e}")
        raise click.Abort()
    except Exception as e:
        print_error(f"Failed to register contract: {e}")
        raise click.Abort()


@contract.command()
@click.option('--agent', '-a', help='Filter by agent name')
@click.option('--version', '-v', help='Show specific version')
@click.option('--contracts-dir', default='.graphbus/contracts',
              help='Directory containing contracts')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
def list(agent: Optional[str], version: Optional[str], contracts_dir: str, format: str):
    """
    List registered contracts

    Example:
        graphbus contract list
        graphbus contract list --agent OrderProcessor
    """
    try:
        manager = ContractManager(storage_path=contracts_dir)

        if agent:
            # Show specific agent
            if version:
                contract_obj = manager.get_contract(agent, version)
                if not contract_obj:
                    print_warning(f"No contract found for {agent} v{version}")
                    return

                if format == 'json':
                    print_json(contract_obj.to_dict())
                else:
                    _display_contract_details(contract_obj)
            else:
                # Show all versions
                versions = manager.get_all_versions(agent)
                if not versions:
                    print_warning(f"No contracts found for {agent}")
                    return

                table = Table(title=f"Contracts for {agent}")
                table.add_column("Version", style="cyan")
                table.add_column("Methods", justify="right")
                table.add_column("Publishes", justify="right")
                table.add_column("Subscribes", justify="right")
                table.add_column("Timestamp")

                for ver in versions:
                    contract_obj = manager.get_contract(agent, ver)
                    if contract_obj:
                        table.add_row(
                            ver,
                            str(len(contract_obj.methods)),
                            str(len(contract_obj.publishes)),
                            str(len(contract_obj.subscribes)),
                            contract_obj.timestamp.strftime("%Y-%m-%d %H:%M")
                        )

                console.print(table)
        else:
            # Show all agents
            table = Table(title="Registered Contracts")
            table.add_column("Agent", style="cyan")
            table.add_column("Latest Version", style="green")
            table.add_column("Total Versions", justify="right")

            for agent_name in sorted(manager.contracts.keys()):
                versions = manager.get_all_versions(agent_name)
                latest = versions[-1] if versions else "N/A"
                table.add_row(agent_name, latest, str(len(versions)))

            console.print(table)

    except Exception as e:
        print_error(f"Failed to list contracts: {e}")
        raise click.Abort()


@contract.command()
@click.option('--agent', '-a', required=True, help='Agent name')
@click.option('--contracts-dir', default='.graphbus/contracts',
              help='Directory containing contracts')
def validate(agent: str, contracts_dir: str):
    """
    Validate agent contract

    Example:
        graphbus contract validate --agent OrderProcessor
    """
    try:
        manager = ContractManager(storage_path=contracts_dir)

        contract_obj = manager.get_contract(agent)
        if not contract_obj:
            print_error(f"No contract found for {agent}")
            raise click.Abort()

        # Basic validation
        issues = []

        # Check methods
        if not contract_obj.methods:
            issues.append("No methods defined")

        for method_name, method in contract_obj.methods.items():
            if not method.input and not method.output:
                issues.append(f"Method '{method_name}' has no input or output schema")

        # Check publishes
        for topic, event in contract_obj.publishes.items():
            if not event.payload:
                issues.append(f"Event '{topic}' has no payload schema")

        if not issues:
            print_success(f"Contract for {agent} v{contract_obj.version} is valid")
            console.print()
            console.print(Panel.fit(
                f"[bold]Methods:[/bold] {len(contract_obj.methods)} ✓\\n"
                f"[bold]Publishes:[/bold] {len(contract_obj.publishes)} topics ✓\\n"
                f"[bold]Subscribes:[/bold] {len(contract_obj.subscribes)} topics ✓",
                title="Validation Results",
                border_style="green"
            ))
        else:
            print_warning(f"Contract for {agent} v{contract_obj.version} has {len(issues)} issues:")
            for issue in issues:
                console.print(f"  • {issue}")

    except Exception as e:
        print_error(f"Failed to validate contract: {e}")
        raise click.Abort()


@contract.command()
@click.argument('contract1')  # Format: Agent@Version
@click.argument('contract2')  # Format: Agent@Version
@click.option('--contracts-dir', default='.graphbus/contracts',
              help='Directory containing contracts')
def diff(contract1: str, contract2: str, contracts_dir: str):
    """
    Show differences between two contract versions

    Example:
        graphbus contract diff OrderProcessor@1.0.0 OrderProcessor@2.0.0
    """
    try:
        # Parse contract specifications
        agent1, version1 = _parse_contract_spec(contract1)
        agent2, version2 = _parse_contract_spec(contract2)

        if agent1 != agent2:
            print_warning("Comparing contracts from different agents")

        manager = ContractManager(storage_path=contracts_dir)

        c1 = manager.get_contract(agent1, version1)
        c2 = manager.get_contract(agent2, version2)

        if not c1:
            print_error(f"Contract not found: {contract1}")
            raise click.Abort()

        if not c2:
            print_error(f"Contract not found: {contract2}")
            raise click.Abort()

        console.print()
        console.print(f"[bold]Comparing:[/bold] {contract1} → {contract2}")
        console.print()

        # Compare methods
        _show_method_diff(c1, c2)

        # Compare publishes
        _show_publishes_diff(c1, c2)

        # Compare subscribes
        _show_subscribes_diff(c1, c2)

    except ValueError as e:
        print_error(f"Invalid contract specification: {e}")
        console.print("Expected format: Agent@Version (e.g., OrderProcessor@1.0.0)")
        raise click.Abort()
    except Exception as e:
        print_error(f"Failed to diff contracts: {e}")
        raise click.Abort()


@contract.command()
@click.argument('contract_spec')  # Format: Agent@Version
@click.option('--contracts-dir', default='.graphbus/contracts',
              help='Directory containing contracts')
@click.option('--graph-dir', default='.graphbus',
              help='Directory containing dependency graph')
def impact(contract_spec: str, contracts_dir: str, graph_dir: str):
    """
    Analyze impact of schema changes using dependency graph

    Example:
        graphbus contract impact OrderProcessor@2.0.0
    """
    try:
        # Parse contract specification
        agent_name, version = _parse_contract_spec(contract_spec)

        # Load graph
        graph_file = Path(graph_dir) / 'graph.json'
        if not graph_file.exists():
            print_error("Dependency graph not found. Run 'graphbus build' first.")
            raise click.Abort()

        import networkx as nx
        from networkx.readwrite import json_graph

        with open(graph_file, 'r') as f:
            graph_data = json.load(f)
            graph = json_graph.node_link_graph(graph_data)

        manager = ContractManager(storage_path=contracts_dir, graph=graph)

        contract_obj = manager.get_contract(agent_name, version)
        if not contract_obj:
            print_error(f"Contract not found: {contract_spec}")
            raise click.Abort()

        # Analyze impact
        impact_analysis = manager.analyze_schema_impact(agent_name, contract_obj.to_dict())

        console.print()
        console.print(Panel.fit(
            f"[bold]Agent:[/bold] {impact_analysis.agent_name}\\n"
            f"[bold]New Version:[/bold] {impact_analysis.new_version}\\n"
            f"[bold]Affected Agents:[/bold] {len(impact_analysis.affected_agents)}\\n"
            f"[bold]Breaking Changes:[/bold] {len(impact_analysis.breaking_changes)}",
            title="Impact Analysis",
            border_style="yellow" if impact_analysis.has_breaking_changes() else "green"
        ))

        if impact_analysis.affected_agents:
            console.print()
            console.print("[bold]Affected Downstream Agents:[/bold]")
            for agent in impact_analysis.affected_agents:
                has_breaking = agent in impact_analysis.breaking_changes
                icon = "⚠️ " if has_breaking else "✓ "
                style = "yellow" if has_breaking else "green"
                console.print(f"  {icon}[{style}]{agent}[/{style}]")

        if impact_analysis.breaking_changes:
            console.print()
            console.print("[bold yellow]Breaking Changes Detected:[/bold yellow]")
            for agent, issues in impact_analysis.breaking_changes.items():
                console.print(f"\\n  [bold]{agent}:[/bold]")
                for issue in issues:
                    console.print(f"    • {issue.description}")
                    if issue.recommendation:
                        console.print(f"      [dim]→ {issue.recommendation}[/dim]")

        if impact_analysis.warnings:
            console.print()
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for warning in impact_analysis.warnings:
                console.print(f"  • {warning}")

    except ValueError as e:
        print_error(f"Invalid contract specification: {e}")
        raise click.Abort()
    except Exception as e:
        print_error(f"Failed to analyze impact: {e}")
        raise click.Abort()


def _parse_contract_spec(spec: str) -> tuple:
    """Parse contract specification like Agent@Version"""
    if '@' not in spec:
        raise ValueError(f"Invalid format: {spec}")

    parts = spec.split('@')
    if len(parts) != 2:
        raise ValueError(f"Invalid format: {spec}")

    return parts[0], parts[1]


def _display_contract_details(contract_obj: Contract):
    """Display detailed contract information"""
    console.print()
    console.print(Panel.fit(
        f"[bold]Agent:[/bold] {contract_obj.agent_name}\\n"
        f"[bold]Version:[/bold] {contract_obj.version}\\n"
        f"[bold]Timestamp:[/bold] {contract_obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\\n"
        f"[bold]Description:[/bold] {contract_obj.description or 'N/A'}",
        title="Contract Details",
        border_style="cyan"
    ))

    # Methods
    if contract_obj.methods:
        console.print()
        table = Table(title="Methods")
        table.add_column("Method", style="cyan")
        table.add_column("Inputs")
        table.add_column("Outputs")

        for method_name, method in contract_obj.methods.items():
            inputs = ", ".join(f"{name}: {field.type}" for name, field in method.input.items())
            outputs = ", ".join(f"{name}: {field.type}" for name, field in method.output.items())
            table.add_row(method_name, inputs or "-", outputs or "-")

        console.print(table)

    # Publishes
    if contract_obj.publishes:
        console.print()
        table = Table(title="Publishes")
        table.add_column("Topic", style="cyan")
        table.add_column("Payload Schema")

        for topic, event in contract_obj.publishes.items():
            payload_str = ", ".join(f"{name}: {field.type}" for name, field in event.payload.items())
            table.add_row(topic, payload_str or "-")

        console.print(table)

    # Subscribes
    if contract_obj.subscribes:
        console.print()
        console.print("[bold]Subscribes to:[/bold]")
        for topic in contract_obj.subscribes:
            console.print(f"  • {topic}")


def _show_method_diff(c1: Contract, c2: Contract):
    """Show method differences"""
    all_methods = set(c1.methods.keys()) | set(c2.methods.keys())

    if not all_methods:
        return

    console.print("[bold]Methods:[/bold]")

    added = set(c2.methods.keys()) - set(c1.methods.keys())
    removed = set(c1.methods.keys()) - set(c2.methods.keys())
    common = set(c1.methods.keys()) & set(c2.methods.keys())

    for method in added:
        console.print(f"  [green]+ {method}[/green] (added)")

    for method in removed:
        console.print(f"  [red]- {method}[/red] (removed)")

    for method in common:
        m1 = c1.methods[method]
        m2 = c2.methods[method]

        if m1.input != m2.input or m1.output != m2.output:
            console.print(f"  [yellow]~ {method}[/yellow] (modified)")

    console.print()


def _show_publishes_diff(c1: Contract, c2: Contract):
    """Show publishes differences"""
    all_topics = set(c1.publishes.keys()) | set(c2.publishes.keys())

    if not all_topics:
        return

    console.print("[bold]Publishes:[/bold]")

    added = set(c2.publishes.keys()) - set(c1.publishes.keys())
    removed = set(c1.publishes.keys()) - set(c2.publishes.keys())

    for topic in added:
        console.print(f"  [green]+ {topic}[/green] (added)")

    for topic in removed:
        console.print(f"  [red]- {topic}[/red] (removed)")

    console.print()


def _show_subscribes_diff(c1: Contract, c2: Contract):
    """Show subscribes differences"""
    topics1 = set(c1.subscribes)
    topics2 = set(c2.subscribes)

    if not topics1 and not topics2:
        return

    console.print("[bold]Subscribes:[/bold]")

    added = topics2 - topics1
    removed = topics1 - topics2

    for topic in added:
        console.print(f"  [green]+ {topic}[/green] (added)")

    for topic in removed:
        console.print(f"  [red]- {topic}[/red] (removed)")

    console.print()
