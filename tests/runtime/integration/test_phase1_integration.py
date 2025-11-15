"""
Integration tests for Phase 1 features (State Persistence, Hot Reload, Health Monitoring)

These tests verify that all Phase 1 features work together correctly as an integrated system.
"""

import pytest
import types
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from graphbus_core.config import RuntimeConfig
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.runtime.health import HealthStatus
from graphbus_core.node_base import GraphBusNode


class StatefulAgent(GraphBusNode):
    """Test agent with state and configurable behavior."""

    VERSION = 1

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
        self.counter = 0
        self.total_processed = 0
        self.fail_after = None
        self.name = "StatefulAgent"

    def process(self, value):
        """Process a value with state tracking."""
        self.counter += 1
        self.total_processed += value

        if self.fail_after is not None and self.counter > self.fail_after:
            raise ValueError(f"Simulated failure after {self.fail_after} calls")

        return {
            "result": value * 2,
            "counter": self.counter,
            "total": self.total_processed
        }

    def get_state(self):
        """Get agent state."""
        return {
            "counter": self.counter,
            "total_processed": self.total_processed
        }

    def set_state(self, state):
        """Set agent state."""
        self.counter = state.get("counter", 0)
        self.total_processed = state.get("total_processed", 0)


class StatefulAgentV2(GraphBusNode):
    """Updated version with improved processing."""

    VERSION = 2

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
        self.counter = 0
        self.total_processed = 0
        self.fail_after = None
        self.name = "StatefulAgent"

    def process(self, value):
        """Process a value (v2: triple instead of double)."""
        self.counter += 1
        self.total_processed += value

        if self.fail_after is not None and self.counter > self.fail_after:
            raise ValueError(f"Simulated failure after {self.fail_after} calls")

        return {
            "result": value * 3,  # Changed from *2 to *3
            "counter": self.counter,
            "total": self.total_processed,
            "version": 2
        }

    def get_state(self):
        """Get agent state."""
        return {
            "counter": self.counter,
            "total_processed": self.total_processed
        }

    def set_state(self, state):
        """Set agent state."""
        self.counter = state.get("counter", 0)
        self.total_processed = state.get("total_processed", 0)


class TestPhase1Integration:
    """Integration tests for all Phase 1 features working together."""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create artifacts directory."""
        artifacts_dir = tmp_path / ".graphbus"
        artifacts_dir.mkdir()

        agent_def = {
            "name": "StatefulAgent",
            "module": "stateful_module",
            "class_name": "StatefulAgent",
            "source_file": "stateful_module.py",
            "source_code": "class StatefulAgent: pass",
            "system_prompt": {
                "text": "Stateful test agent",
                "role": None,
                "capabilities": []
            },
            "methods": [],
            "subscriptions": [],
            "dependencies": []
        }

        with open(artifacts_dir / "agents.json", "w") as f:
            json.dump([agent_def], f)

        with open(artifacts_dir / "graph.json", "w") as f:
            json.dump({
                "nodes": [{"name": "StatefulAgent", "type": "agent", "data": {}}],
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

    @patch('importlib.reload')
    def test_full_lifecycle_with_all_features(self, mock_reload, artifacts_dir, state_dir):
        """
        Test complete lifecycle: state persistence, hot reload with state preservation,
        health monitoring, and recovery.
        """
        # Setup module
        stateful_module = types.ModuleType('stateful_module')
        stateful_module.StatefulAgent = StatefulAgent
        stateful_module.__file__ = "stateful_module.py"
        sys.modules['stateful_module'] = stateful_module

        # Mock reload to update to v2
        def reload_side_effect(module):
            if module is stateful_module:
                module.StatefulAgent = StatefulAgentV2
            return module

        mock_reload.side_effect = reload_side_effect

        try:
            # Phase 1: Initial runtime with all features enabled
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(
                enable_state_persistence=True,
                enable_hot_reload=True,
                enable_health_monitoring=True
            )
            executor.state_manager.state_dir = Path(state_dir)

            # Process some data
            agent = executor.get_node("StatefulAgent")
            result1 = executor.call_method("StatefulAgent", "process", value=10)
            result2 = executor.call_method("StatefulAgent", "process", value=20)

            assert result1["result"] == 20  # 10 * 2
            assert result2["result"] == 40  # 20 * 2
            assert agent.counter == 2
            assert agent.total_processed == 30

            # Save state
            executor.save_node_state("StatefulAgent")

            # Health check - should be healthy
            status = executor.health_monitor.check_health("StatefulAgent")
            assert status == HealthStatus.HEALTHY

            # Phase 2: Hot reload with state preservation
            result = executor.hot_reload_manager.reload_agent("StatefulAgent", preserve_state=True)
            assert result["success"] is True
            assert result["state_preserved"] is True

            # Verify state was preserved and version updated
            agent_v2 = executor.get_node("StatefulAgent")
            assert agent_v2.counter == 2  # Preserved
            assert agent_v2.total_processed == 30  # Preserved
            assert agent_v2.VERSION == 2

            # Process with new version
            result3 = executor.call_method("StatefulAgent", "process", value=10)
            assert result3["result"] == 30  # 10 * 3 (v2 behavior)
            assert result3["version"] == 2
            assert agent_v2.counter == 3

            # Phase 3: Trigger failures and test health monitoring
            agent_v2.fail_after = 3

            failures = 0
            for _ in range(5):
                try:
                    executor.call_method("StatefulAgent", "process", value=5)
                except ValueError:
                    failures += 1

            assert failures > 0

            # Check health status degraded
            metrics = executor.health_monitor.get_metrics("StatefulAgent")
            assert metrics.failed_calls > 0
            assert metrics.status in (HealthStatus.DEGRADED, HealthStatus.FAILED)

            # Phase 4: Recovery
            agent_v2.fail_after = None  # Disable failures

            # Process successfully to recover
            for _ in range(10):
                executor.call_method("StatefulAgent", "process", value=1)

            # Should be recovering
            metrics = executor.health_monitor.get_metrics("StatefulAgent")
            assert metrics.error_rate < 0.5  # Improving

            # Save final state
            executor.save_node_state("StatefulAgent")
            executor.stop()

            # Phase 5: Restart and verify state persistence
            executor2 = RuntimeExecutor(config)
            executor2.start(enable_state_persistence=True)
            executor2.state_manager.state_dir = Path(state_dir)

            # Load saved state
            saved_state = executor2.state_manager.load_state("StatefulAgent")
            assert saved_state is not None

            agent_restored = executor2.get_node("StatefulAgent")
            agent_restored.set_state(saved_state)

            # Verify state persisted across restart
            assert agent_restored.counter > 0
            assert agent_restored.total_processed > 0

            executor2.stop()

        finally:
            del sys.modules['stateful_module']

    @patch('importlib.reload')
    def test_auto_restart_on_failure_with_state(self, mock_reload, artifacts_dir, state_dir):
        """
        Test that auto-restart preserves state when recovering from failures.
        """
        stateful_module = types.ModuleType('stateful_module')
        stateful_module.StatefulAgent = StatefulAgent
        stateful_module.__file__ = "stateful_module.py"
        sys.modules['stateful_module'] = stateful_module

        # Mock reload
        def reload_side_effect(module):
            if module is stateful_module:
                # Reset the agent to healthy version
                module.StatefulAgent = StatefulAgent
            return module

        mock_reload.side_effect = reload_side_effect

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(
                enable_state_persistence=True,
                enable_hot_reload=True,
                enable_health_monitoring=True
            )
            executor.state_manager.state_dir = Path(state_dir)

            # Enable auto-restart
            executor.health_monitor.enable_auto_restart = True

            # Build up state
            for i in range(5):
                executor.call_method("StatefulAgent", "process", value=i)

            agent = executor.get_node("StatefulAgent")
            initial_counter = agent.counter
            assert initial_counter == 5

            # Save state
            executor.save_node_state("StatefulAgent")

            # Trigger failures
            agent.fail_after = 5

            for _ in range(10):
                try:
                    executor.call_method("StatefulAgent", "process", value=1)
                except ValueError:
                    pass

            # Check that restart was attempted
            history = executor.hot_reload_manager.get_reload_history()
            assert len(history) > 0

            # Agent should still have state (auto-restart preserves it)
            agent_after = executor.get_node("StatefulAgent")
            # State should be preserved or loaded from disk
            assert agent_after.counter >= initial_counter

            executor.stop()

        finally:
            del sys.modules['stateful_module']

    def test_state_persistence_across_multiple_hot_reloads(self, artifacts_dir, state_dir):
        """
        Test that state persists correctly through multiple hot reload cycles.
        """
        stateful_module = types.ModuleType('stateful_module')
        stateful_module.StatefulAgent = StatefulAgent
        stateful_module.__file__ = "stateful_module.py"
        sys.modules['stateful_module'] = stateful_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(
                enable_state_persistence=True,
                enable_hot_reload=True
            )
            executor.state_manager.state_dir = Path(state_dir)

            # Initial state
            executor.call_method("StatefulAgent", "process", value=10)
            agent = executor.get_node("StatefulAgent")
            assert agent.counter == 1

            # Multiple reload cycles with state persistence
            with patch('importlib.reload') as mock_reload:
                mock_reload.return_value = stateful_module

                for i in range(3):
                    # Process some data
                    executor.call_method("StatefulAgent", "process", value=5)

                    # Save state
                    executor.save_node_state("StatefulAgent")

                    # Hot reload with state preservation
                    result = executor.hot_reload_manager.reload_agent(
                        "StatefulAgent",
                        preserve_state=True
                    )
                    assert result["success"] is True
                    assert result["state_preserved"] is True

                    # Verify state preserved
                    agent = executor.get_node("StatefulAgent")
                    expected_counter = 2 + i
                    assert agent.counter == expected_counter

            executor.stop()

        finally:
            del sys.modules['stateful_module']

    def test_health_monitoring_metrics_across_hot_reload(self, artifacts_dir):
        """
        Test that health metrics are preserved/reset appropriately during hot reload.
        """
        stateful_module = types.ModuleType('stateful_module')
        stateful_module.StatefulAgent = StatefulAgent
        stateful_module.__file__ = "stateful_module.py"
        sys.modules['stateful_module'] = stateful_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(
                enable_hot_reload=True,
                enable_health_monitoring=True
            )

            # Generate some metrics
            for i in range(10):
                executor.call_method("StatefulAgent", "process", value=i)

            metrics_before = executor.health_monitor.get_metrics("StatefulAgent")
            assert metrics_before.total_calls == 10
            assert metrics_before.successful_calls == 10

            # Hot reload
            with patch('importlib.reload') as mock_reload:
                mock_reload.return_value = stateful_module

                result = executor.hot_reload_manager.reload_agent("StatefulAgent")
                assert result["success"] is True

            # Metrics should still be tracked after reload
            metrics_after = executor.health_monitor.get_metrics("StatefulAgent")
            assert metrics_after is not None
            assert metrics_after.total_calls == 10  # Preserved

            # New calls should continue tracking
            executor.call_method("StatefulAgent", "process", value=1)

            metrics_final = executor.health_monitor.get_metrics("StatefulAgent")
            assert metrics_final.total_calls == 11

            executor.stop()

        finally:
            del sys.modules['stateful_module']
