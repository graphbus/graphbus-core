"""
Centralized constants and defaults for GraphBus
"""

# Default LLM model for agent orchestration (LiteLLM model string format).
# Using spicychai cluster — OpenAI-compatible HAProxy pool with local LM Studio nodes.
# Set SPICYCHAI_BASE_URL and SPICYCHAI_API_KEY, or OPENAI_API_BASE + OPENAI_API_KEY.
# See https://docs.litellm.ai/docs/providers/openai_compatible for custom endpoints.
DEFAULT_LLM_MODEL = "openai/mistralai/ministral-3-14b-reasoning"

# spicychai cluster (Sravan's private LLM pool — HAProxy over LM Studio nodes)
SPICYCHAI_BASE_URL = "http://spicychai.com:3443/light/v1"
SPICYCHAI_API_KEY = "a762a564d533cc28abb325a404e34005cd7b51e698d9dc1e"
SPICYCHAI_MEDIUM_URL = "http://spicychai.com:3443/medium/v1"

# Other LLM defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60  # seconds

# GraphBus warehousing API (api.graphbus.com)
# Used by NegotiationClient to store negotiation history, contracts, proposals.
# Requires GRAPHBUS_API_KEY. NOT used for LLM calls — those use provider keys directly.
GRAPHBUS_API_URL = "https://api.graphbus.com"
GRAPHBUS_WAREHOUSE_ENDPOINT = "/api/negotiations"  # base path for warehoused data
