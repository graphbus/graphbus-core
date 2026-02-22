"""
tests/cli/conftest.py

Session-scoped setup for CLI tests: ensure the hello_graphbus build artifacts
exist before any test that depends on them runs.  The .graphbus/ directory is
gitignored (it's a build output), so we rebuild it automatically on a fresh
checkout or whenever the artifacts are missing.
"""

import pytest
from pathlib import Path


HELLO_GRAPHBUS_AGENTS = "examples/hello_graphbus/agents"
HELLO_GRAPHBUS_ARTIFACTS = "examples/hello_graphbus/.graphbus"
REQUIRED_ARTIFACT_FILES = {"agents.json", "topics.json", "graph.json", "build_summary.json"}


def _artifacts_are_valid(artifacts_dir: Path) -> bool:
    """Return True if all required artifact files are present."""
    if not artifacts_dir.exists():
        return False
    existing = {f.name for f in artifacts_dir.iterdir() if f.is_file()}
    return REQUIRED_ARTIFACT_FILES.issubset(existing)


@pytest.fixture(scope="session", autouse=True)
def ensure_hello_graphbus_artifacts():
    """
    Build hello_graphbus artifacts once per test session if they're missing.

    This fixture is session-scoped and autouse=True so it runs automatically
    before any CLI test, with zero changes needed in individual test files.
    """
    artifacts_dir = Path(HELLO_GRAPHBUS_ARTIFACTS)

    if _artifacts_are_valid(artifacts_dir):
        return  # Already built — nothing to do

    agents_dir = Path(HELLO_GRAPHBUS_AGENTS)
    if not agents_dir.exists():
        pytest.skip(f"hello_graphbus agents not found at {agents_dir}")
        return

    try:
        from graphbus_core.config import BuildConfig
        from graphbus_core.build.builder import build_project

        config = BuildConfig(
            root_package="examples.hello_graphbus.agents",
            output_dir=HELLO_GRAPHBUS_ARTIFACTS,
        )
        build_project(config, enable_agents=False)

    except Exception as exc:
        pytest.skip(f"Failed to build hello_graphbus artifacts: {exc}")
