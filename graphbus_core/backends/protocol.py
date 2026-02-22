"""Contracts for reasoning backends — adapted from alpaca-trader pattern.

GraphBus agents negotiate code improvements rather than trading decisions,
but the backend abstraction is identical: define an AgentSpec, get a
ReasoningResult from whichever backend is configured.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Optional

from pydantic import BaseModel


@dataclass
class AgentSpec:
    """Everything a backend needs to run an agent."""

    prompt_name: str
    system_prompt: str
    output_type: type[BaseModel]
    tools: list[dict] = field(default_factory=list)
    handle_tool_call: Callable[[str, dict], Any] = lambda name, args: {"error": f"Unknown tool: {name}"}
    max_tokens: int = 32768


@dataclass
class ReasoningResult:
    """Unified result from any backend."""

    output: Any  # Can be BaseModel or raw text depending on backend
    raw_text: str = ""  # Raw LLM response text
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    backend: str = ""  # "api", "sdk", or "litellm"


class ReasoningBackend(Protocol):
    """Protocol that all backends must implement."""

    def reason(
        self, spec: AgentSpec, context: str, model_override: str = ""
    ) -> ReasoningResult: ...

    def generate(
        self, prompt: str, system: Optional[str] = None, model_override: str = ""
    ) -> str:
        """Simple text generation without structured output."""
        ...
