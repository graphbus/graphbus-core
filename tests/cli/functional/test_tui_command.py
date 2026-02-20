"""
Tests for TUI Command
"""

import sys
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from graphbus_cli.main import cli


class TestTUICommand:
    """Test the TUI command."""

    def test_tui_missing_textual(self):
        """Test TUI command when textual / chat_app is not importable."""
        runner = CliRunner()

        # Simulate ImportError by blocking the chat_app module
        with patch.dict('sys.modules', {'graphbus_cli.tui.chat_app': None}):
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
        mock_chat_tui = MagicMock(return_value=mock_app)
        mock_module = MagicMock()
        mock_module.ChatTUI = mock_chat_tui

        with patch.dict('sys.modules', {'graphbus_cli.tui.chat_app': mock_module}):
            result = runner.invoke(cli, ['tui', '--theme', 'dark'])

        mock_app.run.assert_called_once()
        # Dark is default, so theme shouldn't change
        assert result.exit_code == 0

    def test_tui_with_light_theme(self):
        """Test TUI command with light theme."""
        runner = CliRunner()

        mock_app = MagicMock()
        mock_chat_tui = MagicMock(return_value=mock_app)
        mock_module = MagicMock()
        mock_module.ChatTUI = mock_chat_tui

        with patch.dict('sys.modules', {'graphbus_cli.tui.chat_app': mock_module}):
            result = runner.invoke(cli, ['tui', '--theme', 'light'])

        mock_app.run.assert_called_once()
        assert mock_app.theme == "textual-light"
        assert result.exit_code == 0

    def test_tui_keyboard_interrupt(self):
        """Test TUI handles keyboard interrupt gracefully."""
        runner = CliRunner()

        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_chat_tui = MagicMock(return_value=mock_app)
        mock_module = MagicMock()
        mock_module.ChatTUI = mock_chat_tui

        with patch.dict('sys.modules', {'graphbus_cli.tui.chat_app': mock_module}):
            result = runner.invoke(cli, ['tui'])

        assert "Goodbye" in result.output
        assert result.exit_code == 0

    def test_tui_runtime_error(self):
        """Test TUI handles runtime errors."""
        runner = CliRunner()

        mock_app = MagicMock()
        mock_app.run.side_effect = Exception("Test error")
        mock_chat_tui = MagicMock(return_value=mock_app)
        mock_module = MagicMock()
        mock_module.ChatTUI = mock_chat_tui

        with patch.dict('sys.modules', {'graphbus_cli.tui.chat_app': mock_module}):
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
    """Integration tests for TUI functionality — skipped if textual not installed."""

    @pytest.fixture(autouse=True)
    def skip_if_no_textual(self):
        pytest.importorskip("textual")
        pytest.importorskip("graphbus_cli.tui.chat_app")

    def test_tui_app_imports(self):
        """Test that TUI app can be imported."""
        from graphbus_cli.tui.chat_app import ChatTUI
        app = ChatTUI()

        assert app is not None

    def test_tui_screens_import(self):
        """Test that all TUI screens can be imported."""
        from graphbus_cli.tui.screens.home import HomeScreen
        from graphbus_cli.tui.screens.build import BuildScreen
        from graphbus_cli.tui.screens.runtime import RuntimeScreen
        from graphbus_cli.tui.screens.dev_tools import DevToolsScreen
        from graphbus_cli.tui.screens.deploy import DeployScreen
        from graphbus_cli.tui.screens.advanced import AdvancedScreen

        assert HomeScreen() is not None
        assert BuildScreen() is not None
        assert RuntimeScreen() is not None
        assert DevToolsScreen() is not None
        assert DeployScreen() is not None
        assert AdvancedScreen() is not None
