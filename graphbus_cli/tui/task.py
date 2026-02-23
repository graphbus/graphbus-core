"""Task model for GraphBus TUI event loop."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime
import uuid


class TaskType(Enum):
    """Task types in the event loop."""
    PROPOSAL = "proposal"
    USER_INPUT = "user_input"
    DISPLAY = "display"
    AGENT_SPAWN = "agent_spawn"
    EVALUATION = "evaluation"
    NEGOTIATION_ROUND = "negotiation_round"


class TaskState(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Task priority levels (higher value = higher priority)."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    
    def __lt__(self, other):
        if not isinstance(other, Priority):
            return NotImplemented
        return self.value < other.value
    
    def __le__(self, other):
        if not isinstance(other, Priority):
            return NotImplemented
        return self.value <= other.value
    
    def __gt__(self, other):
        if not isinstance(other, Priority):
            return NotImplemented
        return self.value > other.value
    
    def __ge__(self, other):
        if not isinstance(other, Priority):
            return NotImplemented
        return self.value >= other.value


@dataclass
class Task:
    """Represents a task in the event loop queue."""
    
    type: TaskType
    priority: Priority = Priority.NORMAL
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data: dict = field(default_factory=dict)
    error: Optional[str] = None
    timeout_seconds: Optional[float] = None
    agent: Optional[str] = None
    proposal_id: Optional[str] = None
    
    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority (higher priority comes first in queue)."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at
    
    def mark_processing(self) -> None:
        """Mark task as started."""
        self.state = TaskState.PROCESSING
        self.started_at = datetime.utcnow()
    
    def mark_done(self) -> None:
        """Mark task as completed successfully."""
        self.state = TaskState.DONE
        self.completed_at = datetime.utcnow()
    
    def mark_error(self, error: str) -> None:
        """Mark task as failed with error message."""
        self.state = TaskState.ERROR
        self.completed_at = datetime.utcnow()
        self.error = error
    
    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.state = TaskState.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def is_complete(self) -> bool:
        """Check if task has finished (in any state)."""
        return self.state in (TaskState.DONE, TaskState.ERROR, TaskState.CANCELLED)
    
    def elapsed_seconds(self) -> float:
        """Get elapsed time since task was created."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def is_expired(self) -> bool:
        """Check if task has exceeded timeout."""
        if self.timeout_seconds is None:
            return False
        return self.elapsed_seconds() > self.timeout_seconds
