"""
graphbus_agent — headless agent SDK for GraphBus

Uses Claude OAuth token (from OpenClaw, env var, or explicit) to activate
LLM agents for code negotiation and refactoring.

Quick start:
    from graphbus_agent import run_agents

    result = run_agents(
        root_package="my_project.agents",
        intent="Add input validation and structured error responses",
    )
    print(result.artifacts_dir)
"""

from graphbus_agent.runner import run_agents, AgentRunResult
from graphbus_agent.auth import resolve_token

__all__ = ["run_agents", "AgentRunResult", "resolve_token"]
