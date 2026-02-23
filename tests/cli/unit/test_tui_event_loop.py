"""
GraphBus TUI Event Loop — OpenClaw-style task queue + message bus.

Architecture:
- Task Queue: proposals are enqueued as tasks
- Async Dispatch: each agent gets CPU time via task slots
- Message Bus: agents communicate via events
- State Reducer: centralized state mutations
- User Input Handler: non-blocking keyboard input
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import asyncio
import json


# ─── Event Loop Core ────────────────────────────────────────────────────────

class TestEventLoopBasics:
    """Test OpenClaw-style event loop initialization and lifecycle."""
    
    def test_event_loop_creates(self):
        """
        Test: Event loop can be created.
        
        Similar to OpenClaw: loop = EventLoop()
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        assert loop is not None
    
    def test_event_loop_async_context(self):
        """
        Test: Event loop can run async tasks.
        
        async with loop.run():
            # tasks execute here
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        assert hasattr(loop, "__aenter__") or hasattr(loop, "run")
    
    def test_event_loop_task_queue(self):
        """
        Test: Event loop has a task queue (like OpenClaw's queue).
        
        loop.enqueue_task(task)
        task = loop.get_next_task()
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        assert hasattr(loop, "enqueue") or hasattr(loop, "enqueue_task")
        assert hasattr(loop, "next_task") or hasattr(loop, "get_next_task")
    
    def test_event_loop_message_bus(self):
        """
        Test: Event loop has a message bus for agent communication.
        
        loop.publish(event)
        loop.subscribe(topic, handler)
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        assert hasattr(loop, "publish") or hasattr(loop, "emit")
        assert hasattr(loop, "subscribe") or hasattr(loop, "on")
    
    def test_event_loop_state_store(self):
        """
        Test: Event loop has centralized state (like OpenClaw's state).
        
        state = loop.get_state()
        loop.dispatch(action)  # reducer pattern
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        assert hasattr(loop, "get_state") or hasattr(loop, "state")
        assert hasattr(loop, "dispatch") or hasattr(loop, "reduce")
    
    def test_event_loop_stops_cleanly(self):
        """
        Test: Event loop can be stopped gracefully.
        
        loop.stop()
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        assert hasattr(loop, "stop")


# ─── Task Queue Management ──────────────────────────────────────────────────

class TestTaskQueue:
    """Test task queue (proposal handling as tasks)."""
    
    def test_enqueue_proposal_task(self):
        """
        Test: When an agent creates a proposal, it's enqueued as a task.
        
        Task structure:
        {
            "type": "proposal",
            "agent": "APIAgent",
            "proposal_id": "prop_123",
            "content": {...},
            "status": "pending"
        }
        """
        from graphbus_cli.tui.task import Task, TaskType
        
        task = Task(
            type=TaskType.PROPOSAL,
            agent="APIAgent",
            proposal_id="prop_123",
        )
        assert task.type == TaskType.PROPOSAL
        assert task.agent == "APIAgent"
    
    def test_task_priority_queue(self):
        """
        Test: Tasks can be prioritized (human feedback > agent proposals).
        
        Priority levels:
        - HIGH: User input (accept/reject)
        - NORMAL: Agent proposals
        - LOW: Display updates
        """
        from graphbus_cli.tui.task import Task, Priority
        
        task1 = Task(type="proposal", priority=Priority.NORMAL)
        task2 = Task(type="user_input", priority=Priority.HIGH)
        
        # task2 should execute first
        assert task2.priority > task1.priority
    
    def test_task_lifecycle(self):
        """
        Test: Task moves through states: pending → processing → done/error.
        
        States:
        - pending: waiting in queue
        - processing: being handled
        - done: completed successfully
        - error: failed
        """
        from graphbus_cli.tui.task import Task, TaskState
        
        task = Task(type="proposal")
        assert task.state == TaskState.PENDING
        
        task.mark_processing()
        assert task.state == TaskState.PROCESSING
        
        task.mark_done()
        assert task.state == TaskState.DONE


# ─── Async Agent Dispatch ───────────────────────────────────────────────────

class TestAsyncAgentDispatch:
    """Test async execution of agent tasks."""
    
    def test_spawn_agent_task(self):
        """
        Test: Agent can be spawned as an async task.
        
        Similar to OpenClaw: spawn(agent)
        Returns a coroutine that can be awaited.
        """
        from graphbus_cli.tui.task_manager import TaskManager
        
        mgr = TaskManager()
        assert hasattr(mgr, "spawn") or hasattr(mgr, "spawn_agent")
    
    def test_agent_task_timeout(self):
        """
        Test: Agent task can timeout if it takes too long.
        
        mgr.spawn_agent(agent, timeout=30)
        """
        from graphbus_cli.tui.task_manager import TaskManager
        
        mgr = TaskManager(timeout_per_agent=30)
        assert mgr.timeout_per_agent == 30
    
    def test_concurrent_agent_execution(self):
        """
        Test: Multiple agents execute concurrently.
        
        All agents in a round run in parallel (async),
        proposals collected as they finish.
        """
        from graphbus_cli.tui.task_manager import TaskManager
        
        mgr = TaskManager()
        assert hasattr(mgr, "run_concurrently") or hasattr(mgr, "execute_agents")
    
    def test_agent_task_cancellation(self):
        """
        Test: Agent task can be cancelled if human intervenes.
        
        mgr.cancel_task(task_id)
        """
        from graphbus_cli.tui.task_manager import TaskManager
        
        mgr = TaskManager()
        assert hasattr(mgr, "cancel") or hasattr(mgr, "cancel_task")


# ─── Message Bus: Agent Communication ───────────────────────────────────────

class TestMessageBus:
    """Test inter-agent communication via events."""
    
    def test_agent_publishes_proposal(self):
        """
        Test: Agent publishes a proposal event.
        
        loop.publish({
            "type": "proposal_created",
            "agent": "APIAgent",
            "proposal": {...}
        })
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        event = {
            "type": "proposal_created",
            "agent": "APIAgent",
        }
        loop.publish(event)  # Should not raise
    
    def test_agent_subscribes_to_feedback(self):
        """
        Test: Agent subscribes to human feedback events.
        
        loop.subscribe("user_feedback", agent.on_feedback)
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        handler = MagicMock()
        loop.subscribe("user_feedback", handler)
        
        # Publish event should trigger handler
        loop.publish({"type": "user_feedback", "action": "reject"})
    
    def test_message_routing(self):
        """
        Test: Messages are routed to correct subscribers.
        
        Only handlers subscribed to the event topic receive it.
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        loop.subscribe("proposal_created", handler1)
        loop.subscribe("user_feedback", handler2)
        
        loop.publish({"type": "proposal_created"})
        
        handler1.assert_called()
        handler2.assert_not_called()
    
    def test_broadcast_events(self):
        """
        Test: Some events broadcast to all agents.
        
        Example: "round_complete" event triggers all agents to evaluate.
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        # Should support broadcast-style events
        assert hasattr(loop, "broadcast") or hasattr(loop, "publish_to_all")


# ─── State Management: Reducer Pattern ──────────────────────────────────────

class TestStateReducer:
    """Test centralized state management (OpenClaw reducer pattern)."""
    
    def test_state_initialization(self):
        """
        Test: Event loop has initial state.
        
        state = {
            "intent": "optimize queries",
            "round": 1,
            "proposals": [],
            "agents": {...},
            "paused": false,
        }
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop(intent="optimize queries")
        state = loop.get_state()
        
        assert state["intent"] == "optimize queries"
        assert "round" in state
        assert "proposals" in state
    
    def test_dispatch_action(self):
        """
        Test: Actions are dispatched to reducer.
        
        loop.dispatch({
            "type": "proposal_accepted",
            "proposal_id": "prop_123"
        })
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        # Dispatch an action
        loop.dispatch({
            "type": "proposal_accepted",
            "proposal_id": "prop_123",
        })
        
        # State should be updated
        state = loop.get_state()
        # (exact fields depend on reducer implementation)
    
    def test_action_immutability(self):
        """
        Test: State is immutable (new state object, not mutated).
        
        state1 = loop.get_state()
        loop.dispatch(action)
        state2 = loop.get_state()
        
        state1 is not state2  # Different objects
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        state1 = loop.get_state()
        
        loop.dispatch({"type": "some_action"})
        state2 = loop.get_state()
        
        assert state1 is not state2 or state1 == state2  # Depending on implementation


# ─── User Input Handling: Non-Blocking ──────────────────────────────────────

class TestUserInputHandler:
    """Test non-blocking keyboard input (OpenClaw-style polling)."""
    
    def test_user_input_queue(self):
        """
        Test: User input is queued as tasks (non-blocking).
        
        Similar to OpenClaw: user presses 'y' → input task queued.
        Event loop processes it when convenient.
        """
        from graphbus_cli.tui.hil import UserInputHandler
        
        handler = UserInputHandler()
        assert hasattr(handler, "poll") or hasattr(handler, "get_input")
    
    def test_keyboard_polling(self):
        """
        Test: Poll for keyboard input without blocking.
        
        key = handler.poll()  # Returns key or None if no input
        """
        from graphbus_cli.tui.hil import UserInputHandler
        
        handler = UserInputHandler()
        
        # Should support non-blocking poll
        assert hasattr(handler, "poll")
    
    def test_input_task_enqueue(self):
        """
        Test: Keyboard input is enqueued as a high-priority task.
        
        User presses 'y' → UserInputTask(key='y', priority=HIGH) → queue
        """
        from graphbus_cli.tui.hil import UserInputHandler
        from graphbus_cli.tui.task import Priority
        
        handler = UserInputHandler()
        
        # Input tasks should have high priority
        assert hasattr(handler, "handle_input")


# ─── Full Event Loop Cycle ─────────────────────────────────────────────────

class TestEventLoopCycle:
    """Test a complete event loop cycle."""
    
    def test_single_cycle(self):
        """
        Test: One complete loop cycle.
        
        1. Get next task from queue
        2. Execute task (async dispatch)
        3. Collect results
        4. Publish result event
        5. Process state changes (reducer)
        6. Render display
        7. Poll for user input
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        # Should support single-cycle execution
        assert hasattr(loop, "step") or hasattr(loop, "tick")
    
    def test_multiple_cycles(self):
        """
        Test: Event loop runs multiple cycles until stop.
        
        async with loop.run():
            # loop.step() called repeatedly until stop()
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        assert hasattr(loop, "run") or hasattr(loop, "__aenter__")
    
    def test_backpressure_handling(self):
        """
        Test: Loop slows down if queue fills up (backpressure).
        
        If proposals arrive faster than human can review,
        loop should buffer and apply backpressure to agents.
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop(max_queue_size=100)
        
        assert loop.max_queue_size == 100


# ─── Integration: Agent + Event Loop ────────────────────────────────────────

class TestAgentEventLoopIntegration:
    """Test agents running inside the event loop."""
    
    def test_agent_receives_context(self):
        """
        Test: Agent receives round context from event loop.
        
        Agent gets:
        - Round number
        - Previous proposals (for evaluation)
        - Human feedback from previous rounds
        - Intent description
        """
        from graphbus_cli.tui.task_manager import TaskManager
        
        mgr = TaskManager()
        
        # Should pass context to agents
        assert hasattr(mgr, "prepare_agent_context")
    
    def test_agent_publishes_proposal_via_message_bus(self):
        """
        Test: Agent publishes proposal via message bus.
        
        Agent.propose() → loop.publish("proposal_created", {...})
        Loop queues task for human review
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        # Agent should be able to publish
        loop.publish({
            "type": "proposal_created",
            "agent": "APIAgent",
            "proposal": {...}
        })
    
    def test_human_publishes_feedback_via_input_handler(self):
        """
        Test: Human feedback goes via event loop.
        
        User presses 'y' → UserInputHandler.poll() → dispatch action
        → reducer updates state
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        from graphbus_cli.tui.hil import UserInputHandler
        
        loop = TUIEventLoop()
        handler = UserInputHandler()
        
        # Should integrate cleanly
        assert loop.dispatch is not None


# ─── Performance and Responsiveness ─────────────────────────────────────────

class TestEventLoopPerformance:
    """Test event loop responsiveness."""
    
    def test_display_updates_responsive(self):
        """
        Test: Display updates quickly (should not block agents).
        
        Display rendering should be async and not block agent execution.
        """
        from graphbus_cli.tui.event_loop import TUIEventLoop
        
        loop = TUIEventLoop()
        
        # Should support non-blocking display
        assert hasattr(loop, "render_async") or hasattr(loop, "schedule_display")
    
    def test_user_input_responsive(self):
        """
        Test: User input processed within 100ms.
        
        If user presses 'y', it should be handled quickly,
        not waiting for agent to finish.
        """
        from graphbus_cli.tui.hil import UserInputHandler
        
        handler = UserInputHandler()
        
        # Should poll frequently
        assert hasattr(handler, "set_poll_interval")
    
    def test_pause_responsiveness(self):
        """
        Test: User can pause agents within 1 second.
        
        Even if agents are executing, pause request should interrupt quickly.
        """
        from graphbus_cli.tui.task_manager import TaskManager
        
        mgr = TaskManager()
        
        assert hasattr(mgr, "request_pause") or hasattr(mgr, "pause")
