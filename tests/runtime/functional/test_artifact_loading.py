"""
Functional tests for artifact loading workflows
"""

import pytest
from pathlib import Path

from graphbus_core.runtime.loader import ArtifactLoader
from graphbus_core.model.graph import AgentGraph
from graphbus_core.model.agent_def import AgentDefinition


class TestArtifactLoadingWorkflow:
    """Test complete artifact loading workflows using Hello World"""

    @pytest.fixture
    def hello_world_artifacts(self):
        """Path to Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found - run build first")
        return artifacts_dir

    def test_load_all_artifacts_workflow(self, hello_world_artifacts):
        """Test loading all artifacts in complete workflow"""
        loader = ArtifactLoader(hello_world_artifacts)
        graph, agents, topics, subscriptions = loader.load_all()

        # Verify graph structure
        assert isinstance(graph, AgentGraph)
        assert len(graph) >= 3
        assert "HelloService" in graph.graph.nodes
        assert "LoggerService" in graph.graph.nodes

        # Verify agents
        assert len(agents) >= 3
        agent_names = [a.name for a in agents]
        assert "HelloService" in agent_names
        assert "LoggerService" in agent_names

        # Verify topics
        assert len(topics) >= 1

        # Verify subscriptions
        assert len(subscriptions) >= 1

    def test_agent_dependency_chain(self, hello_world_artifacts):
        """Test that agent dependencies are properly loaded"""
        loader = ArtifactLoader(hello_world_artifacts)
        agents = loader.load_agents()

        # Verify agents were loaded
        assert len(agents) >= 3
        assert all(isinstance(a, AgentDefinition) for a in agents)

        # Each agent should have proper structure
        for agent in agents:
            assert agent.name is not None
            assert agent.module is not None
            assert agent.class_name is not None
            assert agent.source_code is not None

    def test_agent_subscriptions_mapping(self, hello_world_artifacts):
        """Test that agent subscriptions are properly mapped"""
        loader = ArtifactLoader(hello_world_artifacts)
        agents = loader.load_agents()
        subscriptions = loader.load_subscriptions()

        # Verify subscriptions exist
        assert len(subscriptions) >= 1

        # LoggerService should subscribe to /Hello/MessageGenerated
        logger = next((a for a in agents if a.name == "LoggerService"), None)
        assert logger is not None
        assert len(logger.subscriptions) >= 1

        # Verify subscription records match
        sub_agents = [s.node_name for s in subscriptions]
        assert "LoggerService" in sub_agents

    def test_graph_topology_validation(self, hello_world_artifacts):
        """Test that graph topology is valid"""
        loader = ArtifactLoader(hello_world_artifacts)
        graph = loader.load_graph()

        # Check nodes exist
        assert "HelloService" in graph.graph.nodes
        assert "LoggerService" in graph.graph.nodes

        # Check node attributes
        hello_data = graph.graph.nodes["HelloService"]
        assert hello_data["node_type"] == "agent"

    def test_get_agent_by_name_workflow(self, hello_world_artifacts):
        """Test retrieving specific agents by name"""
        loader = ArtifactLoader(hello_world_artifacts)

        hello_service = loader.get_agent_by_name("HelloService")
        assert hello_service.name == "HelloService"
        assert "hello" in hello_service.module.lower()

        logger_service = loader.get_agent_by_name("LoggerService")
        assert logger_service.name == "LoggerService"
        assert len(logger_service.subscriptions) >= 1

    def test_incremental_loading_workflow(self, hello_world_artifacts):
        """Test loading artifacts incrementally"""
        loader = ArtifactLoader(hello_world_artifacts)

        # Load graph first
        graph = loader.load_graph()
        assert len(graph) >= 3

        # Load agents next
        agents = loader.load_agents()
        assert len(agents) >= 3

        # Verify agent names match graph agent nodes (filter out topic nodes)
        agent_names = {a.name for a in agents}
        graph_agent_nodes = {
            node for node, data in graph.graph.nodes(data=True)
            if data.get("node_type") == "agent"
        }
        assert agent_names == graph_agent_nodes

        # Load topics
        topics = loader.load_topics()
        assert len(topics) >= 1

        # Load subscriptions
        subscriptions = loader.load_subscriptions()
        assert len(subscriptions) >= 1

    def test_artifact_metadata_preservation(self, hello_world_artifacts):
        """Test that artifact metadata is preserved through loading"""
        loader = ArtifactLoader(hello_world_artifacts)
        agents = loader.load_agents()

        # Each agent should have metadata structure
        for agent in agents:
            assert hasattr(agent, 'metadata')
            assert isinstance(agent.metadata, dict)

            # System prompt should be preserved
            assert hasattr(agent, 'system_prompt')
            assert agent.system_prompt is not None
