"""
Graph primitives using networkx
"""

import networkx as nx
from typing import Any
import json


class GraphBusGraph:
    """
    Base wrapper around networkx.DiGraph for GraphBus.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, name: str, **attributes) -> None:
        """Add a node with metadata."""
        self.graph.add_node(name, **attributes)

    def add_edge(self, src: str, dst: str, edge_type: str = "depends_on", **attributes) -> None:
        """Add an edge between nodes."""
        self.graph.add_edge(src, dst, edge_type=edge_type, **attributes)

    def get_node_data(self, name: str) -> dict:
        """Get all attributes for a node."""
        return dict(self.graph.nodes[name])

    def get_edge_data(self, src: str, dst: str) -> dict:
        """Get all attributes for an edge."""
        return dict(self.graph.edges[src, dst])

    def get_neighbors(self, name: str) -> list[str]:
        """Get all nodes that this node depends on (successors)."""
        return list(self.graph.successors(name))

    def get_dependents(self, name: str) -> list[str]:
        """Get all nodes that depend on this node (predecessors)."""
        return list(self.graph.predecessors(name))

    def topological_sort(self) -> list[str]:
        """
        Return nodes in topological order.
        Critical for Build Mode: determines agent activation order.
        """
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError as e:
            raise ValueError(f"Graph contains cycles, cannot perform topological sort: {e}")

    def has_cycle(self) -> bool:
        """Check if graph contains cycles."""
        try:
            nx.find_cycle(self.graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def to_dict(self) -> dict:
        """Serialize graph to dict for JSON artifacts."""
        return {
            "nodes": [
                {"name": node, "data": self.get_node_data(node)}
                for node in self.graph.nodes()
            ],
            "edges": [
                {"src": src, "dst": dst, "data": self.get_edge_data(src, dst)}
                for src, dst in self.graph.edges()
            ]
        }

    def to_json(self, filepath: str) -> None:
        """Save graph to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "GraphBusGraph":
        """Deserialize graph from dict."""
        graph = cls()
        for node in data.get("nodes", []):
            graph.add_node(node["name"], **node["data"])
        for edge in data.get("edges", []):
            graph.add_edge(edge["src"], edge["dst"], **edge["data"])
        return graph

    @classmethod
    def from_json(cls, filepath: str) -> "GraphBusGraph":
        """Load graph from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def __len__(self) -> int:
        """Number of nodes in the graph."""
        return len(self.graph.nodes())

    def __contains__(self, name: str) -> bool:
        """Check if a node exists in the graph."""
        return name in self.graph.nodes()


class AgentGraph(GraphBusGraph):
    """
    Specialized graph for Build Mode agent orchestration.

    Nodes represent agents (with their source code and prompts).
    Edges represent dependencies (who needs who).
    """

    def add_agent(self, agent_def: Any) -> None:
        """
        Add an agent to the graph.

        Args:
            agent_def: AgentDefinition object
        """
        self.add_node(
            agent_def.name,
            module=agent_def.module,
            class_name=agent_def.class_name,
            source_file=agent_def.source_file,
            system_prompt=agent_def.system_prompt.text,
            methods=[m.name for m in agent_def.methods],
            subscriptions=[s.topic.name for s in agent_def.subscriptions],
            metadata=agent_def.metadata
        )

    def add_dependency(self, consumer: str, provider: str, reason: str = "") -> None:
        """
        Add a dependency edge: consumer depends on provider.

        Args:
            consumer: Name of node that depends on another
            provider: Name of node that is depended upon
            reason: Why this dependency exists
        """
        self.add_edge(consumer, provider, edge_type="depends_on", reason=reason)

    def add_schema_dependency(self, consumer: str, provider: str, schema_info: dict) -> None:
        """
        Add a schema dependency edge.

        Args:
            consumer: Node that consumes data
            provider: Node that provides data
            schema_info: Details about the schema relationship
        """
        self.add_edge(consumer, provider, edge_type="schema_depends", schema_info=schema_info)

    def add_topic_edge(self, publisher: str, topic: str, subscriber: str) -> None:
        """
        Add edges for pub/sub relationships.
        Creates: publisher -> topic -> subscriber

        Args:
            publisher: Node that publishes to topic
            topic: Topic name
            subscriber: Node that subscribes to topic
        """
        # Add topic as a special node if it doesn't exist
        if topic not in self.graph:
            self.add_node(topic, node_type="topic")

        # Publisher -> Topic
        if not self.graph.has_edge(publisher, topic):
            self.add_edge(publisher, topic, edge_type="publishes")

        # Topic -> Subscriber
        if not self.graph.has_edge(topic, subscriber):
            self.add_edge(topic, subscriber, edge_type="subscribes")

    def get_agent_activation_order(self) -> list[str]:
        """
        Get the order in which agents should be activated in Build Mode.
        This is the topological sort excluding topic nodes.
        """
        all_nodes = self.topological_sort()
        # Filter out topic nodes
        agent_nodes = [
            node for node in all_nodes
            if self.get_node_data(node).get("node_type") != "topic"
        ]
        return agent_nodes
