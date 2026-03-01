"""
Full ingest pipeline — orchestrates analysis, boundary detection, and generation.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from graphbus_core.ingest.analyzer import scan_source_files, extract_symbols, extract_imports
from graphbus_core.ingest.boundary import detect_boundaries
from graphbus_core.ingest.deps import infer_dependencies
from graphbus_core.ingest.generator import generate_agent_yaml, generate_graph_yaml
from graphbus_core.ingest.memory import init_project_memory


def run_ingest(
    project_path: Path,
    home_dir: Optional[Path] = None,
    strategy: str = "directory",
) -> Dict[str, Any]:
    """
    Run the full ingest pipeline on a project.

    1. Scan source files
    2. Extract symbols from each file
    3. Detect agent boundaries
    4. Infer dependencies
    5. Generate .graphbus/ YAML files
    6. Initialize project memory in ~/.graphbus/

    Args:
        project_path: Root of the project to ingest
        home_dir: Path to ~/.graphbus/ (default: ~/.graphbus)
        strategy: Boundary detection strategy

    Returns:
        Summary dict with agents, edges, files_analyzed
    """
    project_path = Path(project_path).resolve()
    if home_dir is None:
        home_dir = Path.home() / ".graphbus"
    home_dir = Path(home_dir)

    # 1. Scan
    files = scan_source_files(project_path)

    # 2. Extract symbols
    file_data = []
    for f in files:
        symbols = extract_symbols(f)
        file_data.append({"path": f, "symbols": symbols})

    # 3. Detect boundaries
    boundaries = detect_boundaries(file_data, strategy=strategy)

    # 4. Infer dependencies and enrich boundaries
    # Build module prefixes from directory structure
    for b in boundaries:
        # Infer module prefix from file paths
        if b["files"]:
            first_file = Path(b["files"][0])
            try:
                rel = first_file.relative_to(project_path)
                parts = list(rel.parent.parts)
                b["module_prefix"] = ".".join(parts)
            except ValueError:
                b["module_prefix"] = ""

    dep_edges = infer_dependencies(boundaries, project_path)

    # Enrich boundaries with import info for graph generation
    for b in boundaries:
        b["imports_from"] = []
        for from_agent, to_agent in dep_edges:
            if from_agent == b["name"]:
                # Find the module prefix of the target
                for other in boundaries:
                    if other["name"] == to_agent:
                        b["imports_from"].append(other.get("module_prefix", ""))

    # 5. Generate .graphbus/
    graphbus_dir = project_path / ".graphbus"

    for boundary in boundaries:
        generate_agent_yaml(boundary, graphbus_dir, project_path)

    generate_graph_yaml(boundaries, graphbus_dir)

    # 6. Initialize project memory
    init_project_memory(project_path, home_dir)

    return {
        "agents": [b["name"] for b in boundaries],
        "edges": dep_edges,
        "files_analyzed": len(files),
        "graphbus_dir": str(graphbus_dir),
    }
