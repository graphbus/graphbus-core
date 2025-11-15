"""
Unit tests for RuntimeExecutor
"""

import pytest
from pathlib import Path

from graphbus_core.runtime.executor import RuntimeExecutor, run_runtime
from graphbus_core.config import RuntimeConfig


class TestRuntimeExecutor:
    """Tests for RuntimeExecutor using Hello World artifacts"""

    @pytest.fixture
    def hello_world_artifacts(self):
        """Path to Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found - run build first")
        return artifacts_dir

    def test_initialization(self, hello_world_artifacts):
        """Test RuntimeExecutor initialization"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)

        assert executor.config == config
        assert executor.loader is None  # Not loaded until start()
        assert executor.graph is None
        assert executor.nodes == {}
        assert executor.bus is None
        assert executor.router is None
        assert not executor._is_running

    def test_load_artifacts(self, hello_world_artifacts):
        """Test loading artifacts"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.load_artifacts()

        assert executor.graph is not None
        assert executor.agent_definitions is not None
        assert len(executor.agent_definitions) >= 3

    def test_initialize_nodes(self, hello_world_artifacts):
        """Test initializing nodes from agent definitions"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.load_artifacts()
        executor.initialize_nodes()

        assert "HelloService" in executor.nodes
        assert "LoggerService" in executor.nodes
        node = executor.nodes["HelloService"]
        assert node.name == "HelloService"
        assert hasattr(node, "generate_message")

    def test_setup_message_bus(self, hello_world_artifacts):
        """Test setting up message bus with subscriptions"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.load_artifacts()
        executor.initialize_nodes()
        executor.setup_message_bus()

        assert executor.bus is not None
        assert executor.router is not None

        # Check subscription was registered
        handlers = executor.router.get_handlers_for_topic("/Hello/MessageGenerated")
        assert len(handlers) >= 1

    def test_start(self, hello_world_artifacts):
        """Test starting the runtime"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        assert executor._is_running
        assert executor.graph is not None
        assert len(executor.nodes) >= 3
        assert executor.bus is not None
        assert executor.router is not None

        executor.stop()

    def test_start_no_message_bus(self, hello_world_artifacts):
        """Test starting without message bus"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts, enable_message_bus=False)
        executor = RuntimeExecutor(config)
        executor.start()

        assert executor._is_running
        assert executor.bus is None
        assert executor.router is None
        assert len(executor.nodes) >= 3

        executor.stop()

    def test_call_method(self, hello_world_artifacts):
        """Test calling a node method"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        result = executor.call_method("HelloService", "generate_message")

        assert result is not None
        assert isinstance(result, dict)
        assert "message" in result

        executor.stop()

    def test_call_method_node_not_found(self, hello_world_artifacts):
        """Test calling method on non-existent node"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        with pytest.raises(ValueError) as exc_info:
            executor.call_method("NonExistent", "test_method")
        assert "not found" in str(exc_info.value)

        executor.stop()

    def test_call_method_before_start(self, hello_world_artifacts):
        """Test calling method before starting runtime"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)

        with pytest.raises(RuntimeError):
            executor.call_method("HelloService", "generate_message")

    def test_publish(self, hello_world_artifacts):
        """Test publishing event through message bus"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        executor.publish("/Hello/MessageGenerated", {"message": "test"}, source="test")

        # Verify event was published
        stats = executor.get_stats()
        assert stats["message_bus"]["messages_published"] >= 1

        executor.stop()

    def test_publish_no_message_bus(self, hello_world_artifacts):
        """Test publishing when message bus is disabled"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts, enable_message_bus=False)
        executor = RuntimeExecutor(config)
        executor.start()

        with pytest.raises(RuntimeError):
            executor.publish("/test/event", {"data": "test"})

        executor.stop()

    def test_get_node(self, hello_world_artifacts):
        """Test getting a node by name"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        node = executor.get_node("HelloService")
        assert node is not None
        assert node.name == "HelloService"

        executor.stop()

    def test_get_node_not_found(self, hello_world_artifacts):
        """Test getting non-existent node"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        with pytest.raises(ValueError):
            executor.get_node("NonExistent")

        executor.stop()

    def test_get_all_nodes(self, hello_world_artifacts):
        """Test getting all nodes"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        nodes = executor.get_all_nodes()
        assert len(nodes) >= 3
        assert "HelloService" in nodes

        executor.stop()

    def test_get_stats(self, hello_world_artifacts):
        """Test getting runtime statistics"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        # Call a method and publish an event
        executor.call_method("HelloService", "generate_message")
        executor.publish("/Hello/MessageGenerated", {"message": "test"})

        stats = executor.get_stats()

        assert stats["is_running"]
        assert stats["nodes_count"] >= 3
        assert "message_bus" in stats
        assert stats["message_bus"]["messages_published"] >= 1

        executor.stop()

    def test_get_stats_no_message_bus(self, hello_world_artifacts):
        """Test getting stats when message bus is disabled"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts, enable_message_bus=False)
        executor = RuntimeExecutor(config)
        executor.start()

        stats = executor.get_stats()

        assert stats["is_running"]
        assert stats["nodes_count"] >= 3
        # Message bus key may not exist when disabled
        assert stats.get("message_bus") is None

        executor.stop()

    def test_stop(self, hello_world_artifacts):
        """Test stopping the runtime"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)
        executor.start()

        assert executor._is_running

        executor.stop()

        assert not executor._is_running

    def test_multiple_start_calls(self, hello_world_artifacts):
        """Test that multiple start calls work correctly"""
        config = RuntimeConfig(artifacts_dir=hello_world_artifacts)
        executor = RuntimeExecutor(config)

        executor.start()
        first_nodes = set(executor.nodes.keys())

        # Stop and restart
        executor.stop()
        executor.start()
        second_nodes = set(executor.nodes.keys())

        # Should have same nodes
        assert first_nodes == second_nodes

        executor.stop()

    def test_run_runtime_convenience_function(self, hello_world_artifacts):
        """Test run_runtime convenience function"""
        executor = run_runtime(hello_world_artifacts)

        assert isinstance(executor, RuntimeExecutor)
        assert executor._is_running
        assert len(executor.nodes) >= 3

        executor.stop()

    def test_run_runtime_with_options(self, hello_world_artifacts):
        """Test run_runtime with enable_message_bus option"""
        executor = run_runtime(hello_world_artifacts, enable_message_bus=False)

        assert isinstance(executor, RuntimeExecutor)
        assert executor._is_running
        assert executor.bus is None
        assert len(executor.nodes) >= 3

        executor.stop()
