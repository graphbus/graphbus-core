"""Generalized contextual memory system (not TUI-specific).

Hierarchical, multi-session memory with semantic retrieval for any agent type.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime


class SessionMemory:
    """Memory for a single negotiation/interaction session."""
    
    def __init__(self, session_id=None, intent=None, agents=None):
        self.session_id = session_id or str(datetime.utcnow().timestamp())
        self.intent = intent
        self.agents = agents or []
        self.rounds = []
        self.created_at = datetime.utcnow().isoformat()
    
    def get_continuation_context(self):
        """Get context for resuming this session."""
        return {
            "intent": self.intent,
            "agents": self.agents,
            "rounds": len(self.rounds),
            "session_id": self.session_id,
        }


class RoundMemory:
    """Memory of a single negotiation round."""
    
    def __init__(self, round_number):
        self.round_number = round_number
        self.proposals = []
        self.evaluations = []
        self.decisions = []
    
    def add_proposal(self, proposal):
        self.proposals.append(proposal)
    
    def add_decision(self, decision):
        self.decisions.append(decision)


class ProposalMemory:
    """Memory of a single proposal and its feedback."""
    
    def __init__(self, proposal_id, agent, content):
        self.proposal_id = proposal_id
        self.agent = agent
        self.content = content
        self.feedback = None
    
    def record_feedback(self, action, reason):
        self.feedback = {"action": action, "reason": reason}


class ContextCapture:
    """Captures context from negotiations for learning."""
    
    def __init__(self):
        self.proposals = []
        self.evaluations = []
        self.feedback_items = []
        self.arbiter_decisions = []
    
    def record_proposal(self, proposal):
        self.proposals.append(proposal)
    
    def record_feedback(self, feedback):
        self.feedback_items.append(feedback)
    
    def record_evaluation(self, evaluation):
        self.evaluations.append(evaluation)
    
    def record_arbiter_decision(self, decision):
        self.arbiter_decisions.append(decision)


class PatternLearner:
    """Learn patterns from past negotiations."""
    
    def __init__(self):
        self.agent_patterns = {}
        self.user_preferences = {}
        self.intent_patterns = {}
    
    def learn_pattern(self, pattern):
        pass
    
    def get_patterns_for_agent(self, agent):
        return self.agent_patterns.get(agent, [])
    
    def record_decision(self, decision):
        pass
    
    def get_user_preference(self, preference_type):
        return self.user_preferences.get(preference_type)
    
    def get_typical_agents_for_intent(self, intent):
        return self.intent_patterns.get(intent, {}).get("agents", [])
    
    def get_typical_changes_for_intent(self, intent):
        return self.intent_patterns.get(intent, {}).get("changes", [])


class SemanticIndex:
    """Index for semantic search of past sessions by intent."""
    
    def __init__(self):
        self.embeddings = {}
    
    def embed_intent(self, intent):
        """Simple embedding (would be real ML model in production)."""
        return [hash(intent) % 256 for _ in range(10)]
    
    def find_similar(self, intent, top_k=3):
        """Find past sessions similar to this intent."""
        return []
    
    def find_similar_with_time_decay(self, intent):
        return []


class ContextRetriever:
    """Retrieve relevant context for current session."""
    
    def __init__(self):
        self.learner = PatternLearner()
    
    def get_relevant_context(self, intent):
        """Get patterns and agents relevant to this intent."""
        return {
            "agents_involved": self.learner.get_typical_agents_for_intent(intent),
            "patterns": self.learner.get_typical_changes_for_intent(intent),
        }


class ContextInjector:
    """Inject learned context into agent prompts."""
    
    def inject_context(self, base_prompt, context):
        """Add learned patterns to agent's system prompt."""
        if context and context.get("patterns"):
            return (
                base_prompt 
                + "\n\nFrom past similar negotiations:\n"
                + "\n".join(f"- {p}" for p in context["patterns"][:3])
            )
        return base_prompt


class MemoryStore:
    """Central memory storage (local only, not cloud)."""
    
    def __init__(self, max_active_sessions=100):
        self.max_active_sessions = max_active_sessions
        self.sessions = {}
        self._local_path = Path.home() / ".graphbus" / "memory"
    
    @property
    def local_path(self):
        """Path to local memory storage."""
        return self._local_path
    
    def get_storage_path(self):
        """Get the local storage path."""
        return self.local_path
    
    def save_session(self, session):
        """Save session to disk."""
        self.local_path.mkdir(parents=True, exist_ok=True)
        path = self.local_path / f"session_{session.session_id}.json"
        with open(path, 'w') as f:
            json.dump(session.__dict__, f)
    
    def load_session(self, session_id):
        """Load session from disk."""
        path = self.local_path / f"session_{session_id}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None
    
    def check_write_permissions(self):
        """Check if we can write to memory storage."""
        try:
            self.local_path.mkdir(parents=True, exist_ok=True)
            return True
        except:
            return False
    
    def handle_disk_full(self):
        """Handle disk full condition."""
        pass
    
    def clear(self):
        """Clear all memory."""
        import shutil
        if self.local_path.exists():
            shutil.rmtree(self.local_path)
    
    def export(self):
        """Export memory for backup."""
        return {"sessions": list(self.sessions.values())}
    
    def archive(self):
        """Archive old sessions."""
        pass


class MemoryImportance:
    """Score session importance for retention."""
    
    def score_session(self, session):
        """Score how important a session is to keep."""
        return 0.5  # Default medium importance


class AgentMemory:
    """Agent-specific memory of past proposals and feedback."""
    
    def __init__(self, agent):
        self.agent = agent
        self.proposals = []
        self.rejections = {}
    
    def record_proposal(self, proposal):
        self.proposals.append(proposal)
    
    def get_similar_past_proposals(self, proposal):
        """Find similar proposals agent has made before."""
        return [p for p in self.proposals if p.get("type") == proposal.get("type")]
    
    def record_rejection(self, proposal, reason):
        self.rejections[proposal] = reason
    
    def get_rejection_reasons(self):
        return list(self.rejections.values())
    
    def predict_feedback(self, proposal):
        """Predict likely human feedback based on history."""
        return None


class CollaborativeMemory:
    """Memory of how agents work together."""
    
    def __init__(self):
        self.agent_interactions = {}
    
    def get_agent_history(self, agent):
        return self.agent_interactions.get(agent, {})
    
    def get_likely_followup_agents(self, agent):
        """Which agents usually follow this agent's proposals."""
        return []


class MemoryQuery:
    """Query interface for memory retrieval."""
    
    def __init__(self, store: MemoryStore):
        self.store = store
    
    def search(self, query):
        """Search past sessions by intent/keyword."""
        return []
    
    def get_agent_patterns(self, agent):
        """Get patterns for specific agent."""
        return {
            "proposals": [],
            "success_rate": 0.0,
            "common_modifications": [],
        }
    
    def get_user_decisions(self):
        """Get user's decision history."""
        return {
            "accept_rate": 0.0,
            "reject_rate": 0.0,
            "modifications_rate": 0.0,
        }


class MemoryCompaction:
    """Compress and archive old memory."""
    
    def archive_old_rounds(self):
        """Move old rounds to archive."""
        pass
    
    def compress_history(self):
        """Compress history to save space."""
        pass
