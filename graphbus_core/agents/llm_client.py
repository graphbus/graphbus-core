"""
LLM client for GraphBus agent negotiation — powered by LiteLLM.

Supports any model LiteLLM supports. Set the appropriate provider key:
  ANTHROPIC_API_KEY   — for claude-* models
  DEEPSEEK_API_KEY    — for deepseek/* models (default: deepseek/deepseek-reasoner)
  OPENAI_API_KEY      — for gpt-* models
  OPENROUTER_API_KEY  — for openrouter/* models (access everything with one key)

Note: GRAPHBUS_API_KEY is for the warehousing layer only, not LLM calls.
"""

import os
from typing import Optional
import litellm
from graphbus_core.constants import DEFAULT_LLM_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

# Suppress LiteLLM verbose logging by default
litellm.set_verbose = False


class LLMClient:
    """
    LiteLLM-backed LLM client for GraphBus agent negotiation.

    Pass any model string LiteLLM supports:
      "deepseek/deepseek-reasoner"      (default — DeepSeek R1)
      "claude-3-5-sonnet-20241022"      (Anthropic)
      "gpt-4o"                          (OpenAI)
      "openrouter/anthropic/claude-3.5-sonnet"  (via OpenRouter)
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
        self._api_key = api_key
        self._base_url = base_url

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
            kwargs["base_url"] = self._base_url

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
            kwargs["base_url"] = self._base_url

        resp = litellm.completion(**kwargs)
        tool_calls = resp.choices[0].message.tool_calls
        if tool_calls:
            return json.loads(tool_calls[0].function.arguments)
        raise ValueError(f"No tool call in LiteLLM response: {resp.choices[0].message}")
