"""
ClaudeCLIClient — LLM backend using Claude Code CLI subprocess.

Uses the existing Claude CLI OAuth session (no API key needed).
Implements the same interface as graphbus_core's LLMClient so it
can be dropped in as a replacement.

Tool calls are emulated via JSON prompting — Claude returns structured
JSON instead of using the native tool-use API.
"""

import json
import re
import subprocess
import sys
from typing import Optional


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from a response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_claude(prompt: str, system: Optional[str] = None, model: str = "claude-sonnet-4") -> str:
    """
    Call the Claude CLI and return the response text.

    Args:
        prompt: User message.
        system: Optional system prompt (appended via --append-system-prompt).
        model: Claude model name.

    Returns:
        Raw response text from Claude CLI.
    """
    cmd = ["claude", "-p", "--model", model]

    if system:
        cmd += ["--append-system-prompt", system]

    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(f"Claude CLI error (exit {result.returncode}): {stderr[:200]}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude CLI timed out after 120s")


class ClaudeCLIClient:
    """
    Claude CLI-backed LLM client. Drop-in replacement for LLMClient.

    Authenticates via the local Claude Code CLI OAuth session.
    No API key required — uses your existing `claude` login.
    """

    def __init__(
        self,
        model: str = "sonnet",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.temperature = temperature  # Stored but CLI doesn't expose this
        self.max_tokens = max_tokens

        # Verify CLI is available and authenticated
        self._check_auth()

    def _check_auth(self):
        """Quick check that claude CLI is available."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("claude CLI not available")
        except FileNotFoundError:
            raise RuntimeError(
                "claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            )

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate a text response from Claude.

        Args:
            prompt: User prompt.
            system: Optional system prompt.

        Returns:
            Generated text string.
        """
        return _call_claude(prompt, system=system, model=self.model)

    def generate_with_tool(
        self,
        prompt: str,
        tool_name: str,
        tool_schema: dict,
        system: Optional[str] = None,
    ) -> dict:
        """
        Generate a structured JSON response, emulating tool use.

        Instead of the Anthropic tool-use API, we inject the JSON schema
        into the prompt and ask Claude to respond with conforming JSON.

        Args:
            prompt: User prompt.
            tool_name: Name of the "tool" (used for context in the prompt).
            tool_schema: JSON schema describing the expected output structure.
            system: Optional system prompt.

        Returns:
            Parsed dict matching the tool schema.
        """
        schema_str = json.dumps(tool_schema, indent=2)

        structured_prompt = f"""{prompt}

---

Respond with ONLY a valid JSON object that matches this schema (no explanation, no markdown fences):

Schema for `{tool_name}`:
{schema_str}

Your JSON response:"""

        raw = _call_claude(structured_prompt, system=system, model=self.model)
        cleaned = _strip_fences(raw)

        try:
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                raise ValueError(f"Expected a JSON object, got {type(result).__name__}")
            return result
        except json.JSONDecodeError as exc:
            # Try to extract first JSON object from response
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            raise RuntimeError(
                f"ClaudeCLIClient: Could not parse JSON from response.\n"
                f"Raw: {raw[:300]}\nError: {exc}"
            ) from exc
