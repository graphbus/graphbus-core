"""GraphBus reasoning backends — pluggable agent orchestration.

Two backends available:
  - ApiBackend (default): Multi-turn tool-use loop via LiteLLM. Works with any provider.
  - SdkBackend (optional): Claude Agent SDK with forked process + MCP bridge.
    Free reasoning on Max subscription; only formatting step costs tokens.

Usage:
    from graphbus_core.backends import create_backend

    # Default: LiteLLM API backend
    backend = create_backend(model="claude-sonnet-4-6")

    # SDK backend (requires claude-agent-sdk + OAuth token)
    backend = create_backend(backend="sdk", api_key="sk-ant-...")
"""

from typing import Optional

from .protocol import AgentSpec, ReasoningResult, ReasoningBackend
from .api_backend import ApiBackend


def create_backend(
    backend: str = "api",
    model: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 16384,
) -> ApiBackend:
    """Factory function to create the appropriate backend.

    Args:
        backend: "api" (default) or "sdk"
        model: LLM model string (LiteLLM format)
        api_key: Provider API key
        base_url: Custom base URL
        temperature: Sampling temperature
        max_tokens: Max output tokens

    Returns:
        A backend implementing the ReasoningBackend protocol.
    """
    if backend == "sdk":
        from .sdk_backend import SdkBackend
        return SdkBackend(api_key=api_key, model=model)

    return ApiBackend(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


__all__ = [
    "AgentSpec",
    "ReasoningResult",
    "ReasoningBackend",
    "ApiBackend",
    "create_backend",
]
