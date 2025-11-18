"""
LLM client abstraction - minimal Anthropic integration
"""

import os
from typing import Optional
from anthropic import Anthropic
from graphbus_core.constants import DEFAULT_LLM_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS


class LLMClient:
    """
    Simple wrapper around Anthropic API for agent use.
    """

    def __init__(
        self,
        model: str = DEFAULT_LLM_MODEL,
        api_key: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS
    ):
        """
        Initialize LLM client.

        Args:
            model: Model to use (default: from DEFAULT_LLM_MODEL constant)
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Get API key from parameter or environment
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: User prompt
            system: Optional system prompt

        Returns:
            Generated text
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system if system else "",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                response_text = message.content[0].text
                # Debug: Print first 200 chars of response for troubleshooting
                # print(f"[LLM Response Preview]: {response_text[:200]}...")
                return response_text
            else:
                print(f"Warning: Empty response from LLM. Message: {message}")
                return ""

        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            import traceback
            traceback.print_exc()
            raise

    def generate_with_tool(self, prompt: str, tool_name: str, tool_schema: dict, system: Optional[str] = None) -> dict:
        """
        Generate a structured response using Claude's tool use feature.

        Args:
            prompt: User prompt
            tool_name: Name of the tool to use
            tool_schema: JSON schema for the tool's input_schema
            system: Optional system prompt

        Returns:
            Parsed tool use result as dictionary
        """
        try:
            # Build the tool definition
            tool_definition = {
                "name": tool_name,
                "description": f"Use this tool to provide structured output for {tool_name}",
                "input_schema": tool_schema
            }

            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system if system else "",
                tools=[tool_definition],
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract tool use result
            if message.content and len(message.content) > 0:
                for block in message.content:
                    if block.type == "tool_use":
                        # Return the input that was passed to the tool
                        return block.input

                # If no tool use found, raise error
                raise ValueError(f"No tool use found in response. Got: {message.content}")
            else:
                raise ValueError("Empty response from LLM")

        except Exception as e:
            print(f"Error calling Anthropic API with tool: {e}")
            import traceback
            traceback.print_exc()
            raise
