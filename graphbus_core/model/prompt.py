"""
System prompt primitives for LLM agents
"""

from dataclasses import dataclass, field


@dataclass
class SystemPrompt:
    """
    LLM instruction that powers each agent in Build Mode.
    In Runtime Mode, this is metadata only.
    """
    text: str
    role: str | None = None  # e.g. "payment_processor", "inventory_manager"
    capabilities: list[str] = field(default_factory=list)  # e.g. ["refactor_methods", "add_validation"]

    def __str__(self) -> str:
        return self.text
