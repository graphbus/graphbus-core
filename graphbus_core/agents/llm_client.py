"""
LLM client for GraphBus agent negotiation — powered by LiteLLM.

Default provider: spicychai cluster (Sravan's private HAProxy → LM Studio pool).
  Base URL : http://spicychai.com:3443/light/v1
  Model    : openai/mistralai/ministral-3-14b-reasoning
  Key      : SPICYCHAI_API_KEY env var (falls back to constant)

Override with any LiteLLM-compatible provider:
  ANTHROPIC_API_KEY   — claude-* models
  DEEPSEEK_API_KEY    — deepseek/* models
  OPENAI_API_KEY      — gpt-* models
  OPENROUTER_API_KEY  — openrouter/* models

Note: GRAPHBUS_API_KEY is for the warehousing layer only, not LLM calls.
"""

import os
from typing import Optional
import litellm
from graphbus_core.constants import (
    DEFAULT_LLM_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    SPICYCHAI_BASE_URL,
    SPICYCHAI_API_KEY,
)

# Suppress LiteLLM verbose logging by default
litellm.set_verbose = False


def _resolve_spicychai_key() -> str:
    """Return the spicychai bearer token from env or the baked-in constant."""
    return os.getenv("SPICYCHAI_API_KEY", SPICYCHAI_API_KEY)


def _resolve_spicychai_base() -> str:
    """Return the spicychai base URL from env or the baked-in constant."""
    return os.getenv("SPICYCHAI_BASE_URL", SPICYCHAI_BASE_URL)


class LLMClient:
    """
    LiteLLM-backed LLM client for GraphBus agent negotiation.

    Defaults to the spicychai private LLM cluster (OpenAI-compatible).
    Pass any model string LiteLLM supports to switch providers:
      "openai/mistralai/ministral-3-14b-reasoning"  ← spicychai (default)
      "openai/google/gemma-3-4b"                    ← spicychai light
      "deepseek/deepseek-reasoner"                  ← DeepSeek (needs DEEPSEEK_API_KEY)
      "claude-3-5-sonnet-20241022"                  ← Anthropic
      "openrouter/anthropic/claude-3.5-sonnet"      ← OpenRouter
    """

    def __init__(
        self,
        model: str = DEFAULT_LLM_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Resolve credentials: explicit args > env vars > spicychai defaults
        # For openai/* prefixed models with no explicit key/base, default to spicychai.
        is_spicychai_model = (
            base_url is None
            and api_key is None
            and not os.getenv("OPENAI_API_KEY")
            and not os.getenv("OPENAI_API_BASE")
        )
        if is_spicychai_model and model.startswith("openai/"):
            self._api_key = _resolve_spicychai_key()
            self._base_url = _resolve_spicychai_base()
        else:
            self._api_key = api_key
            self._base_url = base_url or os.getenv("OPENAI_API_BASE") or os.getenv("SPICYCHAI_BASE_URL")

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = dict(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["api_base"] = self._base_url   # LiteLLM uses api_base, not base_url

        resp = litellm.completion(**kwargs)
        return resp.choices[0].message.content or ""

    def generate_with_tool(
        self,
        prompt: str,
        tool_name: str,
        tool_schema: dict,
        system: Optional[str] = None,
    ) -> dict:
        import json
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        tool_def = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"Structured output for {tool_name}",
                "parameters": tool_schema,
            },
        }

        kwargs = dict(
            model=self.model,
            messages=messages,
            tools=[tool_def],
            tool_choice={"type": "function", "function": {"name": tool_name}},
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["api_base"] = self._base_url   # LiteLLM uses api_base

        resp = litellm.completion(**kwargs)
        tool_calls = resp.choices[0].message.tool_calls
        if tool_calls:
            return json.loads(tool_calls[0].function.arguments)
        raise ValueError(f"No tool call in LiteLLM response: {resp.choices[0].message}")
