# Code-Graph RAG Integration

This module provides **code-graph-aware quorum resolution** for the GraphBus
negotiation engine.

## Overview

During Build Mode negotiations, multiple agents propose and evaluate code
changes. By default every agent evaluates every proposal. The RAG integration
narrows the evaluation quorum to only those agents whose code is *affected* by
a proposed change, making consensus faster and more relevant.

## Architecture

`CodeGraph` uses a pluggable **backend** system:

| Backend | Library | Parser | Storage | Requires |
|---------|---------|--------|---------|----------|
| `CgrBackend` (primary) | [`code-graph-rag`](https://pypi.org/project/code-graph-rag/) | Tree-sitter | Memgraph / JSON export | `pip install 'code-graph-rag[treesitter-full]'`, cmake |
| `LocalBackend` (fallback) | built-in | Python AST + regex | networkx in-memory | nothing extra |

When `cgr` is installed, `CodeGraph.build_from_project()` automatically selects
`CgrBackend`. If the import fails or the `cgr index` subprocess errors, it
falls back to `LocalBackend` with a warning.

## Components

### `CodeGraphBackend` (ABC)

All backends implement:

```python
class CodeGraphBackend(ABC):
    def build(self, project_path: str) -> None: ...
    def get_affected_symbols(self, changed_files: list[str], hops: int = 2) -> set[str]: ...
    def to_summary(self) -> dict: ...
    def as_graphbus_graph(self) -> GraphBusGraph: ...
```

### `CgrBackend` (`code_graph.py`)

Uses the `code-graph-rag` library in one of two modes:

#### Offline mode (default)

1. Runs `cgr index -o .cgr-index --repo-path <project>` as a subprocess.
2. Loads the resulting `graph.json` via `cgr.load_graph()`.
3. Mirrors nodes and edges into a `GraphBusGraph` for QuorumResolver compat.

```python
from graphbus_core.rag.code_graph import CgrBackend, CodeGraph

# Explicit backend
backend = CgrBackend(index_dir=".cgr-index", mode="offline")
cg = CodeGraph.build_from_project("/path/to/project", backend=backend)
```

#### Live mode (requires Docker + Memgraph)

```python
backend = CgrBackend(mode="live")  # Not yet implemented
```

Live mode requires a running Memgraph instance via Docker. Queries go through
`MemgraphIngestor` and Cypher.

### `LocalBackend` (`code_graph.py`)

The original AST-based implementation. Scans Python/JS/TS files using
`graphbus_core.ingest.analyzer`, extracts symbols and import edges, and builds
a networkx `DiGraph`.

```python
from graphbus_core.rag.code_graph import LocalBackend, CodeGraph

cg = CodeGraph.build_from_project("/path/to/project", backend=LocalBackend())
```

### `CodeGraph` (`code_graph.py`)

Public API that wraps a backend and extends `GraphBusGraph`. Existing code
that accesses `code_graph.graph` or `code_graph.get_node_data()` continues to
work unchanged.

| Node type | Example |
|-----------|---------|
| `file`    | `graphbus_core/model/graph.py` |
| `function`| `graphbus_core/model/graph.py::topological_sort` |
| `class`   | `graphbus_core/model/graph.py::AgentGraph` |

| Edge type  | Meaning |
|------------|---------|
| `contains` | A file contains a function/class, or a class contains a method |
| `imports`  | One file imports from another |
| `calls`    | A function/method calls another (future) |

```python
from graphbus_core.rag import CodeGraph

cg = CodeGraph.build_from_project("/path/to/project")
print(cg.to_summary())
```

### `QuorumResolver` (`quorum.py`)

Given an `AgentGraph` (agents and their dependencies) and a `CodeGraph`, the
resolver determines which agents should evaluate a `Proposal`:

1. Extracts the changed file from the proposal.
2. Runs a BFS on the code graph (default 2 hops) to find affected symbols.
3. Matches affected files against agent `source_file` attributes.
4. Includes agents with dependency edges to affected files.
5. Falls back to all agents if no specific quorum is identified.

```python
from graphbus_core.rag import QuorumResolver

resolver = QuorumResolver(agent_graph, code_graph)
quorum = resolver.resolve(proposal)  # set of agent names
```

## Integration with AsyncNegotiationEngine

Pass `code_graph` and `quorum_resolver` to `AsyncNegotiationEngine.__init__()`.
During `create_commits()`, evaluations are automatically filtered to quorum
members before tallying votes.
