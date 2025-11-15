"""
Configuration objects for Build and Runtime modes
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMConfig:
    """
    Configuration for LLM client (Build Mode only).
    """
    model: str = "claude-sonnet-4"  # Model to use
    api_key: str | None = None  # API key (or use environment variable)
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60  # seconds
    base_url: str | None = None  # Optional custom API endpoint
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyConfig:
    """
    Safety guardrails for agent negotiation.
    """
    max_negotiation_rounds: int = 10  # Max rounds before forcing termination
    max_proposals_per_agent: int = 3  # Max proposals each agent can make total
    max_proposals_per_round: int = 1  # Max proposals per agent per round
    max_back_and_forth: int = 3  # Max times a proposal can be re-evaluated
    convergence_threshold: int = 2  # Rounds with no new proposals = converged
    require_arbiter_on_conflict: bool = True  # Require arbiter when agents disagree
    arbiter_agents: list[str] = field(default_factory=list)  # Names of arbiter agents
    max_file_changes_per_commit: int = 1  # Max files a single commit can modify
    max_total_file_changes: int = 10  # Max total files modified in entire build
    allow_external_dependencies: bool = False  # Allow adding new imports
    protected_files: list[str] = field(default_factory=list)  # Files that can't be modified


@dataclass
class BuildConfig:
    """
    Configuration for Build Mode (agent orchestration & code refactoring).
    """
    root_package: str  # Python package to scan (e.g. "my_project.agents")
    llm_config: LLMConfig | None = None  # LLM configuration for agents
    include_modules: list[str] | None = None  # Specific modules to include
    exclude_modules: list[str] | None = None  # Modules to exclude
    refactoring_goals: list[str] = field(default_factory=list)  # High-level goals
    safety_config: SafetyConfig = field(default_factory=SafetyConfig)  # Safety guardrails
    output_dir: str = ".graphbus"  # Where to write artifacts
    enable_human_in_loop: bool = False  # Pause for human approval
    parallel_agents: bool = False  # Run agents in parallel when possible (future)


@dataclass
class RuntimeConfig:
    """
    Configuration for Runtime Mode (static code execution).
    """
    artifacts_dir: str = ".graphbus"  # Where to load artifacts from
    entrypoint: str | None = None  # Optional entrypoint (e.g. "my_project.main:run")
    enable_message_bus: bool = True  # Enable static pub/sub routing
    log_level: str = "INFO"
    extra_params: dict[str, Any] = field(default_factory=dict)
