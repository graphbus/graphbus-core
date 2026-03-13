"""
Centralized constants and defaults for GraphBus
"""

# Default LLM model for agent orchestration (LiteLLM model string format).
DEFAULT_LLM_MODEL = "anthropic/claude-haiku-4-5"

# spicychai cluster (HAProxy → LM Studio — for openai/* model routing)
# Base URLs are not sensitive; the API key must come from the SPICYCHAI_API_KEY
# environment variable.  No fallback value is stored here — this is a public
# package and hardcoding a bearer token in source is a credential leak.
SPICYCHAI_BASE_URL = "http://spicychai.com:3443/light/v1"
SPICYCHAI_MEDIUM_URL = "http://spicychai.com:3443/medium/v1"
SPICYCHAI_API_KEY = ""  # sentinel — real value must come from env var

# Other LLM defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60  # seconds

# GraphBus warehousing API (api.graphbus.com)
# Used by NegotiationClient to store negotiation history, contracts, proposals.
# Requires GRAPHBUS_API_KEY. NOT used for LLM calls — those use provider keys directly.
GRAPHBUS_API_URL = "https://api.graphbus.com"
GRAPHBUS_WAREHOUSE_ENDPOINT = "/api/negotiations"  # base path for warehoused data
