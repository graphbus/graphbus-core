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
    SYSTEM_PROMPT: str = ""
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
    # Runtime Mode: Event Handling
    # -------------------------------------------------------------------------

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
