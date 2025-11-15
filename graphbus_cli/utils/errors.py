"""
Error handling utilities for GraphBus CLI
"""

import sys
import traceback
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel

console = Console()


class CLIError(Exception):
    """Base exception for CLI errors"""

    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class BuildError(CLIError):
    """Error during build process"""

    def __init__(self, message: str):
        super().__init__(message, exit_code=4)


class ValidationError(CLIError):
    """Error during validation"""

    def __init__(self, message: str):
        super().__init__(message, exit_code=3)


class RuntimeError(CLIError):
    """Error during runtime execution"""

    def __init__(self, message: str):
        super().__init__(message, exit_code=5)


def format_exception(exc: Exception, context: Optional[str] = None) -> str:
    """
    Format exception with context

    Args:
        exc: The exception to format
        context: Optional context about where error occurred

    Returns:
        Formatted error message
    """
    lines = []

    if context:
        lines.append(f"Error in {context}:")

    lines.append(f"{type(exc).__name__}: {str(exc)}")

    return "\n".join(lines)


def show_error(exc: Exception, context: Optional[str] = None, verbose: bool = False):
    """
    Display error message to user

    Args:
        exc: The exception to display
        context: Optional context about where error occurred
        verbose: Show full traceback if True
    """
    if verbose:
        # Show full traceback in verbose mode
        console.print_exception()
    else:
        # Show formatted error message
        error_msg = format_exception(exc, context)
        console.print(Panel(error_msg, title="Error", border_style="red"))

        # Show suggestion if available
        suggestion = suggest_fix(exc)
        if suggestion:
            console.print(f"\n💡 [cyan]Suggestion:[/cyan] {suggestion}")


def suggest_fix(exc: Exception) -> Optional[str]:
    """
    Suggest fixes for common errors

    Args:
        exc: The exception to analyze

    Returns:
        Suggestion string or None
    """
    error_msg = str(exc).lower()

    # File not found errors
    if "no such file or directory" in error_msg or "does not exist" in error_msg:
        return "Check that the path exists and is spelled correctly."

    # Module import errors
    if "no module named" in error_msg:
        return "Ensure all dependencies are installed with 'pip install -r requirements.txt'."

    # Permission errors
    if "permission denied" in error_msg:
        return "Check file permissions or run with appropriate privileges."

    # Invalid JSON/YAML
    if "json" in error_msg or "yaml" in error_msg:
        return "Check that the file is valid JSON/YAML format."

    # Attribute errors (common in agent definitions)
    if "has no attribute" in error_msg:
        return "Verify that all required methods and attributes are defined in your agent class."

    # Dependency cycle
    if "cycle" in error_msg or "circular" in error_msg:
        return "Remove circular dependencies between agents."

    return None


def show_file_context(filepath: Path, line_number: int, context_lines: int = 3):
    """
    Show file context around a specific line

    Args:
        filepath: Path to the file
        line_number: Line number to highlight
        context_lines: Number of lines to show before and after
    """
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        context = []
        for i in range(start, end):
            line_num = i + 1
            line = lines[i].rstrip()

            if line_num == line_number:
                context.append(f"→ {line_num:4d} | {line}")
            else:
                context.append(f"  {line_num:4d} | {line}")

        console.print(Panel(
            "\n".join(context),
            title=f"{filepath}:{line_number}",
            border_style="yellow"
        ))

    except Exception as e:
        console.print(f"Could not show file context: {e}", style="dim")


def handle_cli_error(exc: Exception, verbose: bool = False):
    """
    Handle CLI error and exit with appropriate code

    Args:
        exc: The exception to handle
        verbose: Show full traceback if True
    """
    if isinstance(exc, CLIError):
        show_error(exc, verbose=verbose)
        sys.exit(exc.exit_code)
    else:
        show_error(exc, verbose=verbose)
        sys.exit(1)
