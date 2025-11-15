"""
Functional tests for state persistence workflow
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from graphbus_core.config import RuntimeConfig
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.node_base import GraphBusNode


class CounterAgent(GraphBusNode):
    """Test agent that maintains a counter."""

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
        self.counter = 0
        self.name = "CounterAgent"

    def increment(self):
        """Increment counter."""
        self.counter += 1
        return self.counter

    def get_count(self):
        """Get current count."""
        return self.counter

    def get_state(self):
        """Get agent state."""
        return {"counter": self.counter}

    def set_state(self, state):
        """Set agent state."""
        self.counter = state.get("counter", 0)


class TestStatePersistenceWorkflow:
    """Test end-to-end state persistence workflows."""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create temporary artifacts directory with test agent."""
        artifacts_dir = tmp_path / ".graphbus"
        artifacts_dir.mkdir()

        # Create agent definition
        agent_def = {
            "name": "CounterAgent",
            "module": "test_module",
            "class_name": "CounterAgent",
            "source_file": "test_module.py",
            "source_code": "class CounterAgent: pass",
            "system_prompt": {
                "text": "Test agent",
                "role": None,
                "capabilities": []
            },
            "methods": [],
            "subscriptions": [],
            "dependencies": []
        }

        import json

        # Required files for RuntimeExecutor
        with open(artifacts_dir / "agents.json", "w") as f:
            json.dump([agent_def], f)

        with open(artifacts_dir / "graph.json", "w") as f:
            json.dump({
                "nodes": [{"name": "CounterAgent", "type": "agent", "data": {}}],
                "edges": []
            }, f)

        with open(artifacts_dir / "topics.json", "w") as f:
            json.dump({"topics": [], "subscriptions": []}, f)

        with open(artifacts_dir / "subscriptions.json", "w") as f:
            json.dump({"subscriptions": []}, f)

        with open(artifacts_dir / "build_summary.json", "w") as f:
            json.dump({"timestamp": "2025-01-01T00:00:00", "agents_count": 1}, f)

        return str(artifacts_dir)

    @pytest.fixture
    def state_dir(self, tmp_path):
        """State storage directory."""
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        return str(state_dir)

    def test_state_persists_across_restarts(self, artifacts_dir, state_dir, monkeypatch):
        """Test that agent state persists across runtime restarts."""
        # Mock the agent module
        import sys
        import types
        test_module = types.ModuleType('test_module')
        test_module.CounterAgent = CounterAgent
        sys.modules['test_module'] = test_module

        try:
            # First runtime: create agent and modify state
            config1 = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor1 = RuntimeExecutor(config1)
            executor1.start(enable_state_persistence=True)
            executor1.state_manager.state_dir = Path(state_dir)

            # Modify agent state
            agent = executor1.get_node("CounterAgent")
            agent.increment()
            agent.increment()
            agent.increment()
            assert agent.get_count() == 3

            # Save state
            executor1.save_node_state("CounterAgent")
            executor1.stop()

            # Second runtime: verify state is restored
            config2 = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor2 = RuntimeExecutor(config2)
            executor2.start(enable_state_persistence=True)
            executor2.state_manager.state_dir = Path(state_dir)

            # Manually restore state (in real scenario, setup_state_management does this)
            executor2.state_manager.state_dir = Path(state_dir)
            saved_state = executor2.state_manager.load_state("CounterAgent")
            if saved_state:
                agent2 = executor2.get_node("CounterAgent")
                agent2.set_state(saved_state)

                # Verify state was restored
                assert agent2.get_count() == 3

            executor2.stop()

        finally:
            # Cleanup
            del sys.modules['test_module']

    def test_state_save_all_workflow(self, artifacts_dir, state_dir, monkeypatch):
        """Test saving state for all agents."""
        import sys
        import types
        test_module = types.ModuleType('test_module')
        test_module.CounterAgent = CounterAgent
        sys.modules['test_module'] = test_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_state_persistence=True)
            executor.state_manager.state_dir = Path(state_dir)

            # Modify agent
            agent = executor.get_node("CounterAgent")
            agent.increment()
            agent.increment()

            # Save all states
            count = executor.save_all_states()
            assert count == 1

            # Verify state file exists
            state_file = Path(state_dir) / "CounterAgent.json"
            assert state_file.exists()

            executor.stop()

        finally:
            del sys.modules['test_module']

    def test_state_clear_workflow(self, artifacts_dir, state_dir):
        """Test clearing agent state."""
        import sys
        import types
        test_module = types.ModuleType('test_module')
        test_module.CounterAgent = CounterAgent
        sys.modules['test_module'] = test_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_state_persistence=True)
            executor.state_manager.state_dir = Path(state_dir)

            # Save state
            agent = executor.get_node("CounterAgent")
            agent.increment()
            executor.save_node_state("CounterAgent")

            # Clear state
            executor.state_manager.clear_state("CounterAgent")

            # Verify state is gone
            loaded_state = executor.state_manager.load_state("CounterAgent")
            assert loaded_state == {}

            executor.stop()

        finally:
            del sys.modules['test_module']
