"""
Tests for CodeGraph and QuorumResolver.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from graphbus_core.rag.code_graph import CodeGraph
from graphbus_core.rag.quorum import QuorumResolver
from graphbus_core.model.graph import AgentGraph
from graphbus_core.model.message import Proposal, CodeChange


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


def _make_proposal(file_path: str = "graphbus_core/model/graph.py") -> Proposal:
    """Create a minimal Proposal for testing."""
    return Proposal(
        proposal_id="prop-test-1",
        round=0,
        src="agent_a",
        dst=None,
        intent="test change",
        code_change=CodeChange(
            file_path=file_path,
            target="GraphBusGraph",
            change_type="modify",
            old_code="pass",
            new_code="return True",
        ),
    )


# ---------------------------------------------------------------------------
# CodeGraph.build_from_project
# ---------------------------------------------------------------------------

class TestCodeGraphBuildFromProject:
    """Test building a CodeGraph from the graphbus_core project itself."""

    @pytest.fixture(scope="class")
    def code_graph(self):
        return CodeGraph.build_from_project(PROJECT_ROOT)

    def test_graph_has_nodes(self, code_graph: CodeGraph):
        assert len(code_graph) > 0

    def test_file_nodes_exist(self, code_graph: CodeGraph):
        """graph.py should appear as a file node."""
        file_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "file"
        ]
        assert len(file_nodes) > 0
        # At least the model/graph.py should be present
        assert any("model/graph.py" in n for n in file_nodes)

    def test_function_and_class_nodes_exist(self, code_graph: CodeGraph):
        class_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "class"
        ]
        func_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "function"
        ]
        assert len(class_nodes) > 0, "Expected at least one class node"
        assert len(func_nodes) > 0, "Expected at least one function node"

    def test_contains_edges(self, code_graph: CodeGraph):
        contains_edges = [
            (u, v) for u, v, d in code_graph.graph.edges(data=True)
            if d.get("edge_type") == "contains"
        ]
        assert len(contains_edges) > 0

    def test_imports_edges(self, code_graph: CodeGraph):
        imports_edges = [
            (u, v) for u, v, d in code_graph.graph.edges(data=True)
            if d.get("edge_type") == "imports"
        ]
        assert len(imports_edges) > 0

    def test_to_summary(self, code_graph: CodeGraph):
        summary = code_graph.to_summary()
        assert summary["total_nodes"] > 0
        assert summary["files"] > 0
        assert summary["classes"] > 0
        assert summary["functions"] > 0
        assert summary["contains_edges"] > 0


# ---------------------------------------------------------------------------
# CodeGraph.get_affected_symbols
# ---------------------------------------------------------------------------

class TestGetAffectedSymbols:
    """Test BFS traversal for affected symbols."""

    @pytest.fixture(scope="class")
    def code_graph(self):
        return CodeGraph.build_from_project(PROJECT_ROOT)

    def test_returns_set(self, code_graph: CodeGraph):
        # Pick any file node that exists
        file_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "file"
        ]
        assert file_nodes, "Need at least one file node"
        result = code_graph.get_affected_symbols([file_nodes[0]])
        assert isinstance(result, set)

    def test_includes_starting_node(self, code_graph: CodeGraph):
        file_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "file"
        ]
        result = code_graph.get_affected_symbols([file_nodes[0]])
        assert file_nodes[0] in result

    def test_hops_limit(self, code_graph: CodeGraph):
        file_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "file"
        ]
        # With 0 hops, should only return the seed nodes themselves
        result_0 = code_graph.get_affected_symbols([file_nodes[0]], hops=0)
        assert result_0 == {file_nodes[0]}

        # More hops should give equal or larger result
        result_1 = code_graph.get_affected_symbols([file_nodes[0]], hops=1)
        assert len(result_1) >= len(result_0)

    def test_nonexistent_file_ignored(self, code_graph: CodeGraph):
        result = code_graph.get_affected_symbols(["nonexistent/file.py"])
        assert result == set()

    def test_multiple_changed_files(self, code_graph: CodeGraph):
        file_nodes = [
            n for n, d in code_graph.graph.nodes(data=True)
            if d.get("node_type") == "file"
        ]
        if len(file_nodes) >= 2:
            result = code_graph.get_affected_symbols(file_nodes[:2])
            assert file_nodes[0] in result
            assert file_nodes[1] in result


# ---------------------------------------------------------------------------
# QuorumResolver
# ---------------------------------------------------------------------------

class TestQuorumResolver:
    """Test quorum resolution logic."""

    def _make_agent_graph(self, agents: list[dict]) -> AgentGraph:
        """Build a minimal AgentGraph from a list of agent dicts."""
        ag = AgentGraph()
        for a in agents:
            ag.add_node(a["name"], source_file=a["source_file"])
        return ag

    def test_resolve_returns_matching_agents(self):
        """Agents whose source_file is in the affected set should be included."""
        cg = CodeGraph()
        cg.add_node("graphbus_core/model/graph.py", node_type="file")
        cg.add_node("graphbus_core/model/message.py", node_type="file")
        cg.add_edge("graphbus_core/model/graph.py", "graphbus_core/model/message.py", edge_type="imports")

        ag = self._make_agent_graph([
            {"name": "graph_agent", "source_file": "graphbus_core/model/graph.py"},
            {"name": "message_agent", "source_file": "graphbus_core/model/message.py"},
            {"name": "unrelated_agent", "source_file": "graphbus_core/other.py"},
        ])

        resolver = QuorumResolver(ag, cg)
        proposal = _make_proposal("graphbus_core/model/graph.py")

        quorum = resolver.resolve(proposal)
        assert "graph_agent" in quorum
        # message.py is within 2 hops (imports edge)
        assert "message_agent" in quorum
        # unrelated_agent should not be in the quorum
        assert "unrelated_agent" not in quorum

    def test_fallback_to_all_agents(self):
        """If no agent matches, all agents are returned."""
        cg = CodeGraph()
        cg.add_node("some/random/file.py", node_type="file")

        ag = self._make_agent_graph([
            {"name": "agent_a", "source_file": "graphbus_core/a.py"},
            {"name": "agent_b", "source_file": "graphbus_core/b.py"},
        ])

        resolver = QuorumResolver(ag, cg)
        # Proposal referencing a file not in the code graph
        proposal = _make_proposal("unknown/file.py")

        quorum = resolver.resolve(proposal)
        assert quorum == {"agent_a", "agent_b"}

    def test_empty_code_change(self):
        """Proposal with empty file_path should fall back to all agents."""
        cg = CodeGraph()
        ag = self._make_agent_graph([
            {"name": "agent_x", "source_file": "x.py"},
        ])

        resolver = QuorumResolver(ag, cg)
        proposal = _make_proposal("")

        quorum = resolver.resolve(proposal)
        assert "agent_x" in quorum

    def test_dependency_edges_included(self):
        """Agents connected via dependency edges should be included."""
        cg = CodeGraph()
        cg.add_node("graphbus_core/model/graph.py", node_type="file")
        cg.add_node("graphbus_core/build/orchestrator.py", node_type="file")
        cg.add_edge(
            "graphbus_core/build/orchestrator.py",
            "graphbus_core/model/graph.py",
            edge_type="imports",
        )

        ag = AgentGraph()
        ag.add_node("graph_agent", source_file="graphbus_core/model/graph.py")
        ag.add_node("orch_agent", source_file="graphbus_core/build/orchestrator.py")
        ag.add_dependency("orch_agent", "graph_agent", reason="uses graph")

        resolver = QuorumResolver(ag, cg)
        proposal = _make_proposal("graphbus_core/model/graph.py")

        quorum = resolver.resolve(proposal)
        assert "graph_agent" in quorum
        assert "orch_agent" in quorum
