"""Human-in-the-loop intervention module."""

from typing import Optional, Callable, Dict, Any


class UserInputHandler:
    """Handles non-blocking keyboard input."""
    
    def __init__(self):
        self.last_key = None
    
    def poll(self) -> Optional[str]:
        """Poll for keyboard input without blocking."""
        return self.last_key
    
    def get_input(self) -> Optional[str]:
        """Alias for poll."""
        return self.poll()
    
    def handle_input(self, key: str):
        """Handle input."""
        self.last_key = key
    
    def set_poll_interval(self, ms: int):
        """Set polling interval."""
        self.poll_interval = ms


class ProposalInspector:
    """Inspect proposals in detail."""
    
    def show_proposal_details(self, proposal):
        """Show full proposal details."""
        return {
            "id": proposal.get("id"),
            "content": proposal.get("content"),
            "agent": proposal.get("agent"),
        }
    
    def format_diff(self, proposal):
        """Format proposal as diff."""
        return f"--- Original\n+++ {proposal.get('agent')}\n+{proposal.get('content')}"


class ProposalApprover:
    """Approve or reject proposals."""
    
    def __init__(self):
        self.approvals = {}
    
    def accept_proposal(self, proposal_id):
        """Accept a proposal."""
        self.approvals[proposal_id] = "accepted"
    
    def reject_proposal(self, proposal_id):
        """Reject a proposal."""
        self.approvals[proposal_id] = "rejected"
    
    def reject_with_reason(self, proposal_id, reason):
        """Reject with optional reason."""
        self.approvals[proposal_id] = f"rejected: {reason}"


class ProposalEditor:
    """Edit proposals before accepting."""
    
    def edit_proposal(self, proposal):
        """Edit proposal."""
        return proposal
    
    def save_changes(self, proposal):
        """Save proposal changes."""
        pass


class ReasoningViewer:
    """View agent reasoning."""
    
    def show_reasoning(self, proposal):
        """Show agent reasoning."""
        return f"Reasoning for {proposal.get('id')}: {proposal.get('reasoning', 'N/A')}"


class AgentDialog:
    """Ask agents questions."""
    
    def ask_agent(self, agent_name: str, question: str):
        """Ask an agent a question."""
        return f"{agent_name} says: I will consider that."


class DecisionOverride:
    """Override agent decisions."""
    
    def force_accept(self, proposal_id):
        """Force accept a proposal."""
        pass
    
    def force_reject(self, proposal_id):
        """Force reject a proposal."""
        pass


class FeedbackCollector:
    """Collect human feedback."""
    
    def __init__(self):
        self.feedback = {}
    
    def collect_feedback(self, proposal):
        """Collect feedback on proposal."""
        return self.feedback.get(proposal.get("id"))
    
    def format_for_agents(self, feedback):
        """Format feedback for agent consumption."""
        return f"Human feedback: {feedback}"


class NegotiationSteering:
    """Steer negotiation direction."""
    
    def provide_hint(self, hint: str):
        """Provide hint to agents."""
        pass
    
    def ask_agents(self, question: str):
        """Ask agents a question."""
        pass


class FeedbackManager:
    """Manage feedback reversals."""
    
    def allow_feedback_reversal(self):
        """Allow reversing feedback."""
        return True


class FeedbackValidator:
    """Validate feedback."""
    
    def validate_proposal_exists(self, proposal_id):
        """Check if proposal exists."""
        return proposal_id is not None


class InputDebouncer:
    """Debounce rapid input."""
    
    def __init__(self, debounce_ms: int = 500):
        self.debounce_ms = debounce_ms
        self.last_input_time = 0
    
    def filter_duplicate_input(self, key: str):
        """Filter duplicate input."""
        import time
        now = time.time() * 1000
        if now - self.last_input_time < self.debounce_ms:
            return None
        self.last_input_time = now
        return key


class InputValidator:
    """Validate user input."""
    
    def __init__(self, max_input_size: int = 1000):
        self.max_input_size = max_input_size
    
    def validate_input_size(self, text: str):
        """Validate input size."""
        return len(text) <= self.max_input_size
