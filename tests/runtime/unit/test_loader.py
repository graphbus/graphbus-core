"""
Unit tests for ArtifactLoader
"""

import pytest
import json
import tempfile
from pathlib import Path

from graphbus_core.runtime.loader import ArtifactLoader
from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph


class TestArtifactLoader:
    """Tests for ArtifactLoader"""

    @pytest.fixture
    def temp_artifacts_dir(self):
        """Create temporary artifacts directory with test data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Create minimal graph.json
            graph_data = {
                "nodes": [
                    {"name": "TestAgent", "type": "agent", "data": {}}
                ],
                "edges": []
            }
            (artifacts_dir / "graph.json").write_text(json.dumps(graph_data))

            # Create minimal agents.json
            agents_data = [{
                "name": "TestAgent",
                "module": "test.module",
                "class_name": "TestAgent",
                "source_file": "/test.py",
                "source_code": "class TestAgent: pass",
                "system_prompt": {"text": "Test", "role": None, "capabilities": []},
                "methods": [],
                "subscriptions": [],
                "dependencies": [],
                "is_arbiter": False,
                "metadata": {}
            }]
            (artifacts_dir / "agents.json").write_text(json.dumps(agents_data))

            # Create minimal topics.json
            topics_data = {
                "topics": ["/test/topic"],
                "subscriptions": []
            }
            (artifacts_dir / "topics.json").write_text(json.dumps(topics_data))

            # Create build_summary.json
            summary_data = {"build_time": "2024-11-14", "agents": 1}
            (artifacts_dir / "build_summary.json").write_text(json.dumps(summary_data))

            yield str(artifacts_dir)

    def test_initialization(self, temp_artifacts_dir):
        """Test ArtifactLoader initialization"""
        loader = ArtifactLoader(temp_artifacts_dir)
        assert loader.artifacts_dir == Path(temp_artifacts_dir)

    def test_initialization_missing_directory(self):
        """Test initialization with missing directory"""
        with pytest.raises(FileNotFoundError):
            ArtifactLoader("/nonexistent/directory")

    def test_initialization_missing_files(self):
        """Test initialization with missing required files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError) as exc_info:
                ArtifactLoader(tmpdir)
            assert "Missing required artifact files" in str(exc_info.value)

    def test_load_graph(self, temp_artifacts_dir):
        """Test loading graph"""
        loader = ArtifactLoader(temp_artifacts_dir)
        graph = loader.load_graph()

        assert isinstance(graph, AgentGraph)
        assert "TestAgent" in graph.graph.nodes

    def test_load_agents(self, temp_artifacts_dir):
        """Test loading agents"""
        loader = ArtifactLoader(temp_artifacts_dir)
        agents = loader.load_agents()

        assert len(agents) == 1
        assert isinstance(agents[0], AgentDefinition)
        assert agents[0].name == "TestAgent"

    def test_load_topics(self, temp_artifacts_dir):
        """Test loading topics"""
        loader = ArtifactLoader(temp_artifacts_dir)
        topics = loader.load_topics()

        assert len(topics) == 1
        assert topics[0].name == "/test/topic"

    def test_load_subscriptions(self, temp_artifacts_dir):
        """Test loading subscriptions"""
        loader = ArtifactLoader(temp_artifacts_dir)
        subscriptions = loader.load_subscriptions()

        assert isinstance(subscriptions, list)

    def test_load_all(self, temp_artifacts_dir):
        """Test loading all artifacts at once"""
        loader = ArtifactLoader(temp_artifacts_dir)
        graph, agents, topics, subscriptions = loader.load_all()

        assert isinstance(graph, AgentGraph)
        assert len(agents) == 1
        assert len(topics) == 1
        assert isinstance(subscriptions, list)

    def test_get_agent_by_name(self, temp_artifacts_dir):
        """Test getting specific agent by name"""
        loader = ArtifactLoader(temp_artifacts_dir)
        agent = loader.get_agent_by_name("TestAgent")

        assert agent.name == "TestAgent"
        assert agent.module == "test.module"

    def test_get_agent_by_name_not_found(self, temp_artifacts_dir):
        """Test getting non-existent agent"""
        loader = ArtifactLoader(temp_artifacts_dir)

        with pytest.raises(ValueError) as exc_info:
            loader.get_agent_by_name("NonExistentAgent")
        assert "not found" in str(exc_info.value)

    def test_validate_artifacts(self, temp_artifacts_dir):
        """Test artifact validation"""
        loader = ArtifactLoader(temp_artifacts_dir)
        issues = loader.validate_artifacts()

        # Should have no issues with valid artifacts
        assert isinstance(issues, list)


class TestArtifactLoaderWithHelloWorld:
    """Tests using real Hello World artifacts"""

    def test_load_hello_world_artifacts(self):
        """Test loading actual Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"

        # Skip if artifacts don't exist
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found")

        loader = ArtifactLoader(artifacts_dir)

        # Load all artifacts
        graph, agents, topics, subscriptions = loader.load_all()

        # Verify agents
        assert len(agents) >= 3  # At least HelloService, PrinterService, LoggerService
        agent_names = [a.name for a in agents]
        assert "HelloService" in agent_names
        assert "LoggerService" in agent_names

        # Verify graph
        assert len(graph) >= 3

        # Verify topics
        assert len(topics) >= 1

        # Verify subscriptions
        assert len(subscriptions) >= 1
