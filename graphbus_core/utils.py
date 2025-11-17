"""
Utility functions for GraphBus
"""

import json
from typing import Any, Dict, Optional

from graphbus_core.exceptions import LLMResponseError


def parse_json_from_llm_response(response: str, context: str = "LLM response") -> Any:
    """
    Parse JSON from LLM response, handling markdown code fences.

    LLM responses often include markdown formatting like:
    ```json
    {"key": "value"}
    ```
    or
    ```json
    [{"item": 1}, {"item": 2}]
    ```

    This function strips those markers and parses the JSON.

    Args:
        response: Raw LLM response string
        context: Description of what's being parsed (for error messages)

    Returns:
        Parsed JSON (dict, list, or primitive)

    Raises:
        LLMResponseError: If response cannot be parsed as JSON
    """
    if not response:
        raise LLMResponseError(
            f"Empty response when parsing {context}",
            raw_response=response
        )

    # Strip whitespace
    response = response.strip()

    # Remove markdown code fences
    if response.startswith('```json'):
        response = response[7:]
    elif response.startswith('```'):
        response = response[3:]

    if response.endswith('```'):
        response = response[:-3]

    response = response.strip()

    # Attempt to parse
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise LLMResponseError(
            f"Failed to parse JSON from {context}: {e}",
            raw_response=response
        )


def validate_json_structure(data: dict, required_keys: list, context: str = "JSON") -> None:
    """
    Validate that a JSON object has required keys.

    Args:
        data: Parsed JSON dict
        required_keys: List of required key names
        context: Description for error messages

    Raises:
        LLMResponseError: If required keys are missing
    """
    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        raise LLMResponseError(
            f"{context} missing required keys: {missing_keys}. Got: {list(data.keys())}"
        )


def format_exception_for_user(e: Exception, verbose: bool = False) -> str:
    """
    Format exception message for user-friendly display.

    Args:
        e: The exception
        verbose: If True, include more technical details

    Returns:
        Formatted error message string
    """
    from graphbus_core.exceptions import GraphBusError, LLMResponseError

    if isinstance(e, LLMResponseError):
        msg = f"LLM response error: {str(e)}"
        if verbose and e.raw_response:
            msg += f"\n  Raw response: {e.raw_response[:200]}..."
        return msg

    elif isinstance(e, GraphBusError):
        return f"GraphBus error: {str(e)}"

    else:
        if verbose:
            return f"Unexpected error ({type(e).__name__}): {str(e)}"
        else:
            return f"Error: {str(e)}"
