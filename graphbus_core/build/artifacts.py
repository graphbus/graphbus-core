"""
Build artifacts management
"""

import json
import os
from dataclasses import dataclass, field
from typing import List
from pathlib import Path

from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph
from graphbus_core.model.topic import Topic, Subscription
from graphbus_core.model.message import CommitRecord


@dataclass
class BuildArtifacts:
    """
    Artifacts produced by Build Mode.

    Contains:
    - Agent graph structure
    - Agent metadata
    - Negotiation history
    - Modified files list
    """
    graph: AgentGraph
    agents: List[AgentDefinition]
    topics: List[Topic] = field(default_factory=list)
    subscriptions: List[Subscription] = field(default_factory=list)
    negotiations: List[CommitRecord] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    output_dir: str = ".graphbus"
    success: bool = True  # Build success flag

    def save(self, output_dir: str | None = None) -> None:
        """
        Save artifacts to disk as JSON files.

        Args:
            output_dir: Directory to write artifacts (defaults to self.output_dir)
        """
        output_dir = output_dir or self.output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Save graph
        graph_path = os.path.join(output_dir, "graph.json")
        self.graph.to_json(graph_path)
        print(f"Saved graph to {graph_path}")

        # Save agents
        agents_path = os.path.join(output_dir, "agents.json")
        agents_data = [agent.to_dict() for agent in self.agents]
        with open(agents_path, "w") as f:
            json.dump(agents_data, f, indent=2)
        print(f"Saved {len(self.agents)} agents to {agents_path}")

        # Save topics and subscriptions
        topics_path = os.path.join(output_dir, "topics.json")
        topics_data = {
            "topics": [{"name": topic.name} for topic in self.topics],
            "subscriptions": [sub.to_dict() for sub in self.subscriptions]
        }
        with open(topics_path, "w") as f:
            json.dump(topics_data, f, indent=2)
        print(f"Saved topics to {topics_path}")

        # Save negotiations history
        if self.negotiations:
            negotiations_path = os.path.join(output_dir, "negotiations.json")
            negotiations_data = [neg.to_dict() for neg in self.negotiations]
            with open(negotiations_path, "w") as f:
                json.dump(negotiations_data, f, indent=2)
            print(f"Saved {len(self.negotiations)} negotiations to {negotiations_path}")

        # Save modified files list
        if self.modified_files:
            modified_path = os.path.join(output_dir, "modified_files.json")
            with open(modified_path, "w") as f:
                json.dump({"modified_files": self.modified_files}, f, indent=2)
            print(f"Saved modified files list to {modified_path}")

        # Save summary
        summary_path = os.path.join(output_dir, "build_summary.json")
        summary = {
            "num_agents": len(self.agents),
            "num_topics": len(self.topics),
            "num_subscriptions": len(self.subscriptions),
            "num_negotiations": len(self.negotiations),
            "num_modified_files": len(self.modified_files),
            "agents": [agent.name for agent in self.agents],
            "modified_files": self.modified_files
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved build summary to {summary_path}")

    @classmethod
    def load(cls, artifacts_dir: str = ".graphbus") -> "BuildArtifacts":
        """
        Load artifacts from disk.

        Args:
            artifacts_dir: Directory containing artifacts

        Returns:
            BuildArtifacts object
        """
        if not os.path.exists(artifacts_dir):
            raise FileNotFoundError(f"Artifacts directory not found: {artifacts_dir}")

        # Load graph
        graph_path = os.path.join(artifacts_dir, "graph.json")
        graph = AgentGraph.from_json(graph_path)

        # Load agents
        agents_path = os.path.join(artifacts_dir, "agents.json")
        with open(agents_path, "r") as f:
            agents_data = json.load(f)
        agents = [AgentDefinition.from_dict(data) for data in agents_data]

        # Load topics
        topics_path = os.path.join(artifacts_dir, "topics.json")
        topics = []
        subscriptions = []
        if os.path.exists(topics_path):
            with open(topics_path, "r") as f:
                topics_data = json.load(f)
            topics = [Topic(t["name"]) for t in topics_data.get("topics", [])]
            subscriptions = [Subscription.from_dict(s) for s in topics_data.get("subscriptions", [])]

        # Load negotiations (optional)
        negotiations_path = os.path.join(artifacts_dir, "negotiations.json")
        negotiations = []
        if os.path.exists(negotiations_path):
            with open(negotiations_path, "r") as f:
                negotiations_data = json.load(f)
            # Note: Would need CommitRecord.from_dict() method
            negotiations = negotiations_data  # Simplified for now

        # Load modified files (optional)
        modified_path = os.path.join(artifacts_dir, "modified_files.json")
        modified_files = []
        if os.path.exists(modified_path):
            with open(modified_path, "r") as f:
                data = json.load(f)
            modified_files = data.get("modified_files", [])

        return cls(
            graph=graph,
            agents=agents,
            topics=topics,
            subscriptions=subscriptions,
            negotiations=negotiations,
            modified_files=modified_files,
            output_dir=artifacts_dir
        )
