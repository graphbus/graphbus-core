"""
Interactive Debugger for GraphBus Runtime

Provides breakpoint support, step-through execution, and variable inspection.
"""

import threading
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DebuggerState(Enum):
    """Debugger execution state"""
    RUNNING = "running"
    PAUSED = "paused"
    STEP = "step"
    DISABLED = "disabled"


@dataclass
class Breakpoint:
    """Represents a breakpoint in the debugger"""
    agent_name: str
    method_name: str
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True

    @property
    def full_name(self) -> str:
        """Get full breakpoint name"""
        return f"{self.agent_name}.{self.method_name}"


@dataclass
class ExecutionFrame:
    """Represents an execution frame during debugging"""
    agent_name: str
    method_name: str
    payload: Any
    timestamp: datetime = field(default_factory=datetime.now)
    local_vars: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """Get full method name"""
        return f"{self.agent_name}.{self.method_name}"


class InteractiveDebugger:
    """
    Interactive debugger for GraphBus runtime.

    Features:
    - Breakpoints on method calls
    - Step-through execution
    - Variable inspection
    - Execution trace logging
    - Conditional breakpoints
    """

    def __init__(self):
        """Initialize debugger"""
        self.enabled = False
        self.state = DebuggerState.DISABLED
        self.breakpoints: Dict[str, Breakpoint] = {}
        self.execution_trace: List[ExecutionFrame] = []
        self.current_frame: Optional[ExecutionFrame] = None

        # Thread synchronization
        self._pause_event = threading.Event()
        self._step_event = threading.Event()
        self._lock = threading.Lock()

        # Callbacks
        self._on_break_callbacks: List[Callable[[ExecutionFrame], None]] = []

    def enable(self) -> None:
        """Enable the debugger"""
        with self._lock:
            self.enabled = True
            self.state = DebuggerState.RUNNING
            self._pause_event.set()  # Allow execution

    def disable(self) -> None:
        """Disable the debugger"""
        with self._lock:
            self.enabled = False
            self.state = DebuggerState.DISABLED
            self._pause_event.set()  # Release any waiting threads
            self._step_event.set()

    def add_breakpoint(self, agent_name: str, method_name: str,
                      condition: Optional[str] = None) -> Breakpoint:
        """
        Add a breakpoint.

        Args:
            agent_name: Agent name
            method_name: Method name
            condition: Optional condition expression

        Returns:
            Created breakpoint
        """
        with self._lock:
            full_name = f"{agent_name}.{method_name}"
            breakpoint = Breakpoint(
                agent_name=agent_name,
                method_name=method_name,
                condition=condition
            )
            self.breakpoints[full_name] = breakpoint
            return breakpoint

    def remove_breakpoint(self, agent_name: str, method_name: str) -> bool:
        """
        Remove a breakpoint.

        Args:
            agent_name: Agent name
            method_name: Method name

        Returns:
            True if breakpoint was removed
        """
        with self._lock:
            full_name = f"{agent_name}.{method_name}"
            if full_name in self.breakpoints:
                del self.breakpoints[full_name]
                return True
            return False

    def clear_breakpoints(self) -> None:
        """Clear all breakpoints"""
        with self._lock:
            self.breakpoints.clear()

    def list_breakpoints(self) -> List[Breakpoint]:
        """Get all breakpoints"""
        with self._lock:
            return list(self.breakpoints.values())

    def on_method_call(self, agent_name: str, method_name: str,
                      payload: Any = None, **kwargs) -> None:
        """
        Called before a method executes.

        Args:
            agent_name: Agent name
            method_name: Method name
            payload: Method payload
            **kwargs: Additional local variables
        """
        if not self.enabled:
            return

        # Create execution frame
        frame = ExecutionFrame(
            agent_name=agent_name,
            method_name=method_name,
            payload=payload,
            local_vars=kwargs
        )

        # Add to trace (keep last 1000 entries)
        with self._lock:
            self.execution_trace.append(frame)
            if len(self.execution_trace) > 1000:
                self.execution_trace = self.execution_trace[-1000:]
            self.current_frame = frame

        # Check for breakpoint
        full_name = f"{agent_name}.{method_name}"
        breakpoint = self.breakpoints.get(full_name)

        should_break = False
        if breakpoint and breakpoint.enabled:
            breakpoint.hit_count += 1

            # Check condition if present
            if breakpoint.condition:
                try:
                    # Evaluate condition in context of frame
                    context = {
                        'payload': payload,
                        'agent': agent_name,
                        'method': method_name,
                        **kwargs
                    }
                    should_break = eval(breakpoint.condition, {}, context)
                except Exception:
                    # If condition fails, break anyway
                    should_break = True
            else:
                should_break = True

        # Check if we're in step mode
        if self.state == DebuggerState.STEP:
            should_break = True

        if should_break:
            self._pause_execution(frame)

    def _pause_execution(self, frame: ExecutionFrame) -> None:
        """
        Pause execution at a breakpoint.

        Args:
            frame: Current execution frame
        """
        with self._lock:
            self.state = DebuggerState.PAUSED
            self._pause_event.clear()

        # Call break callbacks
        for callback in self._on_break_callbacks:
            try:
                callback(frame)
            except Exception:
                pass

        # Wait for continue or step
        self._pause_event.wait()

    def continue_execution(self) -> None:
        """Continue execution to next breakpoint"""
        with self._lock:
            if self.state == DebuggerState.PAUSED:
                self.state = DebuggerState.RUNNING
                self._pause_event.set()

    def step(self) -> None:
        """Step to next method call"""
        with self._lock:
            if self.state == DebuggerState.PAUSED:
                self.state = DebuggerState.STEP
                self._pause_event.set()

    def get_current_frame(self) -> Optional[ExecutionFrame]:
        """Get current execution frame"""
        with self._lock:
            return self.current_frame

    def get_execution_trace(self, limit: int = 100) -> List[ExecutionFrame]:
        """
        Get recent execution trace.

        Args:
            limit: Maximum number of frames to return

        Returns:
            List of recent execution frames
        """
        with self._lock:
            return self.execution_trace[-limit:]

    def inspect_payload(self) -> Any:
        """Inspect current frame payload"""
        with self._lock:
            if self.current_frame:
                return self.current_frame.payload
            return None

    def inspect_locals(self) -> Dict[str, Any]:
        """Inspect current frame local variables"""
        with self._lock:
            if self.current_frame:
                return self.current_frame.local_vars.copy()
            return {}

    def on_break(self, callback: Callable[[ExecutionFrame], None]) -> None:
        """
        Register callback for breakpoint hits.

        Args:
            callback: Function to call when breakpoint is hit
        """
        self._on_break_callbacks.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get debugger statistics.

        Returns:
            Dictionary of debugger stats
        """
        with self._lock:
            return {
                'enabled': self.enabled,
                'state': self.state.value,
                'breakpoints_count': len(self.breakpoints),
                'trace_entries': len(self.execution_trace),
                'current_frame': self.current_frame.full_name if self.current_frame else None
            }
