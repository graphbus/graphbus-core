"""
Namespace — logical isolation boundary for agent communication.

A namespace groups agents that can communicate with each other via the message bus.
Agents in different namespaces are isolated unless explicitly bridged.

Features:
  - Communication isolation (agents only see messages in their namespace)
  - Agent registration and discovery
  - Topology tracking (who publishes/subscribes to what)
  - Visualization-ready graph export

Usage:
    from graphbus_core.namespace import Namespace, NamespaceRegistry

    registry = NamespaceRegistry()
    ns = registry.create("backend-api", description="Backend service agents")
    ns.register_agent("AuthAgent", publishes=["/auth/token"], subscribes=["/user/login"])
    ns.register_agent("UserAgent", publishes=["/user/login"], subscribes=["/auth/token"])

    # Get topology for visualization
    topology = ns.get_topology()
    registry.export_all()  # JSON for dashboard
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from graphbus_core.model.graph import AgentGraph


@dataclass
class AgentRegistration:
    """An agent registered in a namespace."""
    name: str
    description: str = ""
    publishes: list[str] = field(default_factory=list)
    subscribes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    source_file: str = ""
    registered_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class Namespace:
    """A logical isolation boundary for agent communication.

    Agents within a namespace can communicate via shared topics.
    Different namespaces are isolated from each other.
    """

    def __init__(self, name: str, description: str = "", owner_uid: str = ""):
        self.name = name
        self.description = description
        self.owner_uid = owner_uid
        self.created_at = time.time()
        self._agents: dict[str, AgentRegistration] = {}
        self._graph: Optional[AgentGraph] = None

    def register_agent(
        self,
        name: str,
        description: str = "",
        publishes: list[str] = None,
        subscribes: list[str] = None,
        methods: list[str] = None,
        source_file: str = "",
        metadata: dict = None,
    ) -> AgentRegistration:
        """Register an agent in this namespace.

        Args:
            name: Agent name (unique within namespace).
            description: What this agent does.
            publishes: Topics this agent publishes to.
            subscribes: Topics this agent subscribes to.
            methods: Public methods exposed by this agent.
            source_file: Path to agent source code.
            metadata: Additional metadata.

        Returns:
            The AgentRegistration object.
        """
        reg = AgentRegistration(
            name=name,
            description=description,
            publishes=publishes or [],
            subscribes=subscribes or [],
            methods=methods or [],
            source_file=source_file,
            metadata=metadata or {},
        )
        self._agents[name] = reg
        self._graph = None  # Invalidate cached graph
        return reg

    def unregister_agent(self, name: str) -> bool:
        """Remove an agent from this namespace."""
        if name in self._agents:
            del self._agents[name]
            self._graph = None
            return True
        return False

    @property
    def agents(self) -> dict[str, AgentRegistration]:
        return dict(self._agents)

    @property
    def topics(self) -> set[str]:
        """All topics used in this namespace."""
        topics = set()
        for agent in self._agents.values():
            topics.update(agent.publishes)
            topics.update(agent.subscribes)
        return topics

    def get_graph(self) -> AgentGraph:
        """Build an AgentGraph representing this namespace's topology."""
        if self._graph is not None:
            return self._graph

        graph = AgentGraph()

        for agent in self._agents.values():
            graph.add_node(
                agent.name,
                node_type="agent",
                description=agent.description,
                methods=agent.methods,
                source_file=agent.source_file,
                namespace=self.name,
            )

        # Add topic nodes and edges
        for agent in self._agents.values():
            for topic in agent.publishes:
                if topic not in graph:
                    graph.add_node(topic, node_type="topic", namespace=self.name)
                graph.add_edge(agent.name, topic, edge_type="publishes")

            for topic in agent.subscribes:
                if topic not in graph:
                    graph.add_node(topic, node_type="topic", namespace=self.name)
                graph.add_edge(topic, agent.name, edge_type="subscribes")

        self._graph = graph
        return graph

    def get_topology(self) -> dict:
        """Get namespace topology as a JSON-serializable dict for visualization.

        Returns a dict with:
          - agents: list of agent info dicts
          - topics: list of topic strings
          - edges: list of {from, to, type} dicts
          - stats: summary statistics
        """
        agents = []
        for a in self._agents.values():
            agents.append({
                "name": a.name,
                "description": a.description,
                "publishes": a.publishes,
                "subscribes": a.subscribes,
                "methods": a.methods,
                "source_file": a.source_file,
            })

        edges = []
        for a in self._agents.values():
            for topic in a.publishes:
                edges.append({"from": a.name, "to": topic, "type": "publishes"})
            for topic in a.subscribes:
                edges.append({"from": topic, "to": a.name, "type": "subscribes"})

        # Find communication pairs (agents connected via shared topics)
        pairs = []
        for topic in self.topics:
            publishers = [a.name for a in self._agents.values() if topic in a.publishes]
            subscribers = [a.name for a in self._agents.values() if topic in a.subscribes]
            for pub in publishers:
                for sub in subscribers:
                    if pub != sub:
                        pairs.append({"publisher": pub, "subscriber": sub, "topic": topic})

        return {
            "namespace": self.name,
            "description": self.description,
            "agents": agents,
            "topics": sorted(self.topics),
            "edges": edges,
            "communication_pairs": pairs,
            "stats": {
                "agent_count": len(self._agents),
                "topic_count": len(self.topics),
                "edge_count": len(edges),
                "pair_count": len(pairs),
            },
        }

    def to_dict(self) -> dict:
        """Serialize namespace for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "owner_uid": self.owner_uid,
            "created_at": self.created_at,
            "agents": {
                name: {
                    "name": a.name,
                    "description": a.description,
                    "publishes": a.publishes,
                    "subscribes": a.subscribes,
                    "methods": a.methods,
                    "source_file": a.source_file,
                    "registered_at": a.registered_at,
                    "metadata": a.metadata,
                }
                for name, a in self._agents.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Namespace":
        """Deserialize namespace from storage."""
        ns = cls(
            name=data["name"],
            description=data.get("description", ""),
            owner_uid=data.get("owner_uid", ""),
        )
        ns.created_at = data.get("created_at", time.time())
        for name, agent_data in data.get("agents", {}).items():
            ns.register_agent(
                name=agent_data["name"],
                description=agent_data.get("description", ""),
                publishes=agent_data.get("publishes", []),
                subscribes=agent_data.get("subscribes", []),
                methods=agent_data.get("methods", []),
                source_file=agent_data.get("source_file", ""),
                metadata=agent_data.get("metadata", {}),
            )
        return ns


class NamespaceRegistry:
    """Registry for managing multiple namespaces.

    Provides CRUD operations and cross-namespace queries.
    Persists to .graphbus/namespaces.json.
    """

    DEFAULT_NAMESPACE = "default"

    def __init__(self, storage_dir: Optional[str] = None):
        self._namespaces: dict[str, Namespace] = {}
        self._storage_path = Path(storage_dir) / "namespaces.json" if storage_dir else None
        self._context_path = Path(storage_dir) / "context.json" if storage_dir else None

        # Auto-load from disk
        if self._storage_path and self._storage_path.exists():
            self._load()

    def create(self, name: str, description: str = "", owner_uid: str = "") -> Namespace:
        """Create a new namespace."""
        if name in self._namespaces:
            raise ValueError(f"Namespace '{name}' already exists")
        ns = Namespace(name=name, description=description, owner_uid=owner_uid)
        self._namespaces[name] = ns
        self._save()
        return ns

    def get(self, name: str) -> Optional[Namespace]:
        """Get a namespace by name."""
        return self._namespaces.get(name)

    def get_or_create(self, name: str, description: str = "", owner_uid: str = "") -> Namespace:
        """Get existing or create new namespace."""
        if name in self._namespaces:
            return self._namespaces[name]
        return self.create(name, description, owner_uid)

    def delete(self, name: str) -> bool:
        """Delete a namespace."""
        if name in self._namespaces:
            del self._namespaces[name]
            self._save()
            return True
        return False

    def list_namespaces(self) -> list[dict]:
        """List all namespaces with summary info."""
        result = []
        for ns in self._namespaces.values():
            result.append({
                "name": ns.name,
                "description": ns.description,
                "agent_count": len(ns.agents),
                "topic_count": len(ns.topics),
                "created_at": ns.created_at,
            })
        return result

    def get_current(self) -> str:
        """Return the active namespace name (reads from context.json, falls back to 'default')."""
        if self._context_path and self._context_path.exists():
            try:
                with open(self._context_path) as f:
                    ctx = json.load(f)
                return ctx.get("current_namespace", self.DEFAULT_NAMESPACE)
            except (json.JSONDecodeError, OSError):
                pass
        return self.DEFAULT_NAMESPACE

    def set_current(self, name: str) -> None:
        """Persist the active namespace to context.json.

        Raises ValueError if the namespace doesn't exist.
        """
        if name not in self._namespaces:
            raise ValueError(f"Namespace '{name}' not found — create it first with: graphbus ns create {name}")
        if not self._context_path:
            raise RuntimeError("NamespaceRegistry has no storage_dir; cannot persist context")
        self._context_path.parent.mkdir(parents=True, exist_ok=True)
        ctx: dict = {}
        if self._context_path.exists():
            try:
                with open(self._context_path) as f:
                    ctx = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        ctx["current_namespace"] = name
        with open(self._context_path, "w") as f:
            json.dump(ctx, f, indent=2)

    def export_all(self) -> dict:
        """Export all namespaces and their topologies for dashboard visualization."""
        return {
            "namespaces": {
                name: ns.get_topology()
                for name, ns in self._namespaces.items()
            },
            "summary": {
                "namespace_count": len(self._namespaces),
                "total_agents": sum(len(ns.agents) for ns in self._namespaces.values()),
                "total_topics": len(set().union(*(ns.topics for ns in self._namespaces.values()))) if self._namespaces else 0,
            },
        }

    def _save(self):
        """Persist to disk."""
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: ns.to_dict() for name, ns in self._namespaces.items()}
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load from disk."""
        if not self._storage_path or not self._storage_path.exists():
            return
        with open(self._storage_path) as f:
            data = json.load(f)
        for name, ns_data in data.items():
            self._namespaces[name] = Namespace.from_dict(ns_data)
