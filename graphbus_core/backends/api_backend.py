"""LiteLLM-based reasoning backend — multi-provider tool-use loop.

Supports any model LiteLLM supports (Anthropic, OpenAI, DeepSeek, OpenRouter, etc.).
Implements the same multi-turn tool-use loop as the alpaca-trader ApiBackend
but uses LiteLLM instead of the Anthropic SDK directly.
"""

import json
import logging
from typing import Optional

import litellm

from .protocol import AgentSpec, ReasoningResult

logger = logging.getLogger(__name__)
litellm.set_verbose = False

MAX_TOOL_TURNS = 25
SUBMIT_TOOL_NAME = "submit_result"


def _clean_schema(schema: dict) -> dict:
    """Strip 'title' fields from JSON schema."""
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        if isinstance(prop, dict):
            prop.pop("title", None)
    for defn in schema.get("$defs", {}).values():
        if isinstance(defn, dict):
            _clean_schema(defn)
    return schema


def _pydantic_to_tool(output_type) -> dict:
    """Convert a Pydantic model into a LiteLLM/OpenAI-format tool definition."""
    schema = _clean_schema(output_type.model_json_schema())
    return {
        "type": "function",
        "function": {
            "name": SUBMIT_TOOL_NAME,
            "description": (
                "Submit your final structured result. Call this tool ONCE when you have "
                "completed your analysis and are ready to return your result. "
                "Every required field must be populated."
            ),
            "parameters": schema,
        },
    }


def _agent_tools_to_litellm(tools: list[dict]) -> list[dict]:
    """Convert Anthropic-format tool defs to LiteLLM/OpenAI format."""
    converted = []
    for t in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return converted


class ApiBackend:
    """Reasoning backend using LiteLLM — supports all major LLM providers.

    Implements multi-turn tool-use loop with structured output via submit_result tool.
    """

    def __init__(
        self,
        model: str = "",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 16384,
    ):
        from graphbus_core.constants import DEFAULT_LLM_MODEL
        self._default_model = model or DEFAULT_LLM_MODEL
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _call_kwargs(self, model: str) -> dict:
        kwargs = {"model": model, "max_tokens": self._max_tokens, "temperature": self._temperature}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return kwargs

    def generate(
        self, prompt: str, system: Optional[str] = None, model_override: str = ""
    ) -> str:
        """Simple text generation without structured output."""
        active_model = model_override or self._default_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = self._call_kwargs(active_model)
        kwargs["messages"] = messages

        resp = litellm.completion(**kwargs)
        return resp.choices[0].message.content or ""

    def reason(
        self, spec: AgentSpec, context: str, model_override: str = ""
    ) -> ReasoningResult:
        """Run multi-turn tool-use loop, returning structured output."""
        active_model = model_override or self._default_model
        messages = [
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": context},
        ]
        total_input = 0
        total_output = 0

        # Build tools: agent tools + submit_result
        all_tools = _agent_tools_to_litellm(spec.tools) + [_pydantic_to_tool(spec.output_type)]

        for turn in range(MAX_TOOL_TURNS):
            kwargs = self._call_kwargs(active_model)
            kwargs["messages"] = messages
            kwargs["tools"] = all_tools

            response = litellm.completion(**kwargs)
            usage = response.usage
            total_input += usage.prompt_tokens if usage else 0
            total_output += usage.completion_tokens if usage else 0

            msg = response.choices[0].message
            tool_calls = msg.tool_calls or []

            if not tool_calls:
                # No tool calls — try to force submit
                logger.warning(
                    "[%s] no tool calls (turn=%d) — forcing submit",
                    spec.prompt_name, turn,
                )
                messages.append({"role": "assistant", "content": msg.content or ""})
                messages.append({"role": "user", "content": "Submit your final result now using the submit_result tool."})

                kwargs["messages"] = messages
                kwargs["tool_choice"] = {"type": "function", "function": {"name": SUBMIT_TOOL_NAME}}
                forced = litellm.completion(**kwargs)
                usage = forced.usage
                total_input += usage.prompt_tokens if usage else 0
                total_output += usage.completion_tokens if usage else 0

                forced_msg = forced.choices[0].message
                for tc in (forced_msg.tool_calls or []):
                    if tc.function.name == SUBMIT_TOOL_NAME:
                        data = json.loads(tc.function.arguments)
                        output = spec.output_type.model_validate(data)
                        return ReasoningResult(
                            output=output,
                            input_tokens=total_input,
                            output_tokens=total_output,
                            model=active_model,
                            backend="api",
                        )
                continue

            # Process tool calls
            messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]})

            for tc in tool_calls:
                if tc.function.name == SUBMIT_TOOL_NAME:
                    logger.info("[%s] submit_result received", spec.prompt_name)
                    data = json.loads(tc.function.arguments)
                    output = spec.output_type.model_validate(data)
                    return ReasoningResult(
                        output=output,
                        input_tokens=total_input,
                        output_tokens=total_output,
                        model=active_model,
                        backend="api",
                    )

                # Execute tool
                logger.info("[%s] tool: %s", spec.prompt_name, tc.function.name)
                try:
                    tool_input = json.loads(tc.function.arguments)
                    result = spec.handle_tool_call(tc.function.name, tool_input)
                except Exception as e:
                    logger.error("[%s] tool error %s: %s", spec.prompt_name, tc.function.name, e)
                    result = {"error": str(e)}

                content = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                if not content or content in ("", "null", "None", "{}", "[]"):
                    content = "(no data returned)"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                })

        raise RuntimeError(f"Agent '{spec.prompt_name}' exceeded {MAX_TOOL_TURNS} tool turns")
