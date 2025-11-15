"""
Serialization models for graph artifacts
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class GraphNodeData:
    """Serialization model for graph node"""
    name: str
    type: str = "agent"
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdgeData:
    """Serialization model for graph edge"""
    from_node: str  # Renamed from 'from' to avoid keyword
    to_node: str    # Renamed from 'to' to avoid keyword
    type: str = "dependency"
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, edge_dict: Dict[str, Any]) -> "GraphEdgeData":
        """Create from dict with 'from'/'to' keys"""
        # Handle both 'from'/'to' and 'source'/'target' formats
        from_node = edge_dict.get("from", edge_dict.get("source", ""))
        to_node = edge_dict.get("to", edge_dict.get("target", ""))
        edge_type = edge_dict.get("type", "dependency")
        edge_data = edge_dict.get("data", {})

        return cls(
            from_node=from_node,
            to_node=to_node,
            type=edge_type,
            data=edge_data
        )


@dataclass
class GraphData:
    """Serialization model for complete graph"""
    nodes: List[GraphNodeData] = field(default_factory=list)
    edges: List[GraphEdgeData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, graph_dict: Dict[str, Any]) -> "GraphData":
        """Deserialize from dict"""
        raw_nodes = graph_dict.get("nodes", [])
        raw_edges = graph_dict.get("edges", [])

        nodes = []
        for node in raw_nodes:
            # Handle both 'name' and 'id' fields
            node_name = node.get("name", node.get("id", ""))
            node_type = node.get("type", "agent")
            node_data = node.get("data", {})

            nodes.append(GraphNodeData(
                name=node_name,
                type=node_type,
                data=node_data
            ))

        edges = [GraphEdgeData.from_dict(edge) for edge in raw_edges]

        return cls(nodes=nodes, edges=edges)


@dataclass
class TopicsData:
    """Serialization model for topics artifact"""
    topics: List[str] = field(default_factory=list)
    subscriptions: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, topics_dict: Dict[str, Any]) -> "TopicsData":
        """Deserialize from dict"""
        topics_raw = topics_dict.get("topics", [])
        subscriptions_list = topics_dict.get("subscriptions", [])

        # Handle both formats: list of strings or list of dicts with "name" key
        topics_list = []
        for topic in topics_raw:
            if isinstance(topic, str):
                topics_list.append(topic)
            elif isinstance(topic, dict) and "name" in topic:
                topics_list.append(topic["name"])

        return cls(
            topics=topics_list,
            subscriptions=subscriptions_list
        )
