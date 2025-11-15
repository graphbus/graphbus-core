"""
Profile command - Profile performance of agent graphs
"""

import click
import time
import sys
from pathlib import Path
from rich.table import Table

from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.config import RuntimeConfig
from graphbus_core.runtime.profiler import PerformanceProfiler
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, print_separator
)
from graphbus_cli.utils.errors import RuntimeError as CLIRuntimeError


@click.command()
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--duration',
    type=int,
    default=60,
    help='Profiling duration in seconds (default: 60)'
)
@click.option(
    '--output',
    type=click.Path(file_okay=True, dir_okay=False),
    help='Save report to file (supports .txt, .html, .json)'
)
@click.option(
    '--threshold',
    type=float,
    default=100.0,
    help='Bottleneck threshold in milliseconds (default: 100ms)'
)
@click.option(
    '--no-message-bus',
    is_flag=True,
    help='Disable message bus'
)
def profile(artifacts_dir: str, duration: int, output: str, threshold: float, no_message_bus: bool):
    """
    Profile performance of agent graph.

    \b
    Runs the agent graph with performance profiling enabled and generates
    a report showing:
      - Method execution times
      - Call frequencies
      - Performance bottlenecks
      - Event routing statistics

    \b
    Examples:
      graphbus profile .graphbus                    # Profile for 60 seconds
      graphbus profile .graphbus --duration 30      # Profile for 30 seconds
      graphbus profile .graphbus --output report.txt  # Save report to file
      graphbus profile .graphbus --threshold 50     # Flag methods >50ms

    \b
    Output Formats:
      .txt  - Plain text report
      .html - Interactive HTML flame graph with charts
      .json - JSON export for external tools

    \b
    Tips:
      - Start interactive REPL and call methods to generate activity
      - Use --duration to control profiling time
      - Use --threshold to tune bottleneck detection
    """
    artifacts_path = Path(artifacts_dir).resolve()
    executor = None
    profiler = PerformanceProfiler()

    try:
        # Add parent directory to Python path
        parent_dir = artifacts_path.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        # Display startup info
        print_header("GraphBus Performance Profiler")
        print_info(f"Loading artifacts from: {artifacts_path}")
        print_info(f"Profiling duration: {duration} seconds")
        console.print()

        # Create runtime config
        config = RuntimeConfig(
            artifacts_dir=str(artifacts_path),
            enable_message_bus=not no_message_bus
        )

        # Start runtime
        with console.status("[cyan]Starting runtime...[/cyan]", spinner="dots"):
            executor = RuntimeExecutor(config)
            executor.load_artifacts()
            executor.initialize_nodes()
            executor.setup_message_bus()

            # Enable profiler
            profiler.enable()

            # Wrap executor methods with profiling
            _wrap_executor_with_profiler(executor, profiler)

            executor._is_running = True

        console.print()
        print_success("Runtime started with profiling enabled")
        console.print()

        # Show status
        print_info(f"Profiling for {duration} seconds...")
        print_info("Waiting for activity (call methods or publish events)...")
        console.print()

        # Run for specified duration
        start_time = time.time()
        elapsed = 0
        last_update = 0

        while elapsed < duration:
            time.sleep(0.5)
            elapsed = time.time() - start_time

            # Show progress every 5 seconds
            if int(elapsed) % 5 == 0 and int(elapsed) != last_update:
                last_update = int(elapsed)
                summary = profiler.get_summary()
                console.print(
                    f"[dim]{int(elapsed)}s / {duration}s - "
                    f"{summary['total_method_calls']} calls, "
                    f"{summary['calls_per_second']:.1f} calls/sec[/dim]"
                )

        console.print()
        print_success("Profiling complete!")
        console.print()

        # Generate report
        _display_profile_report(profiler, threshold)

        # Save to file if requested
        if output:
            _save_profile_report(profiler, output, threshold)

        # Stop runtime
        if executor:
            executor.stop()

    except KeyboardInterrupt:
        console.print()
        print_info("Profiling interrupted")
        if executor:
            executor.stop()

        # Still show report
        console.print()
        _display_profile_report(profiler, threshold)

    except Exception as e:
        console.print()
        if executor:
            executor.stop()
        raise CLIRuntimeError(f"Profiling error: {str(e)}")


def _wrap_executor_with_profiler(executor: RuntimeExecutor, profiler: PerformanceProfiler) -> None:
    """Wrap executor methods to enable profiling"""
    original_call_method = executor.call_method

    def profiled_call_method(node_name: str, method_name: str, **kwargs):
        start_time = profiler.start_method_call(node_name, method_name)
        try:
            result = original_call_method(node_name, method_name, **kwargs)
            return result
        finally:
            profiler.end_method_call(node_name, method_name, start_time)

    executor.call_method = profiled_call_method


def _display_profile_report(profiler: PerformanceProfiler, threshold: float) -> None:
    """Display profile report in terminal"""
    print_header("Performance Profile Report")

    summary = profiler.get_summary()

    # Summary stats
    console.print(f"[cyan]Uptime:[/cyan] {summary['uptime_seconds']:.1f}s")
    console.print(f"[cyan]Total Calls:[/cyan] {summary['total_method_calls']}")
    console.print(f"[cyan]Execution Time:[/cyan] {summary['total_execution_time']:.3f}s")
    console.print(f"[cyan]Calls/Second:[/cyan] {summary['calls_per_second']:.1f}")
    console.print(f"[cyan]Unique Methods:[/cyan] {summary['unique_methods']}")
    console.print(f"[cyan]Unique Agents:[/cyan] {summary['unique_agents']}")
    console.print()

    # Top methods by total time
    top_time = profiler.get_top_methods_by_time(10)
    if top_time:
        print_header("Top Methods by Total Time")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Method", style="cyan")
        table.add_column("Total Time", justify="right")
        table.add_column("Calls", justify="right")
        table.add_column("Avg Time", justify="right")

        for profile in top_time:
            table.add_row(
                f"{profile.agent_name}.{profile.method_name}",
                f"{profile.total_time:.3f}s",
                str(profile.call_count),
                f"{profile.avg_time*1000:.1f}ms"
            )

        console.print(table)
        console.print()

    # Slowest methods
    slowest = profiler.get_slowest_methods(10)
    if slowest:
        print_header("Slowest Methods (by average)")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Method", style="cyan")
        table.add_column("Avg Time", justify="right")
        table.add_column("Max Time", justify="right")
        table.add_column("Calls", justify="right")

        for profile in slowest:
            table.add_row(
                f"{profile.agent_name}.{profile.method_name}",
                f"{profile.avg_time*1000:.1f}ms",
                f"{profile.max_time*1000:.1f}ms",
                str(profile.call_count)
            )

        console.print(table)
        console.print()

    # Bottlenecks
    bottlenecks = profiler.get_bottlenecks(threshold)
    if bottlenecks:
        print_header(f"⚠ Potential Bottlenecks (>{threshold}ms average)")

        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Method", style="yellow")
        table.add_column("Avg Time", justify="right")
        table.add_column("Max Time", justify="right")
        table.add_column("Calls", justify="right")

        for profile in bottlenecks:
            table.add_row(
                f"{profile.agent_name}.{profile.method_name}",
                f"{profile.avg_time*1000:.1f}ms",
                f"{profile.max_time*1000:.1f}ms",
                str(profile.call_count)
            )

        console.print(table)
        console.print()
    else:
        print_success(f"No bottlenecks detected (all methods <{threshold}ms)")
        console.print()


def _save_profile_report(profiler: PerformanceProfiler, output_path: str, threshold: float) -> None:
    """Save profile report to file"""
    output = Path(output_path)

    if output.suffix == '.txt':
        # Plain text report
        report = profiler.generate_report()
        output.write_text(report)
        print_success(f"Report saved to {output}")

    elif output.suffix == '.json':
        # JSON export
        import json

        data = {
            'summary': profiler.get_summary(),
            'top_methods_by_time': [
                {
                    'agent': p.agent_name,
                    'method': p.method_name,
                    'total_time': p.total_time,
                    'call_count': p.call_count,
                    'avg_time': p.avg_time,
                    'min_time': p.min_time,
                    'max_time': p.max_time
                }
                for p in profiler.get_top_methods_by_time(50)
            ],
            'slowest_methods': [
                {
                    'agent': p.agent_name,
                    'method': p.method_name,
                    'avg_time': p.avg_time,
                    'max_time': p.max_time,
                    'call_count': p.call_count
                }
                for p in profiler.get_slowest_methods(50)
            ],
            'bottlenecks': [
                {
                    'agent': p.agent_name,
                    'method': p.method_name,
                    'avg_time': p.avg_time,
                    'max_time': p.max_time,
                    'call_count': p.call_count
                }
                for p in profiler.get_bottlenecks(threshold)
            ]
        }

        output.write_text(json.dumps(data, indent=2))
        print_success(f"JSON report saved to {output}")

    elif output.suffix == '.html':
        # HTML flame graph report
        html = profiler.generate_flame_graph_html()
        output.write_text(html)
        print_success(f"HTML flame graph saved to {output}")
        print_info(f"Open {output} in your browser to view the interactive report")

    else:
        print_error(f"Unsupported output format: {output.suffix}")
        print_info("Supported formats: .txt, .json")
