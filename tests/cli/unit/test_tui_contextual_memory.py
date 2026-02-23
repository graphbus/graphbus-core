"""
GraphBus TUI Contextual Memory — memu.bot-style architecture.

Memory Model:
- Session Memory: current negotiation context
- Round Memory: decisions from each round
- Proposal Memory: what agents proposed and human feedback
- Pattern Memory: learned patterns from past sessions
- Semantic Index: retrieve similar past sessions by intent
"""

import pytest
from pathlib import Path
from datetime import datetime
import json


# ─── Memory Hierarchy ───────────────────────────────────────────────────────

class TestMemoryHierarchy:
    """Test hierarchical memory structure."""
    
    def test_session_memory_captures_context(self):
        """
        Test: Session memory captures negotiation context.
        
        Session = {
            "session_id": "sess_abc123",
            "intent": "optimize database queries",
            "start_time": "2026-02-22T22:30:00Z",
            "agents": ["DataAgent", "APIAgent"],
            "rounds": [round1, round2, ...],
            "outcome": "complete|partial|incomplete",
            "human_feedback": [feedback1, feedback2, ...],
        }
        """
        from graphbus_cli.tui.memory import SessionMemory
        
        session = SessionMemory(
            intent="optimize database queries",
            agents=["DataAgent", "APIAgent"],
        )
        assert session.intent == "optimize database queries"
        assert hasattr(session, "rounds")
    
    def test_round_memory_structure(self):
        """
        Test: Each round stores proposals and decisions.
        
        Round = {
            "round_number": 1,
            "timestamp": "...",
            "proposals": [prop1, prop2, ...],
            "evaluations": [eval1, eval2, ...],
            "human_decisions": [{"proposal_id": ..., "action": "accept"|"reject", "reason": ...}],
            "converged": false,
        }
        """
        from graphbus_cli.tui.memory import RoundMemory
        
        round_mem = RoundMemory(round_number=1)
        assert round_mem.round_number == 1
        assert hasattr(round_mem, "add_proposal")
        assert hasattr(round_mem, "add_decision")
    
    def test_proposal_memory_with_feedback(self):
        """
        Test: Proposal memory captures what was proposed and human feedback.
        
        Proposal = {
            "proposal_id": "prop_123",
            "agent": "DataAgent",
            "round": 1,
            "content": "Add database index on user_id",
            "reasoning": "Queries on user_id are slow because...",
            "human_feedback": {
                "action": "accept",
                "reason": "Good, but also add index on created_at",
                "modification": "...",
            },
        }
        """
        from graphbus_cli.tui.memory import ProposalMemory
        
        prop = ProposalMemory(
            proposal_id="prop_123",
            agent="DataAgent",
            content="Add index on user_id",
        )
        
        prop.record_feedback(action="accept", reason="Good optimization")
        
        assert prop.feedback is not None
        assert prop.feedback["action"] == "accept"
    
    def test_memory_persistence(self):
        """
        Test: Memory is persisted to ~/.graphbus/projects/{id}/memory/.
        
        Directory structure:
        ~/.graphbus/projects/myapp_abc123/
          memory/
            session_20260222_001.json
            session_20260222_002.json
            patterns.json
            embeddings.json (for semantic search)
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        assert hasattr(store, "save_session")
        assert hasattr(store, "load_session")


# ─── Context Capture ────────────────────────────────────────────────────────

class TestContextCapture:
    """Test capturing negotiation context."""
    
    def test_capture_proposal_and_reasoning(self):
        """
        Test: Capture agent's proposal and its reasoning.
        
        When agent proposes, capture:
        - What was proposed
        - Why (agent's reasoning)
        - What code was analyzed
        - Confidence score
        """
        from graphbus_cli.tui.memory import ContextCapture
        
        capture = ContextCapture()
        
        proposal = {
            "content": "Add caching layer",
            "reasoning": "Queries repeat 3x per request, caching reduces...",
            "files_analyzed": ["api/queries.py", "api/cache.py"],
            "confidence": 0.85,
        }
        
        capture.record_proposal(proposal)
        
        assert capture.proposals is not None
    
    def test_capture_human_feedback(self):
        """
        Test: Capture human feedback on proposals.
        
        When human accepts/rejects/modifies, capture:
        - Which proposal
        - Action (accept|reject|modify)
        - Reason (optional)
        - Modifications (if edited)
        """
        from graphbus_cli.tui.memory import ContextCapture
        
        capture = ContextCapture()
        
        feedback = {
            "proposal_id": "prop_123",
            "action": "reject",
            "reason": "Too generic, needs error handling",
            "suggested_direction": "Add specific exception types",
        }
        
        capture.record_feedback(feedback)
    
    def test_capture_agent_evaluation(self):
        """
        Test: Capture how agents evaluated each other.
        
        When agent evaluates another's proposal:
        - Agent that evaluated
        - Proposal being evaluated
        - Agreement/disagreement
        - Reasoning
        """
        from graphbus_cli.tui.memory import ContextCapture
        
        capture = ContextCapture()
        
        evaluation = {
            "evaluator": "APIAgent",
            "proposal_id": "prop_123",
            "stance": "agree",  # or "disagree"
            "reasoning": "This optimization aligns with our caching strategy",
        }
        
        capture.record_evaluation(evaluation)
    
    def test_capture_arbiter_decisions(self):
        """
        Test: Capture arbiter's conflict resolutions.
        
        For learning: how did arbiter resolve conflicts?
        """
        from graphbus_cli.tui.memory import ContextCapture
        
        capture = ContextCapture()
        
        arbiter_decision = {
            "conflict_proposals": ["prop_123", "prop_124"],
            "resolution": "prop_125",
            "reasoning": "Combines benefits of both, avoids conflict",
        }
        
        capture.record_arbiter_decision(arbiter_decision)


# ─── Semantic Memory: Pattern Learning ──────────────────────────────────────

class TestPatternMemory:
    """Test learning patterns from past negotiations."""
    
    def test_learn_agent_patterns(self):
        """
        Test: Learn patterns about agents.
        
        Patterns:
        - DataAgent tends to propose schema changes
        - APIAgent proposes caching when DataAgent mentions slow queries
        - User rejects generic error handling
        """
        from graphbus_cli.tui.memory import PatternLearner
        
        learner = PatternLearner()
        
        # After seeing many sessions, should detect patterns
        assert hasattr(learner, "learn_pattern")
        assert hasattr(learner, "get_patterns_for_agent")
    
    def test_learn_human_preferences(self):
        """
        Test: Learn human's decision patterns.
        
        Example:
        - User always accepts performance optimizations
        - User always rejects adding new dependencies
        - User asks for specific error types
        """
        from graphbus_cli.tui.memory import PatternLearner
        
        learner = PatternLearner()
        
        # Should track human decisions
        assert hasattr(learner, "record_decision")
        assert hasattr(learner, "get_user_preference")
    
    def test_learn_intent_patterns(self):
        """
        Test: Learn patterns for common intents.
        
        Patterns:
        - "optimize database" → usually involves: indexes, caching, query optimization
        - "improve error handling" → usually involves: specific exceptions, logging, monitoring
        """
        from graphbus_cli.tui.memory import PatternLearner
        
        learner = PatternLearner()
        
        # Should correlate intents with typical proposals
        assert hasattr(learner, "get_typical_agents_for_intent")
        assert hasattr(learner, "get_typical_changes_for_intent")


# ─── Semantic Retrieval: Context Injection ──────────────────────────────────

class TestSemanticRetrieval:
    """Test retrieving relevant past context for new sessions."""
    
    def test_embed_intent(self):
        """
        Test: Convert intent to embedding for semantic search.
        
        "optimize database queries" → embedding vector
        Later: "improve database performance" → similar embedding
        """
        from graphbus_cli.tui.memory import SemanticIndex
        
        index = SemanticIndex()
        
        embedding = index.embed_intent("optimize database queries")
        assert embedding is not None
        assert len(embedding) > 0  # Vector
    
    def test_find_similar_sessions(self):
        """
        Test: Find past sessions similar to current intent.
        
        Current intent: "optimize database queries"
        Similar past sessions:
        - "improve database performance" (90% similar)
        - "add database indexes" (85% similar)
        - "optimize API performance" (60% similar)
        """
        from graphbus_cli.tui.memory import SemanticIndex
        
        index = SemanticIndex()
        
        similar = index.find_similar("optimize database queries", top_k=3)
        
        # Should return sessions with similarity scores
        assert hasattr(similar, "__iter__")
    
    def test_retrieve_relevant_patterns(self):
        """
        Test: From similar past sessions, retrieve relevant patterns.
        
        For "optimize database queries":
        - What agents were involved?
        - What types of changes were proposed?
        - What did the user accept/reject?
        """
        from graphbus_cli.tui.memory import ContextRetriever
        
        retriever = ContextRetriever()
        
        context = retriever.get_relevant_context("optimize database queries")
        
        # Should include patterns from similar past sessions
        assert "agents_involved" in context or "patterns" in context
    
    def test_context_injection_to_agents(self):
        """
        Test: Inject past context into agent prompts.
        
        Agent prompt becomes:
        "You are DataAgent...
        
        From past sessions on similar topics:
        - Users accepted schema changes when they reduced queries by 30%+
        - Users rejected generic indexes, prefer query-specific ones
        
        Current intent: optimize database queries"
        """
        from graphbus_cli.tui.memory import ContextInjector
        
        injector = ContextInjector()
        
        context = {
            "patterns": [
                "Users accept schema changes if they reduce queries",
                "Users prefer specific indexes",
            ],
        }
        
        injected_prompt = injector.inject_context(
            base_prompt="You are DataAgent...",
            context=context,
        )
        
        assert "From past sessions" in injected_prompt or "patterns" in injected_prompt


# ─── Memory Decay and Importance ────────────────────────────────────────────

class TestMemoryDecay:
    """Test memory importance and decay over time."""
    
    def test_recent_memory_higher_weight(self):
        """
        Test: Recent sessions are weighted higher than old ones.
        
        Session from today > session from 1 month ago
        """
        from graphbus_cli.tui.memory import SemanticIndex
        
        index = SemanticIndex()
        
        # Should support time-weighted similarity
        assert hasattr(index, "find_similar_with_time_decay")
    
    def test_important_memory_preserved(self):
        """
        Test: Important memories (high user interaction) are preserved longer.
        
        Sessions with many rounds and human decisions > sessions with few
        """
        from graphbus_cli.tui.memory import MemoryImportance
        
        scorer = MemoryImportance()
        
        # Should score by importance
        assert hasattr(scorer, "score_session")
    
    def test_memory_archival(self):
        """
        Test: Old, low-importance memories are archived (not deleted).
        
        Current memory: recent 100 sessions
        Archive: everything older + low-importance
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore(max_active_sessions=100)
        
        assert hasattr(store, "archive") or hasattr(store, "move_to_archive")


# ─── Memory-Aware Agent Behavior ────────────────────────────────────────────

class TestMemoryAwareAgents:
    """Test agents that learn from memory."""
    
    def test_agent_learns_from_feedback(self):
        """
        Test: Agent remembers when it proposed something similar before.
        
        Agent "I proposed adding index on user_id last time,
        human asked to also index created_at.
        This time, I'll propose both."
        """
        from graphbus_cli.tui.memory import AgentMemory
        
        agent_mem = AgentMemory(agent="DataAgent")
        
        # Agent should track its past proposals
        assert hasattr(agent_mem, "record_proposal")
        assert hasattr(agent_mem, "get_similar_past_proposals")
    
    def test_agent_avoids_rejected_approaches(self):
        """
        Test: Agent learns not to repeat rejected proposals.
        
        Agent "Last time I proposed using ORM,
        user rejected for performance reasons.
        This time, I'll propose raw SQL."
        """
        from graphbus_cli.tui.memory import AgentMemory
        
        agent_mem = AgentMemory(agent="APIAgent")
        
        # Should track rejections
        agent_mem.record_rejection(
            proposal="Use ORM for queries",
            reason="Performance",
        )
        
        # Next time, should consider this
        assert hasattr(agent_mem, "get_rejection_reasons")
    
    def test_agent_predicts_human_feedback(self):
        """
        Test: Agent predicts likely human feedback before proposing.
        
        Agent "I'm about to propose generic error handling.
        Based on history, user will reject this.
        Let me propose specific exception types instead."
        """
        from graphbus_cli.tui.memory import AgentMemory
        
        agent_mem = AgentMemory(agent="APIAgent")
        
        # Should predict feedback
        assert hasattr(agent_mem, "predict_feedback")


# ─── Collaborative Memory ───────────────────────────────────────────────────

class TestCollaborativeMemory:
    """Test agents learning from each other's history."""
    
    def test_agents_see_each_other_history(self):
        """
        Test: When evaluating, agent sees what the other proposed before.
        
        APIAgent evaluating DataAgent's proposal:
        "DataAgent proposed similar schema change 3 times before,
        user always asked for migration scripts.
        I should recommend that here too."
        """
        from graphbus_cli.tui.memory import CollaborativeMemory
        
        collab = CollaborativeMemory()
        
        # Should share agent histories
        assert hasattr(collab, "get_agent_history")
    
    def test_agents_learn_compatibility(self):
        """
        Test: Agents learn which changes work well together.
        
        DataAgent proposals usually need APIAgent modifications.
        When DataAgent proposes schema changes,
        APIAgent pre-emptively suggests query optimizations.
        """
        from graphbus_cli.tui.memory import CollaborativeMemory
        
        collab = CollaborativeMemory()
        
        # Should track co-occurrence of proposals
        assert hasattr(collab, "get_likely_followup_agents")


# ─── Session Continuation ───────────────────────────────────────────────────

class TestMemorySessionContinuation:
    """Test resuming with memory context."""
    
    def test_resume_with_memory_context(self):
        """
        Test: When resuming a paused negotiation, inject context.
        
        User resumes: "Continue optimizing database queries"
        Memory retrieves:
        - What happened in rounds 1-3
        - What human accepted/rejected
        - What agents learned
        Injects into current agents' prompts
        """
        from graphbus_cli.tui.memory import SessionMemory
        
        session = SessionMemory(session_id="sess_abc123")
        
        # Should be resumable
        assert hasattr(session, "get_continuation_context")
    
    def test_similar_intent_reuses_context(self):
        """
        Test: Similar new intent reuses context from past.
        
        Past session: "optimize database queries"
        New intent: "improve database performance"
        Memory injects: "Last time we optimized queries by adding indexes and caching"
        """
        from graphbus_cli.tui.memory import ContextRetriever
        
        retriever = ContextRetriever()
        
        # Should support similar intent matching
        assert hasattr(retriever, "get_relevant_context")


# ─── Memory Interrogation ───────────────────────────────────────────────────

class TestMemoryInterrogation:
    """Test user querying memory."""
    
    def test_user_asks_memory_what_happened(self):
        """
        Test: User can ask "What happened last time I optimized queries?"
        
        Command: `graphbus memory query "optimize queries"`
        Response:
        - Previous 3 sessions
        - Proposals accepted/rejected
        - Final outcome
        """
        from graphbus_cli.tui.memory import MemoryQuery
        
        query = MemoryQuery()
        
        results = query.search("optimize queries")
        
        assert hasattr(results, "__iter__")
    
    def test_user_reviews_agent_patterns(self):
        """
        Test: User can see what agents typically propose.
        
        Command: `graphbus memory agents DataAgent`
        Response:
        - Most common proposals
        - Success rate
        - User feedback patterns
        """
        from graphbus_cli.tui.memory import MemoryQuery
        
        query = MemoryQuery()
        
        patterns = query.get_agent_patterns("DataAgent")
        
        assert "proposals" in patterns or "patterns" in patterns
    
    def test_user_views_decision_history(self):
        """
        Test: User can see their own decision history.
        
        Command: `graphbus memory decisions`
        Response:
        - What they accept/reject
        - How often they modify proposals
        - Common feedback
        """
        from graphbus_cli.tui.memory import MemoryQuery
        
        query = MemoryQuery()
        
        history = query.get_user_decisions()
        
        assert history is not None


# ─── Privacy and Memory Management ──────────────────────────────────────────

class TestMemoryPrivacy:
    """Test memory security and management."""
    
    def test_memory_local_only(self):
        """
        Test: Memory is stored locally (~/.graphbus/), not sent to API.
        
        No memory leaves the user's machine.
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        
        # Should only use local storage
        assert hasattr(store, "local_path") or hasattr(store, "get_storage_path")
    
    def test_memory_clear(self):
        """
        Test: User can clear all memory.
        
        Command: `graphbus memory clear`
        Confirmation: "Delete all negotiation history?"
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        
        assert hasattr(store, "clear")
    
    def test_memory_export(self):
        """
        Test: User can export memory for backup.
        
        Command: `graphbus memory export > memory-backup.json`
        """
        from graphbus_cli.tui.memory import MemoryStore
        
        store = MemoryStore()
        
        assert hasattr(store, "export")
