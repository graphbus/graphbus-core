"""
Tests for TUI Command
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from graphbus_cli.main import cli


class TestTUICommand:
    """Test the TUI command."""

    def test_tui_missing_textual(self):
        """Test TUI command when textual is not installed."""
        runner = CliRunner()

        with patch('graphbus_cli.commands.tui.GraphBusTUI', side_effect=ImportError):
            result = runner.invoke(cli, ['tui'])

            assert result.exit_code == 1
            assert "textual" in result.output.lower()
            assert "pip install textual" in result.output

    def test_tui_help(self):
        """Test TUI command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['tui', '--help'])

        assert result.exit_code == 0
        assert "Text User Interface" in result.output
        assert "keyboard shortcuts" in result.output.lower()
        assert "--theme" in result.output

    def test_tui_with_dark_theme(self):
        """Test TUI command with dark theme."""
        runner = CliRunner()

        mock_app = MagicMock()
        with patch('graphbus_cli.commands.tui.GraphBusTUI', return_value=mock_app):
            result = runner.invoke(cli, ['tui', '--theme', 'dark'])

            mock_app.run.assert_called_once()
            # Dark is default, so theme shouldn't change
            assert result.exit_code == 0

    def test_tui_with_light_theme(self):
        """Test TUI command with light theme."""
        runner = CliRunner()

        mock_app = MagicMock()
        with patch('graphbus_cli.commands.tui.GraphBusTUI', return_value=mock_app):
            result = runner.invoke(cli, ['tui', '--theme', 'light'])

            mock_app.run.assert_called_once()
            assert mock_app.theme == "textual-light"
            assert result.exit_code == 0

    def test_tui_keyboard_interrupt(self):
        """Test TUI handles keyboard interrupt gracefully."""
        runner = CliRunner()

        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()

        with patch('graphbus_cli.commands.tui.GraphBusTUI', return_value=mock_app):
            result = runner.invoke(cli, ['tui'])

            assert "Goodbye" in result.output
            assert result.exit_code == 0

    def test_tui_runtime_error(self):
        """Test TUI handles runtime errors."""
        runner = CliRunner()

        mock_app = MagicMock()
        mock_app.run.side_effect = Exception("Test error")

        with patch('graphbus_cli.commands.tui.GraphBusTUI', return_value=mock_app):
            result = runner.invoke(cli, ['tui'])

            assert "Error running TUI" in result.output
            assert "Test error" in result.output
            assert result.exit_code == 1

    def test_tui_invalid_theme(self):
        """Test TUI with invalid theme."""
        runner = CliRunner()
        result = runner.invoke(cli, ['tui', '--theme', 'invalid'])

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid" in result.output.lower()


class TestTUIIntegration:
    """Integration tests for TUI functionality."""

    @pytest.mark.skipif(
        not pytest.importorskip("textual", minversion="0.47.0"),
        reason="textual not installed"
    )
    def test_tui_app_imports(self):
        """Test that TUI app can be imported."""
        from graphbus_cli.tui.app import GraphBusTUI
        app = GraphBusTUI()

        assert app is not None
        assert hasattr(app, 'BINDINGS')
        assert hasattr(app, 'compose')

    @pytest.mark.skipif(
        not pytest.importorskip("textual", minversion="0.47.0"),
        reason="textual not installed"
    )
    def test_tui_screens_import(self):
        """Test that all TUI screens can be imported."""
        from graphbus_cli.tui.screens.home import HomeScreen
        from graphbus_cli.tui.screens.build import BuildScreen
        from graphbus_cli.tui.screens.runtime import RuntimeScreen
        from graphbus_cli.tui.screens.dev_tools import DevToolsScreen
        from graphbus_cli.tui.screens.deploy import DeployScreen
        from graphbus_cli.tui.screens.advanced import AdvancedScreen

        # Test screen instantiation
        assert HomeScreen() is not None
        assert BuildScreen() is not None
        assert RuntimeScreen() is not None
        assert DevToolsScreen() is not None
        assert DeployScreen() is not None
        assert AdvancedScreen() is not None

    @pytest.mark.skipif(
        not pytest.importorskip("textual", minversion="0.47.0"),
        reason="textual not installed"
    )
    def test_tui_app_bindings(self):
        """Test TUI app keyboard bindings."""
        from graphbus_cli.tui.app import GraphBusTUI

        app = GraphBusTUI()

        # Check bindings exist
        binding_keys = [b.key for b in app.BINDINGS]
        assert 'q' in binding_keys  # Quit
        assert 'h' in binding_keys  # Home
        assert 'b' in binding_keys  # Build
        assert 'r' in binding_keys  # Runtime
        assert 'd' in binding_keys  # Dev Tools
        assert 'p' in binding_keys  # Deploy
        assert 'a' in binding_keys  # Advanced

    @pytest.mark.skipif(
        not pytest.importorskip("textual", minversion="0.47.0"),
        reason="textual not installed"
    )
    def test_home_screen_widgets(self):
        """Test home screen has expected widgets."""
        from graphbus_cli.tui.screens.home import HomeScreen

        screen = HomeScreen()

        # Screen should have compose method
        assert hasattr(screen, 'compose')
        assert callable(screen.compose)

        # Screen should have button handler
        assert hasattr(screen, 'on_button_pressed')
        assert callable(screen.on_button_pressed)

    @pytest.mark.skipif(
        not pytest.importorskip("textual", minversion="0.47.0"),
        reason="textual not installed"
    )
    def test_build_screen_command_execution(self):
        """Test build screen can execute commands."""
        from graphbus_cli.tui.screens.build import BuildScreen

        screen = BuildScreen()

        # Screen should have run_command method
        assert hasattr(screen, 'run_command')
        assert callable(screen.run_command)

        # Screen should have command methods
        assert hasattr(screen, 'run_build_command')
        assert hasattr(screen, 'run_validate_command')
        assert hasattr(screen, 'run_inspect_command')
