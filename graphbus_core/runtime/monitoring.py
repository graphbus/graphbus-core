"""
Monitoring and Observability

Provides Prometheus metrics export and OpenTelemetry integration.
"""

import time
import threading
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class MetricValue:
    """Single metric value"""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class PrometheusMetrics:
    """
    Prometheus metrics exporter for GraphBus runtime.

    Tracks and exports metrics in Prometheus format.
    """

    def __init__(self):
        """Initialize metrics collector"""
        self._lock = threading.Lock()

        # Counter metrics
        self.messages_published_total = defaultdict(int)
        self.messages_delivered_total = defaultdict(int)
        self.method_calls_total = defaultdict(int)
        self.method_errors_total = defaultdict(int)

        # Gauge metrics
        self.active_agents = 0
        self.message_queue_depth = defaultdict(int)
        self.agent_health_status = {}  # agent -> status (1=healthy, 0=unhealthy)

        # Histogram metrics (bounded deques for O(1) sliding window, max 1000 observations)
        self.method_duration_seconds: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.event_processing_duration_seconds: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Track start time
        self.start_time = time.time()

    def increment_messages_published(self, topic: str, count: int = 1) -> None:
        """Increment published message counter"""
        with self._lock:
            self.messages_published_total[topic] += count

    def increment_messages_delivered(self, topic: str, count: int = 1) -> None:
        """Increment delivered message counter"""
        with self._lock:
            self.messages_delivered_total[topic] += count

    def increment_method_calls(self, agent: str, method: str, count: int = 1) -> None:
        """Increment method call counter"""
        key = f"{agent}.{method}"
        with self._lock:
            self.method_calls_total[key] += count

    def increment_method_errors(self, agent: str, method: str, count: int = 1) -> None:
        """Increment method error counter"""
        key = f"{agent}.{method}"
        with self._lock:
            self.method_errors_total[key] += count

    def set_active_agents(self, count: int) -> None:
        """Set number of active agents"""
        with self._lock:
            self.active_agents = count

    def set_queue_depth(self, topic: str, depth: int) -> None:
        """Set message queue depth for topic"""
        with self._lock:
            self.message_queue_depth[topic] = depth

    def set_agent_health(self, agent: str, healthy: bool) -> None:
        """Set agent health status (1=healthy, 0=unhealthy)"""
        with self._lock:
            self.agent_health_status[agent] = 1 if healthy else 0

    def observe_method_duration(self, agent: str, method: str, duration: float) -> None:
        """Observe method execution duration (deque auto-evicts oldest beyond maxlen)"""
        key = f"{agent}.{method}"
        with self._lock:
            self.method_duration_seconds[key].append(duration)

    def observe_event_duration(self, topic: str, duration: float) -> None:
        """Observe event processing duration (deque auto-evicts oldest beyond maxlen)"""
        with self._lock:
            self.event_processing_duration_seconds[topic].append(duration)

    def generate_prometheus_metrics(self) -> str:
        """
        Generate Prometheus metrics in text format.

        Returns:
            Metrics in Prometheus exposition format
        """
        with self._lock:
            lines = []

            # Add HELP and TYPE for each metric family
            lines.append("# HELP graphbus_messages_published_total Total number of messages published")
            lines.append("# TYPE graphbus_messages_published_total counter")
            for topic, count in self.messages_published_total.items():
                lines.append(f'graphbus_messages_published_total{{topic="{topic}"}} {count}')

            lines.append("")
            lines.append("# HELP graphbus_messages_delivered_total Total number of messages delivered")
            lines.append("# TYPE graphbus_messages_delivered_total counter")
            for topic, count in self.messages_delivered_total.items():
                lines.append(f'graphbus_messages_delivered_total{{topic="{topic}"}} {count}')

            lines.append("")
            lines.append("# HELP graphbus_method_calls_total Total number of method calls")
            lines.append("# TYPE graphbus_method_calls_total counter")
            for key, count in self.method_calls_total.items():
                agent, method = key.rsplit('.', 1) if '.' in key else (key, 'unknown')
                lines.append(f'graphbus_method_calls_total{{agent="{agent}",method="{method}"}} {count}')

            lines.append("")
            lines.append("# HELP graphbus_method_errors_total Total number of method errors")
            lines.append("# TYPE graphbus_method_errors_total counter")
            for key, count in self.method_errors_total.items():
                agent, method = key.rsplit('.', 1) if '.' in key else (key, 'unknown')
                lines.append(f'graphbus_method_errors_total{{agent="{agent}",method="{method}"}} {count}')

            lines.append("")
            lines.append("# HELP graphbus_active_agents Number of active agents")
            lines.append("# TYPE graphbus_active_agents gauge")
            lines.append(f"graphbus_active_agents {self.active_agents}")

            lines.append("")
            lines.append("# HELP graphbus_message_queue_depth Current message queue depth per topic")
            lines.append("# TYPE graphbus_message_queue_depth gauge")
            for topic, depth in self.message_queue_depth.items():
                lines.append(f'graphbus_message_queue_depth{{topic="{topic}"}} {depth}')

            lines.append("")
            lines.append("# HELP graphbus_agent_health Agent health status (1=healthy, 0=unhealthy)")
            lines.append("# TYPE graphbus_agent_health gauge")
            for agent, status in self.agent_health_status.items():
                lines.append(f'graphbus_agent_health{{agent="{agent}"}} {status}')

            # Duration metrics are exported as Prometheus *summaries*, not histograms.
            #
            # Prometheus distinguishes two client-computed distribution types:
            #   histogram — cumulative bucket counts with le= labels
            #   summary   — pre-computed quantiles with quantile= labels
            #
            # We compute quantiles from the sliding-window deque and emit them with
            # quantile= labels, which is the summary format.  Declaring the type as
            # "histogram" while emitting quantile= lines is a format violation:
            # Prometheus parsers reject or mis-categorise the metric family, making
            # the duration data invisible in Grafana / alerting rules.
            lines.append("")
            lines.append("# HELP graphbus_method_duration_seconds Method execution duration")
            lines.append("# TYPE graphbus_method_duration_seconds summary")
            for key, durations in self.method_duration_seconds.items():
                if durations:
                    agent, method = key.rsplit('.', 1) if '.' in key else (key, 'unknown')
                    sorted_durations = sorted(durations)
                    count = len(sorted_durations)
                    total = sum(sorted_durations)

                    labels = f'agent="{agent}",method="{method}"'
                    lines.append(f'graphbus_method_duration_seconds_count{{{labels}}} {count}')
                    lines.append(f'graphbus_method_duration_seconds_sum{{{labels}}} {total}')

                    # Quantile lines (summary format: quantile= label, no _bucket suffix)
                    p50_idx = int(count * 0.5)
                    p95_idx = int(count * 0.95)
                    p99_idx = int(count * 0.99)

                    p50 = sorted_durations[min(p50_idx, count - 1)]
                    p95 = sorted_durations[min(p95_idx, count - 1)]
                    p99 = sorted_durations[min(p99_idx, count - 1)]

                    lines.append(f'graphbus_method_duration_seconds{{quantile="0.5",{labels}}} {p50}')
                    lines.append(f'graphbus_method_duration_seconds{{quantile="0.95",{labels}}} {p95}')
                    lines.append(f'graphbus_method_duration_seconds{{quantile="0.99",{labels}}} {p99}')

            lines.append("")
            lines.append("# HELP graphbus_event_processing_duration_seconds Event processing duration")
            lines.append("# TYPE graphbus_event_processing_duration_seconds summary")
            for topic, durations in self.event_processing_duration_seconds.items():
                if durations:
                    sorted_durations = sorted(durations)
                    count = len(sorted_durations)
                    total = sum(sorted_durations)

                    labels = f'topic="{topic}"'
                    lines.append(f'graphbus_event_processing_duration_seconds_count{{{labels}}} {count}')
                    lines.append(f'graphbus_event_processing_duration_seconds_sum{{{labels}}} {total}')

                    p50_idx = int(count * 0.5)
                    p95_idx = int(count * 0.95)
                    p99_idx = int(count * 0.99)

                    p50 = sorted_durations[min(p50_idx, count - 1)]
                    p95 = sorted_durations[min(p95_idx, count - 1)]
                    p99 = sorted_durations[min(p99_idx, count - 1)]

                    lines.append(f'graphbus_event_processing_duration_seconds{{quantile="0.5",{labels}}} {p50}')
                    lines.append(f'graphbus_event_processing_duration_seconds{{quantile="0.95",{labels}}} {p95}')
                    lines.append(f'graphbus_event_processing_duration_seconds{{quantile="0.99",{labels}}} {p99}')

            # Add process metrics
            uptime = time.time() - self.start_time
            lines.append("")
            lines.append("# HELP graphbus_uptime_seconds Uptime in seconds")
            lines.append("# TYPE graphbus_uptime_seconds gauge")
            lines.append(f"graphbus_uptime_seconds {uptime}")

            return "\n".join(lines) + "\n"

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.

        Returns:
            Dictionary with metric summaries
        """
        with self._lock:
            return {
                'messages_published': sum(self.messages_published_total.values()),
                'messages_delivered': sum(self.messages_delivered_total.values()),
                'method_calls': sum(self.method_calls_total.values()),
                'method_errors': sum(self.method_errors_total.values()),
                'active_agents': self.active_agents,
                'uptime_seconds': time.time() - self.start_time,
                'topics_tracked': len(self.messages_published_total),
                'methods_tracked': len(self.method_calls_total)
            }


class MetricsServer:
    """
    HTTP server for Prometheus metrics endpoint.

    Serves metrics on /metrics endpoint.
    """

    def __init__(self, metrics: PrometheusMetrics, port: int = 9090):
        """
        Initialize metrics server.

        Args:
            metrics: PrometheusMetrics instance to serve
            port: HTTP port (default: 9090)
        """
        self.metrics = metrics
        self.port = port
        self.server = None
        self._thread = None

    def start(self) -> None:
        """Start metrics server in background thread"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler

            metrics = self.metrics

            class MetricsHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/metrics':
                        # Serve Prometheus metrics
                        metrics_text = metrics.generate_prometheus_metrics()
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain; version=0.0.4')
                        self.end_headers()
                        self.wfile.write(metrics_text.encode('utf-8'))
                    elif self.path == '/health':
                        # Health check endpoint
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b'OK')
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    # Suppress request logs
                    pass

            self.server = HTTPServer(('0.0.0.0', self.port), MetricsHandler)

            # Start server in background thread
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()

            print(f"[MetricsServer] Started on port {self.port}")
            print(f"[MetricsServer] Metrics: http://localhost:{self.port}/metrics")

        except Exception as e:
            print(f"[MetricsServer] Failed to start: {e}")

    def stop(self) -> None:
        """Stop metrics server"""
        if self.server:
            self.server.shutdown()
            print("[MetricsServer] Stopped")
