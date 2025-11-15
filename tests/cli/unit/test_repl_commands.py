"""
Unit tests for REPL reload and health commands
"""

import pytest
from unittest.mock import Mock, MagicMock
from io import StringIO

from graphbus_cli.repl.runtime_repl import RuntimeREPL


class TestReplReloadCommand:
    """Test REPL reload command"""

    @pytest.fixture
    def mock_executor(self):
        """Create mock executor with hot reload manager"""
        executor = Mock()
        executor.hot_reload_manager = Mock()
        executor.bus = Mock()
        executor.health_monitor = Mock()
        return executor

    @pytest.fixture
    def repl(self, mock_executor):
        """Create REPL instance"""
        return RuntimeREPL(mock_executor)

    def test_reload_command_success(self, repl, mock_executor):
        """Test successful reload of agent"""
        mock_executor.hot_reload_manager.reload_agent.return_value = {
            "success": True,
            "old_version": "1.0.0",
            "new_version": "1.0.1",
            "state_preserved": False
        }

        # Capture output
        repl.do_reload("TestAgent")

        # Verify reload was called
        mock_executor.hot_reload_manager.reload_agent.assert_called_once_with(
            "TestAgent",
            preserve_state=False
        )

    def test_reload_command_with_preserve_state(self, repl, mock_executor):
        """Test reload with --preserve-state flag"""
        mock_executor.hot_reload_manager.reload_agent.return_value = {
            "success": True,
            "old_version": "1.0.0",
            "new_version": "1.0.1",
            "state_preserved": True
        }

        repl.do_reload("TestAgent --preserve-state")

        # Verify preserve_state was set
        mock_executor.hot_reload_manager.reload_agent.assert_called_once_with(
            "TestAgent",
            preserve_state=True
        )

    def test_reload_command_failure(self, repl, mock_executor):
        """Test reload failure handling"""
        mock_executor.hot_reload_manager.reload_agent.return_value = {
            "success": False,
            "error": "Module not found"
        }

        repl.do_reload("NonExistentAgent")

        # Verify reload was attempted
        mock_executor.hot_reload_manager.reload_agent.assert_called_once()

    def test_reload_command_no_hot_reload_manager(self, repl, mock_executor):
        """Test reload when hot reload is not enabled"""
        mock_executor.hot_reload_manager = None

        repl.do_reload("TestAgent")

        # Should not crash, just show error message

    def test_reload_command_without_agent_name(self, repl, mock_executor):
        """Test reload command without agent name"""
        repl.do_reload("")

        # Should not call reload, just show usage
        mock_executor.hot_reload_manager.reload_agent.assert_not_called()

    def test_reload_command_exception(self, repl, mock_executor):
        """Test reload command with exception"""
        mock_executor.hot_reload_manager.reload_agent.side_effect = Exception("Test error")

        repl.do_reload("TestAgent")

        # Should not crash, just show error


class TestReplHealthCommand:
    """Test REPL health command"""

    @pytest.fixture
    def mock_executor(self):
        """Create mock executor with health monitor"""
        executor = Mock()
        executor.bus = Mock()
        executor.health_monitor = Mock()
        return executor

    @pytest.fixture
    def repl(self, mock_executor):
        """Create REPL instance"""
        return RuntimeREPL(mock_executor)

    @pytest.fixture
    def mock_metrics(self):
        """Create mock health metrics"""
        metrics = Mock()
        metrics.status = Mock()
        metrics.status.value = "healthy"
        metrics.total_calls = 100
        metrics.successful_calls = 95
        metrics.failed_calls = 5
        metrics.consecutive_failures = 0
        metrics.error_rate = 0.05
        metrics.success_rate = 0.95
        metrics.last_error = None
        return metrics

    def test_health_command_specific_agent(self, repl, mock_executor, mock_metrics):
        """Test health command for specific agent"""
        mock_executor.health_monitor.get_metrics.return_value = mock_metrics

        repl.do_health("TestAgent")

        # Verify metrics were fetched for specific agent
        mock_executor.health_monitor.get_metrics.assert_called_once_with("TestAgent")

    def test_health_command_all_agents(self, repl, mock_executor, mock_metrics):
        """Test health command without agent name shows all agents"""
        mock_executor.health_monitor.get_all_metrics.return_value = {
            "Agent1": mock_metrics,
            "Agent2": mock_metrics
        }

        repl.do_health("")

        # Verify all metrics were fetched
        mock_executor.health_monitor.get_all_metrics.assert_called_once()

    def test_health_command_no_health_monitor(self, repl, mock_executor):
        """Test health command when health monitoring not enabled"""
        mock_executor.health_monitor = None

        repl.do_health("TestAgent")

        # Should not crash, just show error message

    def test_health_command_agent_not_found(self, repl, mock_executor):
        """Test health command for non-existent agent"""
        mock_executor.health_monitor.get_metrics.return_value = None

        repl.do_health("NonExistentAgent")

        # Should show error message for missing agent
        mock_executor.health_monitor.get_metrics.assert_called_once()

    def test_health_command_with_last_error(self, repl, mock_executor, mock_metrics):
        """Test health command displays last error"""
        mock_metrics.last_error = "Connection timeout"
        mock_executor.health_monitor.get_metrics.return_value = mock_metrics

        repl.do_health("TestAgent")

        # Should display metrics including last error
        mock_executor.health_monitor.get_metrics.assert_called_once()

    def test_health_command_degraded_status(self, repl, mock_executor, mock_metrics):
        """Test health command with degraded status"""
        mock_metrics.status.value = "degraded"
        mock_metrics.error_rate = 0.15
        mock_metrics.success_rate = 0.85
        mock_executor.health_monitor.get_metrics.return_value = mock_metrics

        repl.do_health("TestAgent")

        # Should display degraded status
        mock_executor.health_monitor.get_metrics.assert_called_once()

    def test_health_command_failed_status(self, repl, mock_executor, mock_metrics):
        """Test health command with failed status"""
        mock_metrics.status.value = "failed"
        mock_metrics.consecutive_failures = 10
        mock_metrics.error_rate = 1.0
        mock_metrics.success_rate = 0.0
        mock_executor.health_monitor.get_metrics.return_value = mock_metrics

        repl.do_health("TestAgent")

        # Should display failed status
        mock_executor.health_monitor.get_metrics.assert_called_once()

    def test_health_command_exception(self, repl, mock_executor):
        """Test health command with exception"""
        mock_executor.health_monitor.get_metrics.side_effect = Exception("Test error")

        repl.do_health("TestAgent")

        # Should not crash, just show error


class TestReplOtherCommands:
    """Test other REPL commands work with Phase 1 features"""

    @pytest.fixture
    def mock_executor(self):
        """Create mock executor"""
        executor = Mock()
        executor.bus = Mock()
        executor.hot_reload_manager = Mock()
        executor.health_monitor = Mock()
        executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 2,
            'message_bus': {
                'messages_published': 10,
                'messages_delivered': 10
            }
        }
        executor.get_all_nodes.return_value = {
            "Agent1": Mock(),
            "Agent2": Mock()
        }
        return executor

    @pytest.fixture
    def repl(self, mock_executor):
        """Create REPL instance"""
        return RuntimeREPL(mock_executor)

    def test_stats_command(self, repl, mock_executor):
        """Test stats command works"""
        repl.do_stats("")

        # Verify stats were fetched
        mock_executor.get_stats.assert_called()

    def test_nodes_command(self, repl, mock_executor):
        """Test nodes command works"""
        repl.do_nodes("")

        # Verify nodes were fetched
        mock_executor.get_all_nodes.assert_called()

    def test_topics_command(self, repl, mock_executor):
        """Test topics command works with message bus"""
        mock_executor.bus.get_all_topics.return_value = ["/test/topic"]
        mock_executor.bus.get_subscribers.return_value = ["Agent1"]

        repl.do_topics("")

        # Verify topics were fetched
        mock_executor.bus.get_all_topics.assert_called()

    def test_topics_command_no_bus(self, repl, mock_executor):
        """Test topics command when bus is disabled"""
        mock_executor.bus = None

        repl.do_topics("")

        # Should show error message, not crash

    def test_call_command(self, repl, mock_executor):
        """Test call command works"""
        mock_executor.call_method.return_value = {"result": "success"}

        repl.do_call('Agent1.test_method {"arg": "value"}')

        # Verify method was called
        mock_executor.call_method.assert_called_once_with(
            "Agent1", "test_method", arg="value"
        )

    def test_publish_command(self, repl, mock_executor):
        """Test publish command works"""
        mock_executor.get_stats.return_value = {
            'message_bus': {'messages_delivered': 1}
        }

        repl.do_publish('/test/topic {"data": "test"}')

        # Verify event was published
        mock_executor.publish.assert_called_once_with(
            "/test/topic", {"data": "test"}, source="repl"
        )

    def test_publish_command_no_bus(self, repl, mock_executor):
        """Test publish command when bus is disabled"""
        mock_executor.bus = None

        repl.do_publish('/test/topic {"data": "test"}')

        # Should show error message, not crash
        mock_executor.publish.assert_not_called()

    def test_history_command(self, repl, mock_executor):
        """Test history command works"""
        mock_event = Mock()
        mock_event.topic = "/test/topic"
        mock_event.src = "Agent1"
        mock_event.payload = {"data": "test"}

        mock_executor.bus.get_message_history.return_value = [mock_event]

        repl.do_history("10")

        # Verify history was fetched
        mock_executor.bus.get_message_history.assert_called_once_with(limit=10)

    def test_history_command_no_bus(self, repl, mock_executor):
        """Test history command when bus is disabled"""
        mock_executor.bus = None

        repl.do_history("")

        # Should show error message, not crash

    def test_clear_command(self, repl, mock_executor):
        """Test cls command works (clear screen)"""
        # Just verify it doesn't crash
        repl.do_cls("")

    def test_help_command(self, repl, mock_executor):
        """Test help command shows all commands including reload and health"""
        # Just verify it doesn't crash
        repl.do_help("")

    def test_exit_command(self, repl, mock_executor):
        """Test exit command returns True"""
        result = repl.do_exit("")
        assert result is True

    def test_quit_command(self, repl, mock_executor):
        """Test quit command returns True"""
        result = repl.do_quit("")
        assert result is True
