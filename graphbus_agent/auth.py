"""
Token resolution for GraphBus Agent SDK.

Resolution order:
  1. Explicit token passed as argument
  2. GRAPHBUS_TOKEN env var
  3. ANTHROPIC_API_KEY env var
  4. OpenClaw auth-profiles  (~/.openclaw/agents/main/agent/auth-profiles.json)
  5. Claude CLI config       (~/.claude.json)
"""

import json
import os
from pathlib import Path
from typing import Optional


def _read_openclaw_token() -> Optional[str]:
    """Extract Anthropic token from OpenClaw's agent auth store."""
    candidates = [
        Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json",
    ]
    # Also check any other agent dirs
    agents_dir = Path.home() / ".openclaw" / "agents"
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            p = agent_dir / "agent" / "auth-profiles.json"
            if p.exists() and p not in candidates:
                candidates.append(p)

    for path in candidates:
        try:
            data = json.loads(path.read_text())
            profiles = data.get("profiles", {})
            for profile_key, profile in profiles.items():
                if "anthropic" in profile_key.lower():
                    token = profile.get("token") or profile.get("api_key")
                    if token:
                        return token
        except Exception:
            continue

    return None


def _read_claude_cli_token() -> Optional[str]:
    """Extract token from Claude Code CLI config (~/.claude.json)."""
    path = Path.home() / ".claude.json"
    try:
        data = json.loads(path.read_text())
        # Claude CLI may store oauth_token or similar
        for key in ("oauthToken", "oauth_token", "accessToken", "access_token", "apiKey", "api_key"):
            if key in data:
                return data[key]
    except Exception:
        pass
    return None


def resolve_token(token: Optional[str] = None) -> str:
    """
    Resolve an Anthropic-compatible token from all available sources.

    Args:
        token: Explicit token (highest priority).

    Returns:
        Resolved token string.

    Raises:
        RuntimeError: If no token can be found.
    """
    sources = [
        ("explicit argument", lambda: token),
        ("GRAPHBUS_TOKEN env",   lambda: os.environ.get("GRAPHBUS_TOKEN")),
        ("ANTHROPIC_API_KEY env", lambda: os.environ.get("ANTHROPIC_API_KEY")),
        ("OpenClaw auth store",  _read_openclaw_token),
        ("Claude CLI config",    _read_claude_cli_token),
    ]

    for name, getter in sources:
        try:
            value = getter()
        except Exception:
            value = None

        if value:
            print(f"[graphbus-agent] Auth: using token from {name}")
            return value

    raise RuntimeError(
        "No Anthropic token found. Provide one of:\n"
        "  • GRAPHBUS_TOKEN or ANTHROPIC_API_KEY environment variable\n"
        "  • OpenClaw configured with a Claude setup-token\n"
        "  • Run: claude setup-token  (then openclaw models auth setup-token --provider anthropic)"
    )
