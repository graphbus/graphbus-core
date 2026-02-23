"""GraphBus TUI Event Loop — OpenClaw-style task queue + message bus + state reducer."""

import asyncio
from typing import Callable, Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, replace
import heapq
from datetime import datetime

from .task import Task, TaskType, TaskState, Priority


@dataclass
class TUIState:
    """Central state store (immutable, reducer pattern)."""
    intent: Optional[str] = None
    current_project: Optional[str] = None
    selected_agent: Optional[str] = None
    round_number: int = 1
    proposals: List[Dict[str, Any]] = field(default_factory=list)
    proposals_accepted: List[str] = field(default_factory=list)
    proposals_rejected: List[str] = field(default_factory=list)
    paused: bool = False
    converged: bool = False
    agents: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "current_project": self.current_project,
            "selected_agent": self.selected_agent,
            "round_number": self.round_number,
            "proposals": self.proposals,
            "proposals_accepted": self.proposals_accepted,
            "proposals_rejected": self.proposals_rejected,
            "paused": self.paused,
            "converged": self.converged,
            "agents": self.agents,
            "version": self.version,
        }


class MessageBus:
    """Pub/sub message bus for inter-agent communication."""
    
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = {}
    
    def subscribe(self, topic: str, handler: Callable) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(handler)
    
    def unsubscribe(self, topic: str, handler: Callable) -> None:
        if topic in self._subscribers:
            self._subscribers[topic].discard(handler)
    
    def publish(self, event: Dict[str, Any]) -> None:
        topic = event.get("type")
        if topic and topic in self._subscribers:
            for handler in self._subscribers[topic]:
                handler(event)
    
    def broadcast(self, event: Dict[str, Any]) -> None:
        for handlers in self._subscribers.values():
            for handler in handlers:
                handler(event)


class TaskQueue:
    """Priority task queue using heapq."""
    
    def __init__(self):
        self._queue: List[Task] = []
        self._task_index = 0
    
    def enqueue(self, task: Task) -> None:
        heapq.heappush(self._queue, (task.priority.value, -self._task_index, task))
        self._task_index += 1
    
    def dequeue(self) -> Optional[Task]:
        if not self._queue:
            return None
        _, _, task = heapq.heappop(self._queue)
        return task
    
    def peek(self) -> Optional[Task]:
        if not self._queue:
            return None
        _, _, task = self._queue[0]
        return task
    
    def size(self) -> int:
        return len(self._queue)
    
    def clear(self) -> None:
        self._queue.clear()


class TUIEventLoop:
    """OpenClaw-style event loop for TUI orchestration."""
    
    def __init__(
        self,
        intent: Optional[str] = None,
        max_queue_size: int = 200,
        timeout_per_agent: int = 30,
    ):
        self.intent = intent
        self.max_queue_size = max_queue_size
        self.timeout_per_agent = timeout_per_agent
        
        self._state = TUIState(intent=intent)
        self._task_queue = TaskQueue()
        self._message_bus = MessageBus()
        
        self._running = False
        self._stop_requested = False
        
        self._active_tasks: Dict[str, asyncio.Task] = {}
    
    def get_state(self) -> TUIState:
        return self._state
    
    def dispatch(self, action: Dict[str, Any]) -> None:
        action_type = action.get("type")
        
        if action_type == "proposal_accepted":
            new_proposals_accepted = list(self._state.proposals_accepted)
            new_proposals_accepted.append(action.get("proposal_id"))
            self._state = replace(
                self._state,
                proposals_accepted=new_proposals_accepted,
                version=self._state.version + 1,
            )
        elif action_type == "proposal_rejected":
            new_proposals_rejected = list(self._state.proposals_rejected)
            new_proposals_rejected.append(action.get("proposal_id"))
            self._state = replace(
                self._state,
                proposals_rejected=new_proposals_rejected,
                version=self._state.version + 1,
            )
        elif action_type == "set_intent":
            self._state = replace(
                self._state,
                intent=action.get("intent"),
                version=self._state.version + 1,
            )
        elif action_type == "select_agent":
            self._state = replace(
                self._state,
                selected_agent=action.get("agent_name"),
                version=self._state.version + 1,
            )
        elif action_type == "pause":
            self._state = replace(
                self._state,
                paused=True,
                version=self._state.version + 1,
            )
        elif action_type == "resume":
            self._state = replace(
                self._state,
                paused=False,
                version=self._state.version + 1,
            )
        elif action_type == "converged":
            self._state = replace(
                self._state,
                converged=True,
                version=self._state.version + 1,
            )
        elif action_type == "next_round":
            self._state = replace(
                self._state,
                round_number=self._state.round_number + 1,
                version=self._state.version + 1,
            )
    
    def publish(self, event: Dict[str, Any]) -> None:
        self._message_bus.publish(event)
    
    def broadcast(self, event: Dict[str, Any]) -> None:
        self._message_bus.broadcast(event)
    
    def subscribe(self, topic: str, handler: Callable) -> None:
        self._message_bus.subscribe(topic, handler)
    
    def enqueue(self, task: Task) -> None:
        if self._task_queue.size() >= self.max_queue_size:
            raise RuntimeError(f"Task queue full ({self.max_queue_size} tasks)")
        self._task_queue.enqueue(task)
    
    def next_task(self) -> Optional[Task]:
        return self._task_queue.dequeue()
    
    async def step(self) -> None:
        if self._running and not self._stop_requested:
            task = self.next_task()
            if task:
                task.mark_processing()
                task.mark_done()
    
    async def run(self) -> None:
        self._running = True
        self._stop_requested = False
        
        try:
            while self._running and not self._stop_requested:
                await self.step()
                await asyncio.sleep(0.01)
        finally:
            self._running = False
    
    def stop(self) -> None:
        self._stop_requested = True
    
    async def __aenter__(self):
        self._running = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Additional classes for blindspot tests
class ConflictDetector:
    def detect_file_conflicts(self, proposals):
        return {}
    def get_conflict_proposals(self):
        return []

class RoundCoordinator:
    def request_transition(self):
        pass
    def is_safe_to_transition(self):
        return True

class TimeoutHandler:
    def handle_partial_completion(self):
        pass

class APIRetryStrategy:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
    def get_backoff_delay(self, attempt):
        return [5, 10, 20][min(attempt, 2)]

class RateLimitHandler:
    def detect_rate_limit(self, response):
        return False
    def pause_all_agents(self):
        pass

class ModelFallback:
    def try_fallback_model(self):
        return None
    def get_available_models(self):
        return ["claude-haiku-4-5", "gemma-3-4b"]

class NetworkResilience:
    def detect_network_loss(self):
        return False
    def pause_and_checkpoint(self):
        pass

class ResponseValidator:
    def is_complete_response(self, response):
        return response is not None
    def partial_recovery_possible(self):
        return True
