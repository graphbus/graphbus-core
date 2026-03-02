# Code-Graph RAG Integration

This module provides **code-graph-aware quorum resolution** for the GraphBus
negotiation engine.

## Overview

During Build Mode negotiations, multiple agents propose and evaluate code
changes. By default every agent evaluates every proposal. The RAG integration
narrows the evaluation quorum to only those agents whose code is *affected* by
a proposed change, making consensus faster and more relevant.

## Components

### `CodeGraph` (`code_graph.py`)

A directed graph (extending `GraphBusGraph`) that models the structure of a
project's source code:

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

Build a graph from a project directory:

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
