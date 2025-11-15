"""
Performance Profiler for GraphBus Runtime

Tracks and analyzes performance metrics for agents and message routing.
"""

import time
import threading
import psutil
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque


@dataclass
class MethodProfile:
    """Profile data for a single method"""
    agent_name: str
    method_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_time(self) -> float:
        """Average execution time"""
        return self.total_time / self.call_count if self.call_count > 0 else 0.0

    @property
    def recent_avg(self) -> float:
        """Average of recent executions"""
        return sum(self.recent_times) / len(self.recent_times) if self.recent_times else 0.0


@dataclass
class EventProfile:
    """Profile data for event routing"""
    topic: str
    publish_count: int = 0
    delivery_count: int = 0
    total_routing_time: float = 0.0
    recent_routing_times: deque = field(default_factory=lambda: deque(maxlen=100))
    queue_depths: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_routing_time(self) -> float:
        """Average routing time"""
        return self.total_routing_time / self.publish_count if self.publish_count > 0 else 0.0

    @property
    def recent_avg(self) -> float:
        """Average of recent routing times"""
        return sum(self.recent_routing_times) / len(self.recent_routing_times) if self.recent_routing_times else 0.0

    @property
    def avg_queue_depth(self) -> float:
        """Average queue depth"""
        return sum(self.queue_depths) / len(self.queue_depths) if self.queue_depths else 0.0

    @property
    def max_queue_depth(self) -> int:
        """Maximum queue depth observed"""
        return max(self.queue_depths) if self.queue_depths else 0


@dataclass
class SystemSnapshot:
    """System resource snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    thread_count: int


class PerformanceProfiler:
    """
    Performance profiler for GraphBus runtime.

    Tracks:
    - Method execution times
    - Event routing latency
    - Message queue depths
    - Agent call patterns
    - Bottleneck identification
    """

    def __init__(self):
        """Initialize profiler"""
        self.enabled = False
        self.start_time: Optional[datetime] = None
        self._lock = threading.Lock()

        # Profile data
        self.method_profiles: Dict[str, MethodProfile] = {}
        self.event_profiles: Dict[str, EventProfile] = {}
        self.agent_call_counts: Dict[str, int] = defaultdict(int)
        self.active_calls: Dict[str, int] = defaultdict(int)  # Current active calls per method

        # System resource tracking
        self.system_snapshots: deque = deque(maxlen=1000)
        self._process = psutil.Process(os.getpid())
        self._last_snapshot_time = 0.0
        self._snapshot_interval = 1.0  # Take snapshot every second

    def enable(self) -> None:
        """Enable profiling"""
        with self._lock:
            self.enabled = True
            self.start_time = datetime.now()

    def disable(self) -> None:
        """Disable profiling"""
        with self._lock:
            self.enabled = False

    def reset(self) -> None:
        """Reset all profiling data"""
        with self._lock:
            self.method_profiles.clear()
            self.event_profiles.clear()
            self.agent_call_counts.clear()
            self.active_calls.clear()
            self.system_snapshots.clear()
            self._last_snapshot_time = 0.0
            self.start_time = datetime.now() if self.enabled else None

    def _take_system_snapshot(self) -> None:
        """Take a snapshot of system resources"""
        current_time = time.time()

        # Only take snapshot if enough time has passed
        if current_time - self._last_snapshot_time < self._snapshot_interval:
            return

        try:
            # Get CPU and memory stats
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = self._process.memory_percent()
            thread_count = self._process.num_threads()

            snapshot = SystemSnapshot(
                timestamp=current_time,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                thread_count=thread_count
            )

            self.system_snapshots.append(snapshot)
            self._last_snapshot_time = current_time
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process may have terminated or we don't have permissions
            pass

    def start_method_call(self, agent_name: str, method_name: str) -> float:
        """
        Record start of method call.

        Args:
            agent_name: Agent name
            method_name: Method name

        Returns:
            Start timestamp for correlation
        """
        if not self.enabled:
            return time.time()

        start_time = time.time()

        with self._lock:
            full_name = f"{agent_name}.{method_name}"
            self.active_calls[full_name] += 1
            self.agent_call_counts[agent_name] += 1

        # Take system snapshot periodically
        self._take_system_snapshot()

        return start_time

    def end_method_call(self, agent_name: str, method_name: str, start_time: float) -> None:
        """
        Record end of method call.

        Args:
            agent_name: Agent name
            method_name: Method name
            start_time: Start timestamp from start_method_call
        """
        if not self.enabled:
            return

        end_time = time.time()
        execution_time = end_time - start_time
        full_name = f"{agent_name}.{method_name}"

        with self._lock:
            # Get or create profile
            if full_name not in self.method_profiles:
                self.method_profiles[full_name] = MethodProfile(
                    agent_name=agent_name,
                    method_name=method_name
                )

            profile = self.method_profiles[full_name]

            # Update stats
            profile.call_count += 1
            profile.total_time += execution_time
            profile.min_time = min(profile.min_time, execution_time)
            profile.max_time = max(profile.max_time, execution_time)
            profile.recent_times.append(execution_time)

            # Update active calls
            self.active_calls[full_name] -= 1

    def record_event_publish(self, topic: str, routing_time: float, delivery_count: int, queue_depth: int = 0) -> None:
        """
        Record event publishing and routing.

        Args:
            topic: Event topic
            routing_time: Time taken to route event
            delivery_count: Number of handlers notified
            queue_depth: Current message queue depth
        """
        if not self.enabled:
            return

        with self._lock:
            # Get or create profile
            if topic not in self.event_profiles:
                self.event_profiles[topic] = EventProfile(topic=topic)

            profile = self.event_profiles[topic]

            # Update stats
            profile.publish_count += 1
            profile.delivery_count += delivery_count
            profile.total_routing_time += routing_time
            profile.recent_routing_times.append(routing_time)
            profile.queue_depths.append(queue_depth)

    def get_top_methods_by_time(self, limit: int = 10) -> List[MethodProfile]:
        """
        Get methods with highest total execution time.

        Args:
            limit: Number of methods to return

        Returns:
            List of method profiles sorted by total time
        """
        with self._lock:
            sorted_profiles = sorted(
                self.method_profiles.values(),
                key=lambda p: p.total_time,
                reverse=True
            )
            return sorted_profiles[:limit]

    def get_top_methods_by_calls(self, limit: int = 10) -> List[MethodProfile]:
        """
        Get methods with highest call count.

        Args:
            limit: Number of methods to return

        Returns:
            List of method profiles sorted by call count
        """
        with self._lock:
            sorted_profiles = sorted(
                self.method_profiles.values(),
                key=lambda p: p.call_count,
                reverse=True
            )
            return sorted_profiles[:limit]

    def get_slowest_methods(self, limit: int = 10) -> List[MethodProfile]:
        """
        Get methods with highest average execution time.

        Args:
            limit: Number of methods to return

        Returns:
            List of method profiles sorted by average time
        """
        with self._lock:
            sorted_profiles = sorted(
                self.method_profiles.values(),
                key=lambda p: p.avg_time,
                reverse=True
            )
            return sorted_profiles[:limit]

    def get_busiest_agents(self, limit: int = 10) -> List[tuple]:
        """
        Get agents with highest call counts.

        Args:
            limit: Number of agents to return

        Returns:
            List of (agent_name, call_count) tuples
        """
        with self._lock:
            sorted_agents = sorted(
                self.agent_call_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_agents[:limit]

    def get_active_calls(self) -> Dict[str, int]:
        """
        Get currently active method calls.

        Returns:
            Dictionary of method_name -> active_count
        """
        with self._lock:
            return {k: v for k, v in self.active_calls.items() if v > 0}

    def get_event_stats(self) -> List[EventProfile]:
        """
        Get event routing statistics.

        Returns:
            List of event profiles
        """
        with self._lock:
            return list(self.event_profiles.values())

    def get_bottlenecks(self, threshold_ms: float = 100.0) -> List[MethodProfile]:
        """
        Identify potential bottlenecks.

        Args:
            threshold_ms: Threshold in milliseconds for considering a method slow

        Returns:
            List of method profiles that exceed threshold
        """
        threshold_sec = threshold_ms / 1000.0

        with self._lock:
            bottlenecks = [
                profile for profile in self.method_profiles.values()
                if profile.avg_time > threshold_sec or profile.max_time > threshold_sec * 2
            ]

            return sorted(bottlenecks, key=lambda p: p.avg_time, reverse=True)

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system resource statistics.

        Returns:
            Dictionary with CPU, memory, and thread statistics
        """
        with self._lock:
            if not self.system_snapshots:
                return {
                    'cpu_percent_avg': 0.0,
                    'cpu_percent_max': 0.0,
                    'memory_mb_avg': 0.0,
                    'memory_mb_max': 0.0,
                    'memory_percent_avg': 0.0,
                    'memory_percent_max': 0.0,
                    'thread_count_avg': 0,
                    'thread_count_max': 0,
                    'snapshots': 0
                }

            cpu_values = [s.cpu_percent for s in self.system_snapshots]
            memory_mb_values = [s.memory_mb for s in self.system_snapshots]
            memory_percent_values = [s.memory_percent for s in self.system_snapshots]
            thread_values = [s.thread_count for s in self.system_snapshots]

            return {
                'cpu_percent_avg': sum(cpu_values) / len(cpu_values),
                'cpu_percent_max': max(cpu_values),
                'memory_mb_avg': sum(memory_mb_values) / len(memory_mb_values),
                'memory_mb_max': max(memory_mb_values),
                'memory_percent_avg': sum(memory_percent_values) / len(memory_percent_values),
                'memory_percent_max': max(memory_percent_values),
                'thread_count_avg': sum(thread_values) / len(thread_values),
                'thread_count_max': max(thread_values),
                'snapshots': len(self.system_snapshots)
            }

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get message queue depth statistics.

        Returns:
            Dictionary with queue depth statistics per topic
        """
        with self._lock:
            queue_stats = {}
            for topic, profile in self.event_profiles.items():
                if profile.queue_depths:
                    queue_stats[topic] = {
                        'avg_depth': profile.avg_queue_depth,
                        'max_depth': profile.max_queue_depth,
                        'current_depth': profile.queue_depths[-1] if profile.queue_depths else 0
                    }
            return queue_stats

    def get_summary(self) -> Dict[str, Any]:
        """
        Get profiling summary.

        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            total_calls = sum(p.call_count for p in self.method_profiles.values())
            total_time = sum(p.total_time for p in self.method_profiles.values())

            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0

            return {
                'enabled': self.enabled,
                'uptime_seconds': uptime,
                'total_method_calls': total_calls,
                'total_execution_time': total_time,
                'unique_methods': len(self.method_profiles),
                'unique_agents': len(self.agent_call_counts),
                'total_events': sum(p.publish_count for p in self.event_profiles.values()),
                'unique_topics': len(self.event_profiles),
                'active_calls': sum(self.active_calls.values()),
                'calls_per_second': total_calls / uptime if uptime > 0 else 0
            }

    def generate_report(self) -> str:
        """
        Generate text report of profiling data.

        Returns:
            Formatted text report
        """
        summary = self.get_summary()
        system_stats = self.get_system_stats()
        queue_stats = self.get_queue_stats()
        top_time = self.get_top_methods_by_time(5)
        top_calls = self.get_top_methods_by_calls(5)
        slowest = self.get_slowest_methods(5)
        bottlenecks = self.get_bottlenecks()

        lines = []
        lines.append("=" * 60)
        lines.append("PERFORMANCE PROFILE REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Uptime: {summary['uptime_seconds']:.1f}s")
        lines.append(f"Total Method Calls: {summary['total_method_calls']}")
        lines.append(f"Total Execution Time: {summary['total_execution_time']:.3f}s")
        lines.append(f"Calls/Second: {summary['calls_per_second']:.1f}")
        lines.append(f"Unique Methods: {summary['unique_methods']}")
        lines.append(f"Unique Agents: {summary['unique_agents']}")
        lines.append("")

        # System resource stats
        if system_stats['snapshots'] > 0:
            lines.append("System Resources:")
            lines.append("-" * 60)
            lines.append(f"  CPU: {system_stats['cpu_percent_avg']:.1f}% avg, {system_stats['cpu_percent_max']:.1f}% max")
            lines.append(f"  Memory: {system_stats['memory_mb_avg']:.1f} MB avg, {system_stats['memory_mb_max']:.1f} MB max ({system_stats['memory_percent_avg']:.1f}%)")
            lines.append(f"  Threads: {system_stats['thread_count_avg']:.0f} avg, {system_stats['thread_count_max']} max")
            lines.append("")

        # Queue depth stats
        if queue_stats:
            lines.append("Message Queue Depths:")
            lines.append("-" * 60)
            for topic, stats in sorted(queue_stats.items(), key=lambda x: x[1]['max_depth'], reverse=True)[:5]:
                lines.append(
                    f"  {topic}: "
                    f"avg={stats['avg_depth']:.1f}, "
                    f"max={stats['max_depth']}, "
                    f"current={stats['current_depth']}"
                )
            lines.append("")

        if top_time:
            lines.append("Top Methods by Total Time:")
            lines.append("-" * 60)
            for profile in top_time:
                lines.append(
                    f"  {profile.agent_name}.{profile.method_name}: "
                    f"{profile.total_time:.3f}s total, "
                    f"{profile.call_count} calls, "
                    f"{profile.avg_time*1000:.1f}ms avg"
                )
            lines.append("")

        if slowest:
            lines.append("Slowest Methods (by average):")
            lines.append("-" * 60)
            for profile in slowest:
                lines.append(
                    f"  {profile.agent_name}.{profile.method_name}: "
                    f"{profile.avg_time*1000:.1f}ms avg, "
                    f"{profile.max_time*1000:.1f}ms max, "
                    f"{profile.call_count} calls"
                )
            lines.append("")

        if bottlenecks:
            lines.append("⚠ Potential Bottlenecks (>100ms average):")
            lines.append("-" * 60)
            for profile in bottlenecks:
                lines.append(
                    f"  {profile.agent_name}.{profile.method_name}: "
                    f"{profile.avg_time*1000:.1f}ms avg, "
                    f"{profile.max_time*1000:.1f}ms max"
                )
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_flame_graph_data(self) -> List[Dict[str, Any]]:
        """
        Generate data for flame graph visualization.

        Returns:
            List of stack frames with timing data
        """
        with self._lock:
            flame_data = []
            for method_name, profile in self.method_profiles.items():
                flame_data.append({
                    'name': f"{profile.agent_name}.{profile.method_name}",
                    'value': profile.total_time,
                    'count': profile.call_count,
                    'avg_time': profile.avg_time,
                    'max_time': profile.max_time
                })
            return sorted(flame_data, key=lambda x: x['value'], reverse=True)

    def generate_flame_graph_html(self) -> str:
        """
        Generate interactive HTML flame graph.

        Returns:
            HTML string with embedded D3.js flame graph
        """
        flame_data = self.generate_flame_graph_data()
        summary = self.get_summary()
        system_stats = self.get_system_stats()

        # Convert to JSON for embedding
        import json
        data_json = json.dumps(flame_data)

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>GraphBus Performance Flame Graph</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 20px;
            background: #1e1e1e;
            color: #d4d4d4;
        }}
        .header {{
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #4ec9b0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #2d2d30;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #4ec9b0;
        }}
        .stat-card .label {{
            color: #858585;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-card .value {{
            color: #d4d4d4;
            font-size: 24px;
            font-weight: 600;
            margin-top: 5px;
        }}
        .chart-container {{
            background: #2d2d30;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .flame-rect {{
            stroke: #1e1e1e;
            stroke-width: 1;
            cursor: pointer;
        }}
        .flame-rect:hover {{
            opacity: 0.8;
        }}
        .tooltip {{
            position: absolute;
            background: #2d2d30;
            border: 1px solid #4ec9b0;
            padding: 10px;
            border-radius: 4px;
            pointer-events: none;
            display: none;
            font-size: 12px;
            z-index: 1000;
        }}
        .method-list {{
            background: #2d2d30;
            padding: 20px;
            border-radius: 8px;
        }}
        .method-item {{
            padding: 10px;
            margin: 5px 0;
            background: #1e1e1e;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .method-name {{
            color: #4ec9b0;
            font-family: "Courier New", monospace;
        }}
        .method-stats {{
            color: #858585;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Performance Flame Graph</h1>
        <p>GraphBus Runtime Profile</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="label">Uptime</div>
            <div class="value">{summary['uptime_seconds']:.1f}s</div>
        </div>
        <div class="stat-card">
            <div class="label">Total Calls</div>
            <div class="value">{summary['total_method_calls']:,}</div>
        </div>
        <div class="stat-card">
            <div class="label">Calls/Second</div>
            <div class="value">{summary['calls_per_second']:.1f}</div>
        </div>
        <div class="stat-card">
            <div class="label">CPU Usage</div>
            <div class="value">{system_stats.get('cpu_percent_avg', 0):.1f}%</div>
        </div>
        <div class="stat-card">
            <div class="label">Memory</div>
            <div class="value">{system_stats.get('memory_mb_avg', 0):.0f} MB</div>
        </div>
    </div>

    <div class="chart-container">
        <h3>Method Execution Time Distribution</h3>
        <div id="flame-graph"></div>
    </div>

    <div class="method-list">
        <h3>Top Methods by Total Time</h3>
        <div id="method-list"></div>
    </div>

    <div class="tooltip" id="tooltip"></div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const data = {data_json};

        // Render horizontal bar chart (simpler than full flame graph)
        const margin = {{top: 20, right: 30, bottom: 40, left: 200}};
        const width = 900 - margin.left - margin.right;
        const height = Math.min(600, data.length * 40);

        const svg = d3.select("#flame-graph")
            .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

        const x = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.value)])
            .range([0, width]);

        const y = d3.scaleBand()
            .domain(data.map((d, i) => i))
            .range([0, height])
            .padding(0.1);

        const color = d3.scaleSequential()
            .domain([0, data.length])
            .interpolator(d3.interpolateWarm);

        const tooltip = d3.select("#tooltip");

        // Bars
        svg.selectAll(".bar")
            .data(data)
            .enter()
            .append("rect")
            .attr("class", "flame-rect")
            .attr("x", 0)
            .attr("y", (d, i) => y(i))
            .attr("width", d => x(d.value))
            .attr("height", y.bandwidth())
            .attr("fill", (d, i) => color(i))
            .on("mouseover", function(event, d) {{
                tooltip.style("display", "block")
                    .html(`
                        <strong>${{d.name}}</strong><br/>
                        Total: ${{(d.value * 1000).toFixed(2)}}ms<br/>
                        Calls: ${{d.count}}<br/>
                        Avg: ${{(d.avg_time * 1000).toFixed(2)}}ms<br/>
                        Max: ${{(d.max_time * 1000).toFixed(2)}}ms
                    `)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 10) + "px");
            }})
            .on("mouseout", function() {{
                tooltip.style("display", "none");
            }});

        // Labels
        svg.selectAll(".label")
            .data(data)
            .enter()
            .append("text")
            .attr("class", "label")
            .attr("x", -5)
            .attr("y", (d, i) => y(i) + y.bandwidth() / 2)
            .attr("dy", ".35em")
            .attr("text-anchor", "end")
            .style("fill", "#d4d4d4")
            .style("font-size", "11px")
            .text(d => d.name.length > 25 ? d.name.substring(0, 22) + "..." : d.name);

        // X axis
        const xAxis = d3.axisBottom(x)
            .ticks(5)
            .tickFormat(d => (d * 1000).toFixed(0) + "ms");

        svg.append("g")
            .attr("transform", `translate(0,${{height}})`)
            .call(xAxis)
            .style("color", "#858585");

        // Method list
        const methodList = d3.select("#method-list");
        data.slice(0, 20).forEach(d => {{
            const item = methodList.append("div").attr("class", "method-item");
            item.append("div")
                .attr("class", "method-name")
                .text(d.name);
            item.append("div")
                .attr("class", "method-stats")
                .html(`${{(d.value * 1000).toFixed(2)}}ms total | ${{d.count}} calls | ${{(d.avg_time * 1000).toFixed(2)}}ms avg`);
        }});
    </script>
</body>
</html>'''
        return html
