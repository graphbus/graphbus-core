"""
LLM client abstraction - minimal Anthropic integration
"""

import os
from typing import Optional
from anthropic import Anthropic


class LLMClient:
    """
    Simple wrapper around Anthropic API for agent use.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """
        Initialize LLM client.

        Args:
            model: Model to use (default: claude-sonnet-4)
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
                return message.content[0].text
            return ""

        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            raise
