"""
Artifact Loader - Loads build artifacts for Runtime Mode
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple

from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph
from graphbus_core.model.topic import Topic, Subscription
from graphbus_core.model.message import Event
from graphbus_core.model.serialization import GraphData, TopicsData


class ArtifactLoader:
    """
    Loads build artifacts from .graphbus directory for Runtime Mode.

    Responsibilities:
    - Load and deserialize JSON artifacts
    - Reconstruct AgentGraph from serialized data
    - Load agent definitions
    - Load topics and subscriptions
    - Validate artifact integrity
    """

    def __init__(self, artifacts_dir: str):
        """
        Initialize artifact loader.

        Args:
            artifacts_dir: Path to .graphbus directory (e.g., ".graphbus" or "/path/to/.graphbus")
        """
        self.artifacts_dir = Path(artifacts_dir)
        self._validate_directory()

    def _validate_directory(self) -> None:
        """Validate that artifacts directory exists and contains required files."""
        if not self.artifacts_dir.exists():
            raise FileNotFoundError(f"Artifacts directory not found: {self.artifacts_dir}")

        if not self.artifacts_dir.is_dir():
            raise ValueError(f"Artifacts path is not a directory: {self.artifacts_dir}")

        required_files = ["graph.json", "agents.json", "topics.json", "build_summary.json"]
        missing = []
        for filename in required_files:
            if not (self.artifacts_dir / filename).exists():
                missing.append(filename)

        if missing:
            raise FileNotFoundError(
                f"Missing required artifact files in {self.artifacts_dir}: {', '.join(missing)}"
            )

    def load_build_summary(self) -> Dict:
        """
        Load build summary metadata.

        Returns:
            Dict with build summary data
        """
        summary_path = self.artifacts_dir / "build_summary.json"
        with open(summary_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_graph(self) -> AgentGraph:
        """
        Load and reconstruct AgentGraph from graph.json.

        Returns:
            Reconstructed AgentGraph
        """
        graph_path = self.artifacts_dir / "graph.json"
        with open(graph_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Deserialize using dataclass
        graph_data = GraphData.from_dict(raw_data)

        # Create empty AgentGraph
        graph = AgentGraph()

        # Add nodes
        for node in graph_data.nodes:
            # Don't pass node_type if it's already in data to avoid duplication
            if "node_type" in node.data:
                graph.add_node(node.name, **node.data)
            else:
                graph.add_node(node.name, node_type=node.type, **node.data)

        # Add edges
        for edge in graph_data.edges:
            # Don't pass edge_type if it's already in data
            if "edge_type" in edge.data:
                graph.add_edge(edge.from_node, edge.to_node, **edge.data)
            else:
                graph.add_edge(edge.from_node, edge.to_node, edge_type=edge.type, **edge.data)

        return graph

    def load_agents(self) -> List[AgentDefinition]:
        """
        Load agent definitions from agents.json.

        Returns:
            List of AgentDefinition objects
        """
        agents_path = self.artifacts_dir / "agents.json"
        with open(agents_path, 'r', encoding='utf-8') as f:
            agents_data = json.load(f)

        agents = []
        for agent_data in agents_data:
            agent = AgentDefinition.from_dict(agent_data)
            agents.append(agent)

        return agents

    def _load_topics_and_subscriptions(self) -> Tuple[List[Topic], List[Subscription]]:
        """
        Read topics.json once and return both topics and subscriptions.

        This private helper exists so callers that need both (load_all,
        validate_artifacts) can avoid reading and parsing the file twice —
        the original load_topics() and load_subscriptions() each opened the
        same file independently, meaning two disk reads per load_all() call.
        """
        topics_path = self.artifacts_dir / "topics.json"
        with open(topics_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        topics_data = TopicsData.from_dict(raw_data)
        topics = [Topic(topic_name) for topic_name in topics_data.topics]
        subscriptions = [
            Subscription.from_dict(sub_data)
            for sub_data in topics_data.subscriptions
        ]
        return topics, subscriptions

    def load_topics(self) -> List[Topic]:
        """
        Load topics from topics.json.

        Returns:
            List of Topic objects
        """
        topics, _ = self._load_topics_and_subscriptions()
        return topics

    def load_subscriptions(self) -> List[Subscription]:
        """
        Load subscriptions from topics.json.

        Returns:
            List of Subscription objects
        """
        _, subscriptions = self._load_topics_and_subscriptions()
        return subscriptions

    def load_all(self) -> Tuple[AgentGraph, List[AgentDefinition], List[Topic], List[Subscription]]:
        """
        Load all artifacts at once.

        Returns:
            Tuple of (graph, agents, topics, subscriptions)
        """
        graph = self.load_graph()
        agents = self.load_agents()
        # Single read of topics.json rather than two separate calls to
        # load_topics() and load_subscriptions().
        topics, subscriptions = self._load_topics_and_subscriptions()

        return graph, agents, topics, subscriptions

    def get_agent_by_name(self, name: str) -> AgentDefinition:
        """
        Get a specific agent definition by name.

        Args:
            name: Agent name

        Returns:
            AgentDefinition

        Raises:
            ValueError: If agent not found
        """
        agents = self.load_agents()
        for agent in agents:
            if agent.name == name:
                return agent

        raise ValueError(f"Agent '{name}' not found in artifacts")

    def get_subscriptions_for_topic(self, topic_name: str) -> List[Subscription]:
        """
        Get all subscriptions for a specific topic.

        Args:
            topic_name: Topic name (e.g., "/Order/Created")

        Returns:
            List of Subscriptions for this topic
        """
        subscriptions = self.load_subscriptions()
        return [sub for sub in subscriptions if sub.topic.name == topic_name]

    def validate_artifacts(self) -> List[str]:
        """
        Validate artifact integrity and consistency.

        Returns:
            List of validation warnings/errors (empty if all valid)
        """
        issues = []

        try:
            # Check if all files load successfully (single read of topics.json)
            graph = self.load_graph()
            agents = self.load_agents()
            topics, subscriptions = self._load_topics_and_subscriptions()

            # Validate agent references in subscriptions
            agent_names = {agent.name for agent in agents}
            for sub in subscriptions:
                if sub.node_name not in agent_names:
                    issues.append(f"Subscription references unknown agent: {sub.node_name}")

            # Validate topic references
            topic_names = {topic.name for topic in topics}
            for sub in subscriptions:
                if sub.topic.name not in topic_names:
                    issues.append(f"Subscription references unknown topic: {sub.topic.name}")

            # Check graph node references
            for agent in agents:
                if agent.name not in graph.graph.nodes:
                    issues.append(f"Agent '{agent.name}' not found in graph")

        except Exception as e:
            issues.append(f"Error during validation: {str(e)}")

        return issues
