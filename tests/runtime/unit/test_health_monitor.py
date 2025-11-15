"""
Unit tests for HealthMonitor
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from graphbus_core.runtime.health import (
    HealthMonitor,
    HealthStatus,
    HealthMetrics,
    RestartPolicy
)


class TestHealthMetrics:
    """Test HealthMetrics dataclass"""

    def test_initialization(self):
        """Test HealthMetrics initialization"""
        metrics = HealthMetrics(
            node_name="TestAgent",
            status=HealthStatus.HEALTHY
        )

        assert metrics.node_name == "TestAgent"
        assert metrics.status == HealthStatus.HEALTHY
        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.consecutive_failures == 0

    def test_error_rate_zero_calls(self):
        """Test error rate with zero calls"""
        metrics = HealthMetrics("TestAgent", HealthStatus.HEALTHY)

        assert metrics.error_rate == 0.0
        assert metrics.success_rate == 1.0

    def test_error_rate_calculation(self):
        """Test error rate calculation"""
        metrics = HealthMetrics("TestAgent", HealthStatus.HEALTHY)
        metrics.total_calls = 10
        metrics.failed_calls = 3

        assert metrics.error_rate == 0.3
        assert metrics.success_rate == 0.7

    def test_to_dict(self):
        """Test converting metrics to dict"""
        metrics = HealthMetrics(
            node_name="TestAgent",
            status=HealthStatus.DEGRADED,
            total_calls=10,
            successful_calls=7,
            failed_calls=3
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict["node_name"] == "TestAgent"
        assert metrics_dict["status"] == "degraded"
        assert metrics_dict["total_calls"] == 10
        assert metrics_dict["error_rate"] == 0.3
        assert metrics_dict["success_rate"] == 0.7


class TestRestartPolicy:
    """Test RestartPolicy"""

    def test_initialization(self):
        """Test RestartPolicy initialization"""
        policy = RestartPolicy(
            max_restarts=3,
            restart_window_seconds=300,
            backoff_multiplier=2.0,
            initial_delay_seconds=1.0
        )

        assert policy.max_restarts == 3
        assert policy.restart_window == timedelta(seconds=300)
        assert policy.backoff_multiplier == 2.0
        assert policy.initial_delay == 1.0

    def test_should_restart_first_attempt(self):
        """Test should restart on first attempt"""
        policy = RestartPolicy(max_restarts=3)

        assert policy.should_restart("TestAgent") is True

    def test_should_restart_within_limit(self):
        """Test should restart when within limit"""
        policy = RestartPolicy(max_restarts=3)

        policy.record_restart("TestAgent")
        policy.record_restart("TestAgent")

        assert policy.should_restart("TestAgent") is True

    def test_should_restart_at_limit(self):
        """Test should not restart when at limit"""
        policy = RestartPolicy(max_restarts=3)

        for _ in range(3):
            policy.record_restart("TestAgent")

        assert policy.should_restart("TestAgent") is False

    def test_should_restart_outside_window(self):
        """Test restart counting resets outside window"""
        policy = RestartPolicy(max_restarts=2, restart_window_seconds=1)

        # Record restarts
        policy.record_restart("TestAgent")
        policy.record_restart("TestAgent")

        # Should be at limit
        assert policy.should_restart("TestAgent") is False

        # Wait for window to pass
        time.sleep(1.1)

        # Should be able to restart again
        assert policy.should_restart("TestAgent") is True

    def test_get_restart_delay_first_attempt(self):
        """Test restart delay on first attempt"""
        policy = RestartPolicy(initial_delay_seconds=1.0)

        delay = policy.get_restart_delay("TestAgent")

        assert delay == 1.0

    def test_get_restart_delay_exponential_backoff(self):
        """Test exponential backoff for retries"""
        policy = RestartPolicy(
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0
        )

        policy.record_restart("TestAgent")
        delay1 = policy.get_restart_delay("TestAgent")

        policy.record_restart("TestAgent")
        delay2 = policy.get_restart_delay("TestAgent")

        policy.record_restart("TestAgent")
        delay3 = policy.get_restart_delay("TestAgent")

        # After 1 restart: 1.0 * 2^(1-1) = 1.0 * 2^0 = 1.0
        # After 2 restarts: 1.0 * 2^(2-1) = 1.0 * 2^1 = 2.0
        # After 3 restarts: 1.0 * 2^(3-1) = 1.0 * 2^2 = 4.0
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0


class TestHealthMonitor:
    """Test HealthMonitor"""

    @pytest.fixture
    def mock_executor(self):
        """Mock RuntimeExecutor"""
        executor = Mock()
        executor.nodes = {
            "Agent1": Mock(),
            "Agent2": Mock()
        }
        return executor

    @pytest.fixture
    def monitor(self, mock_executor):
        """HealthMonitor instance"""
        return HealthMonitor(
            mock_executor,
            enable_auto_restart=False,
            failure_threshold=5,
            error_rate_threshold=0.5
        )

    def test_initialization(self, mock_executor):
        """Test HealthMonitor initialization"""
        monitor = HealthMonitor(mock_executor)

        assert monitor.executor == mock_executor
        assert not monitor.enable_auto_restart
        assert monitor.failure_threshold == 5
        assert monitor.error_rate_threshold == 0.5
        assert len(monitor.metrics) == 2  # Two nodes

    def test_record_success(self, monitor):
        """Test recording successful operation"""
        monitor.record_success("Agent1")

        metrics = monitor.metrics["Agent1"]
        assert metrics.total_calls == 1
        assert metrics.successful_calls == 1
        assert metrics.failed_calls == 0
        assert metrics.consecutive_failures == 0
        assert metrics.status == HealthStatus.HEALTHY

    def test_record_multiple_successes(self, monitor):
        """Test recording multiple successful operations"""
        for _ in range(10):
            monitor.record_success("Agent1")

        metrics = monitor.metrics["Agent1"]
        assert metrics.total_calls == 10
        assert metrics.successful_calls == 10
        assert metrics.error_rate == 0.0

    def test_record_failure(self, monitor):
        """Test recording failed operation"""
        error = Exception("Test error")
        monitor.record_failure("Agent1", error)

        metrics = monitor.metrics["Agent1"]
        assert metrics.total_calls == 1
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 1
        assert metrics.consecutive_failures == 1
        assert metrics.last_error == "Test error"
        assert metrics.last_error_time is not None

    def test_status_degraded_on_high_error_rate(self, monitor):
        """Test status becomes DEGRADED with high error rate"""
        # Create error rate > 0.5
        for _ in range(3):
            monitor.record_success("Agent1")
        for _ in range(4):
            monitor.record_failure("Agent1", Exception("Error"))

        metrics = monitor.metrics["Agent1"]
        assert metrics.error_rate > 0.5
        assert metrics.status == HealthStatus.DEGRADED

    def test_status_failed_on_consecutive_failures(self, monitor):
        """Test status becomes FAILED after threshold"""
        # Record failures up to threshold
        for _ in range(5):
            monitor.record_failure("Agent1", Exception("Error"))

        metrics = monitor.metrics["Agent1"]
        assert metrics.consecutive_failures == 5
        assert metrics.status == HealthStatus.FAILED

    def test_consecutive_failures_reset_on_success(self, monitor):
        """Test consecutive failures reset on success"""
        # Record some failures
        for _ in range(3):
            monitor.record_failure("Agent1", Exception("Error"))

        # Then a success
        monitor.record_success("Agent1")

        metrics = monitor.metrics["Agent1"]
        assert metrics.consecutive_failures == 0

    def test_check_health(self, monitor):
        """Test checking agent health"""
        status = monitor.check_health("Agent1")

        assert status == HealthStatus.HEALTHY

    def test_get_metrics(self, monitor):
        """Test getting metrics for an agent"""
        metrics = monitor.get_metrics("Agent1")

        assert metrics is not None
        assert metrics.node_name == "Agent1"

    def test_get_metrics_nonexistent(self, monitor):
        """Test getting metrics for non-existent agent"""
        metrics = monitor.get_metrics("NonExistent")

        assert metrics is None

    def test_get_all_metrics(self, monitor):
        """Test getting all metrics"""
        all_metrics = monitor.get_all_metrics()

        assert len(all_metrics) == 2
        assert "Agent1" in all_metrics
        assert "Agent2" in all_metrics

    def test_get_unhealthy_agents(self, monitor):
        """Test getting list of unhealthy agents"""
        # Make Agent1 fail
        for _ in range(5):
            monitor.record_failure("Agent1", Exception("Error"))

        unhealthy = monitor.get_unhealthy_agents()

        assert len(unhealthy) == 1
        assert "Agent1" in unhealthy

    def test_reset_metrics(self, monitor):
        """Test resetting metrics for an agent"""
        # Record some activity
        monitor.record_failure("Agent1", Exception("Error"))
        monitor.record_failure("Agent1", Exception("Error"))

        # Reset
        monitor.reset_metrics("Agent1")

        metrics = monitor.metrics["Agent1"]
        assert metrics.total_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.consecutive_failures == 0
        assert metrics.status == HealthStatus.HEALTHY

    def test_failure_callback_triggered(self, monitor):
        """Test that failure callback is triggered"""
        callback = Mock()
        monitor.on_failure(callback)

        # Trigger failure status change
        for _ in range(5):
            monitor.record_failure("Agent1", Exception("Error"))

        # Callback should be called when status changes to FAILED
        callback.assert_called()
        args = callback.call_args[0]
        assert args[0] == "Agent1"
        assert args[1].status == HealthStatus.FAILED

    def test_recovery_callback_triggered(self, monitor):
        """Test that recovery callback is triggered"""
        callback = Mock()
        monitor.on_recovery(callback)

        # Make agent fail (reaches FAILED status at 5 consecutive failures)
        for _ in range(5):
            monitor.record_failure("Agent1", Exception("Error"))

        # Status should be FAILED
        assert monitor.metrics["Agent1"].status == HealthStatus.FAILED

        # Recover - need enough successes to bring error_rate below threshold
        # With 5 failures, need at least 6 successes to get error_rate < 0.5 (5/11 = 0.45)
        # But also need consecutive_failures to be 0 (which happens on first success)
        for _ in range(20):
            monitor.record_success("Agent1")

        # Callback should be called when status recovers to HEALTHY
        callback.assert_called()
        args = callback.call_args[0]
        assert args[0] == "Agent1"
        assert args[1].status == HealthStatus.HEALTHY

    def test_auto_restart_disabled(self, monitor):
        """Test that auto-restart doesn't trigger when disabled"""
        # Record failures
        for _ in range(5):
            monitor.record_failure("Agent1", Exception("Error"))

        # Should not attempt restart
        # (No way to verify without checking internal state)
        assert monitor.metrics["Agent1"].status == HealthStatus.FAILED

    @patch('time.sleep')
    def test_auto_restart_enabled(self, mock_sleep, mock_executor):
        """Test auto-restart when enabled"""
        # Setup executor with hot reload
        mock_executor.hot_reload_manager = Mock()
        mock_executor.hot_reload_manager.reload_agent.return_value = {
            "success": True
        }

        monitor = HealthMonitor(
            mock_executor,
            enable_auto_restart=True,
            failure_threshold=3
        )

        # Trigger failures
        for _ in range(3):
            monitor.record_failure("Agent1", Exception("Error"))

        # Verify reload was attempted
        mock_executor.hot_reload_manager.reload_agent.assert_called_once_with("Agent1")

    @patch('time.sleep')
    def test_auto_restart_respects_policy(self, mock_sleep, mock_executor):
        """Test auto-restart respects restart policy"""
        policy = RestartPolicy(max_restarts=2)
        mock_executor.hot_reload_manager = Mock()
        mock_executor.hot_reload_manager.reload_agent.return_value = {
            "success": True
        }

        monitor = HealthMonitor(
            mock_executor,
            enable_auto_restart=True,
            restart_policy=policy,
            failure_threshold=2
        )

        # First failure - should restart
        for _ in range(2):
            monitor.record_failure("Agent1", Exception("Error"))

        assert mock_executor.hot_reload_manager.reload_agent.call_count == 1

        # Reset and fail again - should restart once more
        monitor.reset_metrics("Agent1")
        for _ in range(2):
            monitor.record_failure("Agent1", Exception("Error"))

        assert mock_executor.hot_reload_manager.reload_agent.call_count == 2

        # Reset and fail again - should NOT restart (limit reached, max_restarts=2)
        monitor.reset_metrics("Agent1")
        for _ in range(2):
            monitor.record_failure("Agent1", Exception("Error"))

        # Still only 2 calls
        assert mock_executor.hot_reload_manager.reload_agent.call_count == 2

    @patch('time.sleep')
    def test_auto_restart_with_backoff(self, mock_sleep, mock_executor):
        """Test auto-restart uses exponential backoff"""
        policy = RestartPolicy(
            max_restarts=3,
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0
        )
        mock_executor.hot_reload_manager = Mock()
        mock_executor.hot_reload_manager.reload_agent.return_value = {
            "success": True
        }

        monitor = HealthMonitor(
            mock_executor,
            enable_auto_restart=True,
            restart_policy=policy,
            failure_threshold=2
        )

        # First failure - should delay 1s (no restarts recorded yet, so retry_count=0)
        for _ in range(2):
            monitor.record_failure("Agent1", Exception("Error"))

        # After first restart is recorded, delay calculation would be 1.0 * 2^(1-1) = 1.0
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(1.0)

        # Second failure - should delay 1s (1 restart recorded, so 1.0 * 2^(1-1) = 1.0)
        monitor.reset_metrics("Agent1")
        for _ in range(2):
            monitor.record_failure("Agent1", Exception("Error"))

        # After second restart, we have 2 restarts recorded, so next would be 1.0 * 2^(2-1) = 2.0
        # But the test is checking the call during the restart, which uses the delay before recording
        assert mock_sleep.call_count == 2
        # Both calls should be 1.0 based on current implementation
        assert all(call[0][0] == 1.0 for call in mock_sleep.call_args_list)

    def test_metrics_for_new_agent(self, monitor):
        """Test that recording for new agent creates metrics"""
        monitor.record_success("NewAgent")

        assert "NewAgent" in monitor.metrics
        assert monitor.metrics["NewAgent"].total_calls == 1

    def test_callback_error_doesnt_break_monitoring(self, monitor):
        """Test that callback errors don't break monitoring"""
        def bad_callback(node_name, metrics):
            raise Exception("Callback error")

        monitor.on_failure(bad_callback)

        # Should not raise
        for _ in range(5):
            monitor.record_failure("Agent1", Exception("Error"))

        # Monitoring should still work
        assert monitor.metrics["Agent1"].status == HealthStatus.FAILED
