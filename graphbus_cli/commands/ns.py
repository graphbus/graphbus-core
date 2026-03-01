"""
Namespace command — manage namespaces and view agent topologies.
"""

import click
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

from graphbus_core.namespace import NamespaceRegistry

console = Console()


def _get_registry(project_root: str) -> NamespaceRegistry:
    """Get namespace registry for the project."""
    graphbus_dir = Path(project_root) / ".graphbus"
    return NamespaceRegistry(storage_dir=str(graphbus_dir))


@click.group()
def ns():
    """
    Manage namespaces for agent isolation and communication.

    \b
    Namespaces provide logical isolation boundaries for agents.
    Agents within a namespace can communicate via shared topics.
    Different namespaces are isolated unless explicitly bridged.

    \b
    Examples:
      graphbus ns list
      graphbus ns create backend-api --desc "Backend service agents"
      graphbus ns use backend-api
      graphbus ns current
      graphbus ns show backend-api
      graphbus ns topology backend-api
      graphbus ns topology --all
    """
    pass


@ns.command("list")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
def ns_list(project_root):
    """List all namespaces. The active namespace is marked with ✦."""
    registry = _get_registry(project_root)
    namespaces = registry.list_namespaces()
    current = registry.get_current()

    if not namespaces:
        console.print("[dim]No namespaces found. Create one with:[/dim]")
        console.print("  [cyan]graphbus ns create my-namespace[/cyan]")
        return

    table = Table(title="Namespaces", border_style="cyan")
    table.add_column("", width=2)   # active marker
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Agents", justify="right")
    table.add_column("Topics", justify="right")

    for ns_info in namespaces:
        is_active = ns_info["name"] == current
        marker = "[green]✦[/green]" if is_active else ""
        name_cell = f"[green]{ns_info['name']}[/green]" if is_active else ns_info["name"]
        table.add_row(
            marker,
            name_cell,
            ns_info.get("description", ""),
            str(ns_info["agent_count"]),
            str(ns_info["topic_count"]),
        )

    console.print(table)
    console.print(f"[dim]Active namespace: [bold]{current}[/bold]  (change with: graphbus ns use <name>)[/dim]")


@ns.command("create")
@click.argument("name")
@click.option("--desc", "-d", default="", help="Namespace description")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
def ns_create(name, desc, project_root):
    """Create a new namespace."""
    registry = _get_registry(project_root)
    try:
        registry.create(name, description=desc)
        console.print(f"[green]✓[/green] Namespace [bold]{name}[/bold] created")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


@ns.command("use")
@click.argument("name")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
def ns_use(name, project_root):
    """Switch the active namespace context.

    \b
    The active namespace is used by default when running:
      graphbus negotiate .graphbus --intent "..."
      graphbus build agents/ --namespace <name>

    \b
    Examples:
      graphbus ns use backend-api
      graphbus ns use production
    """
    registry = _get_registry(project_root)
    try:
        registry.set_current(name)
        console.print(f"[green]✓[/green] Switched to namespace [bold]{name}[/bold]")
        console.print(f"  [dim]Intent commands will now default to: --namespace {name}[/dim]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


@ns.command("current")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
def ns_current(project_root):
    """Show the active namespace context."""
    registry = _get_registry(project_root)
    current = registry.get_current()
    namespaces = {ns_info["name"] for ns_info in registry.list_namespaces()}

    if current not in namespaces:
        console.print(
            f"[yellow]Active namespace:[/yellow] [bold]{current}[/bold]  "
            f"[dim](not yet created — run: graphbus ns create {current})[/dim]"
        )
    else:
        ns_obj = registry.get(current)
        desc = ns_obj.description if ns_obj and ns_obj.description else ""
        console.print(f"[green]Active namespace:[/green] [bold]{current}[/bold]", end="")
        if desc:
            console.print(f"  [dim]{desc}[/dim]")
        else:
            console.print()
        agent_count = len(ns_obj.agents) if ns_obj else 0
        console.print(f"  [dim]{agent_count} agent(s) registered[/dim]")


@ns.command("delete")
@click.argument("name")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
@click.confirmation_option(prompt="Are you sure you want to delete this namespace?")
def ns_delete(name, project_root):
    """Delete a namespace."""
    registry = _get_registry(project_root)
    if registry.delete(name):
        console.print(f"[green]✓[/green] Namespace [bold]{name}[/bold] deleted")
    else:
        console.print(f"[red]Namespace '{name}' not found[/red]")


@ns.command("show")
@click.argument("name")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
def ns_show(name, project_root):
    """Show details of a namespace."""
    registry = _get_registry(project_root)
    namespace = registry.get(name)
    if not namespace:
        console.print(f"[red]Namespace '{name}' not found[/red]")
        return

    topo = namespace.get_topology()

    console.print(Panel(
        f"[bold]{topo['namespace']}[/bold]\n"
        f"[dim]{topo['description']}[/dim]\n\n"
        f"Agents: [cyan]{topo['stats']['agent_count']}[/cyan]  "
        f"Topics: [cyan]{topo['stats']['topic_count']}[/cyan]  "
        f"Connections: [cyan]{topo['stats']['pair_count']}[/cyan]",
        border_style="cyan",
        title="Namespace",
    ))

    if topo["agents"]:
        console.print()
        for agent in topo["agents"]:
            tree = Tree(f"[bold cyan]{agent['name']}[/bold cyan]")
            if agent["description"]:
                tree.add(f"[dim]{agent['description']}[/dim]")
            if agent["publishes"]:
                pub_branch = tree.add("[green]publishes →[/green]")
                for t in agent["publishes"]:
                    pub_branch.add(f"[green]{t}[/green]")
            if agent["subscribes"]:
                sub_branch = tree.add("[yellow]subscribes ←[/yellow]")
                for t in agent["subscribes"]:
                    sub_branch.add(f"[yellow]{t}[/yellow]")
            if agent["methods"]:
                meth_branch = tree.add("[blue]methods[/blue]")
                for m in agent["methods"]:
                    meth_branch.add(f"[blue]{m}()[/blue]")
            console.print(tree)

    if topo["communication_pairs"]:
        console.print()
        console.print("[bold]Communication Flow:[/bold]")
        for pair in topo["communication_pairs"]:
            console.print(
                f"  [cyan]{pair['publisher']}[/cyan] "
                f"→ [dim]{pair['topic']}[/dim] → "
                f"[cyan]{pair['subscriber']}[/cyan]"
            )


@ns.command("topology")
@click.argument("name", required=False)
@click.option("--all", "show_all", is_flag=True, help="Show all namespaces")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--project-root", "-p", default=".", type=click.Path(exists=True))
def ns_topology(name, show_all, as_json, project_root):
    """Visualize agent topology within a namespace.

    Shows the communication graph: which agents publish/subscribe to which topics.
    """
    registry = _get_registry(project_root)

    if as_json:
        if show_all:
            data = registry.export_all()
        elif name:
            namespace = registry.get(name)
            if not namespace:
                console.print(f"[red]Namespace '{name}' not found[/red]")
                return
            data = namespace.get_topology()
        else:
            data = registry.export_all()
        console.print_json(json.dumps(data, indent=2))
        return

    if show_all or not name:
        namespaces = registry.list_namespaces()
        if not namespaces:
            console.print("[dim]No namespaces. Create one with: graphbus ns create my-namespace[/dim]")
            return
        for ns_info in namespaces:
            ns_obj = registry.get(ns_info["name"])
            if ns_obj:
                _print_topology_tree(ns_obj)
                console.print()
    else:
        namespace = registry.get(name)
        if not namespace:
            console.print(f"[red]Namespace '{name}' not found[/red]")
            return
        _print_topology_tree(namespace)


def _print_topology_tree(namespace):
    """Print a tree visualization of namespace topology."""
    topo = namespace.get_topology()
    tree = Tree(
        f"[bold magenta]⬡ {topo['namespace']}[/bold magenta] "
        f"[dim]({topo['stats']['agent_count']} agents, {topo['stats']['topic_count']} topics)[/dim]"
    )

    for agent in topo["agents"]:
        agent_node = tree.add(f"[bold cyan]{agent['name']}[/bold cyan]")
        for t in agent.get("publishes", []):
            subscribers = [
                p["subscriber"] for p in topo["communication_pairs"]
                if p["topic"] == t
            ]
            sub_text = " → ".join(f"[yellow]{s}[/yellow]" for s in subscribers) if subscribers else "[dim]no subscribers[/dim]"
            agent_node.add(f"[green]↑ {t}[/green] → {sub_text}")

    console.print(tree)
