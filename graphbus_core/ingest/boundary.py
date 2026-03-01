"""
Agent boundary detection — groups source files into logical agents.

Strategies:
- directory: one agent per directory (default, deterministic)
- llm: use LLM to propose boundaries (future)
"""

from pathlib import Path
from typing import List, Dict, Any


def detect_boundaries(
    file_data: List[Dict[str, Any]],
    strategy: str = "directory",
) -> List[Dict[str, Any]]:
    """
    Group files into agent boundaries.

    Args:
        file_data: List of {"path": Path, "symbols": [...]} dicts
        strategy: Detection strategy ("directory" or "llm")

    Returns:
        List of boundary dicts: {name, description, files, symbols}
    """
    if strategy == "directory":
        return _directory_strategy(file_data)
    else:
        raise ValueError(f"Unknown boundary strategy: {strategy}")


def _directory_strategy(file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group files by their parent directory into agents.

    Each unique parent directory becomes an agent.
    Agent name is derived from the directory name, PascalCased + "Agent".
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}

    for entry in file_data:
        path = Path(entry["path"])
        # Use the immediate parent directory as the group key
        parent = path.parent.name
        if parent not in groups:
            groups[parent] = []
        groups[parent].append(entry)

    boundaries = []
    for dir_name, entries in sorted(groups.items()):
        agent_name = _to_agent_name(dir_name)
        all_symbols = []
        for entry in entries:
            for sym in entry["symbols"]:
                sym_copy = dict(sym)
                sym_copy["file"] = str(Path(entry["path"]).name)
                all_symbols.append(sym_copy)

        description = _generate_description(dir_name, all_symbols)

        boundaries.append({
            "name": agent_name,
            "description": description,
            "files": [entry["path"] for entry in entries],
            "symbols": all_symbols,
        })

    return boundaries


def _to_agent_name(dir_name: str) -> str:
    """Convert a directory name to a PascalCase agent name."""
    # Split on underscores, hyphens, dots
    parts = []
    for part in dir_name.replace("-", "_").replace(".", "_").split("_"):
        if part:
            parts.append(part.capitalize())

    name = "".join(parts) if parts else dir_name.capitalize()

    # Append Agent if not already there
    if not name.endswith("Agent"):
        name += "Agent"

    return name


def _generate_description(dir_name: str, symbols: List[Dict[str, Any]]) -> str:
    """Generate a human-readable description of an agent boundary."""
    func_names = [s["name"] for s in symbols if s["type"] == "function"]
    class_names = [s["name"] for s in symbols if s["type"] == "class"]

    parts = [f"Owns the {dir_name}/ directory."]

    if class_names:
        parts.append(f"Defines: {', '.join(class_names[:5])}.")
    if func_names:
        parts.append(f"Functions: {', '.join(func_names[:5])}.")

    return " ".join(parts)
