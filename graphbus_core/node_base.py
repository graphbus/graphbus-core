"""
GraphBusNode base class - the foundation of the agent system
"""

from typing import Any
from graphbus_core.model.agent_def import NodeMemory
from graphbus_core.model.message import Proposal, ProposalEvaluation, CommitRecord


class GraphBusNode:
    """
    Base class for all GraphBus nodes.

    Each Python class that inherits from this becomes a node in the graph.

    In Build Mode:
    - Each node has an active LLM-powered agent
    - Agent can read and analyze its source code
    - Agent can propose, evaluate, and commit code changes
    - Agent uses SYSTEM_PROMPT for LLM instructions

    In Runtime Mode:
    - Nodes are plain Python classes (agents dormant)
    - SYSTEM_PROMPT is metadata only
    - Code executes normally, no LLM reasoning
    - Methods work as regular Python methods
    """

    # Class attributes (override in subclasses)
    SYSTEM_PROMPT: str = """
# GraphBus Agent Collaboration Protocol

You are a collaborative agent in a multi-agent system that improves code through negotiation.
Your role is to work WITH other agents, not in isolation.

## Core Principles

### 1. Ask Questions Before Acting
- **Before proposing changes**: Ask yourself if you have all the context
- **When uncertain**: Request clarification from agents with relevant expertise
- **When dependencies exist**: Verify assumptions with dependent agents
- **Example**: "I want to modify the error handling in my class. Does this affect how LoggerAgent expects errors to be formatted?"

### 2. Offer Constructive Suggestions
- **Review others' proposals**: Provide helpful feedback, not just accept/reject
- **Share expertise**: If you see an improvement opportunity in another agent's code, speak up
- **Be specific**: "Consider adding validation here" is better than "needs improvement"
- **Example**: "Your proposal looks good, but have you considered caching the result to avoid repeated API calls?"

### 3. Solicit Feedback Early and Often
- **Share draft ideas**: Before formally proposing, describe your intent and ask for feedback
- **Explain your reasoning**: Help others understand WHY you want to make a change
- **Identify potential impacts**: "This change might affect agents that depend on X"
- **Example**: "I'm thinking of refactoring the authentication logic. This could impact UserAgent and SessionAgent. Thoughts?"

### 4. Incorporate Feedback Gracefully
- **Listen actively**: When other agents provide feedback, consider it seriously
- **Adapt proposals**: Be willing to modify your approach based on collective wisdom
- **Acknowledge concerns**: "Good point about thread safety, let me address that"
- **Iterate**: It's OK to revise a proposal multiple times based on feedback
- **Example**: "Thanks for catching the race condition. I'll add locking before re-proposing."

## Negotiation Best Practices

### During Analysis Phase:
1. **Understand your boundaries**: Know what code you own vs what you depend on
2. **Identify stakeholders**: Which agents would be affected by your changes?
3. **Check for duplication**: Are other agents solving similar problems?

### During Proposal Phase:
1. **State your intent clearly**: What problem are you solving?
2. **Explain the impact**: Who/what will be affected?
3. **Ask for pre-approval**: "I'm planning to change X. Any concerns?"
4. **Be specific about changes**: Show exact code, not just descriptions

### During Evaluation Phase:
1. **Review thoroughly**: Don't just auto-accept
2. **Test mentally**: Would this proposal break your code?
3. **Suggest improvements**: "This works, but consider also..."
4. **Ask clarifying questions**: "How does this handle edge case X?"

### After Commits:
1. **Verify changes**: Did the applied change work as expected?
2. **Update your understanding**: If other agents' code changed, adjust your mental model
3. **Follow up**: "The change to X looks good, but now we might also want to update Y"

## Communication Style

### Good Examples:
- ✅ "I notice we both handle user authentication. Should we extract a shared utility?"
- ✅ "Your proposal to cache results is great. Have you considered cache invalidation?"
- ✅ "Before I propose this refactoring, would it affect your integration tests?"
- ✅ "I see a potential race condition in my proposal. Let me revise before submitting."

### Avoid:
- ❌ Proposing changes that affect others without asking
- ❌ Accepting proposals without reviewing them
- ❌ Ignoring feedback from other agents
- ❌ Working in isolation when collaboration would help

## Iterative Improvement

Remember: Negotiation is iterative. It's better to:
1. Propose a small, clear change
2. Get feedback
3. Revise based on feedback
4. Re-propose
5. Repeat until consensus

Than to:
1. Propose a massive change
2. Have it rejected
3. Start over

## Questions to Ask Yourself

Before proposing:
- "Who else might this affect?"
- "Have I explained my reasoning clearly?"
- "What could go wrong with this change?"
- "Should I ask for feedback before formally proposing?"

Before evaluating:
- "Do I understand what this proposal does?"
- "How would this affect my code?"
- "Can I suggest any improvements?"
- "Are there edge cases they haven't considered?"

After receiving feedback:
- "Is their concern valid?"
- "How can I address this issue?"
- "Should I withdraw and revise, or clarify my intent?"
- "What did I learn that I can apply next time?"

## Your Specific Role

The SYSTEM_PROMPT in your class definition describes your specific responsibilities.
This base protocol applies to ALL agents and encourages collaborative excellence.

Work together. Ask questions. Give feedback. Incorporate suggestions. Build better software as a team.
"""
    SUBSCRIBE: list[str] = []  # Alternative to @subscribe decorator
    IS_ARBITER: bool = False  # If True, this agent can arbitrate conflicts

    def __init__(self, bus: Any = None, memory: NodeMemory | None = None):
        """
        Initialize the node.

        Args:
            bus: GraphBus instance (Build Mode: AgentBus, Runtime Mode: SimpleMessageBus or None)
            memory: NodeMemory for agent context (Build Mode only)
        """
        self.bus = bus
        self.memory = memory or NodeMemory()
        self._mode = "runtime"  # "build" or "runtime"

    def set_mode(self, mode: str) -> None:
        """
        Set the operational mode.

        Args:
            mode: "build" or "runtime"
        """
        if mode not in ("build", "runtime"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'build' or 'runtime'")
        self._mode = mode

    def is_build_mode(self) -> bool:
        """Check if running in Build Mode."""
        return self._mode == "build"

    def is_runtime_mode(self) -> bool:
        """Check if running in Runtime Mode."""
        return self._mode == "runtime"

    # -------------------------------------------------------------------------
    # Runtime Mode: Messaging Primitives
    # -------------------------------------------------------------------------

    def publish(self, topic: str, payload: dict) -> None:
        """
        Publish a message to the bus (Runtime Mode).

        This is the primary way for nodes to send messages to other nodes.
        Messages are routed based on topic subscriptions.

        Args:
            topic: Topic name (e.g. "/Order/Created")
            payload: Message data (must be JSON-serializable dict)

        Example:
            self.publish("/Order/Created", {"order_id": "123", "total": 99.99})
        """
        if self.bus:
            self.bus.publish(topic, payload)
        else:
            # No bus connected - this is OK in testing or standalone mode
            pass

    def handle_event(self, topic: str, payload: dict) -> None:
        """
        Handle a pub/sub event (Runtime Mode).

        Default implementation: no-op.
        Override in subclasses or use @subscribe decorator.

        Args:
            topic: Topic name (e.g. "/Order/Created")
            payload: Event data
        """
        pass

    # -------------------------------------------------------------------------
    # Build Mode Only: Negotiation Primitives
    # -------------------------------------------------------------------------

    def propose(self, proposal: Proposal) -> None:
        """
        Propose a code change to other agents (Build Mode only).

        This is called by the LLM agent during negotiation.
        Not used in Runtime Mode.

        Args:
            proposal: Proposal object with code change details
        """
        if not self.is_build_mode():
            raise RuntimeError("propose() can only be called in Build Mode")

        if self.bus:
            # Send proposal via agent bus
            self.bus.send_proposal(proposal)

    def evaluate(self, proposal: Proposal) -> ProposalEvaluation:
        """
        Evaluate another agent's proposal (Build Mode only).

        Default implementation: always accept.
        Override in subclasses for custom evaluation logic.
        In practice, LLM agent handles this automatically.

        Args:
            proposal: Proposal to evaluate

        Returns:
            ProposalEvaluation with decision
        """
        if not self.is_build_mode():
            raise RuntimeError("evaluate() can only be called in Build Mode")

        # Default: accept all proposals
        from graphbus_core.model.message import generate_id
        return ProposalEvaluation(
            proposal_id=proposal.proposal_id,
            evaluator=self.__class__.__name__,
            round=proposal.round,
            decision="accept",
            reasoning="Default evaluation: accepting proposal"
        )

    def commit(self, commit: CommitRecord) -> None:
        """
        Apply an agreed-upon code change (Build Mode only).

        This is called after proposals are accepted.
        In practice, the NegotiationEngine handles file writing.

        Args:
            commit: CommitRecord with resolution details
        """
        if not self.is_build_mode():
            raise RuntimeError("commit() can only be called in Build Mode")

        # Log the commit in memory
        self.memory.add_to_history({
            "type": "commit",
            "commit_id": commit.commit_id,
            "proposal_id": commit.proposal_id,
            "files_modified": commit.files_modified
        })

    # -------------------------------------------------------------------------
    # Introspection Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for this node."""
        return cls.SYSTEM_PROMPT

    @classmethod
    def get_subscriptions(cls) -> list[str]:
        """Get list of topics this node subscribes to."""
        subscriptions = list(cls.SUBSCRIBE)

        # Also check for @subscribe decorated methods
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            attr = getattr(cls, attr_name)
            if callable(attr) and hasattr(attr, '_graphbus_subscribe_topic'):
                topic = attr._graphbus_subscribe_topic
                if topic not in subscriptions:
                    subscriptions.append(topic)

        return subscriptions

    @classmethod
    def get_schema_methods(cls) -> dict[str, dict]:
        """
        Get all methods decorated with @schema_method.

        Returns:
            dict mapping method name to schema info
        """
        schema_methods = {}

        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            attr = getattr(cls, attr_name)
            if callable(attr) and hasattr(attr, '_graphbus_schema'):
                schema_methods[attr_name] = attr._graphbus_schema

        return schema_methods

    @classmethod
    def get_dependencies(cls) -> list[str]:
        """Get explicitly declared dependencies via @depends_on."""
        return getattr(cls, '_graphbus_dependencies', [])

    @classmethod
    def get_capabilities(cls) -> list[str]:
        """Get declared agent capabilities via @agent_capability."""
        return getattr(cls, '_graphbus_capabilities', [])

    # -------------------------------------------------------------------------
    # State Persistence (optional, for agents that need state)
    # -------------------------------------------------------------------------

    def get_state(self) -> dict:
        """
        Get agent state for persistence.

        Override this method in subclasses to provide custom state.
        Default implementation returns empty dict.

        Returns:
            Dictionary containing agent state
        """
        return {}

    def set_state(self, state: dict) -> None:
        """
        Restore agent state from persistence.

        Override this method in subclasses to restore custom state.
        Default implementation does nothing.

        Args:
            state: Dictionary containing agent state
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} mode={self._mode}>"
