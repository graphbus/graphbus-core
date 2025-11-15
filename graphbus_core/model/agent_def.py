"""
Agent definition and memory primitives
"""

from dataclasses import dataclass, field
from typing import Any

from graphbus_core.model.prompt import SystemPrompt
from graphbus_core.model.schema import SchemaMethod
from graphbus_core.model.topic import Subscription


@dataclass
class NodeMemory:
    """
    Agent-local memory for maintaining context.

    Build Mode: Used by LLM agents to track negotiation history and decisions.
    Runtime Mode: Minimal or unused - execution is stateless.
    """
    state: dict[str, Any] = field(default_factory=dict)  # current agent state
    history: list[dict] = field(default_factory=list)  # logs, observations, negotiation outcomes
    code_understanding: dict = field(default_factory=dict)  # agent's analysis of its source code
    pending_proposals: list[str] = field(default_factory=list)  # proposal IDs awaiting resolution

    def store(self, key: str, value: Any) -> None:
        """Store a value in agent memory."""
        self.state[key] = value

    def retrieve(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from agent memory."""
        return self.state.get(key, default)

    def add_to_history(self, event: dict) -> None:
        """Add an event to the history log."""
        self.history.append(event)


@dataclass
class AgentDefinition:
    """
    Definition of an agent extracted from a GraphBusNode class.

    Contains all metadata needed to:
    - Activate an LLM-powered agent in Build Mode
    - Execute static code in Runtime Mode
    """
    name: str
    module: str
    class_name: str
    source_file: str  # path to .py file
    source_code: str  # actual code content
    system_prompt: SystemPrompt
    methods: list[SchemaMethod] = field(default_factory=list)
    subscriptions: list[Subscription] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # other nodes this depends on
    is_arbiter: bool = False  # If True, this agent can arbitrate conflicts
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON artifacts."""
        return {
            "name": self.name,
            "module": self.module,
            "class_name": self.class_name,
            "source_file": self.source_file,
            "source_code": self.source_code,
            "system_prompt": {
                "text": self.system_prompt.text,
                "role": self.system_prompt.role,
                "capabilities": self.system_prompt.capabilities
            },
            "methods": [m.to_dict() for m in self.methods],
            "subscriptions": [s.to_dict() for s in self.subscriptions],
            "dependencies": self.dependencies,
            "is_arbiter": self.is_arbiter,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentDefinition":
        """Deserialize from dict."""
        return cls(
            name=data["name"],
            module=data["module"],
            class_name=data["class_name"],
            source_file=data["source_file"],
            source_code=data["source_code"],
            system_prompt=SystemPrompt(
                text=data["system_prompt"]["text"],
                role=data["system_prompt"].get("role"),
                capabilities=data["system_prompt"].get("capabilities", [])
            ),
            methods=[SchemaMethod.from_dict(m) for m in data.get("methods", [])],
            subscriptions=[Subscription.from_dict(s) for s in data.get("subscriptions", [])],
            dependencies=data.get("dependencies", []),
            is_arbiter=data.get("is_arbiter", False),
            metadata=data.get("metadata", {})
        )
