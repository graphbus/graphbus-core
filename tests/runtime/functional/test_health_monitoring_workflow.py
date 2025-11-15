"""
Functional tests for health monitoring workflow
"""

import pytest
import types
import sys
from unittest.mock import Mock, patch

from graphbus_core.config import RuntimeConfig
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.runtime.health import HealthStatus, RestartPolicy
from graphbus_core.node_base import GraphBusNode


class UnreliableAgent(GraphBusNode):
    """Test agent that can fail predictably."""

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
        self.call_count = 0
        self.fail_after = None
        self.name = "UnreliableAgent"

    def process(self, value):
        """Process with potential failure."""
        self.call_count += 1
        if self.fail_after and self.call_count > self.fail_after:
            raise ValueError(f"Simulated failure after {self.fail_after} calls")
        return value * 2

    def reset_failures(self):
        """Reset failure condition."""
        self.call_count = 0
        self.fail_after = None


class TestHealthMonitoringWorkflow:
    """Test end-to-end health monitoring workflows."""

    @pytest.fixture
    def artifacts_dir(self, tmp_path):
        """Create temporary artifacts directory."""
        artifacts_dir = tmp_path / ".graphbus"
        artifacts_dir.mkdir()

        agent_def = {
            "name": "UnreliableAgent",
            "module": "unreliable_module",
            "class_name": "UnreliableAgent",
            "source_file": "unreliable_module.py",
            "source_code": "class UnreliableAgent: pass",
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
                "nodes": [{"name": "UnreliableAgent", "type": "agent", "data": {}}],
                "edges": []
            }, f)

        with open(artifacts_dir / "topics.json", "w") as f:
            json.dump({"topics": [], "subscriptions": []}, f)

        with open(artifacts_dir / "subscriptions.json", "w") as f:
            json.dump({"subscriptions": []}, f)

        with open(artifacts_dir / "build_summary.json", "w") as f:
            json.dump({"timestamp": "2025-01-01T00:00:00", "agents_count": 1}, f)

        return str(artifacts_dir)

    def test_health_status_transitions(self, artifacts_dir):
        """Test that health status transitions correctly based on failures."""
        unreliable_module = types.ModuleType('unreliable_module')
        unreliable_module.UnreliableAgent = UnreliableAgent
        sys.modules['unreliable_module'] = unreliable_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_health_monitoring=True)

            # Initially healthy
            status = executor.health_monitor.check_health("UnreliableAgent")
            assert status == HealthStatus.HEALTHY

            # Trigger some failures
            agent = executor.get_node("UnreliableAgent")
            agent.fail_after = 0

            # Record failures through health monitor
            for _ in range(3):
                try:
                    executor.call_method("UnreliableAgent", "process", value=5)
                except ValueError:
                    pass  # Expected failure

            # Should be degraded
            status = executor.health_monitor.check_health("UnreliableAgent")
            assert status in (HealthStatus.DEGRADED, HealthStatus.FAILED)

            # Reset and allow successes
            agent.reset_failures()
            for _ in range(10):
                executor.call_method("UnreliableAgent", "process", value=5)

            # Should recover
            metrics = executor.health_monitor.get_metrics("UnreliableAgent")
            assert metrics.error_rate < 0.5

            executor.stop()

        finally:
            del sys.modules['unreliable_module']

    def test_failure_callback_workflow(self, artifacts_dir):
        """Test that failure callbacks are triggered."""
        unreliable_module = types.ModuleType('unreliable_module')
        unreliable_module.UnreliableAgent = UnreliableAgent
        sys.modules['unreliable_module'] = unreliable_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_health_monitoring=True)

            # Register callback
            failure_events = []

            def on_failure(node_name, metrics):
                failure_events.append({
                    "node_name": node_name,
                    "status": metrics.status,
                    "failed_calls": metrics.failed_calls
                })

            executor.health_monitor.on_failure(on_failure)

            # Trigger failures
            agent = executor.get_node("UnreliableAgent")
            agent.fail_after = 0

            for _ in range(executor.health_monitor.failure_threshold):
                try:
                    executor.call_method("UnreliableAgent", "process", value=5)
                except ValueError:
                    pass

            # Verify callback was triggered
            assert len(failure_events) > 0
            assert failure_events[-1]["node_name"] == "UnreliableAgent"
            assert failure_events[-1]["status"] == HealthStatus.FAILED

            executor.stop()

        finally:
            del sys.modules['unreliable_module']

    @patch('time.sleep')
    def test_auto_restart_workflow(self, mock_sleep, artifacts_dir):
        """Test auto-restart on agent failure."""
        unreliable_module = types.ModuleType('unreliable_module')
        unreliable_module.UnreliableAgent = UnreliableAgent
        sys.modules['unreliable_module'] = unreliable_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(
                enable_health_monitoring=True,
                enable_hot_reload=True
            )

            # Enable auto-restart
            executor.health_monitor.enable_auto_restart = True
            executor.health_monitor.restart_policy = RestartPolicy(
                max_restarts=2,
                initial_delay_seconds=0.1
            )

            # Trigger failures
            agent = executor.get_node("UnreliableAgent")
            agent.fail_after = 0

            for _ in range(executor.health_monitor.failure_threshold):
                try:
                    executor.call_method("UnreliableAgent", "process", value=5)
                except ValueError:
                    pass

            # Verify restart was attempted
            history = executor.hot_reload_manager.get_reload_history()
            assert len(history) > 0

            # Check that the agent was reloaded
            reload_attempts = [h for h in history if h["node_name"] == "UnreliableAgent"]
            assert len(reload_attempts) > 0

            executor.stop()

        finally:
            del sys.modules['unreliable_module']

    def test_get_unhealthy_agents(self, artifacts_dir):
        """Test getting list of unhealthy agents."""
        unreliable_module = types.ModuleType('unreliable_module')
        unreliable_module.UnreliableAgent = UnreliableAgent
        sys.modules['unreliable_module'] = unreliable_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_health_monitoring=True)

            # Make agent unhealthy
            agent = executor.get_node("UnreliableAgent")
            agent.fail_after = 0

            for _ in range(6):
                try:
                    executor.call_method("UnreliableAgent", "process", value=5)
                except ValueError:
                    pass

            # Get unhealthy agents
            unhealthy = executor.health_monitor.get_unhealthy_agents()
            assert "UnreliableAgent" in unhealthy

            executor.stop()

        finally:
            del sys.modules['unreliable_module']

    def test_metrics_tracking_workflow(self, artifacts_dir):
        """Test that metrics are tracked correctly over time."""
        unreliable_module = types.ModuleType('unreliable_module')
        unreliable_module.UnreliableAgent = UnreliableAgent
        sys.modules['unreliable_module'] = unreliable_module

        try:
            config = RuntimeConfig(
                artifacts_dir=artifacts_dir,
                enable_message_bus=False
            )
            executor = RuntimeExecutor(config)
            executor.start(enable_health_monitoring=True)

            # Mix successes and failures
            agent = executor.get_node("UnreliableAgent")
            agent.fail_after = 3

            for i in range(10):
                try:
                    executor.call_method("UnreliableAgent", "process", value=5)
                except ValueError:
                    pass

            # Check metrics
            metrics = executor.health_monitor.get_metrics("UnreliableAgent")
            assert metrics is not None
            assert metrics.total_calls == 10
            assert metrics.successful_calls == 3
            assert metrics.failed_calls == 7
            assert metrics.error_rate == pytest.approx(0.7, rel=0.1)

            executor.stop()

        finally:
            del sys.modules['unreliable_module']
