"""
Validate command - Validate agent definitions
"""

import click
import sys
from pathlib import Path
import ast
import inspect

from graphbus_core.build.scanner import scan_modules, discover_node_classes
from graphbus_core.build.extractor import extract_agent_definitions
from graphbus_core.build.graph_builder import build_agent_graph, validate_graph_for_build
from graphbus_core.config import BuildConfig
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_warning, print_info,
    print_header
)
from graphbus_cli.utils.errors import ValidationError


@click.command()
@click.argument('agents_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--strict',
    is_flag=True,
    help='Enable strict validation'
)
@click.option(
    '--check-types',
    is_flag=True,
    help='Validate type annotations'
)
@click.option(
    '--check-cycles',
    is_flag=True,
    help='Check for dependency cycles'
)
def validate(agents_dir: str, strict: bool, check_types: bool, check_cycles: bool):
    """
    Validate agent definitions before building.

    \b
    Checks for common issues in agent definitions:
      - Decorator usage
      - Method signatures
      - Dependency cycles
      - Topic naming conventions

    \b
    Examples:
      graphbus validate agents/                # Basic validation
      graphbus validate agents/ --strict       # Strict mode
      graphbus validate agents/ --check-types  # Check type hints
      graphbus validate agents/ --check-cycles # Check cycles

    \b
    Exit Codes:
      0 - All checks passed
      3 - Validation failed
    """
    try:
        agents_path = Path(agents_dir).resolve()

        # Convert to module path
        parent_dir = agents_path.parent
        module_name = agents_path.name

        # Add to sys.path
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        print_header("GraphBus Agent Validator")
        print_info(f"Validating agents in: {agents_path}")
        print_info(f"Module: {module_name}")
        console.print()

        # Create config
        config = BuildConfig(root_package=module_name)

        # Track issues
        errors = []
        warnings = []

        # Stage 1: Scan modules
        console.print("[cyan]Scanning modules...[/cyan]")
        try:
            modules = scan_modules(config.root_package)
            print_success(f"Found {len(modules)} module(s)")
        except Exception as e:
            errors.append(f"Module scanning failed: {str(e)}")
            _print_validation_summary(errors, warnings)
            raise ValidationError("Validation failed")

        # Stage 2: Discover node classes
        console.print("\n[cyan]Discovering agent classes...[/cyan]")
        try:
            discovered_classes = discover_node_classes(modules)
            print_success(f"Found {len(discovered_classes)} agent class(es)")

            # Check decorator usage
            for cls, mod, source_file in discovered_classes:
                if not hasattr(cls, '_graphbus_agent'):
                    warnings.append(f"{cls.__name__}: Missing @agent() decorator")

        except Exception as e:
            errors.append(f"Class discovery failed: {str(e)}")

        # Stage 3: Extract agent definitions
        console.print("\n[cyan]Extracting agent metadata...[/cyan]")
        try:
            agent_defs = extract_agent_definitions(discovered_classes)
            print_success(f"Extracted {len(agent_defs)} agent definition(s)")

            # Validate agent definitions
            for agent_def in agent_defs:
                # Check for methods
                if hasattr(agent_def, 'methods'):
                    if not agent_def.methods and not agent_def.subscriptions:
                        warnings.append(f"{agent_def.name}: No methods or subscriptions defined")

                # Check subscriptions have handlers
                for sub in agent_def.subscriptions:
                    if not sub.handler_name:
                        errors.append(f"{agent_def.name}: Subscription to {sub.topic.name} missing handler")

                # Check type hints if requested
                if check_types:
                    if hasattr(agent_def, 'source_code') and agent_def.source_code:
                        type_warnings = _check_type_annotations(agent_def)
                        warnings.extend(type_warnings)

        except Exception as e:
            errors.append(f"Metadata extraction failed: {str(e)}")

        # Stage 4: Build and validate graph
        console.print("\n[cyan]Building dependency graph...[/cyan]")
        try:
            agent_graph = build_agent_graph(agent_defs)
            print_success(f"Graph: {len(agent_graph)} nodes, {agent_graph.graph.number_of_edges()} edges")

            # Validate graph
            graph_errors = validate_graph_for_build(agent_graph)
            if graph_errors:
                errors.extend([f"Graph validation: {err}" for err in graph_errors])
            else:
                print_success("Graph validation passed")

        except Exception as e:
            errors.append(f"Graph building failed: {str(e)}")

        # Stage 5: Check for cycles if requested
        if check_cycles:
            console.print("\n[cyan]Checking for dependency cycles...[/cyan]")
            try:
                # networkx will raise if there are cycles when getting topological order
                import networkx as nx
                cycles = list(nx.simple_cycles(agent_graph.graph))
                if cycles:
                    for cycle in cycles:
                        errors.append(f"Dependency cycle detected: {' → '.join(cycle)}")
                else:
                    print_success("No cycles detected")
            except Exception as e:
                warnings.append(f"Cycle detection: {str(e)}")

        # Stage 6: Additional strict checks
        if strict:
            console.print("\n[cyan]Running strict checks...[/cyan]")

            # Check topic naming conventions
            topics = set()
            for agent_def in agent_defs:
                for sub in agent_def.subscriptions:
                    topics.add(sub.topic.name)

            for topic in topics:
                if not topic.startswith('/'):
                    warnings.append(f"Topic '{topic}' should start with '/'")

            # Check for isolated agents
            for agent_def in agent_defs:
                if not agent_def.subscriptions and not agent_def.dependencies:
                    warnings.append(f"{agent_def.name}: Isolated agent (no subscriptions or dependencies)")

        # Print summary
        console.print()
        _print_validation_summary(errors, warnings)

        # Exit with appropriate code
        if errors:
            raise ValidationError(f"Validation failed with {len(errors)} error(s)")

    except ValidationError:
        raise
    except Exception as e:
        console.print()
        raise ValidationError(f"Validation failed: {str(e)}")


def _check_type_annotations(agent_def):
    """Check for type annotations in agent code"""
    warnings = []

    if not hasattr(agent_def, 'source_code') or not agent_def.source_code:
        return warnings

    try:
        tree = ast.parse(agent_def.source_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has type hints
                if node.name.startswith('on_'):  # Likely a handler
                    if not node.args.args or len(node.args.args) < 2:
                        continue

                    # Check for payload parameter type hint
                    payload_arg = node.args.args[1]  # self is first
                    if not payload_arg.annotation:
                        warnings.append(
                            f"{agent_def.name}.{node.name}: Missing type hint for parameter '{payload_arg.arg}'"
                        )

    except Exception:
        pass  # Ignore parsing errors

    return warnings


def _print_validation_summary(errors, warnings):
    """Print validation summary"""
    print_header("Validation Summary")

    if errors:
        console.print("[red]Errors:[/red]")
        for error in errors:
            print_error(error)
        console.print()

    if warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in warnings:
            print_warning(warning)
        console.print()

    # Final summary
    if not errors and not warnings:
        print_success("All checks passed! ✨")
        console.print(f"  [dim]No errors or warnings found[/dim]")
    else:
        console.print(f"[bold]Results:[/bold]")
        if errors:
            console.print(f"  [red]✗ {len(errors)} error(s)[/red]")
        else:
            console.print(f"  [green]✓ 0 errors[/green]")

        if warnings:
            console.print(f"  [yellow]⚠ {len(warnings)} warning(s)[/yellow]")
        else:
            console.print(f"  [dim]0 warnings[/dim]")

    console.print()
