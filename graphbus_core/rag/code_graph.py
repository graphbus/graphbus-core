"""
Code graph — builds a dependency graph of files, functions, and classes
from a project's source code.

Supports two backends:
- CgrBackend: uses the ``code-graph-rag`` library (Tree-sitter + Memgraph/JSON)
- LocalBackend: custom AST-based analysis via graphbus_core.ingest.analyzer
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import warnings
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from typing import Optional

from graphbus_core.model.graph import GraphBusGraph

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------

class CodeGraphBackend(ABC):
    """Abstract backend for code graph storage/query."""

    @abstractmethod
    def build(self, project_path: str) -> None:
        """Build/index the code graph for the given project."""
        ...

    @abstractmethod
    def get_affected_symbols(self, changed_files: list[str], hops: int = 2) -> set[str]:
        """Return node names reachable from *changed_files* within *hops* edges."""
        ...

    @abstractmethod
    def to_summary(self) -> dict:
        """Return summary statistics about the code graph."""
        ...

    # Needed so QuorumResolver can call get_node_data / iterate graph.nodes
    @abstractmethod
    def as_graphbus_graph(self) -> GraphBusGraph:
        """Return the underlying GraphBusGraph (for QuorumResolver compat)."""
        ...


# ---------------------------------------------------------------------------
# Protobuf payload → label / primary-key mappings
# ---------------------------------------------------------------------------

_PAYLOAD_LABEL_MAP: dict[str, str] = {
    "project": "Project",
    "package": "Package",
    "folder": "Folder",
    "module": "Module",
    "class_node": "Class",
    "function": "Function",
    "method": "Method",
    "file": "File",
    "external_package": "ExternalPackage",
    "module_implementation": "ModuleImplementation",
    "module_interface": "ModuleInterface",
}

_PRIMARY_KEY_FIELD: dict[str, str] = {
    "project": "name",
    "package": "qualified_name",
    "folder": "path",
    "module": "qualified_name",
    "class_node": "qualified_name",
    "function": "qualified_name",
    "method": "qualified_name",
    "file": "path",
    "external_package": "name",
    "module_implementation": "qualified_name",
    "module_interface": "qualified_name",
}


# ---------------------------------------------------------------------------
# CgrBackend — code-graph-rag library
# ---------------------------------------------------------------------------

class CgrBackend(CodeGraphBackend):
    """
    Backend using the ``code-graph-rag`` library.

    Two modes:

    - **offline** (default): runs ``cgr index`` CLI to produce ``graph.json``,
      then loads via ``cgr.load_graph()``.
    - **live**: connects to Memgraph via ``MemgraphIngestor`` (requires Docker).

    For ``get_affected_symbols()``:

    - Start from changed file nodes (match by ``.properties["path"]`` or
      ``.properties["name"]``).
    - BFS using ``graph.get_relationships_for_node(node_id)`` up to *hops* edges.
    - Return set of file paths / symbol names from reachable nodes.
    """

    def __init__(self, index_dir: str = ".cgr-index", mode: str = "offline"):
        try:
            import cgr  # noqa: F401
        except ImportError:
            raise ImportError(
                "code-graph-rag is not installed. "
                "Install with: pip install 'code-graph-rag[treesitter-full]'"
            )
        self._index_dir = index_dir
        self._mode = mode
        self._cgr_graph = None  # populated by build()
        # Internal GraphBusGraph mirror for QuorumResolver compat
        self._gbg = GraphBusGraph()

    def build(self, project_path: str) -> None:
        """Run ``cgr index``, decode protobuf to JSON, then load the graph."""
        import cgr as cgr_mod

        index_path = Path(self._index_dir)
        index_path.mkdir(parents=True, exist_ok=True)

        if self._mode == "offline":
            cgr_bin = Path(sys.executable).parent / "cgr"
            try:
                subprocess.run(
                    [
                        str(cgr_bin), "index",
                        "-o", str(index_path),
                        "--repo-path", str(project_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                raise RuntimeError(
                    f"cgr index failed: {exc}. "
                    "Ensure code-graph-rag CLI is installed and cmake is available."
                ) from exc

            # cgr index produces index.bin; decode to graph.json
            index_bin = index_path / "index.bin"
            graph_json = index_path / "graph.json"

            if index_bin.exists() and not graph_json.exists():
                self._decode_protobuf_to_json(str(index_bin), str(graph_json))

            if not graph_json.exists():
                raise FileNotFoundError(
                    f"Expected {graph_json} after cgr index, but it was not created. "
                    f"Neither index.bin nor graph.json found in {index_path}."
                )
            self._cgr_graph = cgr_mod.load_graph(str(graph_json))

        elif self._mode == "live":
            ingestor = cgr_mod.MemgraphIngestor()
            ingestor.ingest(project_path)
            raise NotImplementedError(
                "Live Memgraph mode is not yet supported in this wrapper. "
                "Use mode='offline'."
            )
        else:
            raise ValueError(f"Unknown mode: {self._mode!r}. Use 'offline' or 'live'.")

        # Mirror into a GraphBusGraph so QuorumResolver can use .graph
        self._mirror_to_graphbus_graph()

    # -- internal helpers ----------------------------------------------------

    def _mirror_to_graphbus_graph(self) -> None:
        """Populate ``self._gbg`` from the cgr graph object."""
        g = self._cgr_graph
        if g is None:
            return

        _id_to_name: dict[int, str] = {}  # cgr node_id → gbg node name

        # Add nodes
        for label in ("File", "Function", "Class", "Method", "Module"):
            try:
                nodes = g.find_nodes_by_label(label)
            except Exception:
                continue
            for node in nodes:
                props = node.properties if hasattr(node, "properties") else {}
                name = (
                    props.get("path")
                    or props.get("qualified_name")
                    or props.get("name")
                    or str(node.node_id)
                )
                node_type = label.lower()
                self._gbg.add_node(
                    name, node_type=node_type, cgr_id=node.node_id, **props,
                )
                _id_to_name[node.node_id] = name

        # Mirror relationships
        for src_name, src_data in self._gbg.graph.nodes(data=True):
            cgr_id = src_data.get("cgr_id")
            if cgr_id is None:
                continue
            try:
                rels = g.get_relationships_for_node(cgr_id)
            except Exception:
                continue
            for rel in rels:
                if rel.from_id != cgr_id:
                    continue  # only outgoing
                tgt_name = _id_to_name.get(rel.to_id)
                if tgt_name and not self._gbg.graph.has_edge(src_name, tgt_name):
                    self._gbg.add_edge(
                        src_name, tgt_name, edge_type=rel.type.lower(),
                    )

    # -- protobuf codec helpers ----------------------------------------------

    @staticmethod
    def _import_codec():
        """Import ``codec.schema_pb2``, trying multiple resolution strategies."""
        # 1. Direct import (codec already on sys.path or installed)
        try:
            from codec import schema_pb2
            return schema_pb2
        except ImportError:
            pass

        # 2. Locate codec relative to the cgr package installation
        try:
            import cgr as _cgr
            codec_parent = str(Path(_cgr.__file__).resolve().parent.parent)
            if codec_parent not in sys.path:
                sys.path.append(codec_parent)
            from codec import schema_pb2
            return schema_pb2
        except (ImportError, AttributeError):
            pass

        raise ImportError(
            "Could not import codec.schema_pb2. "
            "Ensure the code-graph-rag codec package is available."
        )

    @staticmethod
    def _decode_protobuf_to_json(index_bin_path: str, output_json_path: str) -> None:
        """
        Decode cgr protobuf binary (index.bin) to JSON compatible with
        ``cgr.load_graph()``.

        Uses ``codec.schema_pb2.GraphCodeIndex`` to parse the binary.

        Output JSON format::

            {"nodes": [...], "relationships": [...], "metadata": {...}}

        Node format:  ``{"node_id": int, "labels": [str], "properties": dict}``
        Rel format:   ``{"from_id": int, "to_id": int, "type": str, "properties": dict}``
        """
        schema_pb2 = CgrBackend._import_codec()
        from google.protobuf import json_format as _pb_json_fmt

        with open(index_bin_path, "rb") as fh:
            data = fh.read()

        idx = schema_pb2.GraphCodeIndex()
        idx.ParseFromString(data)

        # -- nodes -----------------------------------------------------------
        nodes_json: list[dict] = []
        node_id_map: dict[str, int] = {}  # primary-key string → integer id

        for i, node in enumerate(idx.nodes):
            payload_name = node.WhichOneof("payload")
            if payload_name is None:
                continue
            payload = getattr(node, payload_name)
            label = _PAYLOAD_LABEL_MAP.get(payload_name, payload_name.title())

            # Extract properties from payload fields
            props: dict = {}
            for fd in payload.DESCRIPTOR.fields:
                val = getattr(payload, fd.name)
                if fd.label == fd.LABEL_REPEATED:
                    val = list(val)
                if val:  # skip proto3 defaults (0, False, "", [])
                    props[fd.name] = val

            nodes_json.append({
                "node_id": i,
                "labels": [label],
                "properties": props,
            })

            # Build node_id_map using primary key
            pk_field = _PRIMARY_KEY_FIELD.get(payload_name)
            if pk_field:
                pk_value = getattr(payload, pk_field, "")
                if pk_value:
                    node_id_map[pk_value] = i

        # -- relationships ---------------------------------------------------
        rel_type_desc = schema_pb2.Relationship.RelationshipType.DESCRIPTOR
        rels_json: list[dict] = []

        for rel in idx.relationships:
            type_name = rel_type_desc.values_by_number[rel.type].name
            from_id = node_id_map.get(rel.source_id)
            to_id = node_id_map.get(rel.target_id)
            if from_id is None or to_id is None:
                continue

            rel_props: dict = {}
            if rel.HasField("properties"):
                rel_props = _pb_json_fmt.MessageToDict(rel.properties)

            rels_json.append({
                "from_id": from_id,
                "to_id": to_id,
                "type": type_name,
                "properties": rel_props,
            })

        output = {
            "nodes": nodes_json,
            "relationships": rels_json,
            "metadata": {
                "total_nodes": len(nodes_json),
                "total_relationships": len(rels_json),
            },
        }

        with open(output_json_path, "w") as fh:
            json.dump(output, fh)

    # -- public interface ----------------------------------------------------

    def get_affected_symbols(self, changed_files: list[str], hops: int = 2) -> set[str]:
        """BFS from changed file nodes within the mirrored graph."""
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()

        for f in changed_files:
            if f in self._gbg.graph:
                queue.append((f, 0))
                visited.add(f)

        while queue:
            node, depth = queue.popleft()
            if depth >= hops:
                continue
            neighbors = (
                set(self._gbg.graph.successors(node))
                | set(self._gbg.graph.predecessors(node))
            )
            for nbr in neighbors:
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append((nbr, depth + 1))

        return visited

    def to_summary(self) -> dict:
        if self._cgr_graph is not None:
            try:
                return self._cgr_graph.summary()
            except Exception:
                pass
        # Fall back to counting from mirrored graph
        nodes = list(self._gbg.graph.nodes(data=True))
        edges = list(self._gbg.graph.edges(data=True))
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "files": sum(1 for _, d in nodes if d.get("node_type") == "file"),
            "functions": sum(1 for _, d in nodes if d.get("node_type") == "function"),
            "classes": sum(1 for _, d in nodes if d.get("node_type") == "class"),
        }

    def as_graphbus_graph(self) -> GraphBusGraph:
        return self._gbg


# ---------------------------------------------------------------------------
# LocalBackend — custom AST-based implementation (fallback)
# ---------------------------------------------------------------------------

class LocalBackend(CodeGraphBackend):
    """
    Fallback backend using the custom AST-based implementation.

    Uses ``graphbus_core.ingest.analyzer`` to scan files, extract symbols,
    and resolve import edges.  Works without any external dependencies beyond
    the Python standard library.
    """

    def __init__(self):
        self._gbg = GraphBusGraph()

    def build(self, project_path: str) -> None:
        from graphbus_core.ingest.analyzer import (
            scan_source_files,
            extract_symbols,
            extract_imports,
        )

        project = Path(project_path)
        files = scan_source_files(project)

        module_to_file: dict[str, str] = {}

        for file_path in files:
            rel = str(file_path.relative_to(project))
            self._gbg.add_node(rel, node_type="file")

            if file_path.suffix == ".py":
                module_name = (
                    str(file_path.relative_to(project))
                    .replace("/", ".")
                    .removesuffix(".py")
                )
                module_to_file[module_name] = rel

            symbols = extract_symbols(file_path)
            for sym in symbols:
                sym_name = f"{rel}::{sym['name']}"
                self._gbg.add_node(sym_name, node_type=sym["type"], file=rel)
                self._gbg.add_edge(rel, sym_name, edge_type="contains")

                if sym["type"] == "class":
                    for method in sym.get("methods", []):
                        method_name = f"{rel}::{sym['name']}.{method['name']}"
                        self._gbg.add_node(method_name, node_type="function", file=rel)
                        self._gbg.add_edge(sym_name, method_name, edge_type="contains")

        # Second pass: resolve imports
        for file_path in files:
            rel = str(file_path.relative_to(project))
            imports = extract_imports(file_path)

            for imp in imports:
                target_file = module_to_file.get(imp)
                if target_file is None:
                    parts = imp.split(".")
                    for i in range(len(parts), 0, -1):
                        candidate = ".".join(parts[:i])
                        if candidate in module_to_file:
                            target_file = module_to_file[candidate]
                            break

                if target_file and target_file != rel:
                    if not self._gbg.graph.has_edge(rel, target_file):
                        self._gbg.add_edge(rel, target_file, edge_type="imports")

    def get_affected_symbols(self, changed_files: list[str], hops: int = 2) -> set[str]:
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()

        for f in changed_files:
            if f in self._gbg.graph:
                queue.append((f, 0))
                visited.add(f)

        while queue:
            node, depth = queue.popleft()
            if depth >= hops:
                continue
            neighbors = (
                set(self._gbg.graph.successors(node))
                | set(self._gbg.graph.predecessors(node))
            )
            for nbr in neighbors:
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append((nbr, depth + 1))

        return visited

    def to_summary(self) -> dict:
        nodes = list(self._gbg.graph.nodes(data=True))
        edges = list(self._gbg.graph.edges(data=True))
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "files": sum(1 for _, d in nodes if d.get("node_type") == "file"),
            "functions": sum(1 for _, d in nodes if d.get("node_type") == "function"),
            "classes": sum(1 for _, d in nodes if d.get("node_type") == "class"),
            "imports_edges": sum(1 for _, _, d in edges if d.get("edge_type") == "imports"),
            "contains_edges": sum(1 for _, _, d in edges if d.get("edge_type") == "contains"),
            "calls_edges": sum(1 for _, _, d in edges if d.get("edge_type") == "calls"),
        }

    def as_graphbus_graph(self) -> GraphBusGraph:
        return self._gbg


# ---------------------------------------------------------------------------
# CodeGraph — public API
# ---------------------------------------------------------------------------

def _cgr_available() -> bool:
    """Return True if the ``cgr`` package is importable."""
    try:
        import cgr  # noqa: F401
        return True
    except ImportError:
        return False


class CodeGraph(GraphBusGraph):
    """
    Public API — wraps a :class:`CodeGraphBackend`, exposes a stable interface
    for :class:`~graphbus_core.rag.quorum.QuorumResolver`.

    Auto-selects backend:
    - If ``cgr`` is importable → :class:`CgrBackend`
    - Otherwise → :class:`LocalBackend` (with a warning)

    The class still extends :class:`GraphBusGraph` so that existing code
    (``QuorumResolver``) that accesses ``code_graph.graph``,
    ``code_graph.get_node_data()``, etc. continues to work.
    """

    def __init__(self, backend: Optional[CodeGraphBackend] = None):
        super().__init__()
        self._backend = backend

    @classmethod
    def build_from_project(
        cls,
        project_path: str,
        backend: Optional[CodeGraphBackend] = None,
    ) -> CodeGraph:
        """
        Build a CodeGraph by scanning and analyzing a project directory.

        Args:
            project_path: Root directory of the project to analyze.
            backend: Explicit backend to use.  When *None*, auto-selects
                     CgrBackend (if available) with fallback to LocalBackend.

        Returns:
            Populated CodeGraph instance.
        """
        if backend is not None:
            selected = backend
        elif _cgr_available():
            try:
                selected = CgrBackend()
            except Exception as exc:
                warnings.warn(
                    f"Failed to initialise CgrBackend ({exc}); "
                    "falling back to LocalBackend.",
                    stacklevel=2,
                )
                selected = LocalBackend()
        else:
            warnings.warn(
                "code-graph-rag (cgr) is not installed — using LocalBackend. "
                "Install with: pip install 'code-graph-rag[treesitter-full]'",
                stacklevel=2,
            )
            selected = LocalBackend()

        # Build the graph
        try:
            selected.build(project_path)
        except Exception as exc:
            if not isinstance(selected, LocalBackend):
                warnings.warn(
                    f"CgrBackend.build() failed ({exc}); "
                    "falling back to LocalBackend.",
                    stacklevel=2,
                )
                selected = LocalBackend()
                selected.build(project_path)
            else:
                raise

        instance = cls(backend=selected)
        # Mirror the backend's GraphBusGraph into our own .graph so that
        # QuorumResolver (which accesses code_graph.graph) keeps working.
        instance.graph = selected.as_graphbus_graph().graph
        return instance

    def get_affected_symbols(self, changed_files: list[str], hops: int = 2) -> set[str]:
        """
        BFS from changed file nodes, returning all reachable nodes within
        *hops* edges.

        Delegates to the underlying backend.
        """
        if self._backend is not None:
            return self._backend.get_affected_symbols(changed_files, hops=hops)

        # Direct graph fallback (for manually constructed CodeGraph instances
        # used in tests that don't go through build_from_project).
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
            neighbors = (
                set(self.graph.successors(node))
                | set(self.graph.predecessors(node))
            )
            for nbr in neighbors:
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append((nbr, depth + 1))

        return visited

    def to_summary(self) -> dict:
        """Return summary statistics about the code graph."""
        if self._backend is not None:
            return self._backend.to_summary()

        # Direct graph fallback
        nodes = list(self.graph.nodes(data=True))
        edges = list(self.graph.edges(data=True))
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "files": sum(1 for _, d in nodes if d.get("node_type") == "file"),
            "functions": sum(1 for _, d in nodes if d.get("node_type") == "function"),
            "classes": sum(1 for _, d in nodes if d.get("node_type") == "class"),
            "imports_edges": sum(1 for _, _, d in edges if d.get("edge_type") == "imports"),
            "contains_edges": sum(1 for _, _, d in edges if d.get("edge_type") == "contains"),
            "calls_edges": sum(1 for _, _, d in edges if d.get("edge_type") == "calls"),
        }
