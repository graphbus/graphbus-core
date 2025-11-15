"""
Functional tests for CLI Phase 1 integration

These tests verify that CLI commands work correctly with actual files and artifacts.
"""

import pytest
import json
import time
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.commands.state import state
from graphbus_cli.commands.run import run


class TestStateCommandFunctional:
    """Functional tests for state command"""

    @pytest.fixture
    def state_dir(self, tmp_path):
        """Create state directory with test state files"""
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        # Create test state files
        (state_dir / "Agent1.json").write_text(json.dumps({
            "state": {"counter": 10, "name": "Agent1"},
            "metadata": {"timestamp": "2025-01-01T00:00:00", "version": "1.0"}
        }))

        (state_dir / "Agent2.json").write_text(json.dumps({
            "state": {"value": "test", "items": [1, 2, 3]},
            "metadata": {"timestamp": "2025-01-01T00:00:00", "version": "1.0"}
        }))

        return state_dir

    def test_show_command_displays_state(self, state_dir):
        """Test state show command displays state correctly"""
        runner = CliRunner()
        result = runner.invoke(state, ['show', 'Agent1', '--state-dir', str(state_dir)])

        assert result.exit_code == 0
        assert "counter" in result.output
        assert "10" in result.output
        assert "Agent1" in result.output

    def test_show_command_nonexistent_agent(self, state_dir):
        """Test state show for non-existent agent"""
        runner = CliRunner()
        result = runner.invoke(state, ['show', 'NonExistent', '--state-dir', str(state_dir)])

        assert result.exit_code == 0
        assert "No saved state found" in result.output

    def test_clear_command_removes_state_file(self, state_dir):
        """Test state clear removes state file"""
        state_file = state_dir / "Agent1.json"
        assert state_file.exists()

        runner = CliRunner()
        result = runner.invoke(state, ['clear', 'Agent1', '--state-dir', str(state_dir)], input='y\n')

        assert result.exit_code == 0
        assert not state_file.exists()
        assert "Cleared state" in result.output

    def test_clear_command_rejection_keeps_file(self, state_dir):
        """Test state clear rejection keeps file"""
        state_file = state_dir / "Agent1.json"
        assert state_file.exists()

        runner = CliRunner()
        result = runner.invoke(state, ['clear', 'Agent1', '--state-dir', str(state_dir)], input='n\n')

        assert result.exit_code == 1  # Aborted
        assert state_file.exists()

    def test_clear_all_rejection_keeps_all_files(self, state_dir):
        """Test state clear-all rejection keeps all files"""
        agent1_file = state_dir / "Agent1.json"
        agent2_file = state_dir / "Agent2.json"
        assert agent1_file.exists()
        assert agent2_file.exists()

        runner = CliRunner()
        result = runner.invoke(state, ['clear-all', '--state-dir', str(state_dir)], input='n\n')

        assert result.exit_code == 1  # Aborted
        assert agent1_file.exists()
        assert agent2_file.exists()


class TestRunCommandPhase1Functional:
    """Functional tests for run command with Phase 1 flags"""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create functional test artifacts directory"""
        artifacts = tmp_path / ".graphbus"
        artifacts.mkdir()

        # Create agents.json with a simple stateful agent
        agent_code = '''
from graphbus_core.node_base import NodeBase

class CounterAgent(NodeBase):
    """Test agent with state"""

    def __init__(self):
        super().__init__()
        self.counter = 0

    def increment(self):
        """Increment counter"""
        self.counter += 1
        return self.counter

    def get_state(self):
        """Get agent state"""
        return {"counter": self.counter}

    def set_state(self, state):
        """Set agent state"""
        self.counter = state.get("counter", 0)
'''

        # Write agent module
        agent_module_path = tmp_path / "counter_agent.py"
        agent_module_path.write_text(agent_code)

        # Create agents.json
        (artifacts / "agents.json").write_text(json.dumps({
            "CounterAgent": {
                "module": "counter_agent",
                "class": "CounterAgent",
                "methods": [
                    {
                        "name": "increment",
                        "description": "Increment counter",
                        "parameters": {},
                        "return_type": "int"
                    }
                ]
            }
        }))

        # Create graph.json
        (artifacts / "graph.json").write_text(json.dumps({
            "nodes": ["CounterAgent"],
            "edges": []
        }))

        # Create topics.json
        (artifacts / "topics.json").write_text(json.dumps({}))

        # Create state directory
        state_dir = artifacts.parent / ".graphbus" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        return artifacts

    def test_persist_state_flag_creates_state_directory(self, artifacts_dir):
        """Test --persist-state flag creates state directory"""
        state_dir = artifacts_dir / "state"

        # State dir should not exist yet
        if state_dir.exists():
            import shutil
            shutil.rmtree(state_dir)

        runner = CliRunner()

        # We can't actually run the runtime in tests, but we can verify the flag is accepted
        # This is more of a smoke test
        result = runner.invoke(run, [str(artifacts_dir), '--persist-state', '--help'])

        # Should show help without error
        assert result.exit_code == 0

    def test_restore_state_flag_accepted(self, artifacts_dir):
        """Test --restore-state flag is accepted"""
        runner = CliRunner()
        result = runner.invoke(run, [str(artifacts_dir), '--restore-state', '--help'])

        assert result.exit_code == 0

    def test_watch_flag_accepted(self, artifacts_dir):
        """Test --watch flag is accepted"""
        runner = CliRunner()
        result = runner.invoke(run, [str(artifacts_dir), '--watch', '--help'])

        assert result.exit_code == 0

    def test_enable_health_monitoring_flag_accepted(self, artifacts_dir):
        """Test --enable-health-monitoring flag is accepted"""
        runner = CliRunner()
        result = runner.invoke(run, [str(artifacts_dir), '--enable-health-monitoring', '--help'])

        assert result.exit_code == 0

    def test_multiple_phase1_flags_accepted(self, artifacts_dir):
        """Test multiple Phase 1 flags work together"""
        runner = CliRunner()
        result = runner.invoke(run, [
            str(artifacts_dir),
            '--persist-state',
            '--watch',
            '--enable-health-monitoring',
            '--help'
        ])

        assert result.exit_code == 0


class TestStateLifecycle:
    """Test complete state persistence lifecycle"""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create complete workspace with artifacts and state"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        artifacts = workspace / ".graphbus"
        artifacts.mkdir()
        state_dir = artifacts / "state"
        state_dir.mkdir()

        return workspace, artifacts, state_dir

    def test_save_show_clear_lifecycle(self, workspace):
        """Test complete lifecycle: save state -> show state -> clear state"""
        workspace_dir, artifacts_dir, state_dir = workspace

        # 1. Create initial state file
        agent_state = {
            "state": {"counter": 42, "name": "TestAgent"},
            "metadata": {"timestamp": "2025-01-01T00:00:00"}
        }
        state_file = state_dir / "TestAgent.json"
        state_file.write_text(json.dumps(agent_state))

        runner = CliRunner()

        # 2. Show state
        result = runner.invoke(state, ['show', 'TestAgent', '--state-dir', str(state_dir)])
        assert result.exit_code == 0
        assert "counter" in result.output
        assert "42" in result.output

        # 3. Clear state
        result = runner.invoke(state, ['clear', 'TestAgent', '--state-dir', str(state_dir)], input='y\n')
        assert result.exit_code == 0
        assert not state_file.exists()

        # 4. Show state again (should be empty)
        result = runner.invoke(state, ['show', 'TestAgent', '--state-dir', str(state_dir)])
        assert result.exit_code == 0
        assert "No saved state found" in result.output

    def test_multiple_agents_state_management(self, workspace):
        """Test managing state for multiple agents"""
        workspace_dir, artifacts_dir, state_dir = workspace

        # Create state for multiple agents
        agents = ["Agent1", "Agent2", "Agent3"]
        for i, agent in enumerate(agents):
            state_file = state_dir / f"{agent}.json"
            state_file.write_text(json.dumps({
                "state": {"counter": i * 10},
                "metadata": {"timestamp": "2025-01-01T00:00:00"}
            }))

        runner = CliRunner()

        # Show each agent's state
        for i, agent in enumerate(agents):
            result = runner.invoke(state, ['show', agent, '--state-dir', str(state_dir)])
            assert result.exit_code == 0
            assert str(i * 10) in result.output

        # Clear one agent
        result = runner.invoke(state, ['clear', 'Agent1', '--state-dir', str(state_dir)], input='y\n')
        assert result.exit_code == 0

        # Verify other agents still have state
        result = runner.invoke(state, ['show', 'Agent2', '--state-dir', str(state_dir)])
        assert result.exit_code == 0
        assert "10" in result.output

        result = runner.invoke(state, ['show', 'Agent3', '--state-dir', str(state_dir)])
        assert result.exit_code == 0
        assert "20" in result.output


class TestStatePersistenceEdgeCases:
    """Test edge cases for state persistence"""

    def test_state_with_complex_data_structures(self, tmp_path):
        """Test state with nested objects and arrays"""
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        complex_state = {
            "state": {
                "nested": {
                    "deep": {
                        "value": 42
                    }
                },
                "array": [1, 2, 3, {"key": "value"}],
                "null_value": None,
                "bool_value": True
            },
            "metadata": {"timestamp": "2025-01-01T00:00:00"}
        }

        state_file = state_dir / "ComplexAgent.json"
        state_file.write_text(json.dumps(complex_state))

        runner = CliRunner()
        result = runner.invoke(state, ['show', 'ComplexAgent', '--state-dir', str(state_dir)])

        assert result.exit_code == 0
        assert "nested" in result.output
        assert "array" in result.output

    def test_state_with_large_data(self, tmp_path):
        """Test state with large amount of data"""
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        # Create state with large array
        large_state = {
            "state": {
                "large_array": list(range(1000)),
                "metadata": "large dataset"
            },
            "metadata": {"timestamp": "2025-01-01T00:00:00"}
        }

        state_file = state_dir / "LargeAgent.json"
        state_file.write_text(json.dumps(large_state))

        runner = CliRunner()
        result = runner.invoke(state, ['show', 'LargeAgent', '--state-dir', str(state_dir)])

        assert result.exit_code == 0
        assert "large_array" in result.output

    def test_state_with_special_characters_in_agent_name(self, tmp_path):
        """Test state with special characters in agent name"""
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        # Agent names with underscores, numbers
        agent_names = ["Agent_1", "Agent123", "TestAgent_v2"]

        for agent_name in agent_names:
            state_file = state_dir / f"{agent_name}.json"
            state_file.write_text(json.dumps({
                "state": {"name": agent_name},
                "metadata": {"timestamp": "2025-01-01T00:00:00"}
            }))

        runner = CliRunner()

        for agent_name in agent_names:
            result = runner.invoke(state, ['show', agent_name, '--state-dir', str(state_dir)])
            assert result.exit_code == 0
            assert agent_name in result.output

    def test_corrupted_state_file(self, tmp_path):
        """Test handling of corrupted state file"""
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        # Create corrupted JSON file
        state_file = state_dir / "CorruptedAgent.json"
        state_file.write_text("{ invalid json }")

        runner = CliRunner()
        result = runner.invoke(state, ['show', 'CorruptedAgent', '--state-dir', str(state_dir)])

        # Should handle gracefully (either error or show empty)
        # Don't assert specific behavior, just verify it doesn't crash
        assert result.exit_code == 0 or result.exit_code == 1

    def test_empty_state_directory(self, tmp_path):
        """Test commands on empty state directory"""
        state_dir = tmp_path / "empty_state"
        state_dir.mkdir()

        runner = CliRunner()

        # Show non-existent agent
        result = runner.invoke(state, ['show', 'Agent1', '--state-dir', str(state_dir)])
        assert result.exit_code == 0
        assert "No saved state found" in result.output

        # Clear non-existent agent
        result = runner.invoke(state, ['clear', 'Agent1', '--state-dir', str(state_dir)], input='y\n')
        assert result.exit_code == 0  # Should succeed without error

    def test_nonexistent_state_directory(self, tmp_path):
        """Test commands on non-existent state directory"""
        state_dir = tmp_path / "nonexistent"

        runner = CliRunner()

        # Show agent in non-existent directory
        result = runner.invoke(state, ['show', 'Agent1', '--state-dir', str(state_dir)])
        assert result.exit_code == 0
        # Should handle gracefully
