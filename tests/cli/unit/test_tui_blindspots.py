"""
GraphBus TUI Blindspot Tests — edge cases and failure modes.

Identifies hidden assumptions and potential failure points.
"""

import pytest
from pathlib import Path
import asyncio
from unittest.mock import patch, MagicMock


# ─── Concurrency Edge Cases ──────────────────────────────────────────────────

class TestConcurrencyEdgeCases:
    """Test concurrent agent behavior."""
    
    def test_simultaneous_proposals_same_file(self):
        """
        Blindspot: What if two agents propose changes to the same file?
        
        Round 1:
        - DataAgent: "Add index on user_id" (schema.sql)
        - APIAgent: "Update query to use new index" (queries.py)
        
        But both reference the same change in different ways.
        Need to detect and reconcile.
        """
        from graphbus_cli.tui.event_loop import ConflictDetector
        
        detector = ConflictDetector()
        
        assert hasattr(detector, "detect_file_conflicts")
        assert hasattr(detector, "get_conflict_proposals")
    
    def test_race_condition_proposal_accept(self):
        """
        Blindspot: What if human accepts proposal while agent is modifying it?
        
        1. Agent is writing proposal_123
        2. Proposal gets queued (partial)
        3. Human accepts it (race condition)
        4. Should wait for proposal to be complete
        """
        from graphbus_cli.tui.task import Task, TaskState
        
        task = Task(type="proposal")
        
        # Should not allow acceptance until complete
        assert hasattr(task, "is_complete")
    
    def test_concurrent_round_transitions(self):
        """
        Blindspot: What if human accepts final proposal while round 2 starting?
        
        State: Round 1 evaluations finishing, Round 2 starting
        Human: Accepts Round 1 proposal and marks done
        Agents: Already spawning for Round 2
        
        Should cleanly transition or stop round 2.
        """
        from graphbus_cli.tui.event_loop import RoundCoordinator
        
        coord = RoundCoordinator()
        
        assert hasattr(coord, "request_transition")
        assert hasattr(coord, "is_safe_to_transition")
    
    def test_agent_timeout_mid_proposal(self):
        """
        Blindspot: Agent times out while writing proposal.
        
        Agent is at 29.9 seconds of 30 second timeout.
        Proposal is 90% complete.
        Timeout fires before proposal finishes.
        
        Should save partial work or retry.
        """
        from graphbus_cli.tui.task_manager import TimeoutHandler
        
        handler = TimeoutHandler()
        
        assert hasattr(handler, "handle_partial_completion")


# ─── Network and API Failures ────────────────────────────────────────────────

class TestNetworkFailures:
    """Test handling of network and API failures."""
    
    def test_agent_api_timeout_retry(self):
        """
        Blindspot: Agent calls LLM API, request times out after 30s.
        
        Should retry with exponential backoff.
        Max retries: 3
        Backoff: 5s, 10s, 20s
        If all fail, agent skips round.
        """
        from graphbus_cli.tui.agent_loop import APIRetryStrategy
        
        strategy = APIRetryStrategy(max_retries=3)
        
        assert strategy.max_retries == 3
        assert hasattr(strategy, "get_backoff_delay")
    
    def test_agent_api_rate_limited(self):
        """
        Blindspot: API returns 429 (rate limited).
        
        Should detect and back off across all agents.
        If one agent hits rate limit, pause all agents.
        Display: "Rate limited, resuming in 60s..."
        """
        from graphbus_cli.tui.agent_loop import RateLimitHandler
        
        handler = RateLimitHandler()
        
        assert hasattr(handler, "detect_rate_limit")
        assert hasattr(handler, "pause_all_agents")
    
    def test_model_endpoint_unreachable(self):
        """
        Blindspot: Assigned model endpoint is down.
        
        Agent spawned with model="claude-haiku-4-5"
        Endpoint unreachable.
        
        Should fallback to next available model,
        or show error and allow human to choose alternative.
        """
        from graphbus_cli.tui.agent_loop import ModelFallback
        
        fallback = ModelFallback()
        
        assert hasattr(fallback, "try_fallback_model")
        assert hasattr(fallback, "get_available_models")
    
    def test_connection_lost_mid_negotiation(self):
        """
        Blindspot: Internet connection drops during negotiation.
        
        Agents executing, API calls start failing.
        Should gracefully pause, cache state,
        allow resume when connection restored.
        """
        from graphbus_cli.tui.event_loop import NetworkResilience
        
        resilience = NetworkResilience()
        
        assert hasattr(resilience, "detect_network_loss")
        assert hasattr(resilience, "pause_and_checkpoint")
    
    def test_partial_response_from_api(self):
        """
        Blindspot: API returns incomplete JSON response.
        
        Agent receives:
        {
            "type": "proposal",
            "agent": "APIAgent",
            "content": "Add cache layer to reduce...
        (truncated - connection lost)
        
        Should detect incomplete response and retry or reject.
        """
        from graphbus_cli.tui.agent_loop import ResponseValidator
        
        validator = ResponseValidator()
        
        assert hasattr(validator, "is_complete_response")
        assert hasattr(validator, "partial_recovery_possible")


# ─── State Consistency ───────────────────────────────────────────────────────

class TestStateConsistency:
    """Test state consistency between event loop and display."""
    
    def test_display_desync_with_state(self):
        """
        Blindspot: Display shows old state while event loop updated.
        
        Display rendering takes 100ms.
        User action completes, state changes.
        Display still showing old state, user confused.
        
        Should use versioned state or double-buffering.
        """
        from graphbus_cli.tui.display import StateSync
        
        sync = StateSync()
        
        assert hasattr(sync, "get_latest_state")
        assert hasattr(sync, "version_state")
    
    def test_proposal_accepted_but_not_displayed(self):
        """
        Blindspot: Human accepts proposal, but display glitches.
        
        State: proposal marked accepted
        Display: still shows pending
        Human: thinks proposal still needs review
        
        Should ensure state changes are reflected before displaying.
        """
        from graphbus_cli.tui.display import DisplayConsistency
        
        consistency = DisplayConsistency()
        
        assert hasattr(consistency, "validate_consistency")
    
    def test_round_mismatch_between_state_and_display(self):
        """
        Blindspot: Event loop on round 3, display shows round 2.
        
        Agents: proposing round 3 changes
        Display: showing round 2 queue
        Human: trying to review wrong round
        
        Should sync display to current round before showing.
        """
        from graphbus_cli.tui.state import StateValidator
        
        validator = StateValidator()
        
        assert hasattr(validator, "validate_round_consistency")


# ─── Token Counting and Context Window ───────────────────────────────────────

class TestTokenManagement:
    """Test handling of token limits and context windows."""
    
    def test_context_window_overflow(self):
        """
        Blindspot: After 10 rounds, context is too large for next agent.
        
        Context = prompt + all past proposals + feedback
        Agent has 6B tokens, context needs 8B.
        
        Should summarize old rounds before sending to agent.
        """
        from graphbus_cli.tui.agent_loop import ContextManager
        
        mgr = ContextManager(max_context_tokens=8000)
        
        assert hasattr(mgr, "summarize_old_rounds")
        assert hasattr(mgr, "estimate_token_count")
    
    def test_proposal_too_large_for_model(self):
        """
        Blindspot: Agent generates proposal larger than model's output limit.
        
        Model max: 4096 tokens
        Proposal: 5000 tokens
        
        Should split into multiple proposals or truncate intelligently.
        """
        from graphbus_cli.tui.agent_loop import ProposalSize
        
        sizer = ProposalSize(max_output=4096)
        
        assert hasattr(sizer, "split_large_proposal")
        assert hasattr(sizer, "validate_size")
    
    def test_token_count_estimation_accuracy(self):
        """
        Blindspot: Estimated tokens don't match actual tokens.
        
        Estimate: 3000 tokens
        Actual: 3500 tokens (different tokenizer)
        Agent runs out of space mid-proposal.
        
        Should use actual tokenizer from model provider.
        """
        from graphbus_cli.tui.agent_loop import TokenCounter
        
        counter = TokenCounter()
        
        assert hasattr(counter, "count_tokens_accurate")


# ─── Proposal Ordering and Dependencies ──────────────────────────────────────

class TestProposalOrdering:
    """Test ordering of proposal application."""
    
    def test_proposal_order_matters(self):
        """
        Blindspot: Two proposals conflict in order of application.
        
        Proposal 1: "Rename function foo() to optimize_queries()"
        Proposal 2: "Update call to foo() in API layer"
        
        If P2 applied first, P1 breaks it.
        Should apply in dependency order.
        """
        from graphbus_cli.tui.agent_loop import ProposalOrdering
        
        ordering = ProposalOrdering()
        
        assert hasattr(ordering, "detect_ordering_dependencies")
        assert hasattr(ordering, "topological_sort_proposals")
    
    def test_circular_dependency_in_proposals(self):
        """
        Blindspot: Proposals form circular dependency.
        
        P1: Add import X (needs P2 first)
        P2: Remove import X (needs P1 first)
        
        Circular! Can't apply either.
        Should detect and flag for human review.
        """
        from graphbus_cli.tui.agent_loop import ProposalOrdering
        
        ordering = ProposalOrdering()
        
        assert hasattr(ordering, "detect_circular_dependencies")


# ─── Intent Evolution ────────────────────────────────────────────────────────

class TestIntentEvolution:
    """Test handling of intent changes mid-negotiation."""
    
    def test_human_changes_intent_mid_negotiation(self):
        """
        Blindspot: Human changes goal mid-negotiation.
        
        Initial intent: "optimize database queries"
        Round 2: Human says "Actually, let's add caching instead"
        
        Should:
        1. Pause agents
        2. Ask confirmation: new intent replaces old?
        3. Restart with new intent or resume with both?
        """
        from graphbus_cli.tui.intent import IntentManager
        
        mgr = IntentManager()
        
        assert hasattr(mgr, "request_intent_change")
        assert hasattr(mgr, "merge_intents") or hasattr(mgr, "replace_intent")
    
    def test_human_refines_intent(self):
        """
        Blindspot: Human clarifies/refines intent.
        
        Intent: "optimize queries"
        Refinement: "Specifically, reduce latency < 100ms"
        
        Should incorporate refinement without restarting.
        """
        from graphbus_cli.tui.intent import IntentManager
        
        mgr = IntentManager()
        
        assert hasattr(mgr, "refine_intent")
    
    def test_contradictory_feedback_vs_intent(self):
        """
        Blindspot: Human feedback contradicts stated intent.
        
        Intent: "optimize for speed"
        Feedback: Rejects performance optimization (wants readability instead)
        
        Should warn human or infer actual intent.
        """
        from graphbus_cli.tui.intent import IntentValidator
        
        validator = IntentValidator()
        
        assert hasattr(validator, "check_feedback_alignment")


# ─── Memory Corruption and Recovery ──────────────────────────────────────────

class TestMemoryRobustness:
    """Test memory file corruption and recovery."""
    
    def test_corrupted_memory_file(self):
        """
        Blindspot: Memory JSON file is corrupted/truncated.
        
        File: ~/.graphbus/projects/myapp/memory/session_001.json
        Content: truncated mid-JSON
        
        Should detect and recover from backup, or skip.
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        
        assert hasattr(store, "validate_memory_file")
        assert hasattr(store, "recover_from_backup")
    
    def test_memory_file_permission_denied(self):
        """
        Blindspot: Can't write to memory directory (permission denied).
        
        Should warn but continue negotiation.
        Memory loss on restart, but negotiation completes.
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        
        assert hasattr(store, "check_write_permissions")
    
    def test_memory_disk_full(self):
        """
        Blindspot: Disk full while saving memory.
        
        Should warn, fall back to in-memory only for this session,
        offer to clean up old memory.
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        
        assert hasattr(store, "handle_disk_full")


# ─── Deadlocks and Infinite Loops ───────────────────────────────────────────

class TestDeadlocksAndLoops:
    """Test detection and prevention of deadlocks."""
    
    def test_agent_waiting_for_feedback_forever(self):
        """
        Blindspot: Agent is stalled waiting for human feedback.
        
        Agent A proposed change, waiting for acceptance.
        Agent B can't proceed without A's proposal accepted.
        Human: forgot to respond, went to lunch.
        
        After 5 minutes, should timeout and pause.
        """
        from graphbus_cli.tui.agent_loop import StallDetector
        
        detector = StallDetector(timeout_seconds=300)
        
        assert hasattr(detector, "detect_stalled_agent")
    
    def test_agent_looping_same_proposal(self):
        """
        Blindspot: Agent keeps proposing the same change.
        
        Round 1: "Add index on user_id"
        Round 2: "Add index on user_id" (ignored, human feedback not clear)
        Round 3: "Add index on user_id" (stuck in loop!)
        
        Should detect and break loop.
        """
        from graphbus_cli.tui.agent_loop import LoopDetector
        
        detector = LoopDetector()
        
        assert hasattr(detector, "detect_proposal_loop")
        assert hasattr(detector, "suggest_break_loop_action")
    
    def test_circular_agent_dependencies(self):
        """
        Blindspot: Agents waiting for each other.
        
        Agent A depends on Agent B's proposal
        Agent B depends on Agent A's proposal
        
        Classic circular dependency deadlock.
        Should detect and flag.
        """
        from graphbus_cli.tui.agent_loop import DeadlockDetector
        
        detector = DeadlockDetector()
        
        assert hasattr(detector, "detect_circular_dependencies")


# ─── Model Availability and Fallback ─────────────────────────────────────────

class TestModelAvailability:
    """Test handling of model unavailability."""
    
    def test_assigned_model_rate_limited(self):
        """
        Blindspot: Assigned model hits rate limit.
        
        Agent configured to use claude-haiku-4-5.
        API returns 429 (rate limited).
        
        Should fallback to next tier (opus) or different provider.
        """
        from graphbus_cli.tui.agent_loop import ModelFallback
        
        fallback = ModelFallback()
        
        assert hasattr(fallback, "has_fallback_available")
        assert hasattr(fallback, "suggest_fallback")
    
    def test_model_requires_authentication(self):
        """
        Blindspot: Model endpoint requires auth token.
        
        Agent configured to use local model.
        Endpoint responds: 401 Unauthorized.
        
        Should prompt for credentials or fallback.
        """
        from graphbus_cli.tui.agent_loop import AuthHandler
        
        handler = AuthHandler()
        
        assert hasattr(handler, "handle_auth_failure")
    
    def test_all_models_unavailable(self):
        """
        Blindspot: All configured models are unavailable.
        
        Primary: rate limited
        Fallback 1: offline
        Fallback 2: auth failed
        
        Should gracefully pause and wait for user action.
        """
        from graphbus_cli.tui.agent_loop import ModelAvailability
        
        mgr = ModelAvailability()
        
        assert hasattr(mgr, "get_available_models")
        assert hasattr(mgr, "wait_for_availability")


# ─── Large-Scale and Performance ─────────────────────────────────────────────

class TestLargeScalePerformance:
    """Test behavior with large-scale operations."""
    
    def test_many_proposals_queue_overload(self):
        """
        Blindspot: Agents proposing faster than human can review.
        
        Round 1: 50 agents, each propose → 50 proposals
        Human can review max 2/minute
        Queue backs up to 500 pending.
        
        Should apply backpressure to agents.
        """
        from graphbus_cli.tui.event_loop import Backpressure
        
        bp = Backpressure(max_queue_size=200)
        
        assert bp.max_queue_size == 200
        assert hasattr(bp, "apply_backpressure")
    
    def test_very_large_codebase_many_files(self):
        """
        Blindspot: Ingesting massive codebase (10,000+ files).
        
        Ingest creates 500 agents.
        Graph visualization becomes unreadable.
        Memory usage spikes.
        
        Should handle gracefully, paginate display, summarize.
        """
        from graphbus_cli.tui.display import LargeGraphHandler
        
        handler = LargeGraphHandler(max_agents_to_display=20)
        
        assert hasattr(handler, "paginate_agents")
        assert hasattr(handler, "summarize_graph")
    
    def test_long_running_negotiation_memory_leak(self):
        """
        Blindspot: Negotiation runs for hours, memory grows unbounded.
        
        Each round adds history, proposals, evaluations.
        After 100 rounds, memory usage is 2GB.
        
        Should clean up old rounds, archive old context.
        """
        from graphbus_cli.tui.memory import MemoryCompaction
        
        compaction = MemoryCompaction()
        
        assert hasattr(compaction, "archive_old_rounds")
        assert hasattr(compaction, "compress_history")


# ─── User Input Edge Cases ──────────────────────────────────────────────────

class TestUserInputEdgeCases:
    """Test edge cases in user input handling."""
    
    def test_rapid_key_presses(self):
        """
        Blindspot: User spams keys rapidly.
        
        User repeatedly presses 'y' (accept) while navigating.
        Multiple input tasks queued.
        Could accept multiple proposals unintentionally.
        
        Should debounce or require confirmation for repeated actions.
        """
        from graphbus_cli.tui.hil import InputDebouncer
        
        debouncer = InputDebouncer(debounce_ms=500)
        
        assert hasattr(debouncer, "filter_duplicate_input")
    
    def test_terminal_resize_mid_display(self):
        """
        Blindspot: User resizes terminal while displaying graph.
        
        Display is 80x24, user resizes to 200x50.
        Could cause rendering corruption.
        
        Should detect and re-render.
        """
        from graphbus_cli.tui.display import ResizeHandler
        
        handler = ResizeHandler()
        
        assert hasattr(handler, "detect_resize")
        assert hasattr(handler, "redraw_full_screen")
    
    def test_paste_large_text_into_input(self):
        """
        Blindspot: User pastes 10KB of text into input field.
        
        System might crash or behave unexpectedly.
        Should limit input size or handle gracefully.
        """
        from graphbus_cli.tui.hil import InputValidator
        
        validator = InputValidator(max_input_size=1000)
        
        assert hasattr(validator, "validate_input_size")


# ─── Proposal Validation ─────────────────────────────────────────────────────

class TestProposalValidation:
    """Test validation of proposals."""
    
    def test_proposal_with_syntax_errors(self):
        """
        Blindspot: Agent proposes invalid Python code.
        
        Proposal: "def foo(: pass"  (syntax error)
        
        Should detect and ask agent to fix before committing.
        """
        from graphbus_cli.tui.agent_loop import ProposalValidator
        
        validator = ProposalValidator()
        
        assert hasattr(validator, "validate_code_syntax")
    
    def test_proposal_deletes_critical_files(self):
        """
        Blindspot: Agent proposes deleting critical files.
        
        Proposal: "rm -rf /home/ubuntu/important.py"
        
        Should warn and require confirmation.
        """
        from graphbus_cli.tui.agent_loop import SafetyValidator
        
        validator = SafetyValidator()
        
        assert hasattr(validator, "check_dangerous_operations")
    
    def test_proposal_creates_infinite_loop(self):
        """
        Blindspot: Agent proposes code with infinite loop.
        
        Should be detectable via static analysis.
        """
        from graphbus_cli.tui.agent_loop import ProposalValidator
        
        validator = ProposalValidator()
        
        assert hasattr(validator, "detect_infinite_loops")


# ─── Feedback Consistency ────────────────────────────────────────────────────

class TestFeedbackConsistency:
    """Test consistency of human feedback."""
    
    def test_contradictory_feedback_same_proposal(self):
        """
        Blindspot: Human accepts then rejects same proposal.
        
        Initial: User accepts proposal_123
        Later: User changes mind, wants to reject it
        
        Should handle rejection of accepted proposals.
        """
        from graphbus_cli.tui.hil import FeedbackManager
        
        mgr = FeedbackManager()
        
        assert hasattr(mgr, "allow_feedback_reversal")
    
    def test_feedback_on_nonexistent_proposal(self):
        """
        Blindspot: User tries to give feedback on proposal that doesn't exist.
        
        User: "Reject proposal_999"
        System: proposal_999 doesn't exist
        
        Should warn and ask for clarification.
        """
        from graphbus_cli.tui.hil import FeedbackValidator
        
        validator = FeedbackValidator()
        
        assert hasattr(validator, "validate_proposal_exists")
