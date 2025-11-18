"""
CLI Hooks - Callback system for external integrations (UI, TUI, etc.)

Allows external systems to receive real-time updates from GraphBus operations.
"""

import sys
import json
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class HookEvent:
    """Event sent to hooks"""
    type: str  # "message", "progress", "question", "error", "result"
    data: Dict[str, Any]
    source: str = "graphbus"

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))


class HookManager:
    """
    Manages callbacks for CLI operations.

    Hooks allow external systems (like UIs) to receive real-time updates:
    - Agent messages during negotiation
    - Progress updates during build
    - Questions that need user input
    - Errors and warnings
    - Final results
    """

    def __init__(self, output_stream=None):
        """
        Initialize hook manager.

        Args:
            output_stream: Stream to write hook events (default: stdout)
        """
        self.output_stream = output_stream or sys.stdout
        self.hooks: Dict[str, list] = {
            "message": [],
            "progress": [],
            "question": [],
            "error": [],
            "result": []
        }
        self.enabled = True

    def register(self, event_type: str, callback: Callable):
        """Register a callback for an event type"""
        if event_type not in self.hooks:
            self.hooks[event_type] = []
        self.hooks[event_type].append(callback)

    def emit(self, event_type: str, data: Dict[str, Any], source: str = "graphbus"):
        """
        Emit an event to all registered callbacks.

        Args:
            event_type: Type of event ("message", "progress", etc.)
            data: Event data
            source: Source of the event
        """
        if not self.enabled:
            return

        event = HookEvent(type=event_type, data=data, source=source)

        # Call registered callbacks
        for callback in self.hooks.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                print(f"Hook callback error: {e}", file=sys.stderr)

        # Write to output stream for external consumption
        self._write_event(event)

    def _write_event(self, event: HookEvent):
        """Write event to output stream in parseable format"""
        # Use special prefix so external systems can parse it
        line = f"HOOK:{event.to_json()}\n"
        self.output_stream.write(line)
        self.output_stream.flush()

    def message(self, text: str, agent: str = None, level: str = "info"):
        """Emit a message event"""
        self.emit("message", {
            "text": text,
            "agent": agent,
            "level": level
        })

    def progress(self, current: int, total: int, message: str = ""):
        """Emit a progress event"""
        self.emit("progress", {
            "current": current,
            "total": total,
            "message": message,
            "percent": int((current / total) * 100) if total > 0 else 0
        })

    def question(self, question: str, options: list = None, context: str = None) -> str:
        """
        Emit a question event and wait for response.

        Note: This is a sync operation. The external system should respond
        via stdin or another mechanism.

        Args:
            question: Question to ask
            options: List of possible answers
            context: Additional context for the question

        Returns:
            User's answer
        """
        self.emit("question", {
            "question": question,
            "options": options or [],
            "context": context
        })

        # Wait for answer from stdin
        # External system should write: ANSWER:<json>
        while True:
            line = sys.stdin.readline().strip()
            if line.startswith("ANSWER:"):
                answer_json = line[7:]
                try:
                    answer_data = json.loads(answer_json)
                    return answer_data.get("answer", "")
                except json.JSONDecodeError:
                    # Fallback: treat rest of line as answer
                    return answer_json

    def error(self, message: str, exception: Exception = None):
        """Emit an error event"""
        self.emit("error", {
            "message": message,
            "exception": str(exception) if exception else None,
            "type": type(exception).__name__ if exception else None
        })

    def result(self, data: Dict[str, Any]):
        """Emit a result event"""
        self.emit("result", data)

    def disable(self):
        """Disable hook emissions (for testing)"""
        self.enabled = False

    def enable(self):
        """Enable hook emissions"""
        self.enabled = True


# Global hook manager instance
_global_hooks: Optional[HookManager] = None


def get_hooks() -> HookManager:
    """Get the global hook manager"""
    global _global_hooks
    if _global_hooks is None:
        _global_hooks = HookManager()
    return _global_hooks


def set_hooks(hooks: HookManager):
    """Set the global hook manager"""
    global _global_hooks
    _global_hooks = hooks
