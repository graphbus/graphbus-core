"""
Integration tests for Hello World example in Runtime Mode
"""

import pytest
from pathlib import Path

from graphbus_core.runtime.executor import run_runtime


class TestHelloWorldRuntime:
    """Integration tests using Hello World example"""

    @pytest.fixture
    def hello_world_artifacts(self):
        """Path to Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found - run build first")
        return artifacts_dir

    def test_hello_world_full_startup(self, hello_world_artifacts):
        """Test complete Hello World runtime startup"""
        executor = run_runtime(hello_world_artifacts)

        # Verify runtime is running
        assert executor._is_running

        # Verify nodes loaded
        assert len(executor.nodes) >= 3

        # Verify key nodes exist
        assert "HelloService" in executor.nodes
        assert "LoggerService" in executor.nodes

        # Verify message bus
        assert executor.bus is not None
        assert executor.router is not None

        executor.stop()

    def test_hello_world_node_initialization(self, hello_world_artifacts):
        """Test that Hello World nodes are properly initialized"""
        executor = run_runtime(hello_world_artifacts)

        # Get HelloService node
        hello_service = executor.get_node("HelloService")
        assert hello_service is not None
        assert hello_service.name == "HelloService"
        assert hasattr(hello_service, "generate_message")

        # Get LoggerService node
        logger_service = executor.get_node("LoggerService")
        assert logger_service is not None
        assert logger_service.name == "LoggerService"
        assert hasattr(logger_service, "on_message_generated")

        executor.stop()

    def test_hello_world_method_invocation(self, hello_world_artifacts):
        """Test invoking Hello World methods"""
        executor = run_runtime(hello_world_artifacts)

        # Call HelloService.generate_message()
        result = executor.call_method("HelloService", "generate_message")

        # Verify result
        assert result is not None
        assert isinstance(result, dict)
        assert "message" in result
        assert len(result["message"]) > 0

        executor.stop()

    def test_hello_world_event_publishing(self, hello_world_artifacts):
        """Test publishing events in Hello World"""
        executor = run_runtime(hello_world_artifacts)

        # Publish to Hello topic
        executor.publish(
            "/Hello/MessageGenerated",
            {"message": "Test message from integration test"},
            source="integration_test"
        )

        # Verify event was published
        stats = executor.get_stats()
        assert stats["message_bus"]["messages_published"] >= 1

        executor.stop()

    def test_hello_world_full_workflow(self, hello_world_artifacts):
        """Test complete Hello World workflow"""
        executor = run_runtime(hello_world_artifacts)

        # Step 1: Generate message
        message = executor.call_method("HelloService", "generate_message")
        assert message is not None

        # Step 2: Publish message to trigger subscribers
        executor.publish(
            "/Hello/MessageGenerated",
            {"message": message},
            source="HelloService"
        )

        # Step 3: Verify message was delivered
        stats = executor.get_stats()
        assert stats["message_bus"]["messages_published"] >= 1
        assert stats["message_bus"]["messages_delivered"] >= 1

        # Step 4: Check message history
        history = executor.bus.get_message_history()
        assert len(history) >= 1

        executor.stop()

    def test_hello_world_subscriptions(self, hello_world_artifacts):
        """Test that Hello World subscriptions are registered"""
        executor = run_runtime(hello_world_artifacts)

        # Check that subscriptions exist
        all_topics = executor.bus.get_all_topics()
        assert len(all_topics) > 0

        # Check specific topic has subscribers
        subscribers = executor.bus.get_subscribers("/Hello/MessageGenerated")
        assert len(subscribers) > 0

        executor.stop()

    def test_hello_world_statistics(self, hello_world_artifacts):
        """Test Hello World runtime statistics"""
        executor = run_runtime(hello_world_artifacts)

        # Get initial stats
        stats = executor.get_stats()
        assert stats["is_running"]
        assert stats["nodes_count"] >= 3
        assert "message_bus" in stats

        initial_published = stats["message_bus"]["messages_published"]

        # Perform some operations
        executor.call_method("HelloService", "generate_message")
        executor.publish("/test", {"data": "test"})

        # Get updated stats
        stats = executor.get_stats()
        assert stats["message_bus"]["messages_published"] > initial_published

        executor.stop()

    def test_hello_world_multiple_message_sequence(self, hello_world_artifacts):
        """Test sequence of multiple messages in Hello World"""
        executor = run_runtime(hello_world_artifacts)

        # Generate and publish multiple messages
        for i in range(5):
            message = executor.call_method("HelloService", "generate_message")
            executor.publish(
                "/Hello/MessageGenerated",
                {"message": f"{message} #{i}"},
                source="HelloService"
            )

        # Verify all messages processed
        stats = executor.get_stats()
        assert stats["message_bus"]["messages_published"] >= 5

        # Check history
        history = executor.bus.get_message_history()
        assert len(history) >= 5

        executor.stop()

    def test_hello_world_graph_structure(self, hello_world_artifacts):
        """Test that Hello World graph structure is correct"""
        executor = run_runtime(hello_world_artifacts)

        # Verify graph exists
        assert executor.graph is not None
        assert len(executor.graph) >= 3

        # Verify nodes in graph
        nodes = list(executor.graph.graph.nodes)
        assert "HelloService" in nodes
        assert "LoggerService" in nodes

        executor.stop()

    def test_hello_world_without_message_bus(self, hello_world_artifacts):
        """Test Hello World runtime without message bus"""
        executor = run_runtime(hello_world_artifacts, enable_message_bus=False)

        # Nodes should still be initialized
        assert len(executor.nodes) >= 3

        # Message bus should be disabled
        assert executor.bus is None
        assert executor.router is None

        # Direct method calls should still work
        result = executor.call_method("HelloService", "generate_message")
        assert result is not None

        executor.stop()

    def test_hello_world_restart(self, hello_world_artifacts):
        """Test restarting Hello World runtime"""
        executor = run_runtime(hello_world_artifacts)

        # Already started by run_runtime()
        assert executor._is_running
        first_nodes = executor.nodes.copy()

        # Stop
        executor.stop()
        assert not executor._is_running

        # Restart
        executor.start()
        assert executor._is_running
        second_nodes = executor.nodes

        # Should have same nodes
        assert set(first_nodes.keys()) == set(second_nodes.keys())

        executor.stop()

    def test_hello_world_error_handling(self, hello_world_artifacts):
        """Test error handling in Hello World runtime"""
        executor = run_runtime(hello_world_artifacts)

        # Try to call non-existent method
        with pytest.raises((AttributeError, ValueError)):
            executor.call_method("HelloService", "non_existent_method")

        # Try to get non-existent node
        with pytest.raises(ValueError):
            executor.get_node("NonExistentNode")

        # Runtime should still be operational
        assert executor._is_running

        executor.stop()

    def test_hello_world_concurrent_operations(self, hello_world_artifacts):
        """Test concurrent operations in Hello World"""
        executor = run_runtime(hello_world_artifacts)

        # Perform multiple operations
        results = []
        for i in range(10):
            result = executor.call_method("HelloService", "generate_message")
            results.append(result)
            executor.publish(
                "/Hello/MessageGenerated",
                {"message": result},
                source="concurrent_test"
            )

        # All operations should complete
        assert len(results) == 10

        # Stats should reflect all operations
        stats = executor.get_stats()
        assert stats["message_bus"]["messages_published"] >= 10

        executor.stop()
