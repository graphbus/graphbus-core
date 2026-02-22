"""Claude Agent SDK reasoning backend for GraphBus.

Architecture (adapted from alpaca-trader):
  1. MCP bridge converts tool defs → in-process MCP server
  2. SDK runs the agent in a forked subprocess (complete event loop isolation)
  3. Agent's text response is formatted into Pydantic structured output
     using a cheap formatting call via LiteLLM
  4. Agent reasoning is free on Claude Max subscription (SDK uses OAuth token)

Requirements:
  - claude-agent-sdk installed
  - CLAUDE_CODE_OAUTH_TOKEN set (run `claude setup-token`)
  - Optional: ANTHROPIC_API_KEY for the formatting step
"""

import logging
import multiprocessing as mp
import os
import queue
from typing import Optional

from .protocol import AgentSpec, ReasoningResult

logger = logging.getLogger(__name__)

FORMATTING_MODEL = "claude-sonnet-4-6"
SDK_TIMEOUT = 1200  # 20 minutes

# Fork context for complete process isolation
_fork_ctx = mp.get_context("fork")


def _sdk_worker(result_queue, prompt, system_prompt, model, max_turns, mcp_servers, env):
    """Run SDK query in an isolated forked process with its own event loop."""
    import asyncio
    import os

    # Remove API key from forked process so SDK only uses OAuth token
    os.environ.pop("ANTHROPIC_API_KEY", None)

    async def _run():
        from claude_agent_sdk import ClaudeAgentOptions, query
        from claude_agent_sdk.types import ResultMessage

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=model,
            max_turns=max_turns,
            permission_mode="bypassPermissions",
            mcp_servers=mcp_servers,
            env=env,
        )

        result_msg = None
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    result_msg = message
        except Exception as e:
            if result_msg is None:
                raise
        return result_msg

    try:
        result_msg = asyncio.run(_run())
        if result_msg is None:
            result_queue.put({"error": "SDK query produced no result"})
        elif result_msg.is_error:
            result_queue.put({"error": f"SDK error: {result_msg.result}"})
        else:
            result_queue.put({"text": result_msg.result or ""})
    except Exception as e:
        result_queue.put({"error": str(e)})


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


def _format_with_litellm(agent_text: str, spec: AgentSpec, api_key: Optional[str] = None) -> tuple:
    """Use a cheap model to format agent text into Pydantic structured output.

    Returns (output, input_tokens, output_tokens).
    """
    import json
    import litellm

    schema = _clean_schema(spec.output_type.model_json_schema())
    tool_def = {
        "type": "function",
        "function": {
            "name": "submit_result",
            "description": "Submit the structured result extracted from the agent's analysis.",
            "parameters": schema,
        },
    }

    kwargs = {
        "model": FORMATTING_MODEL,
        "max_tokens": 8192,
        "messages": [
            {"role": "system", "content": (
                "You are a formatting assistant. Extract the key information from "
                "the agent's response and structure it into the required output format. "
                "Call submit_result with the extracted data. Be faithful to the agent's "
                "analysis — do not add, change, or omit information."
            )},
            {"role": "user", "content": agent_text},
        ],
        "tools": [tool_def],
        "tool_choice": {"type": "function", "function": {"name": "submit_result"}},
    }
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.completion(**kwargs)
    usage = response.usage

    msg = response.choices[0].message
    for tc in (msg.tool_calls or []):
        if tc.function.name == "submit_result":
            data = json.loads(tc.function.arguments)
            output = spec.output_type.model_validate(data)
            return output, usage.prompt_tokens or 0, usage.completion_tokens or 0

    raise RuntimeError("Formatting model did not produce structured output")


class SdkBackend:
    """Reasoning backend using the Claude Agent SDK (Max subscription).

    Agent reasoning runs via SDK + OAuth token in a forked process (no per-token cost).
    Formatting step uses a cheap model via LiteLLM (minimal cost).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = ""):
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError:
            raise ImportError(
                "claude-agent-sdk is not installed. "
                "Install it with: pip install claude-agent-sdk"
            )

        token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
        if not token:
            raise ValueError(
                "CLAUDE_CODE_OAUTH_TOKEN not set. "
                "Run `claude setup-token` to generate a token."
            )

        self._default_model = model or "sonnet"
        self._api_key = api_key

    def generate(
        self, prompt: str, system: Optional[str] = None, model_override: str = ""
    ) -> str:
        """Simple text generation via SDK (no structured output)."""
        result_queue = _fork_ctx.Queue()
        proc = _fork_ctx.Process(
            target=_sdk_worker,
            args=(
                result_queue, prompt, system or "",
                model_override or self._default_model, 5, None,
                {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"},
            ),
        )
        proc.start()

        try:
            result = result_queue.get(timeout=SDK_TIMEOUT)
        except queue.Empty:
            proc.kill()
            proc.join(timeout=5)
            raise RuntimeError("SDK query timed out")
        finally:
            proc.join(timeout=30)
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5)

        if "error" in result:
            raise RuntimeError(f"SDK error: {result['error']}")
        return result.get("text", "")

    def reason(
        self, spec: AgentSpec, context: str, model_override: str = ""
    ) -> ReasoningResult:
        """Run agent via SDK, then format output with cheap model."""
        from .mcp_bridge import create_mcp_server_config

        active_model = model_override or self._default_model

        # Build MCP servers for the SDK agent
        mcp_servers = {}
        if spec.tools:
            mcp_config = create_mcp_server_config(
                agent_name=spec.prompt_name,
                tools=spec.tools,
                handler=spec.handle_tool_call,
            )
            mcp_servers[f"graphbus-{spec.prompt_name}-tools"] = mcp_config

        # Step 1: Run in forked process
        result_queue = _fork_ctx.Queue()
        proc = _fork_ctx.Process(
            target=_sdk_worker,
            args=(
                result_queue, context, spec.system_prompt,
                active_model, 25, mcp_servers if mcp_servers else None,
                {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"},
            ),
        )
        proc.start()
        logger.info("[%s] SDK worker forked (pid=%d)", spec.prompt_name, proc.pid)

        try:
            result = result_queue.get(timeout=SDK_TIMEOUT)
        except queue.Empty:
            proc.kill()
            proc.join(timeout=5)
            raise RuntimeError(f"SDK query for '{spec.prompt_name}' timed out")
        finally:
            proc.join(timeout=30)
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5)

        if "error" in result:
            raise RuntimeError(f"SDK worker error: {result['error']}")

        agent_text = result["text"]
        if not agent_text:
            raise RuntimeError(f"SDK query for '{spec.prompt_name}' returned empty result")

        # Step 2: Format → structured output via cheap model
        logger.info("[%s] formatting SDK response with %s", spec.prompt_name, FORMATTING_MODEL)
        output, fmt_input, fmt_output = _format_with_litellm(
            agent_text, spec, self._api_key
        )

        return ReasoningResult(
            output=output,
            raw_text=agent_text,
            input_tokens=fmt_input,
            output_tokens=fmt_output,
            model=FORMATTING_MODEL,
            backend="sdk",
        )
