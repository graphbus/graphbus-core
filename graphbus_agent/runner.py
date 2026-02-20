"""
GraphBus Headless Agent Runner

Scans a project, activates LLM agents (via Claude OAuth token),
runs the negotiation cycle, and emits build artifacts.

Usage as a library:
    from graphbus_agent.runner import run_agents
    result = run_agents("my_project/agents", intent="Add error handling")

Usage from CLI:
    python3 -m graphbus_agent --package my_project.agents --intent "Add error handling"
"""

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

# Ensure graphbus_core is importable when running from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphbus_agent.auth import resolve_token


@dataclass
class AgentRunResult:
    success: bool
    package: str
    intent: Optional[str]
    artifacts_dir: str
    agents_found: int
    agents_active: int
    modified_files: list[str]
    log: list[str]
    duration_s: float
    error: Optional[str] = None


def run_agents(
    root_package: str,
    intent: Optional[str] = None,
    output_dir: Optional[str] = None,
    token: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    dry_run: bool = False,
) -> AgentRunResult:
    """
    Run GraphBus agent negotiation on a Python package.

    Args:
        root_package:  Dotted Python package path containing GraphBusNode subclasses.
                       e.g. "examples.hello_graphbus.agents"
        intent:        Natural-language goal for the agents.
                       e.g. "Add input validation and better error messages"
        output_dir:    Where to write .graphbus/ artifacts. Defaults to cwd/.graphbus
        token:         Anthropic/Claude OAuth token. Auto-resolved if not provided.
        model:         Claude model to use (default: claude-sonnet-4-20250514).
        dry_run:       If True, run build pipeline but skip LLM calls.

    Returns:
        AgentRunResult with outcome, logs, and artifact path.
    """
    from graphbus_core.config import BuildConfig
    from graphbus_core.build.builder import build_project

    log: list[str] = []
    t0 = time.time()

    def _log(msg: str):
        print(msg)
        log.append(msg)

    _log(f"[graphbus-agent] Package  : {root_package}")
    _log(f"[graphbus-agent] Intent   : {intent or '(none)'}")
    _log(f"[graphbus-agent] Dry-run  : {dry_run}")

    resolved_output = output_dir or os.path.join(os.getcwd(), ".graphbus")

    try:
        # Resolve auth — decide between direct API key or Claude CLI (OAuth)
        resolved_token = None
        use_cli_backend = False

        if not dry_run:
            resolved_token = resolve_token(token)
            # OAuth setup-tokens (sk-ant-oat01-) can't be used directly with the API;
            # route through the Claude CLI which is already OAuth-authenticated.
            if resolved_token and resolved_token.startswith("sk-ant-oat01-"):
                _log("[graphbus-agent] OAuth token detected → using Claude CLI backend")
                use_cli_backend = True

        # Build config
        config = BuildConfig(
            root_package=root_package,
            output_dir=resolved_output,
        )
        if intent:
            config.user_intent = intent

        if use_cli_backend:
            # Inject the Claude CLI client into the build pipeline
            from graphbus_agent.claude_client import ClaudeCLIClient
            from graphbus_core.config import LLMConfig
            cli_client = ClaudeCLIClient(model="sonnet")
            # Store on config for the orchestrator to pick up
            config.llm_config = LLMConfig(model="sonnet", api_key="cli-backend")
            config._cli_llm_client = cli_client  # custom attribute for patching
        elif resolved_token:
            from graphbus_core.config import LLMConfig
            config.llm_config = LLMConfig(model=model, api_key=resolved_token)

        enable_agents = not dry_run and resolved_token is not None

        # Run build
        _log(f"[graphbus-agent] Running build (agents={'ON' if enable_agents else 'OFF'}) ...")
        artifacts = build_project(config, enable_agents=enable_agents)

        modified = getattr(artifacts, "modified_files", []) or []
        summary = getattr(artifacts, "summary", {}) or {}
        agents_found = summary.get("agents_count", 0) if summary else 0

        _log(f"[graphbus-agent] ✅ Done  — artifacts: {resolved_output}")
        if modified:
            _log(f"[graphbus-agent] Modified files ({len(modified)}):")
            for f in modified:
                _log(f"  • {f}")

        return AgentRunResult(
            success=True,
            package=root_package,
            intent=intent,
            artifacts_dir=resolved_output,
            agents_found=agents_found,
            agents_active=1 if enable_agents else 0,
            modified_files=modified,
            log=log,
            duration_s=round(time.time() - t0, 2),
        )

    except Exception as exc:
        _log(f"[graphbus-agent] ❌ Failed: {exc}")
        return AgentRunResult(
            success=False,
            package=root_package,
            intent=intent,
            artifacts_dir=resolved_output,
            agents_found=0,
            agents_active=0,
            modified_files=[],
            log=log,
            duration_s=round(time.time() - t0, 2),
            error=str(exc),
        )
