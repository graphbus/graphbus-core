"""
LLM client abstraction — supports DeepSeek (default) and Anthropic.

Provider is inferred from the model name:
  - "deepseek-*"  → DeepSeek API  (OpenAI-compatible, needs DEEPSEEK_API_KEY)
  - "claude-*"    → Anthropic API (needs ANTHROPIC_API_KEY)
  - anything else → treated as OpenAI-compatible (needs OPENAI_API_KEY or
                    set base_url + api_key explicitly)

Note: GRAPHBUS_API_KEY is used separately for the warehousing layer
(storing negotiation history at api.graphbus.com). It does NOT affect
LLM calls — those always use your own provider key.

Environment variables:
  ANTHROPIC_API_KEY  — for claude-* models
  DEEPSEEK_API_KEY   — for deepseek-* models (default model: deepseek-reasoner)
  OPENAI_API_KEY     — fallback for other OpenAI-compatible models
  GRAPHBUS_API_KEY   — warehousing only (see NegotiationClient)
"""

import json
import os
from typing import Optional

from graphbus_core.constants import DEFAULT_LLM_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


def _infer_provider(model: str) -> str:
    if model.startswith("deepseek"):
        return "deepseek"
    if model.startswith("claude"):
        return "anthropic"
    return "openai"


class LLMClient:
    """
    Provider-agnostic LLM client for GraphBus agent negotiation.

    LLM calls always use the user's own provider API key — GraphBus
    never proxies LLM traffic.

    Default model: DeepSeek R1 (deepseek-reasoner) — strong reasoning,
    cost-effective for the proposal/evaluate/vote negotiation cycle.
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
        self._provider = _infer_provider(model)

        if self._provider == "anthropic":
            self._init_anthropic(api_key)
        else:
            self._init_openai_compatible(api_key, base_url)

    # ── Initialisation ─────────────────────────────────────────────────────

    def _init_anthropic(self, api_key: Optional[str]) -> None:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "Anthropic API key required for claude-* models.\n"
                "  Set ANTHROPIC_API_KEY or pass api_key= to LLMClient."
            )
        self._client = Anthropic(api_key=key)

    def _init_openai_compatible(self, api_key: Optional[str], base_url: Optional[str]) -> None:
        from openai import OpenAI

        if self._provider == "deepseek":
            key = api_key or os.environ.get("DEEPSEEK_API_KEY")
            url = base_url or DEEPSEEK_BASE_URL
            if not key:
                raise ValueError(
                    "DeepSeek API key required for deepseek-* models.\n"
                    "  Set DEEPSEEK_API_KEY or pass api_key= to LLMClient."
                )
        else:
            key = api_key or os.environ.get("OPENAI_API_KEY", "")
            url = base_url  # None = default OpenAI endpoint

        kwargs: dict = {"api_key": key}
        if url:
            kwargs["base_url"] = url
        self._client = OpenAI(**kwargs)

    # ── Public API ──────────────────────────────────────────────────────────

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response. Returns the text content."""
        if self._provider == "anthropic":
            return self._generate_anthropic(prompt, system)
        return self._generate_openai(prompt, system)

    def generate_with_tool(
        self,
        prompt: str,
        tool_name: str,
        tool_schema: dict,
        system: Optional[str] = None,
    ) -> dict:
        """Generate a structured response using tool/function calling."""
        if self._provider == "anthropic":
            return self._generate_tool_anthropic(prompt, tool_name, tool_schema, system)
        return self._generate_tool_openai(prompt, tool_name, tool_schema, system)

    # ── Anthropic ───────────────────────────────────────────────────────────

    def _generate_anthropic(self, prompt: str, system: Optional[str]) -> str:
        try:
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
            if msg.content:
                return msg.content[0].text
            print(f"Warning: empty Anthropic response. Raw: {msg}")
            return ""
        except Exception as e:
            print(f"Anthropic API error: {e}")
            raise

    def _generate_tool_anthropic(
        self, prompt: str, tool_name: str, tool_schema: dict, system: Optional[str]
    ) -> dict:
        try:
            tool_def = {
                "name": tool_name,
                "description": f"Structured output for {tool_name}",
                "input_schema": tool_schema,
            }
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system or "",
                tools=[tool_def],
                messages=[{"role": "user", "content": prompt}],
            )
            for block in msg.content or []:
                if block.type == "tool_use":
                    return block.input
            raise ValueError(f"No tool_use block in Anthropic response: {msg.content}")
        except Exception as e:
            print(f"Anthropic tool API error: {e}")
            raise

    # ── OpenAI-compatible (DeepSeek / OpenAI) ──────────────────────────────

    def _generate_openai(self, prompt: str, system: Optional[str]) -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"OpenAI-compatible API error ({self._provider}): {e}")
            raise

    def _generate_tool_openai(
        self, prompt: str, tool_name: str, tool_schema: dict, system: Optional[str]
    ) -> dict:
        try:
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
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[tool_def],
                tool_choice={"type": "function", "function": {"name": tool_name}},
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            tool_call = resp.choices[0].message.tool_calls
            if tool_call:
                return json.loads(tool_call[0].function.arguments)
            raise ValueError(f"No tool call in response: {resp.choices[0].message}")
        except Exception as e:
            print(f"OpenAI-compatible tool API error ({self._provider}): {e}")
            raise
