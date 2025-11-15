"""
Health Monitor

Monitors agent health and handles failures with automatic recovery.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum
import time


class HealthStatus(Enum):
    """Agent health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


@dataclass
class HealthMetrics:
    """Health metrics for an agent"""
    node_name: str
    status: HealthStatus
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    uptime_seconds: float = 0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0 to 1.0)"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        return 1.0 - self.error_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "node_name": self.node_name,
            "status": self.status.value,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "error_rate": self.error_rate,
            "success_rate": self.success_rate,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "consecutive_failures": self.consecutive_failures,
            "uptime_seconds": self.uptime_seconds
        }


class RestartPolicy:
    """Policy for restarting failed agents"""

    def __init__(
        self,
        max_restarts: int = 3,
        restart_window_seconds: int = 300,
        backoff_multiplier: float = 2.0,
        initial_delay_seconds: float = 1.0
    ):
        """
        Initialize restart policy.

        Args:
            max_restarts: Maximum number of restarts within window
            restart_window_seconds: Time window for restart counting
            backoff_multiplier: Exponential backoff multiplier
            initial_delay_seconds: Initial delay before first restart
        """
        self.max_restarts = max_restarts
        self.restart_window = timedelta(seconds=restart_window_seconds)
        self.backoff_multiplier = backoff_multiplier
        self.initial_delay = initial_delay_seconds
        self.restart_history: Dict[str, list[datetime]] = {}

    def should_restart(self, node_name: str) -> bool:
        """
        Check if an agent should be restarted.

        Args:
            node_name: Name of the agent

        Returns:
            True if restart should be attempted
        """
        if node_name not in self.restart_history:
            return True

        # Get recent restarts within window
        now = datetime.utcnow()
        cutoff = now - self.restart_window
        recent_restarts = [
            ts for ts in self.restart_history[node_name]
            if ts > cutoff
        ]

        # Update history
        self.restart_history[node_name] = recent_restarts

        return len(recent_restarts) < self.max_restarts

    def record_restart(self, node_name: str) -> None:
        """Record a restart attempt."""
        if node_name not in self.restart_history:
            self.restart_history[node_name] = []

        self.restart_history[node_name].append(datetime.utcnow())

    def get_restart_delay(self, node_name: str) -> float:
        """
        Calculate delay before restart based on retry count.

        Args:
            node_name: Name of the agent

        Returns:
            Delay in seconds
        """
        if node_name not in self.restart_history:
            return self.initial_delay

        retry_count = len(self.restart_history[node_name])
        return self.initial_delay * (self.backoff_multiplier ** (retry_count - 1))


class HealthMonitor:
    """
    Monitors agent health and handles failures.

    Tracks success/failure rates, detects unhealthy agents,
    and can automatically restart failed agents.
    """

    def __init__(
        self,
        runtime_executor,
        enable_auto_restart: bool = False,
        restart_policy: Optional[RestartPolicy] = None,
        failure_threshold: int = 5,
        error_rate_threshold: float = 0.5
    ):
        """
        Initialize HealthMonitor.

        Args:
            runtime_executor: RuntimeExecutor instance
            enable_auto_restart: Enable automatic restart of failed agents
            restart_policy: Policy for restarting agents
            failure_threshold: Consecutive failures before marking unhealthy
            error_rate_threshold: Error rate threshold for degraded status
        """
        self.executor = runtime_executor
        self.enable_auto_restart = enable_auto_restart
        self.restart_policy = restart_policy or RestartPolicy()
        self.failure_threshold = failure_threshold
        self.error_rate_threshold = error_rate_threshold

        self.metrics: Dict[str, HealthMetrics] = {}
        self.failure_callbacks: list[Callable] = []
        self.recovery_callbacks: list[Callable] = []

        # Initialize metrics for all nodes
        for node_name in self.executor.nodes.keys():
            self.metrics[node_name] = HealthMetrics(
                node_name=node_name,
                status=HealthStatus.HEALTHY
            )

    def record_success(self, node_name: str) -> None:
        """
        Record a successful operation for an agent.

        Args:
            node_name: Name of the agent
        """
        if node_name not in self.metrics:
            self.metrics[node_name] = HealthMetrics(
                node_name=node_name,
                status=HealthStatus.HEALTHY
            )

        metrics = self.metrics[node_name]
        metrics.total_calls += 1
        metrics.successful_calls += 1
        metrics.consecutive_failures = 0
        metrics.last_success_time = datetime.utcnow()

        # Update status
        self._update_status(node_name)

    def record_failure(self, node_name: str, error: Exception) -> None:
        """
        Record a failed operation for an agent.

        Args:
            node_name: Name of the agent
            error: Exception that caused the failure
        """
        if node_name not in self.metrics:
            self.metrics[node_name] = HealthMetrics(
                node_name=node_name,
                status=HealthStatus.HEALTHY
            )

        metrics = self.metrics[node_name]
        metrics.total_calls += 1
        metrics.failed_calls += 1
        metrics.consecutive_failures += 1
        metrics.last_error = str(error)
        metrics.last_error_time = datetime.utcnow()

        # Update status
        old_status = metrics.status
        self._update_status(node_name)

        # Trigger failure callbacks if status changed
        if old_status != metrics.status:
            self._trigger_failure_callbacks(node_name, metrics)

        # Auto-restart if enabled and threshold exceeded
        if self.enable_auto_restart and metrics.status == HealthStatus.FAILED:
            self._attempt_restart(node_name)

    def check_health(self, node_name: str) -> HealthStatus:
        """
        Check agent health status.

        Args:
            node_name: Name of the agent

        Returns:
            Current health status
        """
        if node_name not in self.metrics:
            return HealthStatus.HEALTHY

        return self.metrics[node_name].status

    def get_metrics(self, node_name: str) -> Optional[HealthMetrics]:
        """
        Get health metrics for an agent.

        Args:
            node_name: Name of the agent

        Returns:
            HealthMetrics or None if agent not found
        """
        return self.metrics.get(node_name)

    def get_all_metrics(self) -> Dict[str, HealthMetrics]:
        """Get health metrics for all agents."""
        return self.metrics.copy()

    def get_unhealthy_agents(self) -> list[str]:
        """
        Get list of unhealthy agent names.

        Returns:
            List of agent names with UNHEALTHY or FAILED status
        """
        return [
            name for name, metrics in self.metrics.items()
            if metrics.status in (HealthStatus.UNHEALTHY, HealthStatus.FAILED)
        ]

    def reset_metrics(self, node_name: str) -> None:
        """
        Reset health metrics for an agent.

        Args:
            node_name: Name of the agent
        """
        if node_name in self.metrics:
            self.metrics[node_name] = HealthMetrics(
                node_name=node_name,
                status=HealthStatus.HEALTHY
            )

    def on_failure(self, callback: Callable) -> None:
        """
        Register callback for agent failures.

        Args:
            callback: Function(node_name, metrics) called on failure
        """
        self.failure_callbacks.append(callback)

    def on_recovery(self, callback: Callable) -> None:
        """
        Register callback for agent recovery.

        Args:
            callback: Function(node_name, metrics) called on recovery
        """
        self.recovery_callbacks.append(callback)

    def _update_status(self, node_name: str) -> None:
        """Update health status based on metrics."""
        metrics = self.metrics[node_name]
        old_status = metrics.status

        # Determine new status
        if metrics.consecutive_failures >= self.failure_threshold:
            new_status = HealthStatus.FAILED
        elif metrics.error_rate > self.error_rate_threshold:
            new_status = HealthStatus.DEGRADED
        elif metrics.consecutive_failures > 0:
            new_status = HealthStatus.DEGRADED
        else:
            new_status = HealthStatus.HEALTHY

        metrics.status = new_status

        # Trigger recovery callbacks if recovered to HEALTHY from any unhealthy state
        if old_status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.FAILED) and new_status == HealthStatus.HEALTHY:
            self._trigger_recovery_callbacks(node_name, metrics)

    def _attempt_restart(self, node_name: str) -> bool:
        """
        Attempt to restart a failed agent.

        Args:
            node_name: Name of the agent

        Returns:
            True if restart was successful
        """
        if not self.restart_policy.should_restart(node_name):
            print(f"⚠ Agent '{node_name}' exceeded restart limit")
            return False

        # Calculate delay
        delay = self.restart_policy.get_restart_delay(node_name)
        print(f"Waiting {delay:.1f}s before restarting '{node_name}'...")
        time.sleep(delay)

        try:
            # Record restart attempt
            self.restart_policy.record_restart(node_name)

            # Try to restart by reloading the agent
            if hasattr(self.executor, 'hot_reload_manager'):
                print(f"Attempting to restart '{node_name}'...")
                result = self.executor.hot_reload_manager.reload_agent(node_name)

                if result.get("success"):
                    print(f"✓ Successfully restarted '{node_name}'")
                    self.reset_metrics(node_name)
                    return True
                else:
                    print(f"✗ Failed to restart '{node_name}': {result.get('error')}")
                    return False
            else:
                print(f"⚠ Hot reload not available, cannot restart '{node_name}'")
                return False

        except Exception as e:
            print(f"✗ Error restarting '{node_name}': {e}")
            return False

    def _trigger_failure_callbacks(self, node_name: str, metrics: HealthMetrics) -> None:
        """Trigger registered failure callbacks."""
        for callback in self.failure_callbacks:
            try:
                callback(node_name, metrics)
            except Exception:
                pass  # Don't let callback errors affect monitoring

    def _trigger_recovery_callbacks(self, node_name: str, metrics: HealthMetrics) -> None:
        """Trigger registered recovery callbacks."""
        for callback in self.recovery_callbacks:
            try:
                callback(node_name, metrics)
            except Exception:
                pass
