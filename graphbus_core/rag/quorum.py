"""
Quorum resolver — determines which agents should participate in evaluating
a proposal based on code-graph proximity to the changed files.
"""

from __future__ import annotations

from graphbus_core.model.graph import AgentGraph
from graphbus_core.rag.code_graph import CodeGraph
from graphbus_core.model.message import Proposal


class QuorumResolver:
    """
    Resolves the quorum of agents that should evaluate a given proposal.

    Uses the CodeGraph to find symbols affected by the proposed change, then
    checks which agents in the AgentGraph overlap with those affected files
    (either by owning the source file or having a dependency edge).
    """

    def __init__(self, agent_graph: AgentGraph, code_graph: CodeGraph):
        self.agent_graph = agent_graph
        self.code_graph = code_graph

    def resolve(self, proposal: Proposal) -> set[str]:
        """
        Determine which agents should evaluate *proposal*.

        Steps:
            1. Extract the changed file from the proposal's code_change.
            2. Query the code graph for affected symbols within 2 hops.
            3. Collect agents whose source_file overlaps with affected files.
            4. Also include agents with dependency edges on the changed files.
            5. Fall back to all agents if the resolved set is empty.

        Args:
            proposal: The proposal to resolve quorum for.

        Returns:
            Set of agent names that form the quorum.
        """
        # 1. Extract changed files
        changed_files: list[str] = []
        if proposal.code_change and proposal.code_change.file_path:
            changed_files.append(proposal.code_change.file_path)

        if not changed_files:
            return self._all_agents()

        # 2. Get affected symbols / files from code graph
        affected = self.code_graph.get_affected_symbols(changed_files)
        # Keep only file-level nodes for matching against agent source_file
        affected_files = set()
        for node in affected:
            data = {}
            try:
                data = self.code_graph.get_node_data(node)
            except KeyError:
                pass
            if data.get("node_type") == "file":
                affected_files.add(node)

        # 3. Match agents whose source_file overlaps with affected files
        quorum: set[str] = set()
        for agent_name in self.agent_graph.graph.nodes():
            agent_data = self.agent_graph.get_node_data(agent_name)
            # Skip non-agent nodes (e.g. topic nodes)
            if agent_data.get("node_type") == "topic":
                continue

            source_file = agent_data.get("source_file", "")
            if source_file in affected_files:
                quorum.add(agent_name)

        # 4. Include agents connected via dependency edges to changed files
        for changed in changed_files:
            for agent_name in self.agent_graph.graph.nodes():
                agent_data = self.agent_graph.get_node_data(agent_name)
                if agent_data.get("node_type") == "topic":
                    continue
                source_file = agent_data.get("source_file", "")
                if source_file == changed:
                    quorum.add(agent_name)
                # Check if agent has a dependency edge involving the changed file
                for neighbor in self.agent_graph.get_neighbors(agent_name):
                    nbr_data = self.agent_graph.get_node_data(neighbor)
                    if nbr_data.get("source_file", "") in affected_files:
                        quorum.add(agent_name)

        # 5. Fallback: return all agents if none matched
        if not quorum:
            return self._all_agents()

        return quorum

    def _all_agents(self) -> set[str]:
        """Return names of all agent nodes (excluding topic nodes)."""
        agents: set[str] = set()
        for node in self.agent_graph.graph.nodes():
            data = self.agent_graph.get_node_data(node)
            if data.get("node_type") != "topic":
                agents.add(node)
        return agents
