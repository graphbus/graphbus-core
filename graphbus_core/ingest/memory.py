"""
Project memory management — ~/.graphbus/ structure.

Stores per-project negotiation history, context, and learned preferences
separate from the in-repo .graphbus/ config.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_project_id(project_path: Path) -> str:
    """
    Generate a deterministic project ID from the project path.

    Includes the directory name for readability + a hash for uniqueness.
    """
    project_path = Path(project_path).resolve()
    dir_name = project_path.name

    # Hash the full path for uniqueness
    path_hash = hashlib.sha256(str(project_path).encode()).hexdigest()[:8]

    return f"{dir_name}_{path_hash}"


def init_project_memory(
    project_path: Path,
    home_dir: Path,
) -> str:
    """
    Initialize or update project memory in ~/.graphbus/.

    Creates the project directory structure if it doesn't exist.
    Preserves existing negotiation history and context.

    Args:
        project_path: Path to the project being ingested
        home_dir: Path to ~/.graphbus/

    Returns:
        Project ID
    """
    project_path = Path(project_path).resolve()
    home_dir = Path(home_dir)

    project_id = get_project_id(project_path)
    project_dir = home_dir / "projects" / project_id

    # Create directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "negotiations").mkdir(exist_ok=True)

    # Write/update context.json (preserve existing fields)
    context_path = project_dir / "context.json"
    if context_path.exists():
        context = json.loads(context_path.read_text())
        context["updated_at"] = datetime.now(timezone.utc).isoformat()
    else:
        context = {
            "project_path": str(project_path),
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    context_path.write_text(json.dumps(context, indent=2))

    return project_id
