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
    Suggest actionable fixes for common GraphBus errors.

    Analyses the exception type and message to return a human-readable
    fix suggestion tailored to GraphBus usage patterns.

    Args:
        exc: The exception to analyse.

    Returns:
        A fix suggestion string, or ``None`` if no suggestion is available.

    Examples::

        >>> suggest_fix(FileNotFoundError("No such file: .graphbus/graph.json"))
        'Check that the path exists and is spelled correctly.'

        >>> suggest_fix(ImportError("No module named 'anthropic'"))
        "Ensure all dependencies are installed with 'pip install -r requirements.txt'."
    """
    error_msg = str(exc).lower()
    exc_type = type(exc)

    # ------------------------------------------------------------------ #
    # File / path errors                                                   #
    # ------------------------------------------------------------------ #
    if "no such file or directory" in error_msg or "does not exist" in error_msg:
        if ".graphbus" in error_msg or "artifacts" in error_msg or "graph.json" in error_msg:
            return (
                "Artifacts directory not found. Run 'graphbus build' first to generate "
                "the required build artifacts before starting the runtime."
            )
        return "Check that the path exists and is spelled correctly."

    # ------------------------------------------------------------------ #
    # Module / import errors                                               #
    # ------------------------------------------------------------------ #
    if "no module named" in error_msg or exc_type is ModuleNotFoundError:
        return "Ensure all dependencies are installed with 'pip install -r requirements.txt'."

    # ------------------------------------------------------------------ #
    # Permission errors                                                    #
    # ------------------------------------------------------------------ #
    if "permission denied" in error_msg or exc_type is PermissionError:
        return "Check file permissions or run with appropriate privileges."

    # ------------------------------------------------------------------ #
    # Authentication / API key errors                                      #
    # ------------------------------------------------------------------ #
    if (
        "api_key" in error_msg
        or "api key" in error_msg
        or "authentication" in error_msg
        or "unauthorized" in error_msg
        or "401" in error_msg
        or "anthropic_api_key" in error_msg
        or "openai_api_key" in error_msg
    ):
        return (
            "API key is missing or invalid. Set ANTHROPIC_API_KEY (or the relevant "
            "provider key) in your environment or in a .env file at the project root."
        )

    # ------------------------------------------------------------------ #
    # Network / connection errors                                          #
    # ------------------------------------------------------------------ #
    if "connection refused" in error_msg or "connection reset" in error_msg:
        return (
            "Connection refused. Check that any required services (e.g. Redis, "
            "GraphBus API server) are running and reachable."
        )

    if "timed out" in error_msg or "timeout" in error_msg:
        return (
            "Operation timed out. Check your network connection and ensure upstream "
            "services (LLM API, Redis) are responsive. Consider increasing the timeout "
            "via the GRAPHBUS_TIMEOUT environment variable."
        )

    if "address already in use" in error_msg or "port" in error_msg and "in use" in error_msg:
        return (
            "Port is already in use. Stop the existing process on that port, or specify "
            "a different port with --port."
        )

    # ------------------------------------------------------------------ #
    # Invalid JSON/YAML                                                    #
    # ------------------------------------------------------------------ #
    if "json" in error_msg or "yaml" in error_msg:
        return "Check that the file is valid JSON/YAML format."

    # ------------------------------------------------------------------ #
    # Type / value errors common in agent definitions                      #
    # ------------------------------------------------------------------ #
    if exc_type is TypeError and "argument" in error_msg:
        return (
            "Incorrect arguments passed to an agent method. Check the method signature "
            "and ensure all required parameters are provided with the correct types."
        )

    if exc_type is KeyError or "keyerror" in error_msg:
        key = str(exc).strip("'\"")
        return (
            f"Missing key {key!r} in configuration or payload. "
            "Verify your agent definition and topic schema are up-to-date."
        )

    # ------------------------------------------------------------------ #
    # Attribute errors (common in agent definitions)                       #
    # ------------------------------------------------------------------ #
    if "has no attribute" in error_msg:
        return "Verify that all required methods and attributes are defined in your agent class."

    # ------------------------------------------------------------------ #
    # Dependency cycles                                                    #
    # ------------------------------------------------------------------ #
    if "cycle" in error_msg or "circular" in error_msg:
        return (
            "Circular dependency detected between agents. Run 'graphbus inspect' to "
            "visualise the graph and remove the cycle."
        )

    # ------------------------------------------------------------------ #
    # Duplicate / name-collision errors                                    #
    # ------------------------------------------------------------------ #
    if "duplicate" in error_msg or "already exists" in error_msg or "already registered" in error_msg:
        return (
            "Duplicate name detected. Ensure each agent has a unique name in your "
            "project definition."
        )

    # ------------------------------------------------------------------ #
    # Schema / contract validation errors                                  #
    # ------------------------------------------------------------------ #
    if "schema" in error_msg or "contract" in error_msg or "breaking change" in error_msg:
        return (
            "Schema or contract validation failed. Run 'graphbus validate' to identify "
            "breaking changes and update consumer definitions accordingly."
        )

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
