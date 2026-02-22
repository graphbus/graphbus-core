"""
API Key authentication for the GraphBus API.

On startup:
- Uses GRAPHBUS_API_KEY env var if set
- Otherwise generates a secure random key and persists it to .env

When Firebase is initialized, API keys are also validated against Firestore
(multi-tenant mode). The env-var key always works as a fallback (self-hosted mode).
"""

import os
import secrets
from pathlib import Path

from fastapi import Header, HTTPException

from graphbus_api.firebase_auth import is_firebase_initialized, validate_api_key


_api_key: str = ""

# Repo root (one level up from graphbus_api/)
_REPO_ROOT = Path(__file__).resolve().parent.parent


def init_api_key() -> None:
    """Load or generate the API key. Call once at startup."""
    global _api_key

    _api_key = os.environ.get("GRAPHBUS_API_KEY", "").strip()

    if _api_key:
        print("\n" + "=" * 60)
        print("  GraphBus API Key loaded from environment")
        print("=" * 60 + "\n")
        return

    # Generate a new key
    _api_key = secrets.token_urlsafe(32)

    # Persist to .env
    env_path = _REPO_ROOT / ".env"
    _update_env_file(env_path, "GRAPHBUS_API_KEY", _api_key)

    # Also set in current process so downstream code can read it
    os.environ["GRAPHBUS_API_KEY"] = _api_key

    print("\n" + "=" * 60)
    print("  GraphBus API Key (generated — save this!):")
    print(f"  {_api_key}")
    print(f"  Written to {env_path}")
    print("=" * 60 + "\n")


def _update_env_file(env_path: Path, key: str, value: str) -> None:
    """Write or update a key=value pair in a .env file."""
    lines: list[str] = []
    found = False

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)


def get_api_key() -> str:
    """Return the current API key."""
    return _api_key


async def require_api_key(x_api_key: str = Header(...)) -> str:
    """FastAPI dependency — validates the X-Api-Key header."""
    # Multi-tenant: check Firestore if Firebase is initialized
    if is_firebase_initialized():
        user = validate_api_key(x_api_key)
        if user:
            return x_api_key

    # Self-hosted fallback: check env-var key
    if x_api_key == _api_key:
        return x_api_key

    raise HTTPException(status_code=401, detail="Invalid API key")
