"""
GraphBus Core - Agent-Driven Code Refactoring Framework

Build Mode: Agents are active, can negotiate and refactor code
Runtime Mode: Agents are dormant, code executes statically
"""

from graphbus_core.node_base import GraphBusNode
from graphbus_core.decorators import schema_method, subscribe, depends_on
from graphbus_core.config import BuildConfig, RuntimeConfig, LLMConfig, GraphBusConfig

__version__ = "0.1.0"

__all__ = [
    "GraphBusNode",
    "schema_method",
    "subscribe",
    "depends_on",
    "BuildConfig",
    "RuntimeConfig",
    "LLMConfig",
    "GraphBusConfig",
]
