"""
Centralized constants and defaults for GraphBus
"""

# Default LLM model for agent orchestration
# DeepSeek R1 via DeepSeek API (OpenAI-compatible)
# Set DEEPSEEK_API_KEY env var, or ANTHROPIC_API_KEY for Claude models.
DEFAULT_LLM_MODEL = "deepseek-reasoner"

# Other LLM defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60  # seconds

# GraphBus warehousing API (api.graphbus.com)
# Used by NegotiationClient to store negotiation history, contracts, proposals.
# Requires GRAPHBUS_API_KEY. NOT used for LLM calls — those use provider keys directly.
GRAPHBUS_API_URL = "https://api.graphbus.com"
GRAPHBUS_WAREHOUSE_ENDPOINT = "/api/negotiations"  # base path for warehoused data
