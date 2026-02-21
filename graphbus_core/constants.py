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
