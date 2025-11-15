"""
Functional tests for hot reload workflow
"""

import pytest
import tempfile
from pathlib import Path
import types
import sys
from unittest.mock import patch

from graphbus_core.config import RuntimeConfig
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.node_base import GraphBusNode


class DynamicAgent(GraphBusNode):
    """Test agent for hot reload testing."""

    VERSION = 1

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
        self.data = {}
        self.name = "DynamicAgent"

    def process(self, value):
        """Process a value (v1 implementation)."""
        return value * 2

    def get_state(self):
        """Get agent state."""
        return self.data.copy()

    def set_state(self, state):
        """Set agent state."""
        self.data = state.copy()


class DynamicAgentV2(GraphBusNode):
    """Updated version of DynamicAgent."""

    VERSION = 2

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
        self.data = {}
        self.name = "DynamicAgent"

    def process(self, value):
        """Process a value (v2 implementation - triple instead of double)."""
        return value * 3

    def get_state(self):
        """Get agent state."""
        return self.data.copy()

    def set_state(self, state):
        """Set agent state."""
        self.data = state.copy()


class TestHotReloadWorkflow:
    """Test end-to-end hot reload workflows."""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create temporary artifacts directory."""
        artifacts_dir = tmp_path / ".graphbus"
        artifacts_dir.mkdir()

        # Create agent definition
        agent_def = {
            "name": "DynamicAgent",
            "module": "dynamic_module",
            "class_name": "DynamicAgent",
            "source_file": "dynamic_module.py",
            "source_code": "class DynamicAgent: pass",
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
        with open(artifacts_dir / "agents.json", "w") as f:
            json.dump([agent_def], f)

        with open(artifacts_dir / "graph.json", "w") as f:
            json.dump({
                "nodes": [{"name": "DynamicAgent", "type": "agent", "data": {}}],
                "edges": []
            }, f)

        with open(artifacts_dir / "topics.json", "w") as f:
            json.dump({"topics": [], "subscriptions": []}, f)

        with open(artifacts_dir / "subscriptions.json", "w") as f:
            json.dump({"subscriptions": []}, f)

        with open(artifacts_dir / "build_summary.json", "w") as f:
            json.dump({"timestamp": "2025-01-01T00:00:00", "agents_count": 1}, f)

        return str(artifacts_dir)

    @patch('importlib.reload')
    def test_hot_reload_preserves_state(self, mock_reload, artifacts_dir):
        """Test that hot reload preserves agent state."""
        # Setup module with v1
        dynamic_module = types.ModuleType('dynamic_module')
        dynamic_module.DynamicAgent = DynamicAgent
        dynamic_module.__file__ = "dynamic_module.py"
        sys.modules['dynamic_module'] = dynamic_module

        # Mock reload to update the module with v2
        def reload_side_effect(module):
            if module is dynamic_module:
                module.DynamicAgent = DynamicAgentV2
            return module

        mock_reload.side_effect = reload_side_effect

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_hot_reload=True)

            # Set agent state
            agent = executor.get_node("DynamicAgent")
            agent.data = {"counter": 42, "name": "test"}

            # Verify v1 behavior
            assert agent.process(5) == 10
            assert agent.VERSION == 1

            # Hot reload with v2
            result = executor.hot_reload_manager.reload_agent("DynamicAgent", preserve_state=True)

            assert result["success"] is True
            assert result["state_preserved"] is True

            # Verify state was preserved
            agent_new = executor.get_node("DynamicAgent")
            assert agent_new.data == {"counter": 42, "name": "test"}

            # Verify v2 behavior
            assert agent_new.process(5) == 15
            assert agent_new.VERSION == 2

            executor.stop()

        finally:
            del sys.modules['dynamic_module']

    @patch('importlib.reload')
    def test_hot_reload_without_state_preservation(self, mock_reload, artifacts_dir):
        """Test hot reload without state preservation."""
        dynamic_module = types.ModuleType('dynamic_module')
        dynamic_module.DynamicAgent = DynamicAgent
        dynamic_module.__file__ = "dynamic_module.py"
        sys.modules['dynamic_module'] = dynamic_module

        # Mock reload to update the module with v2
        def reload_side_effect(module):
            if module is dynamic_module:
                module.DynamicAgent = DynamicAgentV2
            return module

        mock_reload.side_effect = reload_side_effect

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_hot_reload=True)

            # Set agent state
            agent = executor.get_node("DynamicAgent")
            agent.data = {"counter": 42}

            # Hot reload without preserving state
            result = executor.hot_reload_manager.reload_agent("DynamicAgent", preserve_state=False)

            assert result["success"] is True

            # Verify state was NOT preserved
            agent_new = executor.get_node("DynamicAgent")
            assert agent_new.data == {}

            executor.stop()

        finally:
            del sys.modules['dynamic_module']

    @patch('importlib.reload')
    def test_reload_all_agents_workflow(self, mock_reload, artifacts_dir):
        """Test reloading all agents at once."""
        dynamic_module = types.ModuleType('dynamic_module')
        dynamic_module.DynamicAgent = DynamicAgent
        dynamic_module.__file__ = "dynamic_module.py"
        sys.modules['dynamic_module'] = dynamic_module

        # Mock reload to update the module with v2
        def reload_side_effect(module):
            if module is dynamic_module:
                module.DynamicAgent = DynamicAgentV2
            return module

        mock_reload.side_effect = reload_side_effect

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_hot_reload=True)

            # Reload all
            result = executor.hot_reload_manager.reload_all_agents()

            assert result["total"] == 1
            assert result["succeeded"] == 1
            assert result["failed"] == 0

            # Verify update
            agent = executor.get_node("DynamicAgent")
            assert agent.VERSION == 2

            executor.stop()

        finally:
            del sys.modules['dynamic_module']

    @patch('importlib.reload')
    def test_reload_history_tracking(self, mock_reload, artifacts_dir):
        """Test that reload history is tracked."""
        dynamic_module = types.ModuleType('dynamic_module')
        dynamic_module.DynamicAgent = DynamicAgent
        dynamic_module.__file__ = "dynamic_module.py"
        sys.modules['dynamic_module'] = dynamic_module

        # Mock reload to alternate between v1 and v2
        reload_count = [0]

        def reload_side_effect(module):
            if module is dynamic_module:
                reload_count[0] += 1
                module.DynamicAgent = DynamicAgentV2 if reload_count[0] % 2 else DynamicAgent
            return module

        mock_reload.side_effect = reload_side_effect

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_hot_reload=True)

            # Perform multiple reloads
            for _ in range(3):
                executor.hot_reload_manager.reload_agent("DynamicAgent")

            # Check history
            history = executor.hot_reload_manager.get_reload_history()
            assert len(history) == 3

            # Check history for specific agent
            agent_history = executor.hot_reload_manager.get_reload_history(node_name="DynamicAgent")
            assert len(agent_history) == 3
            assert all(h["node_name"] == "DynamicAgent" for h in agent_history)

            executor.stop()

        finally:
            del sys.modules['dynamic_module']
