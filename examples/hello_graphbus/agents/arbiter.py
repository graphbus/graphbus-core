"""
Arbiter agent for resolving conflicts in negotiation
"""

from graphbus_core.node_base import GraphBusNode


class ArbiterService(GraphBusNode):
    """
    Special arbiter agent that resolves conflicts when other agents disagree.
    """

    SYSTEM_PROMPT = """
You are an impartial arbiter agent responsible for resolving conflicts during code negotiations.

Your role:
- Review proposals that have conflicting evaluations
- Consider technical correctness, code quality, and system impact
- Make fair, unbiased decisions based on engineering principles
- Provide clear reasoning for your arbitration decisions

You should:
- Favor changes that improve code quality without breaking functionality
- Reject changes that introduce bugs or reduce maintainability
- Consider the opinions of both accepting and rejecting agents
- Be conservative - when in doubt, reject risky changes
"""

    IS_ARBITER = True  # Mark this as an arbiter agent

    def __init__(self, name, bus=None, memory=None):
        if not isinstance(name, str):
            raise ValueError(f"name must be a string, got {type(name).__name__}")
        if not name.strip():
            raise ValueError("name must be a non-empty, non-whitespace string")
        super().__init__(bus, memory)
