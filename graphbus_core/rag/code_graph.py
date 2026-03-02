"""
Code graph — builds a dependency graph of files, functions, and classes
from a project's source code using the static analyzer.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Optional

from graphbus_core.model.graph import GraphBusGraph
from graphbus_core.ingest.analyzer import scan_source_files, extract_symbols, extract_imports


class CodeGraph(GraphBusGraph):
    """
    A graph representing code structure and dependencies.

    Node types: file, function, class
    Edge types: calls, imports, contains
    """

    @classmethod
    def build_from_project(cls, project_path: str) -> CodeGraph:
        """
        Build a CodeGraph by scanning and analyzing a project directory.

        Uses the static analyzer to discover files, extract symbols, and
        map import relationships.

        Args:
            project_path: Root directory of the project to analyze.

        Returns:
            Populated CodeGraph instance.
        """
        graph = cls()
        project = Path(project_path)
        files = scan_source_files(project)

        # Map from module-style import names to file node names
        module_to_file: dict[str, str] = {}

        for file_path in files:
            rel = str(file_path.relative_to(project))
            graph.add_node(rel, node_type="file")

            # Build module name for import resolution (Python only)
            if file_path.suffix == ".py":
                module_name = str(file_path.relative_to(project)).replace("/", ".").removesuffix(".py")
                module_to_file[module_name] = rel

            # Extract symbols (functions, classes) and add as nodes
            symbols = extract_symbols(file_path)
            for sym in symbols:
                sym_name = f"{rel}::{sym['name']}"
                graph.add_node(sym_name, node_type=sym["type"], file=rel)
                graph.add_edge(rel, sym_name, edge_type="contains")

                # Methods inside classes
                if sym["type"] == "class":
                    for method in sym.get("methods", []):
                        method_name = f"{rel}::{sym['name']}.{method['name']}"
                        graph.add_node(method_name, node_type="function", file=rel)
                        graph.add_edge(sym_name, method_name, edge_type="contains")

        # Second pass: resolve imports to "imports" edges between files
        for file_path in files:
            rel = str(file_path.relative_to(project))
            imports = extract_imports(file_path)

            for imp in imports:
                # Try to match import to a known file in the project
                target_file = module_to_file.get(imp)
                if target_file is None:
                    # Try prefix matching (e.g. "graphbus_core.model.graph" -> look for parent)
                    parts = imp.split(".")
                    for i in range(len(parts), 0, -1):
                        candidate = ".".join(parts[:i])
                        if candidate in module_to_file:
                            target_file = module_to_file[candidate]
                            break

                if target_file and target_file != rel:
                    if not graph.graph.has_edge(rel, target_file):
                        graph.add_edge(rel, target_file, edge_type="imports")

        return graph

    def get_affected_symbols(self, changed_files: list[str], hops: int = 2) -> set[str]:
        """
        BFS from changed file nodes, returning all reachable nodes within *hops* edges.

        Traverses both successors and predecessors so that dependents of a
        changed file are also included.

        Args:
            changed_files: List of relative file paths that changed.
            hops: Maximum traversal depth.

        Returns:
            Set of node names reachable within the hop limit.
        """
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()

        for f in changed_files:
            if f in self.graph:
                queue.append((f, 0))
                visited.add(f)

        while queue:
            node, depth = queue.popleft()
            if depth >= hops:
                continue

            # Traverse both directions
            neighbors = set(self.graph.successors(node)) | set(self.graph.predecessors(node))
            for nbr in neighbors:
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append((nbr, depth + 1))

        return visited

    def to_summary(self) -> dict:
        """
        Return summary statistics about the code graph.
        """
        nodes = list(self.graph.nodes(data=True))
        file_count = sum(1 for _, d in nodes if d.get("node_type") == "file")
        func_count = sum(1 for _, d in nodes if d.get("node_type") == "function")
        class_count = sum(1 for _, d in nodes if d.get("node_type") == "class")

        edges = list(self.graph.edges(data=True))
        imports_count = sum(1 for _, _, d in edges if d.get("edge_type") == "imports")
        contains_count = sum(1 for _, _, d in edges if d.get("edge_type") == "contains")
        calls_count = sum(1 for _, _, d in edges if d.get("edge_type") == "calls")

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "files": file_count,
            "functions": func_count,
            "classes": class_count,
            "imports_edges": imports_count,
            "contains_edges": contains_count,
            "calls_edges": calls_count,
        }
