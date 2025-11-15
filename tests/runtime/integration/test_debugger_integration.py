"""
Integration tests for Debugger with RuntimeExecutor
Refactored to use mocks and minimal fixtures for faster execution
"""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from graphbus_core.runtime.debugger import InteractiveDebugger, ExecutionFrame, Breakpoint
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.config import RuntimeConfig


@pytest.fixture
def mock_debugger():
    """Create a real debugger instance (lightweight)"""
    debugger = InteractiveDebugger()
    debugger.enable()
    return debugger


@pytest.fixture
def mock_executor():
    """Create a mocked RuntimeExecutor with real debugger"""
    executor = Mock(spec=RuntimeExecutor)
    executor.debugger = InteractiveDebugger()
    executor.debugger.enable()
    executor.nodes = {}
    executor.is_running = True
    return executor


@pytest.fixture
def mock_agent():
    """Create a simple mock agent for testing"""
    agent = Mock()
    agent.test_method = Mock(return_value={"count": 1})
    agent.slow_method = Mock(return_value={"result": "done"})
    return agent


class TestDebuggerIntegration:
    """Integration tests for debugger - using mocks for speed"""

    def test_debugger_enables_with_runtime(self, mock_executor):
        """Test that debugger can be enabled with runtime"""
        assert mock_executor.debugger is not None
        assert mock_executor.debugger.enabled is True

    def test_debugger_hooks_method_calls(self, mock_debugger, mock_agent):
        """Test that debugger intercepts method calls"""
        # Simulate a method call through debugger
        mock_debugger.on_method_call("TestAgent", "test_method", payload={"test": "data"})

        # Check debugger recorded it
        assert len(mock_debugger.execution_trace) == 1
        frame = mock_debugger.execution_trace[0]
        assert frame.agent_name == "TestAgent"
        assert frame.method_name == "test_method"
        assert frame.payload == {"test": "data"}

    def test_debugger_breakpoint_pauses_execution(self, mock_debugger):
        """Test that breakpoint pauses execution"""
        # Set breakpoint
        mock_debugger.add_breakpoint("TestAgent", "test_method")

        # Track if callback was called
        callback_called = []

        def on_break(frame):
            callback_called.append(frame.full_name)
            # Auto-continue to avoid blocking
            mock_debugger.continue_execution()

        mock_debugger.on_break(on_break)

        # Call method in thread (it will pause at breakpoint)
        def call_method():
            mock_debugger.on_method_call("TestAgent", "test_method")

        thread = threading.Thread(target=call_method)
        thread.start()

        # Wait a bit for breakpoint to hit
        time.sleep(0.1)

        # Should have hit breakpoint
        assert len(callback_called) == 1
        assert callback_called[0] == "TestAgent.test_method"

        # Wait for thread to complete
        thread.join(timeout=1.0)

    def test_debugger_conditional_breakpoint(self, mock_debugger):
        """Test conditional breakpoint"""
        # Add conditional breakpoint
        bp = mock_debugger.add_breakpoint("TestAgent", "test_method", condition="payload.get('amount', 0) > 100")

        # Track which calls actually break
        breaks = []

        def on_break_callback(frame):
            breaks.append(frame.payload)
            mock_debugger.continue_execution()

        mock_debugger.on_break(on_break_callback)

        # Call with condition False - should not break (but hit_count still increments)
        def call1():
            mock_debugger.on_method_call("TestAgent", "test_method", payload={"amount": 50})

        thread1 = threading.Thread(target=call1)
        thread1.start()
        thread1.join(timeout=1.0)

        # Hit count increments regardless of condition
        assert bp.hit_count == 1
        # But callback should not have been called (didn't actually break)
        assert len(breaks) == 0

        # Call with condition True - should break
        def call2():
            mock_debugger.on_method_call("TestAgent", "test_method", payload={"amount": 150})

        thread2 = threading.Thread(target=call2)
        thread2.start()
        thread2.join(timeout=1.0)

        # Hit count is now 2
        assert bp.hit_count == 2
        # Callback should have been called once (this one broke)
        assert len(breaks) == 1
        assert breaks[0]["amount"] == 150

    def test_debugger_execution_trace(self, mock_debugger):
        """Test execution trace captures all calls"""
        # Make multiple calls
        for i in range(5):
            mock_debugger.on_method_call("TestAgent", "test_method", payload={"call": i})

        # Check trace has all calls
        trace = mock_debugger.get_execution_trace(limit=10)
        assert len(trace) == 5

        # All should be for TestAgent.test_method
        for frame in trace:
            assert frame.agent_name == "TestAgent"
            assert frame.method_name == "test_method"

    def test_debugger_inspect_current_frame(self, mock_debugger):
        """Test inspecting current execution frame"""
        # Set breakpoint
        mock_debugger.add_breakpoint("TestAgent", "test_method")

        # Call method in thread
        def call_method():
            mock_debugger.on_method_call("TestAgent", "test_method", payload={"data": "test"})

        thread = threading.Thread(target=call_method)
        thread.start()

        # Wait for breakpoint
        time.sleep(0.1)

        # Check current frame
        frame = mock_debugger.get_current_frame()
        assert frame is not None
        assert frame.agent_name == "TestAgent"
        assert frame.method_name == "test_method"
        assert frame.payload == {"data": "test"}

        # Continue
        mock_debugger.continue_execution()
        thread.join(timeout=1.0)

    def test_debugger_step_mode(self, mock_debugger):
        """Test step mode"""
        hit_count = []

        def on_break(frame):
            hit_count.append(frame.full_name)
            # Auto-continue or step
            if len(hit_count) == 1:
                mock_debugger.step()
            else:
                mock_debugger.continue_execution()

        mock_debugger.on_break(on_break)

        # Manually set step mode
        from graphbus_core.runtime.debugger import DebuggerState
        mock_debugger.state = DebuggerState.STEP

        def make_calls():
            # First call - will break due to step mode
            mock_debugger.on_method_call("TestAgent", "test_method")
            time.sleep(0.05)

            # Second call - should also break due to step
            mock_debugger.on_method_call("TestAgent", "test_method")
            time.sleep(0.05)

        thread = threading.Thread(target=make_calls)
        thread.start()
        thread.join(timeout=2.0)

        # Both calls should have been caught
        assert len(hit_count) == 2

    def test_debugger_stats(self, mock_debugger):
        """Test debugger statistics"""
        # Add auto-continue callback to avoid blocking
        def auto_continue(frame):
            mock_debugger.continue_execution()

        mock_debugger.on_break(auto_continue)

        # Add breakpoints
        mock_debugger.add_breakpoint("TestAgent", "test_method")
        mock_debugger.add_breakpoint("TestAgent", "slow_method")

        # Make some calls in thread to avoid blocking
        def call():
            mock_debugger.on_method_call("TestAgent", "test_method")

        thread = threading.Thread(target=call)
        thread.start()
        thread.join(timeout=1.0)

        # Check stats
        stats = mock_debugger.get_stats()
        assert stats['enabled'] is True
        assert stats['breakpoints_count'] == 2
        assert stats['trace_entries'] >= 1

    def test_debugger_disabled_no_overhead(self):
        """Test that disabled debugger has minimal overhead"""
        debugger = InteractiveDebugger()
        # Don't enable it
        assert debugger.enabled is False

        # Calling on_method_call should do nothing
        debugger.on_method_call("TestAgent", "test_method")

        # No trace should be recorded
        assert len(debugger.execution_trace) == 0

    def test_debugger_clear_breakpoints(self, mock_debugger):
        """Test clearing breakpoints"""
        # Add breakpoints
        mock_debugger.add_breakpoint("TestAgent", "test_method")
        mock_debugger.add_breakpoint("TestAgent", "slow_method")

        assert len(mock_debugger.breakpoints) == 2

        # Clear all
        mock_debugger.clear_breakpoints()

        assert len(mock_debugger.breakpoints) == 0

    def test_debugger_remove_specific_breakpoint(self, mock_debugger):
        """Test removing specific breakpoint"""
        # Add breakpoints
        mock_debugger.add_breakpoint("TestAgent", "test_method")
        mock_debugger.add_breakpoint("TestAgent", "slow_method")

        # Remove one
        result = mock_debugger.remove_breakpoint("TestAgent", "test_method")
        assert result is True

        assert len(mock_debugger.breakpoints) == 1
        assert "TestAgent.slow_method" in mock_debugger.breakpoints

    def test_debugger_list_breakpoints(self, mock_debugger):
        """Test listing breakpoints"""
        # Add breakpoints
        bp1 = mock_debugger.add_breakpoint("TestAgent", "test_method")
        bp2 = mock_debugger.add_breakpoint("TestAgent", "slow_method")

        # List them
        breakpoints = mock_debugger.list_breakpoints()
        assert len(breakpoints) == 2

        names = [bp.full_name for bp in breakpoints]
        assert "TestAgent.test_method" in names
        assert "TestAgent.slow_method" in names

    def test_debugger_thread_safety(self, mock_debugger):
        """Test debugger is thread-safe"""
        # Auto-continue when breakpoints hit
        def auto_continue(frame):
            mock_debugger.continue_execution()

        mock_debugger.on_break(auto_continue)

        def add_breakpoints():
            for i in range(10):
                mock_debugger.add_breakpoint(f"Agent{i}", f"method{i}")

        def call_methods():
            for i in range(10):
                mock_debugger.on_method_call(f"Agent{i}", f"method{i}")

        threads = [
            threading.Thread(target=add_breakpoints),
            threading.Thread(target=call_methods)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Should complete without errors
        assert len(mock_debugger.breakpoints) >= 10
        assert len(mock_debugger.execution_trace) >= 10

    def test_debugger_breakpoint_hit_count(self, mock_debugger):
        """Test breakpoint hit count tracking"""
        bp = mock_debugger.add_breakpoint("TestAgent", "test_method")

        # Auto-continue callback
        def auto_continue(frame):
            mock_debugger.continue_execution()

        mock_debugger.on_break(auto_continue)

        # Call method multiple times
        for i in range(5):
            def call():
                mock_debugger.on_method_call("TestAgent", "test_method")

            thread = threading.Thread(target=call)
            thread.start()
            thread.join(timeout=1.0)

        # Hit count should be 5
        assert bp.hit_count == 5

    def test_debugger_execution_trace_limit(self, mock_debugger):
        """Test that execution trace is limited to 1000 entries"""
        # Make 1100 calls
        for i in range(1100):
            mock_debugger.on_method_call("TestAgent", "test_method", payload={"call": i})

        # Should only keep last 1000
        trace = mock_debugger.get_execution_trace(limit=2000)
        assert len(trace) == 1000

        # Should be the most recent ones (call 100-1099)
        assert trace[0].payload["call"] == 100
        assert trace[-1].payload["call"] == 1099

    def test_debugger_multiple_callbacks(self, mock_debugger):
        """Test multiple on_break callbacks"""
        callback1_calls = []
        callback2_calls = []

        def callback1(frame):
            callback1_calls.append(frame.full_name)

        def callback2(frame):
            callback2_calls.append(frame.full_name)
            # Auto-continue
            mock_debugger.continue_execution()

        mock_debugger.on_break(callback1)
        mock_debugger.on_break(callback2)

        # Add breakpoint
        mock_debugger.add_breakpoint("TestAgent", "test_method")

        # Call method
        def call():
            mock_debugger.on_method_call("TestAgent", "test_method")

        thread = threading.Thread(target=call)
        thread.start()
        thread.join(timeout=1.0)

        # Both callbacks should have been called
        assert len(callback1_calls) == 1
        assert len(callback2_calls) == 1

    def test_debugger_disable_enables_correctly(self, mock_debugger):
        """Test enabling and disabling debugger"""
        assert mock_debugger.enabled is True

        # Disable
        mock_debugger.disable()
        assert mock_debugger.enabled is False

        # Method calls should not be traced
        mock_debugger.on_method_call("TestAgent", "test_method")
        assert len(mock_debugger.execution_trace) == 0

        # Re-enable
        mock_debugger.enable()
        assert mock_debugger.enabled is True

        # Should trace now
        mock_debugger.on_method_call("TestAgent", "test_method")
        assert len(mock_debugger.execution_trace) == 1
