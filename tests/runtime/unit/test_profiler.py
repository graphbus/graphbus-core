"""
Tests for Performance Profiler
"""

import pytest
import time
from graphbus_core.runtime.profiler import (
    PerformanceProfiler,
    MethodProfile,
    EventProfile
)


class TestMethodProfile:
    """Test MethodProfile dataclass"""

    def test_method_profile_creation(self):
        """Test creating a method profile"""
        profile = MethodProfile(agent_name="TestAgent", method_name="test_method")

        assert profile.agent_name == "TestAgent"
        assert profile.method_name == "test_method"
        assert profile.call_count == 0
        assert profile.total_time == 0.0
        assert profile.min_time == float('inf')
        assert profile.max_time == 0.0

    def test_avg_time_no_calls(self):
        """Test average time with no calls"""
        profile = MethodProfile(agent_name="Test", method_name="method")
        assert profile.avg_time == 0.0

    def test_avg_time_with_calls(self):
        """Test average time calculation"""
        profile = MethodProfile(agent_name="Test", method_name="method")
        profile.call_count = 4
        profile.total_time = 2.0  # 2 seconds total

        assert profile.avg_time == 0.5  # 500ms average

    def test_recent_avg(self):
        """Test recent average calculation"""
        profile = MethodProfile(agent_name="Test", method_name="method")
        profile.recent_times.extend([0.1, 0.2, 0.3, 0.4])

        assert profile.recent_avg == 0.25


class TestEventProfile:
    """Test EventProfile dataclass"""

    def test_event_profile_creation(self):
        """Test creating an event profile"""
        profile = EventProfile(topic="/test/topic")

        assert profile.topic == "/test/topic"
        assert profile.publish_count == 0
        assert profile.delivery_count == 0
        assert profile.total_routing_time == 0.0

    def test_avg_routing_time(self):
        """Test average routing time calculation"""
        profile = EventProfile(topic="/test/topic")
        profile.publish_count = 5
        profile.total_routing_time = 0.5

        assert profile.avg_routing_time == 0.1

    def test_recent_avg(self):
        """Test recent average calculation"""
        profile = EventProfile(topic="/test/topic")
        profile.recent_routing_times.extend([0.1, 0.2, 0.3])

        assert abs(profile.recent_avg - 0.2) < 0.001  # Account for floating point precision


class TestPerformanceProfiler:
    """Test PerformanceProfiler class"""

    @pytest.fixture
    def profiler(self):
        """Create a profiler instance"""
        return PerformanceProfiler()

    def test_profiler_initialization(self):
        """Test profiler starts disabled"""
        profiler = PerformanceProfiler()

        assert profiler.enabled is False
        assert profiler.start_time is None
        assert len(profiler.method_profiles) == 0
        assert len(profiler.event_profiles) == 0
        assert len(profiler.agent_call_counts) == 0

    def test_enable_disable(self, profiler):
        """Test enabling and disabling profiler"""
        assert profiler.enabled is False
        assert profiler.start_time is None

        profiler.enable()
        assert profiler.enabled is True
        assert profiler.start_time is not None

        profiler.disable()
        assert profiler.enabled is False

    def test_reset(self, profiler):
        """Test resetting profiler data"""
        profiler.enable()
        profiler.start_method_call("Agent", "method")
        time.sleep(0.01)
        profiler.end_method_call("Agent", "method", time.time() - 0.01)

        assert len(profiler.method_profiles) > 0

        profiler.reset()

        assert len(profiler.method_profiles) == 0
        assert len(profiler.event_profiles) == 0
        assert len(profiler.agent_call_counts) == 0

    def test_start_method_call_disabled(self, profiler):
        """Test start_method_call when disabled"""
        start_time = profiler.start_method_call("Agent", "method")

        # Should return timestamp but not record anything
        assert isinstance(start_time, float)
        assert len(profiler.method_profiles) == 0

    def test_start_method_call_enabled(self, profiler):
        """Test start_method_call when enabled"""
        profiler.enable()

        start_time = profiler.start_method_call("Agent", "method")

        assert isinstance(start_time, float)
        assert profiler.active_calls["Agent.method"] == 1
        assert profiler.agent_call_counts["Agent"] == 1

    def test_end_method_call(self, profiler):
        """Test end_method_call records profile"""
        profiler.enable()

        start_time = profiler.start_method_call("TestAgent", "test_method")
        time.sleep(0.01)  # Sleep for 10ms
        profiler.end_method_call("TestAgent", "test_method", start_time)

        profile = profiler.method_profiles["TestAgent.test_method"]
        assert profile.call_count == 1
        assert profile.total_time > 0.01  # At least 10ms
        assert profile.min_time > 0
        assert profile.max_time > 0
        assert len(profile.recent_times) == 1

    def test_multiple_method_calls(self, profiler):
        """Test multiple calls to same method"""
        profiler.enable()

        for i in range(5):
            start_time = profiler.start_method_call("Agent", "method")
            time.sleep(0.005)  # 5ms each
            profiler.end_method_call("Agent", "method", start_time)

        profile = profiler.method_profiles["Agent.method"]
        assert profile.call_count == 5
        assert profile.total_time > 0.025  # At least 25ms total
        assert len(profile.recent_times) == 5

    def test_different_methods(self, profiler):
        """Test profiling different methods"""
        profiler.enable()

        # Method 1
        start = profiler.start_method_call("Agent1", "method1")
        time.sleep(0.01)
        profiler.end_method_call("Agent1", "method1", start)

        # Method 2
        start = profiler.start_method_call("Agent2", "method2")
        time.sleep(0.01)
        profiler.end_method_call("Agent2", "method2", start)

        assert len(profiler.method_profiles) == 2
        assert "Agent1.method1" in profiler.method_profiles
        assert "Agent2.method2" in profiler.method_profiles

    def test_active_calls_tracking(self, profiler):
        """Test active calls are tracked"""
        profiler.enable()

        start1 = profiler.start_method_call("Agent", "method1")
        assert profiler.active_calls["Agent.method1"] == 1

        start2 = profiler.start_method_call("Agent", "method2")
        assert profiler.active_calls["Agent.method2"] == 1

        profiler.end_method_call("Agent", "method1", start1)
        assert profiler.active_calls["Agent.method1"] == 0

    def test_record_event_publish(self, profiler):
        """Test recording event publishing"""
        profiler.enable()

        profiler.record_event_publish("/test/topic", routing_time=0.05, delivery_count=3)

        profile = profiler.event_profiles["/test/topic"]
        assert profile.publish_count == 1
        assert profile.delivery_count == 3
        assert profile.total_routing_time == 0.05
        assert len(profile.recent_routing_times) == 1

    def test_multiple_event_publishes(self, profiler):
        """Test multiple event publishes"""
        profiler.enable()

        for i in range(5):
            profiler.record_event_publish("/test/topic", routing_time=0.01, delivery_count=2)

        profile = profiler.event_profiles["/test/topic"]
        assert profile.publish_count == 5
        assert profile.delivery_count == 10  # 5 publishes * 2 deliveries
        assert profile.total_routing_time == 0.05

    def test_get_top_methods_by_time(self, profiler):
        """Test getting top methods by total time"""
        profiler.enable()

        # Create methods with different execution times
        for i in range(5):
            start = profiler.start_method_call(f"Agent{i}", "method")
            time.sleep(0.001 * (i + 1))  # Increasing time
            profiler.end_method_call(f"Agent{i}", "method", start)

        top = profiler.get_top_methods_by_time(limit=3)

        assert len(top) == 3
        # Should be sorted by total time (descending)
        assert top[0].total_time >= top[1].total_time >= top[2].total_time
        # Top entry should match the maximum observed total time
        max_total_time = max(p.total_time for p in profiler.method_profiles.values())
        assert top[0].total_time == max_total_time

    def test_get_top_methods_by_calls(self, profiler):
        """Test getting top methods by call count"""
        profiler.enable()

        # Create methods with different call counts
        for count in [3, 1, 5, 2]:
            for _ in range(count):
                start = profiler.start_method_call(f"Agent{count}", "method")
                profiler.end_method_call(f"Agent{count}", "method", start)

        top = profiler.get_top_methods_by_calls(limit=3)

        assert len(top) == 3
        # Should be sorted by call count (descending)
        assert top[0].call_count >= top[1].call_count >= top[2].call_count
        assert top[0].agent_name == "Agent5"  # Most calls

    def test_get_slowest_methods(self, profiler):
        """Test getting slowest methods by average time"""
        profiler.enable()

        # Create methods with different speeds
        # Slow method - 1 call, 50ms
        start = profiler.start_method_call("SlowAgent", "method")
        time.sleep(0.05)
        profiler.end_method_call("SlowAgent", "method", start)

        # Fast method - 10 calls, 1ms each
        for _ in range(10):
            start = profiler.start_method_call("FastAgent", "method")
            time.sleep(0.001)
            profiler.end_method_call("FastAgent", "method", start)

        slowest = profiler.get_slowest_methods(limit=5)

        assert len(slowest) == 2
        # Slowest should be first
        assert slowest[0].agent_name == "SlowAgent"
        assert slowest[0].avg_time > slowest[1].avg_time

    def test_get_busiest_agents(self, profiler):
        """Test getting busiest agents"""
        profiler.enable()

        # Agent1: 5 calls
        for _ in range(5):
            start = profiler.start_method_call("Agent1", "method")
            profiler.end_method_call("Agent1", "method", start)

        # Agent2: 10 calls
        for _ in range(10):
            start = profiler.start_method_call("Agent2", "method")
            profiler.end_method_call("Agent2", "method", start)

        # Agent3: 3 calls
        for _ in range(3):
            start = profiler.start_method_call("Agent3", "method")
            profiler.end_method_call("Agent3", "method", start)

        busiest = profiler.get_busiest_agents(limit=5)

        assert len(busiest) == 3
        assert busiest[0] == ("Agent2", 10)
        assert busiest[1] == ("Agent1", 5)
        assert busiest[2] == ("Agent3", 3)

    def test_get_active_calls(self, profiler):
        """Test getting currently active calls"""
        profiler.enable()

        start1 = profiler.start_method_call("Agent1", "method1")
        start2 = profiler.start_method_call("Agent2", "method2")

        active = profiler.get_active_calls()
        assert len(active) == 2
        assert active["Agent1.method1"] == 1
        assert active["Agent2.method2"] == 1

        profiler.end_method_call("Agent1", "method1", start1)

        active = profiler.get_active_calls()
        assert len(active) == 1
        assert "Agent2.method2" in active

    def test_get_event_stats(self, profiler):
        """Test getting event statistics"""
        profiler.enable()

        profiler.record_event_publish("/topic1", 0.01, 2)
        profiler.record_event_publish("/topic2", 0.02, 3)

        stats = profiler.get_event_stats()
        assert len(stats) == 2
        topics = [s.topic for s in stats]
        assert "/topic1" in topics
        assert "/topic2" in topics

    def test_get_bottlenecks(self, profiler):
        """Test identifying bottlenecks"""
        profiler.enable()

        # Fast method - 5ms average
        for _ in range(5):
            start = profiler.start_method_call("FastAgent", "method")
            time.sleep(0.005)
            profiler.end_method_call("FastAgent", "method", start)

        # Slow method - 150ms average (above 100ms threshold)
        start = profiler.start_method_call("SlowAgent", "method")
        time.sleep(0.15)
        profiler.end_method_call("SlowAgent", "method", start)

        bottlenecks = profiler.get_bottlenecks(threshold_ms=100.0)

        assert len(bottlenecks) == 1
        assert bottlenecks[0].agent_name == "SlowAgent"
        assert bottlenecks[0].avg_time > 0.1  # Over 100ms

    def test_get_bottlenecks_custom_threshold(self, profiler):
        """Test bottlenecks with custom threshold"""
        profiler.enable()

        # Method with 30ms average
        for _ in range(3):
            start = profiler.start_method_call("Agent", "method")
            time.sleep(0.03)
            profiler.end_method_call("Agent", "method", start)

        # With 100ms threshold - no bottlenecks
        bottlenecks = profiler.get_bottlenecks(threshold_ms=100.0)
        assert len(bottlenecks) == 0

        # With 20ms threshold - found
        bottlenecks = profiler.get_bottlenecks(threshold_ms=20.0)
        assert len(bottlenecks) == 1

    def test_get_summary(self, profiler):
        """Test getting profiler summary"""
        profiler.enable()

        # Make some calls
        for i in range(3):
            start = profiler.start_method_call(f"Agent{i}", "method")
            time.sleep(0.01)
            profiler.end_method_call(f"Agent{i}", "method", start)

        # Publish some events
        profiler.record_event_publish("/topic1", 0.01, 2)
        profiler.record_event_publish("/topic2", 0.01, 3)

        summary = profiler.get_summary()

        assert summary['enabled'] is True
        assert summary['uptime_seconds'] > 0
        assert summary['total_method_calls'] == 3
        assert summary['total_execution_time'] > 0.03
        assert summary['unique_methods'] == 3
        assert summary['unique_agents'] == 3
        assert summary['total_events'] == 2
        assert summary['unique_topics'] == 2
        assert summary['calls_per_second'] > 0

    def test_generate_report(self, profiler):
        """Test generating text report"""
        profiler.enable()

        # Create some profile data
        for _ in range(5):
            start = profiler.start_method_call("TestAgent", "test_method")
            time.sleep(0.01)
            profiler.end_method_call("TestAgent", "test_method", start)

        # Create a slow method (bottleneck)
        start = profiler.start_method_call("SlowAgent", "slow_method")
        time.sleep(0.15)
        profiler.end_method_call("SlowAgent", "slow_method", start)

        report = profiler.generate_report()

        assert "PERFORMANCE PROFILE REPORT" in report
        assert "Uptime:" in report
        assert "Total Method Calls:" in report
        assert "Top Methods by Total Time:" in report
        assert "Slowest Methods" in report
        assert "Potential Bottlenecks" in report
        assert "TestAgent.test_method" in report
        assert "SlowAgent.slow_method" in report

    def test_recent_times_limit(self, profiler):
        """Test recent times buffer is limited to 100 entries"""
        profiler.enable()

        # Make 150 calls
        for _ in range(150):
            start = profiler.start_method_call("Agent", "method")
            profiler.end_method_call("Agent", "method", start)

        profile = profiler.method_profiles["Agent.method"]
        assert profile.call_count == 150
        assert len(profile.recent_times) == 100  # Limited to 100

    def test_min_max_time_tracking(self, profiler):
        """Test min and max time tracking"""
        profiler.enable()

        # First call - 10ms
        start = profiler.start_method_call("Agent", "method")
        time.sleep(0.01)
        profiler.end_method_call("Agent", "method", start)

        # Second call - 30ms (max)
        start = profiler.start_method_call("Agent", "method")
        time.sleep(0.03)
        profiler.end_method_call("Agent", "method", start)

        # Third call - 5ms (min)
        start = profiler.start_method_call("Agent", "method")
        time.sleep(0.005)
        profiler.end_method_call("Agent", "method", start)

        profile = profiler.method_profiles["Agent.method"]
        assert profile.min_time < 0.01  # Less than 10ms
        assert profile.max_time > 0.03  # More than 30ms

    def test_profiler_disabled_no_recording(self, profiler):
        """Test that disabled profiler doesn't record"""
        # Don't enable profiler

        start = profiler.start_method_call("Agent", "method")
        profiler.end_method_call("Agent", "method", start)

        profiler.record_event_publish("/topic", 0.01, 2)

        assert len(profiler.method_profiles) == 0
        assert len(profiler.event_profiles) == 0
        assert len(profiler.agent_call_counts) == 0
