"""Project management."""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json


def list_projects(home_dir: Path) -> List[Dict[str, Any]]:
    """List all projects in ~/.graphbus/projects/."""
    home_dir = Path(home_dir)
    projects_dir = home_dir / "projects"
    
    if not projects_dir.exists():
        return []
    
    projects = []
    for project_dir in sorted(projects_dir.iterdir()):
        if project_dir.is_dir():
            context_file = project_dir / "context.json"
            if context_file.exists():
                try:
                    with open(context_file) as f:
                        context = json.load(f)
                        projects.append({
                            "id": context.get("project_id"),
                            "path": context.get("project_path"),
                            "created_at": context.get("created_at"),
                        })
                except (json.JSONDecodeError, IOError):
                    pass
    
    return projects


def get_project_info(home_dir: Path, project_id: str) -> Dict[str, Any]:
    """Get information about a specific project."""
    projects = list_projects(home_dir)
    for project in projects:
        if project.get("id") == project_id:
            return project
    
    raise ValueError(f"Project not found: {project_id}")


def list_recent_projects(home_dir: Path) -> List[Dict[str, Any]]:
    """List most recent projects."""
    projects = list_projects(home_dir)
    # Sort by created_at (most recent first)
    return sorted(projects, key=lambda p: p.get("created_at", ""), reverse=True)
