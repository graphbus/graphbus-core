"""
Coherence tracking CLI commands
"""

import click
from pathlib import Path
from datetime import timedelta
from rich.table import Table
from rich.panel import Panel
import networkx as nx
from networkx.readwrite import json_graph
import json

from graphbus_core.runtime.coherence import CoherenceTracker
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_warning, print_info, print_json
)


@click.group()
def coherence():
    """Track and analyze long-form coherence"""
    pass


@coherence.command()
@click.option('--coherence-dir', default='.graphbus/coherence',
              help='Directory containing coherence data')
@click.option('--graph-dir', default='.graphbus',
              help='Directory containing dependency graph')
def check(coherence_dir: str, graph_dir: str):
    """
    Check system coherence score

    Example:
        graphbus coherence check
    """
    try:
        # Load graph
        graph = None
        graph_file = Path(graph_dir) / 'graph.json'
        if graph_file.exists():
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                graph = json_graph.node_link_graph(graph_data)

        tracker = CoherenceTracker(storage_path=coherence_dir, graph=graph)

        # Calculate metrics
        metrics = tracker.calculate_metrics()

        console.print()
        console.print(Panel.fit(
            f"[bold]Coherence Score:[/bold] {metrics.overall_score:.2%}\\n"
            f"[bold]Level:[/bold] {metrics.get_level().value.upper()}",
            title="System Coherence",
            border_style=_get_score_color(metrics.overall_score)
        ))

        console.print()
        table = Table(title="Coherence Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Status")

        metrics_list = [
            ("Schema Version Consistency", metrics.schema_version_consistency),
            ("Contract Compliance Rate", metrics.contract_compliance_rate),
            ("Migration Completion Rate", metrics.migration_completion_rate),
            ("Breaking Change Propagation", metrics.breaking_change_propagation),
            ("Temporal Consistency", metrics.temporal_consistency),
            ("Spatial Consistency", metrics.spatial_consistency),
        ]

        for name, score in metrics_list:
            status = _get_status_icon(score)
            color = _get_score_color(score)
            table.add_row(name, f"[{color}]{score:.1%}[/{color}]", status)

        console.print(table)

        # Show recommendations if score is low
        if metrics.overall_score < 0.7:
            console.print()
            print_warning("Coherence score is below recommended threshold (70%)")
            console.print("Run 'graphbus coherence report' for detailed analysis")

    except Exception as e:
        print_error(f"Failed to check coherence: {e}")
        raise click.Abort()


@coherence.command()
@click.option('--coherence-dir', default='.graphbus/coherence',
              help='Directory containing coherence data')
@click.option('--graph-dir', default='.graphbus',
              help='Directory containing dependency graph')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'html']),
              default='text', help='Output format')
@click.option('--output', '-o', help='Output file (stdout if not specified)')
def report(coherence_dir: str, graph_dir: str, format: str, output: str):
    """
    Generate detailed coherence report

    Example:
        graphbus coherence report
        graphbus coherence report --format html --output report.html
    """
    try:
        # Load graph
        graph = None
        graph_file = Path(graph_dir) / 'graph.json'
        if graph_file.exists():
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                graph = json_graph.node_link_graph(graph_data)

        tracker = CoherenceTracker(storage_path=coherence_dir, graph=graph)

        if not graph:
            print_warning("No dependency graph found - path analysis will be limited")

        console.print()
        console.print("[bold]Generating coherence report...[/bold]")

        # Analyze coherence paths
        try:
            report_data = tracker.analyze_coherence_paths()
        except ValueError as e:
            print_error(f"Cannot analyze paths: {e}")
            print_info("Run with --graph-dir to enable path analysis")
            return

        if format == 'json':
            report_dict = {
                'timestamp': report_data.timestamp.isoformat(),
                'overall_score': report_data.overall_score,
                'level': report_data.level.value,
                'metrics': {
                    'schema_version_consistency': report_data.metrics.schema_version_consistency,
                    'contract_compliance_rate': report_data.metrics.contract_compliance_rate,
                    'temporal_consistency': report_data.metrics.temporal_consistency,
                    'spatial_consistency': report_data.metrics.spatial_consistency,
                },
                'drift_warnings': len(report_data.drift_warnings),
                'incoherent_paths': len(report_data.incoherent_paths),
                'recommendations': len(report_data.recommendations)
            }

            if output:
                with open(output, 'w') as f:
                    json.dump(report_dict, f, indent=2)
                print_success(f"Report saved to {output}")
            else:
                print_json(report_dict)

        elif format == 'html':
            html_content = _generate_html_report(report_data)
            if output:
                with open(output, 'w') as f:
                    f.write(html_content)
                print_success(f"HTML report saved to {output}")
            else:
                console.print(html_content)

        else:  # text format
            _display_text_report(report_data)

    except Exception as e:
        print_error(f"Failed to generate report: {e}")
        raise click.Abort()


@coherence.command()
@click.option('--coherence-dir', default='.graphbus/coherence',
              help='Directory containing coherence data')
@click.option('--graph-dir', default='.graphbus',
              help='Directory containing dependency graph')
@click.option('--time-window', type=int, help='Check drift in last N hours')
def drift(coherence_dir: str, graph_dir: str, time_window: int):
    """
    Detect schema drift

    Example:
        graphbus coherence drift
        graphbus coherence drift --time-window 24
    """
    try:
        # Load graph
        graph = None
        graph_file = Path(graph_dir) / 'graph.json'
        if graph_file.exists():
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                graph = json_graph.node_link_graph(graph_data)

        tracker = CoherenceTracker(storage_path=coherence_dir, graph=graph)

        # Detect drift
        time_delta = timedelta(hours=time_window) if time_window else None
        warnings = tracker.detect_schema_drift(time_window=time_delta)

        if not warnings:
            print_success("No schema drift detected ✓")
            return

        console.print()
        print_warning(f"Detected {len(warnings)} drift warnings")
        console.print()

        table = Table(title="Schema Drift Warnings")
        table.add_column("Agent", style="cyan")
        table.add_column("Current Ver", style="red")
        table.add_column("Expected Ver", style="green")
        table.add_column("Severity", justify="right")
        table.add_column("Affected")
        table.add_column("First Detected")

        for warning in warnings:
            severity_color = "red" if warning.drift_severity > 0.3 else "yellow"
            table.add_row(
                warning.agent_name,
                warning.actual_version,
                warning.expected_version,
                f"[{severity_color}]{warning.drift_severity:.1%}[/{severity_color}]",
                str(warning.affected_interactions),
                warning.first_detected.strftime("%Y-%m-%d %H:%M")
            )

        console.print(table)

        console.print()
        print_info("Recommendations:")
        for warning in warnings[:3]:  # Show top 3
            console.print(f"  • Update {warning.agent_name} to {warning.expected_version}")

    except Exception as e:
        print_error(f"Failed to detect drift: {e}")
        raise click.Abort()


@coherence.command()
@click.option('--coherence-dir', default='.graphbus/coherence',
              help='Directory containing coherence data')
@click.option('--graph-dir', default='.graphbus',
              help='Directory containing dependency graph')
@click.option('--output', '-o', type=click.Path(), help='Output file for visualization')
def visualize(coherence_dir: str, graph_dir: str, output: str):
    """
    Visualize coherence graph (networkx)

    Example:
        graphbus coherence visualize
        graphbus coherence visualize --output coherence.png
    """
    try:
        # Load graph
        graph = None
        graph_file = Path(graph_dir) / 'graph.json'
        if graph_file.exists():
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                graph = json_graph.node_link_graph(graph_data)

        if not graph:
            print_error("No dependency graph found")
            print_info("Run 'graphbus build' first to generate dependency graph")
            raise click.Abort()

        tracker = CoherenceTracker(storage_path=coherence_dir, graph=graph)

        # Generate coherence graph
        coherence_graph = tracker.visualize_coherence()

        console.print()
        console.print(f"[bold]Coherence Graph:[/bold]")
        console.print(f"  Nodes: {len(coherence_graph.nodes())}")
        console.print(f"  Edges: {len(coherence_graph.edges())}")

        if output:
            try:
                import matplotlib.pyplot as plt
                import matplotlib

                # Draw graph
                pos = nx.spring_layout(coherence_graph)

                # Color edges by coherence score
                edge_colors = []
                for u, v in coherence_graph.edges():
                    edge_data = coherence_graph[u][v]
                    score = edge_data.get('coherence_score', 1.0)
                    edge_colors.append(score)

                plt.figure(figsize=(12, 8))
                nx.draw(
                    coherence_graph,
                    pos,
                    with_labels=True,
                    node_color='lightblue',
                    node_size=2000,
                    font_size=10,
                    font_weight='bold',
                    edge_color=edge_colors,
                    edge_cmap=plt.cm.RdYlGn,
                    edge_vmin=0,
                    edge_vmax=1,
                    width=2,
                    arrows=True,
                    arrowsize=20
                )

                plt.title("Agent Coherence Graph", fontsize=16, fontweight='bold')
                plt.colorbar(plt.cm.ScalarMappable(cmap=plt.cm.RdYlGn), label='Coherence Score')
                plt.tight_layout()
                plt.savefig(output, dpi=300, bbox_inches='tight')

                print_success(f"Visualization saved to {output}")

            except ImportError:
                print_error("matplotlib not installed")
                print_info("Install with: pip install matplotlib")
        else:
            # Print text representation
            console.print()
            for u, v in coherence_graph.edges():
                edge_data = coherence_graph[u][v]
                score = edge_data.get('coherence_score', 1.0)
                versions = edge_data.get('versions', set())
                count = edge_data.get('interaction_count', 0)

                score_color = _get_score_color(score)
                console.print(f"  [{score_color}]{u} → {v}[/{score_color}] "
                            f"(score: {score:.2f}, versions: {len(versions)}, count: {count})")

    except Exception as e:
        print_error(f"Failed to visualize coherence: {e}")
        raise click.Abort()


def _get_score_color(score: float) -> str:
    """Get color based on score"""
    if score >= 0.9:
        return "green"
    elif score >= 0.7:
        return "yellow"
    elif score >= 0.5:
        return "orange"
    else:
        return "red"


def _get_status_icon(score: float) -> str:
    """Get status icon based on score"""
    if score >= 0.9:
        return "[green]✓[/green]"
    elif score >= 0.7:
        return "[yellow]⚠[/yellow]"
    else:
        return "[red]✗[/red]"


def _display_text_report(report_data):
    """Display text format report"""
    console.print()
    console.print(Panel.fit(
        f"[bold]Coherence Report[/bold]\\n"
        f"Generated: {report_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\\n"
        f"Overall Score: {report_data.overall_score:.2%}\\n"
        f"Level: {report_data.level.value.upper()}",
        border_style=_get_score_color(report_data.overall_score)
    ))

    # Drift warnings
    if report_data.drift_warnings:
        console.print()
        console.print(f"[bold yellow]Schema Drift Warnings: {len(report_data.drift_warnings)}[/bold yellow]")
        for warning in report_data.drift_warnings[:5]:
            console.print(f"  • {warning.agent_name}: {warning.actual_version} → {warning.expected_version}")

    # Incoherent paths
    if report_data.incoherent_paths:
        console.print()
        console.print(f"[bold red]Incoherent Paths: {len(report_data.incoherent_paths)}[/bold red]")
        for path_issue in report_data.incoherent_paths[:3]:
            path_str = " → ".join(path_issue.path)
            console.print(f"  • {path_str} (score: {path_issue.coherence_score:.2f})")
            console.print(f"    Recommendation: {path_issue.recommendation}")

    # Recommendations
    if report_data.recommendations:
        console.print()
        console.print(f"[bold]Update Recommendations: {len(report_data.recommendations)}[/bold]")
        for rec in report_data.recommendations[:5]:
            priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(rec.priority, "white")
            console.print(f"  [{priority_color}]•[/{priority_color}] {rec.agent_name}: "
                        f"{rec.current_version} → {rec.recommended_version} ({rec.priority})")
            console.print(f"    Reason: {rec.reason}")


def _generate_html_report(report_data) -> str:
    """Generate HTML format report"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Coherence Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .score {{ font-size: 48px; font-weight: bold; }}
        .metric {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Coherence Report</h1>
    <p>Generated: {report_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="score">Overall Score: {report_data.overall_score:.2%}</div>
    <p>Level: {report_data.level.value.upper()}</p>

    <h2>Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Score</th>
        </tr>
        <tr>
            <td>Schema Version Consistency</td>
            <td>{report_data.metrics.schema_version_consistency:.1%}</td>
        </tr>
        <tr>
            <td>Contract Compliance Rate</td>
            <td>{report_data.metrics.contract_compliance_rate:.1%}</td>
        </tr>
        <tr>
            <td>Temporal Consistency</td>
            <td>{report_data.metrics.temporal_consistency:.1%}</td>
        </tr>
        <tr>
            <td>Spatial Consistency</td>
            <td>{report_data.metrics.spatial_consistency:.1%}</td>
        </tr>
    </table>

    <h2>Drift Warnings</h2>
    <p>Found {len(report_data.drift_warnings)} drift warnings</p>

    <h2>Incoherent Paths</h2>
    <p>Found {len(report_data.incoherent_paths)} incoherent paths</p>

    <h2>Recommendations</h2>
    <p>Generated {len(report_data.recommendations)} recommendations</p>

</body>
</html>
"""
    return html
