"""
Integration tests for Profiler with RuntimeExecutor
"""

import pytest
import time
from pathlib import Path
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.runtime.profiler import PerformanceProfiler
from graphbus_core.config import RuntimeConfig


@pytest.fixture
def test_artifacts_dir(tmp_path):
    """Create test artifacts directory with agents"""
    artifacts_dir = tmp_path / ".graphbus"
    artifacts_dir.mkdir()

    # Create agents.json (array format, not object)
    agents_json = [
        {
            "name": "FastAgent",
            "module": "fast_agent",
            "class_name": "FastAgent",
            "source_file": "fast_agent.py",
            "source_code": "",
            "system_prompt": {"text": "", "role": None, "capabilities": []},
            "methods": [],
            "subscriptions": [],
            "dependencies": [],
            "is_arbiter": False,
            "metadata": {}
        },
        {
            "name": "SlowAgent",
            "module": "slow_agent",
            "class_name": "SlowAgent",
            "source_file": "slow_agent.py",
            "source_code": "",
            "system_prompt": {"text": "", "role": None, "capabilities": []},
            "methods": [],
            "subscriptions": [],
            "dependencies": [],
            "is_arbiter": False,
            "metadata": {}
        }
    ]

    import json
    (artifacts_dir / "agents.json").write_text(json.dumps(agents_json, indent=2))

    # Create graph.json
    graph_json = {
        "agents": ["FastAgent", "SlowAgent"],
        "topics": [],
        "edges": []
    }
    (artifacts_dir / "graph.json").write_text(json.dumps(graph_json, indent=2))

    # Create topics.json and subscriptions.json
    (artifacts_dir / "topics.json").write_text(json.dumps({"topics": []}, indent=2))
    (artifacts_dir / "subscriptions.json").write_text(json.dumps({"subscriptions": []}, indent=2))

    # Create build_summary.json
    build_summary_json = {
        "num_agents": 2,
        "num_topics": 0,
        "num_subscriptions": 0,
        "num_negotiations": 0,
        "num_modified_files": 0,
        "agents": ["FastAgent", "SlowAgent"],
        "modified_files": []
    }
    (artifacts_dir / "build_summary.json").write_text(json.dumps(build_summary_json, indent=2))

    # Create agent modules
    modules_dir = artifacts_dir / "modules"
    modules_dir.mkdir()

    fast_agent_code = '''
from graphbus_core import GraphBusNode, schema_method

class FastAgent(GraphBusNode):
    def __init__(self, bus=None, memory=None):
        super().__init__(bus=bus, memory=memory)

    @schema_method(input_schema={}, output_schema={"result": str})
    def fast_method(self):
        """Fast method"""
        return {"result": "fast"}
'''

    slow_agent_code = '''
from graphbus_core import GraphBusNode, schema_method
import time

class SlowAgent(GraphBusNode):
    def __init__(self, bus=None, memory=None):
        super().__init__(bus=bus, memory=memory)

    @schema_method(input_schema={}, output_schema={"result": str})
    def slow_method(self):
        """Slow method"""
        time.sleep(0.05)  # 50ms
        return {"result": "slow"}
'''

    (modules_dir / "fast_agent.py").write_text(fast_agent_code)
    (modules_dir / "slow_agent.py").write_text(slow_agent_code)

    # Add to Python path
    import sys
    if str(modules_dir) not in sys.path:
        sys.path.insert(0, str(modules_dir))

    return artifacts_dir


class TestProfilerIntegration:
    """Integration tests for profiler with runtime"""

    def test_profiler_tracks_method_calls(self, test_artifacts_dir):
        """Test that profiler tracks method execution"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor with profiler
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make calls
        executor.call_method("FastAgent", "fast_method")
        executor.call_method("SlowAgent", "slow_method")

        # Check profiler recorded them
        assert len(profiler.method_profiles) == 2
        assert "FastAgent.fast_method" in profiler.method_profiles
        assert "SlowAgent.slow_method" in profiler.method_profiles

        executor.stop()

    def test_profiler_measures_execution_time(self, test_artifacts_dir):
        """Test that profiler measures execution time"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Call slow method
        executor.call_method("SlowAgent", "slow_method")

        # Check timing
        profile = profiler.method_profiles["SlowAgent.slow_method"]
        assert profile.total_time > 0.05  # At least 50ms
        assert profile.call_count == 1

        executor.stop()

    def test_profiler_identifies_bottlenecks(self, test_artifacts_dir):
        """Test that profiler identifies slow methods"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make calls
        executor.call_method("FastAgent", "fast_method")
        executor.call_method("SlowAgent", "slow_method")

        # Check bottlenecks (30ms threshold)
        bottlenecks = profiler.get_bottlenecks(threshold_ms=30.0)

        assert len(bottlenecks) >= 1
        # Slow method should be identified as bottleneck
        assert any(b.agent_name == "SlowAgent" for b in bottlenecks)

        executor.stop()

    def test_profiler_tracks_multiple_calls(self, test_artifacts_dir):
        """Test profiler with multiple calls"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make multiple calls
        for _ in range(5):
            executor.call_method("FastAgent", "fast_method")

        # Check call count
        profile = profiler.method_profiles["FastAgent.fast_method"]
        assert profile.call_count == 5
        assert profile.avg_time > 0

        executor.stop()

    def test_profiler_top_methods_by_time(self, test_artifacts_dir):
        """Test getting top methods by total time"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Fast method many times (low total time per call but many calls)
        for _ in range(10):
            executor.call_method("FastAgent", "fast_method")

        # Slow method few times (high total time per call)
        for _ in range(3):
            executor.call_method("SlowAgent", "slow_method")

        # Get top by time
        top = profiler.get_top_methods_by_time(limit=2)

        # Slow method should have more total time despite fewer calls
        assert top[0].agent_name == "SlowAgent"

        executor.stop()

    def test_profiler_slowest_methods(self, test_artifacts_dir):
        """Test getting slowest methods by average time"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make calls
        executor.call_method("FastAgent", "fast_method")
        executor.call_method("SlowAgent", "slow_method")

        # Get slowest
        slowest = profiler.get_slowest_methods(limit=2)

        # Slow method should be first
        assert slowest[0].agent_name == "SlowAgent"
        assert slowest[0].avg_time > slowest[1].avg_time

        executor.stop()

    def test_profiler_busiest_agents(self, test_artifacts_dir):
        """Test getting busiest agents by call count"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # FastAgent called more
        for _ in range(10):
            executor.call_method("FastAgent", "fast_method")

        # SlowAgent called less
        for _ in range(3):
            executor.call_method("SlowAgent", "slow_method")

        # Get busiest
        busiest = profiler.get_busiest_agents(limit=2)

        assert busiest[0][0] == "FastAgent"
        assert busiest[0][1] == 10
        assert busiest[1][0] == "SlowAgent"
        assert busiest[1][1] == 3

        executor.stop()

    def test_profiler_summary(self, test_artifacts_dir):
        """Test profiler summary statistics"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make various calls
        executor.call_method("FastAgent", "fast_method")
        executor.call_method("FastAgent", "fast_method")
        executor.call_method("SlowAgent", "slow_method")

        # Get summary
        summary = profiler.get_summary()

        assert summary['enabled'] is True
        assert summary['total_method_calls'] == 3
        assert summary['unique_methods'] == 2
        assert summary['unique_agents'] == 2
        assert summary['uptime_seconds'] > 0

        executor.stop()

    def test_profiler_generate_report(self, test_artifacts_dir):
        """Test generating profiler report"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make calls
        executor.call_method("FastAgent", "fast_method")
        executor.call_method("SlowAgent", "slow_method")

        # Generate report
        report = profiler.generate_report()

        assert "PERFORMANCE PROFILE REPORT" in report
        assert "Uptime:" in report
        assert "Total Method Calls:" in report
        assert "FastAgent.fast_method" in report
        assert "SlowAgent.slow_method" in report

        executor.stop()

    def test_profiler_reset(self, test_artifacts_dir):
        """Test resetting profiler data"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make calls
        executor.call_method("FastAgent", "fast_method")

        assert len(profiler.method_profiles) == 1

        # Reset
        profiler.reset()

        assert len(profiler.method_profiles) == 0
        assert len(profiler.agent_call_counts) == 0

        executor.stop()

    def test_profiler_min_max_tracking(self, test_artifacts_dir):
        """Test min/max execution time tracking"""
        config = RuntimeConfig(artifacts_dir=str(test_artifacts_dir), enable_message_bus=False)
        executor = RuntimeExecutor(config)
        profiler = PerformanceProfiler()

        executor.start()
        profiler.enable()

        # Wrap executor
        original_call = executor.call_method

        def profiled_call(node_name, method_name, **kwargs):
            start = profiler.start_method_call(node_name, method_name)
            try:
                return original_call(node_name, method_name, **kwargs)
            finally:
                profiler.end_method_call(node_name, method_name, start)

        executor.call_method = profiled_call

        # Make multiple calls
        for _ in range(5):
            executor.call_method("SlowAgent", "slow_method")

        # Check min/max
        profile = profiler.method_profiles["SlowAgent.slow_method"]
        assert profile.min_time > 0
        assert profile.max_time > 0
        assert profile.max_time >= profile.min_time

        executor.stop()
