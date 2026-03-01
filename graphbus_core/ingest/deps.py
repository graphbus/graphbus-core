"""
Dependency inference — analyze imports to find edges between agents.
"""

from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

from graphbus_core.ingest.analyzer import extract_imports


def infer_dependencies(
    boundaries: List[Dict[str, Any]],
    project_path: Path,
) -> List[Tuple[str, str]]:
    """
    Infer dependency edges between agents by analyzing imports.

    Args:
        boundaries: List of boundary dicts with name, files, module_prefix
        project_path: Root of the project

    Returns:
        List of (from_agent, to_agent) tuples
    """
    # Build a mapping of module prefixes to agent names
    prefix_to_agent: Dict[str, str] = {}
    for b in boundaries:
        if "module_prefix" in b:
            prefix_to_agent[b["module_prefix"]] = b["name"]

    # Also map individual files to agents
    file_to_agent: Dict[str, str] = {}
    for b in boundaries:
        for f in b["files"]:
            file_to_agent[str(f)] = b["name"]

    edges: Set[Tuple[str, str]] = set()

    for b in boundaries:
        agent_name = b["name"]

        for file_path in b["files"]:
            imports = extract_imports(Path(file_path))

            for imp in imports:
                # Check if this import matches another agent's module prefix
                target_agent = _resolve_import_to_agent(imp, prefix_to_agent)
                if target_agent and target_agent != agent_name:
                    edges.add((agent_name, target_agent))

    return sorted(edges)


def _resolve_import_to_agent(
    import_path: str,
    prefix_to_agent: Dict[str, str],
) -> str:
    """Resolve an import path to an agent name."""
    # Try exact match first
    if import_path in prefix_to_agent:
        return prefix_to_agent[import_path]

    # Try prefix match (e.g., "myapp.models.user" matches "myapp.models")
    for prefix, agent in prefix_to_agent.items():
        if import_path.startswith(prefix + ".") or import_path == prefix:
            return agent

    return ""
