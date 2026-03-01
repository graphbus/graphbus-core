"""
TUI Command - Launch interactive text-based UI
"""

import click
import sys


@click.command()
@click.option(
    '--theme',
    type=click.Choice(['dark', 'light']),
    default='dark',
    help='UI theme (default: dark)'
)
def tui(theme):
    """
    Launch GraphBus Text User Interface (TUI)

    An interactive terminal interface for GraphBus that provides visual
    access to all CLI commands through an intuitive menu-driven interface.

    \b
    Features:
    - Visual navigation with keyboard shortcuts
    - Interactive forms for all commands
    - Real-time output display
    - Tabbed interface for command categories
    - Built-in help system

    \b
    Keyboard Shortcuts:
      h - Home screen
      b - Build & Validate
      r - Runtime
      d - Dev Tools
      p - Deploy
      a - Advanced
      q - Quit
      ? - Help

    \b
    Examples:
      graphbus tui                  # Launch TUI with dark theme
      graphbus tui --theme light    # Launch with light theme

    Note: Requires 'textual' package. Install with:
      pip install textual
    """
    try:
        from graphbus_cli.tui.chat_app import ChatTUI
    except ImportError:
        click.echo(
            "❌ Error: The 'textual' package is required for TUI mode.\n\n"
            "Install it with:\n"
            "  pip install textual\n\n"
            "Or install graphbus with TUI support:\n"
            "  pip install graphbus[tui]",
            err=True
        )
        sys.exit(1)

    # Create and run the chat TUI app
    app = ChatTUI()
    if theme == 'light':
        app.theme = "textual-light"

    try:
        app.run()
    except KeyboardInterrupt:
        click.echo("\n👋 Goodbye!")
    except Exception as e:
        click.echo(f"❌ Error running TUI: {str(e)}", err=True)
        sys.exit(1)

def register(parser):
    """Register TUI command with CLI parser."""
    tui_parser = parser.add_parser('tui', help='Launch GraphBus TUI')
    tui_parser.add_argument('path', nargs='?', default='.', help='Project path')
    tui_parser.add_argument('--graphbus-dir', default='~/.graphbus', help='GraphBus home directory')
    tui_parser.set_defaults(func=main)
    return tui_parser
