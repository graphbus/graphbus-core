"""Human-in-the-loop intervention module."""

from typing import Optional, Callable


class UserInputHandler:
    """Handles non-blocking keyboard input."""
    
    def __init__(self):
        pass
    
    def poll(self) -> Optional[str]:
        """Poll for keyboard input without blocking."""
        return None
    
    def get_input(self) -> Optional[str]:
        """Alias for poll."""
        return self.poll()
    
    def handle_input(self, key: str):
        """Handle input."""
        raise NotImplementedError
    
    def set_poll_interval(self, ms: int):
        """Set polling interval."""
        raise NotImplementedError


class ProposalInspector:
    """Inspect proposals in detail."""
    
    def show_proposal_details(self, proposal):
        """Show full proposal details."""
        raise NotImplementedError
    
    def format_diff(self, proposal):
        """Format proposal as diff."""
        raise NotImplementedError


class ProposalApprover:
    """Approve or reject proposals."""
    
    def accept_proposal(self, proposal_id):
        """Accept a proposal."""
        raise NotImplementedError
    
    def reject_proposal(self, proposal_id):
        """Reject a proposal."""
        raise NotImplementedError
    
    def reject_with_reason(self, proposal_id, reason):
        """Reject with optional reason."""
        raise NotImplementedError


class ProposalEditor:
    """Edit proposals before accepting."""
    
    def edit_proposal(self, proposal):
        """Edit proposal."""
        raise NotImplementedError
    
    def save_changes(self, proposal):
        """Save proposal changes."""
        raise NotImplementedError


class ReasoningViewer:
    """View agent reasoning."""
    
    def show_reasoning(self, proposal):
        """Show agent reasoning."""
        raise NotImplementedError


class AgentDialog:
    """Ask agents questions."""
    
    def ask_agent(self, agent_name: str, question: str):
        """Ask an agent a question."""
        raise NotImplementedError


class DecisionOverride:
    """Override agent decisions."""
    
    def force_accept(self, proposal_id):
        """Force accept a proposal."""
        raise NotImplementedError
    
    def force_reject(self, proposal_id):
        """Force reject a proposal."""
        raise NotImplementedError


class FeedbackCollector:
    """Collect human feedback."""
    
    def collect_feedback(self, proposal):
        """Collect feedback on proposal."""
        raise NotImplementedError
    
    def format_for_agents(self, feedback):
        """Format feedback for agent consumption."""
        raise NotImplementedError


class NegotiationSteering:
    """Steer negotiation direction."""
    
    def provide_hint(self, hint: str):
        """Provide hint to agents."""
        raise NotImplementedError
    
    def ask_agents(self, question: str):
        """Ask agents a question."""
        raise NotImplementedError


class FeedbackManager:
    """Manage feedback reversals."""
    
    def allow_feedback_reversal(self):
        """Allow reversing feedback."""
        raise NotImplementedError


class FeedbackValidator:
    """Validate feedback."""
    
    def validate_proposal_exists(self, proposal_id):
        """Check if proposal exists."""
        raise NotImplementedError


class InputDebouncer:
    """Debounce rapid input."""
    
    def __init__(self, debounce_ms: int = 500):
        self.debounce_ms = debounce_ms
    
    def filter_duplicate_input(self, key: str):
        """Filter duplicate input."""
        raise NotImplementedError


class InputValidator:
    """Validate user input."""
    
    def __init__(self, max_input_size: int = 1000):
        self.max_input_size = max_input_size
    
    def validate_input_size(self, text: str):
        """Validate input size."""
        return len(text) <= self.max_input_size
