"""
Inspect command - Inspect build artifacts
"""

import click
import json
import yaml
from pathlib import Path
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

from graphbus_core.runtime.loader import ArtifactLoader
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, print_json
)
from graphbus_cli.utils.errors import CLIError


@click.command()
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--graph',
    is_flag=True,
    help='Display graph structure'
)
@click.option(
    '--agents',
    is_flag=True,
    help='List all agents'
)
@click.option(
    '--topics',
    is_flag=True,
    help='List all topics'
)
@click.option(
    '--subscriptions',
    is_flag=True,
    help='Show subscription mappings'
)
@click.option(
    '--agent',
    type=str,
    help='Show detailed agent info'
)
@click.option(
    '--format',
    type=click.Choice(['table', 'json', 'yaml']),
    default='table',
    help='Output format'
)
def inspect(artifacts_dir: str, graph: bool, agents: bool, topics: bool,
            subscriptions: bool, agent: str, format: str):
    """
    Inspect build artifacts without running.

    \b
    View agent graphs, dependencies, topics, and subscriptions
    without starting the runtime.

    \b
    Examples:
      graphbus inspect .graphbus                 # Show graph structure
      graphbus inspect .graphbus --agents        # List all agents
      graphbus inspect .graphbus --topics        # List topics
      graphbus inspect .graphbus --agent HelloService  # Agent details
      graphbus inspect .graphbus --format json   # JSON output

    \b
    Output Formats:
      table    - Pretty tables (default)
      json     - JSON format
      yaml     - YAML format
    """
    try:
        artifacts_path = Path(artifacts_dir).resolve()

        # Load artifacts
        print_header("GraphBus Artifact Inspector")
        print_info(f"Loading artifacts from: {artifacts_path}")
        console.print()

        loader = ArtifactLoader(str(artifacts_path))

        # Load all artifacts
        graph_obj, agent_defs, topic_list, subscription_list = loader.load_all()

        # If no specific option, show graph by default
        if not any([graph, agents, topics, subscriptions, agent]):
            graph = True

        # Show graph structure
        if graph:
            _display_graph(graph_obj, agent_defs, format)

        # Show agents list
        if agents:
            _display_agents(agent_defs, format)

        # Show topics
        if topics:
            _display_topics(topic_list, subscription_list, format)

        # Show subscriptions
        if subscriptions:
            _display_subscriptions(subscription_list, format)

        # Show specific agent details
        if agent:
            _display_agent_details(loader, agent, format)

    except Exception as e:
        console.print()
        raise CLIError(f"Inspection failed: {str(e)}")


def _display_graph(graph, agent_defs, format):
    """Display graph structure"""
    print_header("Agent Graph")

    if format == 'json':
        graph_data = {
            "nodes": [{"name": name, "type": data.get("node_type", "unknown")}
                     for name, data in graph.graph.nodes(data=True)],
            "edges": [{"from": u, "to": v} for u, v in graph.graph.edges()],
            "stats": {
                "nodes": len(graph),
                "edges": graph.graph.number_of_edges(),
                "agents": len(agent_defs)
            }
        }
        print_json(graph_data)
        return
    elif format == 'yaml':
        graph_data = {
            "nodes": [{"name": name, "type": data.get("node_type", "unknown")}
                     for name, data in graph.graph.nodes(data=True)],
            "edges": [{"from": u, "to": v} for u, v in graph.graph.edges()],
        }
        console.print(yaml.dump(graph_data, default_flow_style=False))
        return

    # Table format
    # Show agent activation order
    try:
        activation_order = graph.get_agent_activation_order()
        console.print("[cyan]Agent Activation Order:[/cyan]")
        console.print("  " + " → ".join(activation_order))
        console.print()
    except Exception:
        pass

    # Show nodes and edges
    console.print(f"[cyan]Nodes:[/cyan] {len(graph)}")
    console.print(f"[cyan]Edges:[/cyan] {graph.graph.number_of_edges()}")
    console.print(f"[cyan]Agents:[/cyan] {len(agent_defs)}")
    console.print()

    # List all nodes
    agent_nodes = [name for name, data in graph.graph.nodes(data=True)
                   if data.get("node_type") == "agent"]

    if agent_nodes:
        console.print("[cyan]Agent Nodes:[/cyan]")
        for node in sorted(agent_nodes):
            # Get dependencies
            deps = list(graph.graph.predecessors(node))
            if deps:
                console.print(f"  • {node} (depends on: {', '.join(deps)})")
            else:
                console.print(f"  • {node}")


def _display_agents(agent_defs, format):
    """Display agents list"""
    print_header("Agents")

    if format == 'json':
        agents_data = [
            {
                "name": agent.name,
                "module": agent.module,
                "class": agent.class_name,
                "methods": len(agent.methods) if hasattr(agent, 'methods') and agent.methods else 0,
                "subscriptions": len(agent.subscriptions),
                "dependencies": agent.dependencies if hasattr(agent, 'dependencies') else []
            }
            for agent in agent_defs
        ]
        print_json(agents_data)
        return
    elif format == 'yaml':
        agents_data = [
            {
                "name": agent.name,
                "module": agent.module,
                "methods": len(agent.methods) if hasattr(agent, 'methods') and agent.methods else 0,
                "subscriptions": len(agent.subscriptions)
            }
            for agent in agent_defs
        ]
        console.print(yaml.dump(agents_data, default_flow_style=False))
        return

    # Table format
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan")
    table.add_column("Methods", justify="right")
    table.add_column("Subscribes", justify="right")
    table.add_column("Dependencies", justify="right")

    for agent in sorted(agent_defs, key=lambda a: a.name):
        methods_count = len(agent.methods) if hasattr(agent, 'methods') and agent.methods else 0
        subs_count = len(agent.subscriptions)
        deps_count = len(agent.dependencies) if hasattr(agent, 'dependencies') else 0

        table.add_row(
            agent.name,
            str(methods_count),
            str(subs_count),
            str(deps_count)
        )

    console.print(table)


def _display_topics(topic_list, subscription_list, format):
    """Display topics and subscriptions"""
    print_header("Topics and Subscriptions")

    if format == 'json':
        topics_data = []
        for topic in sorted(topic_list):
            subs = [s for s in subscription_list if s.topic.name == topic.name]
            topics_data.append({
                "topic": topic.name,
                "subscribers": [{"agent": s.node_name, "handler": s.handler_name} for s in subs]
            })
        print_json(topics_data)
        return
    elif format == 'yaml':
        topics_data = [
            {
                "topic": topic.name,
                "subscribers": len([s for s in subscription_list if s.topic.name == topic.name])
            }
            for topic in sorted(topic_list, key=lambda t: t.name)
        ]
        console.print(yaml.dump(topics_data, default_flow_style=False))
        return

    # Table format
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Topic", style="cyan")
    table.add_column("Subscribers")
    table.add_column("Handler")

    for topic in sorted(topic_list, key=lambda t: t.name):
        subs = [s for s in subscription_list if s.topic.name == topic.name]

        if subs:
            for sub in subs:
                table.add_row(topic.name, sub.node_name, sub.handler_name)
        else:
            table.add_row(topic.name, "[dim]none[/dim]", "")

    console.print(table)


def _display_subscriptions(subscription_list, format):
    """Display subscription mappings"""
    print_header("Subscription Mappings")

    if format == 'json':
        subs_data = [
            {
                "agent": sub.node_name,
                "topic": sub.topic.name,
                "handler": sub.handler_name
            }
            for sub in subscription_list
        ]
        print_json(subs_data)
        return
    elif format == 'yaml':
        subs_data = [
            {
                "agent": sub.node_name,
                "topic": sub.topic.name,
                "handler": sub.handler_name
            }
            for sub in subscription_list
        ]
        console.print(yaml.dump(subs_data, default_flow_style=False))
        return

    # Group by agent
    by_agent = {}
    for sub in subscription_list:
        if sub.node_name not in by_agent:
            by_agent[sub.node_name] = []
        by_agent[sub.node_name].append(sub)

    for agent_name in sorted(by_agent.keys()):
        console.print(f"\n[cyan]{agent_name}:[/cyan]")
        for sub in by_agent[agent_name]:
            console.print(f"  • {sub.topic.name} → {sub.handler_name}()")


def _display_agent_details(loader, agent_name, format):
    """Display detailed agent information"""
    print_header(f"Agent: {agent_name}")

    try:
        agent = loader.get_agent_by_name(agent_name)
    except ValueError:
        print_error(f"Agent '{agent_name}' not found")
        return

    if format == 'json':
        agent_data = {
            "name": agent.name,
            "module": agent.module,
            "class": agent.class_name,
            "methods": agent.methods if hasattr(agent, 'methods') else [],
            "subscriptions": [
                {"topic": sub.topic.name, "handler": sub.handler_name}
                for sub in agent.subscriptions
            ],
            "dependencies": agent.dependencies if hasattr(agent, 'dependencies') else [],
            "system_prompt": agent.system_prompt if hasattr(agent, 'system_prompt') else None
        }
        print_json(agent_data)
        return
    elif format == 'yaml':
        agent_data = {
            "name": agent.name,
            "module": agent.module,
            "class": agent.class_name,
            "methods": agent.methods if hasattr(agent, 'methods') else [],
            "subscriptions": len(agent.subscriptions)
        }
        console.print(yaml.dump(agent_data, default_flow_style=False))
        return

    # Table format - detailed view
    console.print(f"[cyan]Module:[/cyan] {agent.module}")
    console.print(f"[cyan]Class:[/cyan] {agent.class_name}")
    console.print()

    # Methods
    if hasattr(agent, 'methods') and agent.methods:
        console.print("[cyan]Methods:[/cyan]")
        for method in agent.methods:
            console.print(f"  • {method}")
    else:
        console.print("[cyan]Methods:[/cyan] None")
    console.print()

    # Subscriptions
    if agent.subscriptions:
        console.print("[cyan]Subscribes To:[/cyan]")
        for sub in agent.subscriptions:
            console.print(f"  • {sub.topic.name} → {sub.handler_name}()")
    else:
        console.print("[cyan]Subscribes To:[/cyan] None")
    console.print()

    # Dependencies
    if hasattr(agent, 'dependencies') and agent.dependencies:
        console.print("[cyan]Dependencies:[/cyan]")
        for dep in agent.dependencies:
            console.print(f"  • {dep}")
    else:
        console.print("[cyan]Dependencies:[/cyan] None")
    console.print()

    # System prompt
    if hasattr(agent, 'system_prompt') and agent.system_prompt:
        console.print("[cyan]System Prompt:[/cyan]")
        prompt_text = agent.system_prompt.get('text', '') if isinstance(agent.system_prompt, dict) else str(agent.system_prompt)
        if prompt_text:
            console.print(Panel(prompt_text, border_style="dim"))
