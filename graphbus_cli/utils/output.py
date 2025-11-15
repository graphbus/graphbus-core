"""
Output utilities for GraphBus CLI using Rich
"""

from typing import Any, Dict, List, Optional
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.syntax import Syntax
from rich.panel import Panel
from rich.tree import Tree

console = Console()


def print_success(message: str):
    """Print success message with green checkmark"""
    console.print(f"✓ {message}", style="bold green")


def print_error(message: str):
    """Print error message with red X"""
    console.print(f"✗ {message}", style="bold red")


def print_warning(message: str):
    """Print warning message with yellow triangle"""
    console.print(f"⚠ {message}", style="bold yellow")


def print_info(message: str):
    """Print info message with blue icon"""
    console.print(f"ℹ {message}", style="bold blue")


def print_table(data: List[Dict[str, Any]], headers: List[str], title: Optional[str] = None):
    """
    Print data as a formatted table

    Args:
        data: List of dictionaries with row data
        headers: List of column headers
        title: Optional table title
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")

    for header in headers:
        table.add_column(header)

    for row in data:
        table.add_row(*[str(row.get(h, "")) for h in headers])

    console.print(table)


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON string"""
    return json.dumps(data, indent=indent, default=str)


def print_json(data: Any, title: Optional[str] = None):
    """Print JSON with syntax highlighting"""
    json_str = format_json(data)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

    if title:
        console.print(Panel(syntax, title=title, border_style="cyan"))
    else:
        console.print(syntax)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def create_progress_bar():
    """Create a progress bar for long-running operations"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    )


def print_panel(content: str, title: Optional[str] = None, style: str = "cyan"):
    """Print content in a panel"""
    console.print(Panel(content, title=title, border_style=style))


def print_tree(root_name: str, tree_data: Dict[str, Any]) -> None:
    """
    Print hierarchical data as a tree

    Args:
        root_name: Name of root node
        tree_data: Dictionary representing tree structure
    """
    tree = Tree(f"[bold]{root_name}[/bold]")
    _build_tree(tree, tree_data)
    console.print(tree)


def _build_tree(tree: Tree, data: Dict[str, Any]) -> None:
    """Recursively build tree structure"""
    for key, value in data.items():
        if isinstance(value, dict):
            branch = tree.add(f"[cyan]{key}[/cyan]")
            _build_tree(branch, value)
        elif isinstance(value, list):
            branch = tree.add(f"[cyan]{key}[/cyan]")
            for item in value:
                if isinstance(item, dict):
                    _build_tree(branch, item)
                else:
                    branch.add(str(item))
        else:
            tree.add(f"[cyan]{key}[/cyan]: {value}")


def print_header(text: str):
    """Print section header"""
    console.print(f"\n[bold cyan]{text}[/bold cyan]")


def print_separator():
    """Print horizontal separator"""
    console.print("─" * console.width, style="dim")


def clear_screen():
    """Clear the terminal screen"""
    console.clear()
