"""
Tests for REPL debugger commands
"""

import pytest
from io import StringIO
from unittest.mock import Mock, patch
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.runtime.debugger import InteractiveDebugger, ExecutionFrame
from graphbus_core.config import RuntimeConfig
from graphbus_cli.repl.runtime_repl import RuntimeREPL


@pytest.fixture
def mock_executor():
    """Create a mock executor with debugger"""
    executor = Mock(spec=RuntimeExecutor)
    debugger = InteractiveDebugger()
    debugger.enable()
    executor.debugger = debugger
    executor.bus = None  # No message bus for these tests
    return executor


class TestREPLDebuggerCommands:
    """Test REPL debugger commands"""

    def test_break_command_sets_breakpoint(self, mock_executor):
        """Test 'break' command sets a breakpoint"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_success') as mock_success:
            repl.do_break("TestAgent.test_method")

            # Check breakpoint was added
            assert "TestAgent.test_method" in mock_executor.debugger.breakpoints
            mock_success.assert_called_once()

    def test_break_command_with_condition(self, mock_executor):
        """Test 'break' command with condition"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_success'):
            repl.do_break("TestAgent.test_method payload['amount'] > 100")

            # Check breakpoint with condition
            bp = mock_executor.debugger.breakpoints["TestAgent.test_method"]
            assert bp.condition == "payload['amount'] > 100"

    def test_break_command_lists_breakpoints(self, mock_executor):
        """Test 'break' without args lists breakpoints"""
        repl = RuntimeREPL(mock_executor)

        # Add some breakpoints
        mock_executor.debugger.add_breakpoint("Agent1", "method1")
        mock_executor.debugger.add_breakpoint("Agent2", "method2")

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_break("")

            # Should print table
            mock_console.print.assert_called()

    def test_break_command_no_debugger(self):
        """Test 'break' command when debugger not enabled"""
        executor = Mock(spec=RuntimeExecutor)
        executor.debugger = None
        repl = RuntimeREPL(executor)

        with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
            repl.do_break("TestAgent.test_method")

            # Should show error
            mock_error.assert_called_once()
            assert "not enabled" in str(mock_error.call_args[0][0]).lower()

    def test_break_command_invalid_format(self, mock_executor):
        """Test 'break' with invalid format"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
            repl.do_break("InvalidFormat")

            # Should show error about format
            mock_error.assert_called_once()
            assert "format" in str(mock_error.call_args[0][0]).lower()

    def test_continue_command(self, mock_executor):
        """Test 'continue' command"""
        repl = RuntimeREPL(mock_executor)

        # Set debugger to paused state
        mock_executor.debugger.state = mock_executor.debugger.state.PAUSED

        with patch('graphbus_cli.repl.runtime_repl.print_info') as mock_info:
            repl.do_continue("")

            mock_info.assert_called_once()

    def test_step_command(self, mock_executor):
        """Test 'step' command"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_info') as mock_info:
            repl.do_step("")

            mock_info.assert_called_once()

    def test_inspect_command_shows_frame(self, mock_executor):
        """Test 'inspect' command shows current frame"""
        repl = RuntimeREPL(mock_executor)

        # Create a frame
        frame = ExecutionFrame(
            agent_name="TestAgent",
            method_name="test_method",
            payload={"key": "value"}
        )
        mock_executor.debugger.current_frame = frame

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_inspect("")

            # Should print table with frame info
            mock_console.print.assert_called()

    def test_inspect_payload(self, mock_executor):
        """Test 'inspect payload' shows payload"""
        repl = RuntimeREPL(mock_executor)

        # Create frame with payload
        frame = ExecutionFrame(
            agent_name="TestAgent",
            method_name="test_method",
            payload={"key": "value", "amount": 100}
        )
        mock_executor.debugger.current_frame = frame

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_inspect("payload")

            # Should print payload as JSON
            mock_console.print.assert_called()

    def test_inspect_locals(self, mock_executor):
        """Test 'inspect locals' shows local variables"""
        repl = RuntimeREPL(mock_executor)

        # Create frame with locals
        frame = ExecutionFrame(
            agent_name="TestAgent",
            method_name="test_method",
            payload=None,
            local_vars={"x": 10, "y": 20}
        )
        mock_executor.debugger.current_frame = frame

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_inspect("locals")

            # Should print locals
            mock_console.print.assert_called()

    def test_inspect_no_frame(self, mock_executor):
        """Test 'inspect' when no current frame"""
        repl = RuntimeREPL(mock_executor)

        mock_executor.debugger.current_frame = None

        with patch('graphbus_cli.repl.runtime_repl.print_info') as mock_info:
            repl.do_inspect("")

            mock_info.assert_called_once()
            assert "No current" in str(mock_info.call_args[0][0])

    def test_trace_command_shows_trace(self, mock_executor):
        """Test 'trace' command shows execution trace"""
        repl = RuntimeREPL(mock_executor)

        # Add some trace entries
        for i in range(5):
            mock_executor.debugger.on_method_call(
                f"Agent{i}",
                "method",
                payload={"count": i}
            )

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_trace("")

            # Should print table with trace
            mock_console.print.assert_called()

    def test_trace_with_limit(self, mock_executor):
        """Test 'trace' with custom limit"""
        repl = RuntimeREPL(mock_executor)

        # Add many trace entries
        for i in range(50):
            mock_executor.debugger.on_method_call("Agent", "method", payload={"i": i})

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_trace("10")

            # Should be called (exact number of calls hard to check without inspecting args)
            assert mock_console.print.called

    def test_trace_no_entries(self, mock_executor):
        """Test 'trace' when no trace entries"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_info') as mock_info:
            repl.do_trace("")

            mock_info.assert_called_once()
            assert "No execution trace" in str(mock_info.call_args[0][0])

    def test_clear_all_breakpoints(self, mock_executor):
        """Test 'clear' without args clears all breakpoints"""
        repl = RuntimeREPL(mock_executor)

        # Add breakpoints
        mock_executor.debugger.add_breakpoint("Agent1", "method1")
        mock_executor.debugger.add_breakpoint("Agent2", "method2")

        with patch('graphbus_cli.repl.runtime_repl.print_success') as mock_success:
            repl.do_clear("")

            # All breakpoints should be cleared
            assert len(mock_executor.debugger.breakpoints) == 0
            mock_success.assert_called_once()

    def test_clear_specific_breakpoint(self, mock_executor):
        """Test 'clear' with specific breakpoint"""
        repl = RuntimeREPL(mock_executor)

        # Add breakpoints
        mock_executor.debugger.add_breakpoint("Agent1", "method1")
        mock_executor.debugger.add_breakpoint("Agent2", "method2")

        with patch('graphbus_cli.repl.runtime_repl.print_success') as mock_success:
            repl.do_clear("Agent1.method1")

            # Only one should remain
            assert len(mock_executor.debugger.breakpoints) == 1
            assert "Agent2.method2" in mock_executor.debugger.breakpoints
            mock_success.assert_called_once()

    def test_clear_nonexistent_breakpoint(self, mock_executor):
        """Test 'clear' with non-existent breakpoint"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
            repl.do_clear("NonExistent.method")

            # Should show error
            mock_error.assert_called_once()
            assert "No breakpoint found" in str(mock_error.call_args[0][0])

    def test_clear_invalid_format(self, mock_executor):
        """Test 'clear' with invalid format"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
            repl.do_clear("InvalidFormat")

            # Should show error about format
            mock_error.assert_called_once()
            assert "format" in str(mock_error.call_args[0][0]).lower()

    def test_debugger_commands_without_debugger(self):
        """Test all debugger commands show error when debugger not enabled"""
        executor = Mock(spec=RuntimeExecutor)
        executor.debugger = None
        repl = RuntimeREPL(executor)

        commands = [
            ("do_continue", ""),
            ("do_step", ""),
            ("do_inspect", ""),
            ("do_trace", ""),
            ("do_clear", ""),
        ]

        for cmd_name, arg in commands:
            with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
                getattr(repl, cmd_name)(arg)
                mock_error.assert_called_once()

    def test_trace_invalid_limit(self, mock_executor):
        """Test 'trace' with invalid limit"""
        repl = RuntimeREPL(mock_executor)

        with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
            repl.do_trace("invalid")

            mock_error.assert_called_once()
            assert "Invalid limit" in str(mock_error.call_args[0][0])

    def test_breakpoint_hit_count_display(self, mock_executor):
        """Test that breakpoint list shows hit counts"""
        repl = RuntimeREPL(mock_executor)

        # Add breakpoint and hit it
        bp = mock_executor.debugger.add_breakpoint("TestAgent", "test_method")
        bp.hit_count = 5

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_break("")

            # Should print table (can't easily check content without more mocking)
            assert mock_console.print.called

    def test_inspect_unknown_target(self, mock_executor):
        """Test 'inspect' with unknown target"""
        repl = RuntimeREPL(mock_executor)

        # Create a frame
        frame = ExecutionFrame(
            agent_name="TestAgent",
            method_name="test_method",
            payload={}
        )
        mock_executor.debugger.current_frame = frame

        with patch('graphbus_cli.repl.runtime_repl.print_error') as mock_error:
            repl.do_inspect("unknown_target")

            mock_error.assert_called_once()
            assert "Unknown inspect target" in str(mock_error.call_args[0][0])

    def test_inspect_empty_payload(self, mock_executor):
        """Test inspecting empty/None payload"""
        repl = RuntimeREPL(mock_executor)

        frame = ExecutionFrame(
            agent_name="TestAgent",
            method_name="test_method",
            payload=None
        )
        mock_executor.debugger.current_frame = frame

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_inspect("payload")

            # Should show "No payload"
            mock_console.print.assert_called()
            call_args = str(mock_console.print.call_args)
            assert "No payload" in call_args

    def test_inspect_empty_locals(self, mock_executor):
        """Test inspecting empty local variables"""
        repl = RuntimeREPL(mock_executor)

        frame = ExecutionFrame(
            agent_name="TestAgent",
            method_name="test_method",
            payload=None,
            local_vars={}
        )
        mock_executor.debugger.current_frame = frame

        with patch('graphbus_cli.repl.runtime_repl.console') as mock_console:
            repl.do_inspect("locals")

            # Should show "No local variables"
            mock_console.print.assert_called()
            call_args = str(mock_console.print.call_args)
            assert "No local" in call_args
