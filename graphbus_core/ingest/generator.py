"""
YAML generator — writes .graphbus/agents/*.yaml and .graphbus/graph.yaml.
"""

from pathlib import Path
from typing import List, Dict, Any

import yaml


def generate_agent_yaml(
    boundary: Dict[str, Any],
    output_dir: Path,
    project_path: Path,
) -> Path:
    """
    Generate a YAML agent definition from a boundary.

    Args:
        boundary: Boundary dict with name, description, files, symbols
        output_dir: .graphbus/ directory
        project_path: Root of the project (for relative paths)

    Returns:
        Path to the generated YAML file
    """
    agents_dir = output_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Build relative source file paths
    source_files = []
    for f in boundary["files"]:
        try:
            rel = Path(f).relative_to(project_path)
        except ValueError:
            rel = Path(f)
        source_files.append(str(rel))

    # Build methods from symbols
    methods = {}
    for sym in boundary.get("symbols", []):
        if sym["type"] == "function" and sym.get("params"):
            methods[sym["name"]] = {
                "input": {k: v for k, v in sym["params"].items()},
                "output": {},  # Would need return type analysis
                "description": sym.get("docstring", ""),
            }

    # Generate system prompt
    system_prompt = _generate_system_prompt(boundary)

    agent_def = {
        "name": boundary["name"],
        "description": boundary["description"],
        "source_files": source_files,
        "system_prompt": system_prompt,
        "methods": methods,
        "subscribes": [],
        "publishes": [],
    }

    yaml_path = agents_dir / f"{boundary['name']}.yaml"
    yaml_path.write_text(yaml.dump(agent_def, default_flow_style=False, sort_keys=False))
    return yaml_path


def _generate_system_prompt(boundary: Dict[str, Any]) -> str:
    """Generate a system prompt for an agent based on its boundary."""
    name = boundary["name"]
    desc = boundary["description"]

    func_names = [s["name"] for s in boundary.get("symbols", []) if s["type"] == "function"]
    class_names = [s["name"] for s in boundary.get("symbols", []) if s["type"] == "class"]

    lines = [
        f"You are {name}, responsible for the following code.",
        f"{desc}",
    ]

    if class_names:
        lines.append(f"You manage these classes: {', '.join(class_names[:10])}.")
    if func_names:
        lines.append(f"You manage these functions: {', '.join(func_names[:10])}.")

    lines.append("In Build Mode, you can negotiate changes to improve this code.")

    return "\n".join(lines)


def generate_graph_yaml(
    boundaries: List[Dict[str, Any]],
    output_dir: Path,
) -> Path:
    """
    Generate graph.yaml with agent nodes and dependency edges.

    Args:
        boundaries: List of boundary dicts (must include 'imports_from' for edges)
        output_dir: .graphbus/ directory

    Returns:
        Path to graph.yaml
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build agent list
    agents = []
    for b in boundaries:
        agents.append({
            "name": b["name"],
            "description": b.get("description", ""),
        })

    # Build edges from imports_from
    edges = []
    agent_names = {b["name"] for b in boundaries}
    for b in boundaries:
        for dep in b.get("imports_from", []):
            # Find the agent that owns this module
            dep_agent = _find_agent_for_module(dep, boundaries)
            if dep_agent and dep_agent != b["name"] and dep_agent in agent_names:
                edge = {"from": b["name"], "to": dep_agent, "type": "depends_on"}
                if edge not in edges:
                    edges.append(edge)

    graph = {
        "agents": agents,
        "edges": edges,
    }

    graph_path = output_dir / "graph.yaml"
    graph_path.write_text(yaml.dump(graph, default_flow_style=False, sort_keys=False))
    return graph_path


def _find_agent_for_module(module_name: str, boundaries: List[Dict[str, Any]]) -> str:
    """Find which agent owns a given module prefix."""
    for b in boundaries:
        if b.get("module_prefix") and module_name.startswith(b["module_prefix"]):
            return b["name"]
        # Also check directory name match
        dir_name = module_name.split(".")[-1] if "." in module_name else module_name
        if dir_name.lower() in b["name"].lower():
            return b["name"]
    return ""
