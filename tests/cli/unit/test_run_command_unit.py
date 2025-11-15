"""
Unit tests for CLI run command Phase 1 flags
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from graphbus_cli.commands.run import run


class TestRunCommandPhase1Flags:
    """Test run command Phase 1 feature flags"""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create minimal artifacts directory"""
        artifacts = tmp_path / ".graphbus"
        artifacts.mkdir()

        # Create minimal artifacts
        (artifacts / "agents.json").write_text(json.dumps({
            "TestAgent": {
                "module": "test_agent",
                "class": "TestAgent",
                "methods": []
            }
        }))

        (artifacts / "graph.json").write_text(json.dumps({
            "nodes": ["TestAgent"],
            "edges": []
        }))

        (artifacts / "topics.json").write_text(json.dumps({}))

        return str(artifacts)

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_persist_state_flag_enables_state_persistence(self, mock_executor_class, artifacts_dir):
        """Test --persist-state flag enables state persistence"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        # Run with --persist-state flag and exit immediately
        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            # Make signal.pause() raise KeyboardInterrupt to exit
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--persist-state'])

        # Verify executor.start was called with enable_state_persistence=True
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_state_persistence'] is True
        assert call_kwargs['enable_hot_reload'] is False
        assert call_kwargs['enable_health_monitoring'] is False

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_restore_state_flag_enables_state_persistence(self, mock_executor_class, artifacts_dir):
        """Test --restore-state flag enables state persistence"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor.state_manager = None
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--restore-state'])

        # Verify executor.start was called with enable_state_persistence=True
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_state_persistence'] is True

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_restore_state_loads_saved_state(self, mock_executor_class, artifacts_dir):
        """Test --restore-state loads saved state for agents"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }

        # Mock agent with state
        mock_agent = Mock()
        mock_agent.set_state = Mock()
        mock_executor.get_node.return_value = mock_agent
        mock_executor.get_all_nodes.return_value = {"TestAgent": mock_agent}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": mock_agent}

        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.load_state.return_value = {"counter": 42}
        mock_executor.state_manager = mock_state_manager

        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--restore-state'])

        # Verify state was loaded and restored
        mock_state_manager.load_state.assert_called_once_with("TestAgent")
        mock_agent.set_state.assert_called_once_with({"counter": 42})

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_watch_flag_enables_hot_reload(self, mock_executor_class, artifacts_dir):
        """Test --watch flag enables hot reload"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--watch'])

        # Verify executor.start was called with enable_hot_reload=True
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_hot_reload'] is True
        assert call_kwargs['enable_state_persistence'] is False
        assert call_kwargs['enable_health_monitoring'] is False

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_enable_health_monitoring_flag(self, mock_executor_class, artifacts_dir):
        """Test --enable-health-monitoring flag enables health monitoring"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor.health_monitor = None
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--enable-health-monitoring'])

        # Verify executor.start was called with enable_health_monitoring=True
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_health_monitoring'] is True
        assert call_kwargs['enable_state_persistence'] is False
        assert call_kwargs['enable_hot_reload'] is False

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_multiple_phase1_flags_combined(self, mock_executor_class, artifacts_dir):
        """Test multiple Phase 1 flags can be combined"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor.state_manager = None
        mock_executor.health_monitor = None
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [
                artifacts_dir,
                '--persist-state',
                '--watch',
                '--enable-health-monitoring'
            ])

        # Verify all features were enabled
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_state_persistence'] is True
        assert call_kwargs['enable_hot_reload'] is True
        assert call_kwargs['enable_health_monitoring'] is True

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_persist_and_restore_state_combined(self, mock_executor_class, artifacts_dir):
        """Test --persist-state and --restore-state can be combined"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }

        mock_agent = Mock()
        mock_agent.set_state = Mock()
        mock_executor.get_node.return_value = mock_agent
        mock_executor.get_all_nodes.return_value = {"TestAgent": mock_agent}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": mock_agent}

        mock_state_manager = Mock()
        mock_state_manager.load_state.return_value = {"counter": 42}
        mock_executor.state_manager = mock_state_manager

        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [
                artifacts_dir,
                '--persist-state',
                '--restore-state'
            ])

        # Verify state persistence enabled and state was restored
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_state_persistence'] is True

        mock_state_manager.load_state.assert_called_once()
        mock_agent.set_state.assert_called_once()

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_no_phase1_flags_all_disabled(self, mock_executor_class, artifacts_dir):
        """Test running without Phase 1 flags keeps features disabled"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir])

        # Verify all Phase 1 features are disabled by default
        mock_executor.start.assert_called_once()
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_state_persistence'] is False
        assert call_kwargs['enable_hot_reload'] is False
        assert call_kwargs['enable_health_monitoring'] is False

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_restore_state_without_state_manager(self, mock_executor_class, artifacts_dir):
        """Test --restore-state gracefully handles missing state manager"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor.state_manager = None  # No state manager
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--restore-state'])

        # Should not crash, just skip state restoration
        assert result.exit_code == 0

    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_restore_state_with_agent_without_set_state(self, mock_executor_class, artifacts_dir):
        """Test --restore-state skips agents without set_state method"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }

        # Mock agent without set_state method
        mock_agent = Mock(spec=[])  # Empty spec, no set_state
        mock_executor.get_node.return_value = mock_agent
        mock_executor.get_all_nodes.return_value = {"TestAgent": mock_agent}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": mock_agent}

        mock_state_manager = Mock()
        mock_state_manager.load_state.return_value = {"counter": 42}
        mock_executor.state_manager = mock_state_manager

        mock_executor_class.return_value = mock_executor

        runner = CliRunner()

        with patch('graphbus_cli.commands.run.signal') as mock_signal:
            mock_signal.pause.side_effect = KeyboardInterrupt()

            result = runner.invoke(run, [artifacts_dir, '--restore-state'])

        # Should load state but not call set_state (doesn't exist)
        mock_state_manager.load_state.assert_called_once()
        assert not hasattr(mock_agent, 'set_state')


class TestRunCommandInteractiveMode:
    """Test run command interactive mode with Phase 1 features"""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create minimal artifacts directory"""
        artifacts = tmp_path / ".graphbus"
        artifacts.mkdir()

        (artifacts / "agents.json").write_text(json.dumps({
            "TestAgent": {
                "module": "test_agent",
                "class": "TestAgent",
                "methods": []
            }
        }))

        (artifacts / "graph.json").write_text(json.dumps({
            "nodes": ["TestAgent"],
            "edges": []
        }))

        (artifacts / "topics.json").write_text(json.dumps({}))

        return str(artifacts)

    @patch('graphbus_cli.repl.runtime_repl.start_repl')
    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_interactive_mode_with_watch_flag(self, mock_executor_class, mock_start_repl, artifacts_dir):
        """Test interactive mode with --watch flag"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()
        result = runner.invoke(run, [artifacts_dir, '--interactive', '--watch'])

        # Verify REPL was started with executor
        mock_start_repl.assert_called_once_with(mock_executor)

        # Verify hot reload was enabled
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_hot_reload'] is True

    @patch('graphbus_cli.repl.runtime_repl.start_repl')
    @patch('graphbus_cli.commands.run.RuntimeExecutor')
    def test_interactive_mode_with_health_monitoring(self, mock_executor_class, mock_start_repl, artifacts_dir):
        """Test interactive mode with --enable-health-monitoring flag"""
        mock_executor = Mock()
        mock_executor.get_stats.return_value = {
            'is_running': True,
            'nodes_count': 1
        }
        mock_executor.get_all_nodes.return_value = {"TestAgent": Mock()}
        mock_executor.bus = None
        mock_executor.nodes = {"TestAgent": Mock()}
        mock_executor.health_monitor = None
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()
        result = runner.invoke(run, [artifacts_dir, '--interactive', '--enable-health-monitoring'])

        # Verify REPL was started
        mock_start_repl.assert_called_once()

        # Verify health monitoring was enabled
        call_kwargs = mock_executor.start.call_args[1]
        assert call_kwargs['enable_health_monitoring'] is True
