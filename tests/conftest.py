"""
Root conftest.py — test-suite wide configuration.

Adds the examples/ directory to sys.path so that example projects such as
hello_graphbus are importable when the RuntimeExecutor tries to load their
agent modules (e.g. "hello_graphbus.agents.hello").
"""

import sys
from pathlib import Path

# Repo root is one level above this file (tests/conftest.py → repo root)
REPO_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"

if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))
