"""
Unit tests for Runtime REPL
"""

import pytest
from unittest.mock import Mock, MagicMock
from io import StringIO

from graphbus_cli.repl.runtime_repl import RuntimeREPL
from graphbus_core.runtime.executor import RuntimeExecutor


class TestRuntimeREPL:
    """Tests for Runtime REPL commands"""

    @pytest.fixture
    def mock_executor(self):
        """Create mock executor"""
        executor = Mock(spec=RuntimeExecutor)
        executor.bus = Mock()
        executor.get_stats.return_value = {
            "is_running": True,
            "nodes_count": 4,
            "message_bus": {
                "messages_published": 10,
                "messages_delivered": 10
            }
        }
        executor.get_all_nodes.return_value = {
            "TestNode": Mock()
        }
        return executor

    @pytest.fixture
    def repl(self, mock_executor):
        """Create REPL instance"""
        return RuntimeREPL(mock_executor)

    def test_repl_initialization(self, mock_executor):
        """Test REPL initialization"""
        repl = RuntimeREPL(mock_executor)

        assert repl.executor == mock_executor
        assert repl.prompt == "[cyan]runtime>[/cyan] "

    def test_empty_line_does_nothing(self, repl):
        """Test that empty line doesn't cause error"""
        result = repl.emptyline()
        assert result is None

    def test_do_exit_returns_true(self, repl):
        """Test that exit command returns True to stop loop"""
        result = repl.do_exit("")
        assert result is True

    def test_do_quit_alias(self, repl):
        """Test that quit is alias for exit"""
        result = repl.do_quit("")
        assert result is True

    def test_do_stats_calls_get_stats(self, repl, mock_executor):
        """Test stats command calls executor.get_stats"""
        repl.do_stats("")

        mock_executor.get_stats.assert_called_once()

    def test_do_nodes_calls_get_all_nodes(self, repl, mock_executor):
        """Test nodes command calls executor.get_all_nodes"""
        repl.do_nodes("")

        mock_executor.get_all_nodes.assert_called_once()

    def test_do_topics_requires_message_bus(self, repl, mock_executor):
        """Test topics command when message bus is disabled"""
        # Disable message bus
        mock_executor.bus = None

        repl.do_topics("")

        # Should not crash, just show error

    def test_do_call_with_valid_method(self, repl, mock_executor):
        """Test calling a valid method"""
        mock_executor.call_method.return_value = {"result": "success"}

        repl.do_call("TestNode.test_method")

        mock_executor.call_method.assert_called_once_with(
            "TestNode",
            "test_method"
        )

    def test_do_call_with_json_args(self, repl, mock_executor):
        """Test calling method with JSON arguments"""
        mock_executor.call_method.return_value = {"result": "success"}

        repl.do_call('TestNode.test_method {"arg": "value"}')

        mock_executor.call_method.assert_called_once_with(
            "TestNode",
            "test_method",
            arg="value"
        )

    def test_do_call_invalid_format(self, repl, mock_executor):
        """Test calling with invalid format"""
        repl.do_call("InvalidFormat")

        # Should not call the method
        mock_executor.call_method.assert_not_called()

    def test_do_call_invalid_json(self, repl, mock_executor):
        """Test calling with invalid JSON args"""
        repl.do_call("TestNode.method {invalid json}")

        # Should not call the method
        mock_executor.call_method.assert_not_called()

    def test_do_publish_with_valid_event(self, repl, mock_executor):
        """Test publishing a valid event"""
        mock_executor.bus.get_stats.return_value = {}

        repl.do_publish('/test/topic {"data": "test"}')

        mock_executor.publish.assert_called_once_with(
            "/test/topic",
            {"data": "test"},
            source="repl"
        )

    def test_do_publish_without_message_bus(self, repl, mock_executor):
        """Test publish when message bus is disabled"""
        mock_executor.bus = None

        repl.do_publish('/test/topic {"data": "test"}')

        # Should not crash, just show error
        mock_executor.publish.assert_not_called()

    def test_do_publish_invalid_json(self, repl, mock_executor):
        """Test publish with invalid JSON"""
        repl.do_publish("/test/topic {invalid}")

        # Should not call publish
        mock_executor.publish.assert_not_called()

    def test_do_history_with_limit(self, repl, mock_executor):
        """Test history command with limit"""
        mock_event = Mock()
        mock_event.topic = "/test/topic"
        mock_event.src = "test"
        mock_event.payload = {"data": "test"}

        mock_executor.bus.get_message_history.return_value = [mock_event]

        repl.do_history("5")

        mock_executor.bus.get_message_history.assert_called_once_with(limit=5)

    def test_do_history_without_limit(self, repl, mock_executor):
        """Test history command without limit (default 10)"""
        mock_executor.bus.get_message_history.return_value = []

        repl.do_history("")

        mock_executor.bus.get_message_history.assert_called_once_with(limit=10)

    def test_do_history_invalid_limit(self, repl, mock_executor):
        """Test history with invalid limit"""
        repl.do_history("invalid")

        # Should not crash, just show error
        mock_executor.bus.get_message_history.assert_not_called()

    def test_do_history_without_message_bus(self, repl, mock_executor):
        """Test history when message bus is disabled"""
        mock_executor.bus = None

        repl.do_history("")

        # Should not crash, just show error

    def test_do_clear_command(self, repl):
        """Test cls command (clear screen)"""
        # Should not raise exception
        repl.do_cls("")

    def test_precmd_strips_whitespace(self, repl):
        """Test that precmd strips whitespace"""
        result = repl.precmd("  command  ")
        assert result == "command"

    def test_default_handles_unknown_command(self, repl):
        """Test handling of unknown commands"""
        # Should not raise exception
        repl.default("unknown_command")
