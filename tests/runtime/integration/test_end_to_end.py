"""
End-to-end integration tests for Runtime Mode using Hello World
"""

import pytest
from pathlib import Path

from graphbus_core.runtime.executor import run_runtime


class TestEndToEndRuntime:
    """End-to-end integration tests using Hello World as complete system"""

    @pytest.fixture
    def hello_world_artifacts(self):
        """Path to Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found - run build first")
        return artifacts_dir

    def test_complete_data_pipeline(self, hello_world_artifacts):
        """Test complete system startup and method invocation"""
        executor = run_runtime(hello_world_artifacts)

        # Call method to generate data
        result = executor.call_method("HelloService", "generate_message")

        # Verify result
        assert result is not None
        assert isinstance(result, dict)
        assert "message" in result

        executor.stop()

    def test_multiple_items_through_pipeline(self, hello_world_artifacts):
        """Test multiple method invocations"""
        executor = run_runtime(hello_world_artifacts)

        # Generate multiple messages
        results = []
        for i in range(5):
            result = executor.call_method("HelloService", "generate_message")
            results.append(result)

        # Verify all succeeded
        assert len(results) == 5
        assert all("message" in r for r in results)

        executor.stop()

    def test_query_stored_data(self, hello_world_artifacts):
        """Test querying node state after operations"""
        executor = run_runtime(hello_world_artifacts)

        # Perform operations
        for i in range(3):
            executor.call_method("HelloService", "generate_message")

        # Nodes should be accessible
        hello_service = executor.get_node("HelloService")
        assert hello_service is not None
        assert hello_service.name == "HelloService"

        executor.stop()

    def test_message_flow_statistics(self, hello_world_artifacts):
        """Test tracking message flow through system"""
        executor = run_runtime(hello_world_artifacts)

        initial_stats = executor.get_stats()
        initial_published = initial_stats["message_bus"]["messages_published"]

        # Generate and publish messages
        for i in range(3):
            result = executor.call_method("HelloService", "generate_message")
            executor.publish(
                "/Hello/MessageGenerated",
                result,
                source="HelloService"
            )

        # Check statistics increased
        final_stats = executor.get_stats()
        assert final_stats["message_bus"]["messages_published"] > initial_published

        executor.stop()

    def test_message_history_tracking(self, hello_world_artifacts):
        """Test message history through system"""
        executor = run_runtime(hello_world_artifacts)

        # Publish message
        executor.publish(
            "/Hello/MessageGenerated",
            {"message": "Test message"},
            source="test"
        )

        # Check message history
        history = executor.bus.get_message_history()
        assert len(history) >= 1

        # Verify message is in history
        topics = [event.topic for event in history]
        assert "/Hello/MessageGenerated" in topics

        executor.stop()

    def test_system_state_consistency(self, hello_world_artifacts):
        """Test that system state remains consistent"""
        executor = run_runtime(hello_world_artifacts)

        # Get initial stats
        initial_stats = executor.get_stats()
        initial_count = initial_stats["nodes_count"]

        # Perform operations
        executor.call_method("HelloService", "generate_message")

        # Verify node count unchanged
        final_stats = executor.get_stats()
        assert final_stats["nodes_count"] == initial_count

        executor.stop()

    def test_pipeline_with_errors(self, hello_world_artifacts):
        """Test system behavior with error conditions"""
        executor = run_runtime(hello_world_artifacts)

        # Valid operation
        result = executor.call_method("HelloService", "generate_message")
        assert result is not None

        # Invalid operation should raise error
        with pytest.raises((AttributeError, ValueError)):
            executor.call_method("HelloService", "non_existent_method")

        # System should still be operational
        result2 = executor.call_method("HelloService", "generate_message")
        assert result2 is not None

        executor.stop()

    def test_system_restart_preserves_nothing(self, hello_world_artifacts):
        """Test that system restart creates fresh state"""
        executor = run_runtime(hello_world_artifacts)

        # Publish messages
        executor.publish("/test", {"data": "test"}, source="test")

        first_stats = executor.get_stats()
        first_published = first_stats["message_bus"]["messages_published"]
        assert first_published >= 1

        # Stop and restart
        executor.stop()
        executor.start()

        # Message bus stats should be reset
        restart_stats = executor.get_stats()
        restart_published = restart_stats["message_bus"]["messages_published"]
        assert restart_published == 0  # Fresh start

        executor.stop()

    def test_direct_node_access(self, hello_world_artifacts):
        """Test direct access to nodes for inspection"""
        executor = run_runtime(hello_world_artifacts)

        # Get all nodes
        all_nodes = executor.get_all_nodes()
        assert len(all_nodes) >= 3

        # Access specific nodes
        hello_service = executor.get_node("HelloService")
        logger_service = executor.get_node("LoggerService")

        # Verify nodes have expected attributes
        assert hasattr(hello_service, "generate_message")
        assert hasattr(logger_service, "on_message_generated")

        executor.stop()

    def test_topic_subscription_integrity(self, hello_world_artifacts):
        """Test that topic subscriptions remain intact"""
        executor = run_runtime(hello_world_artifacts)

        # Check subscriptions exist
        subscribers = executor.bus.get_subscribers("/Hello/MessageGenerated")
        assert len(subscribers) >= 1

        # LoggerService should be subscribed
        assert "LoggerService" in subscribers

        executor.stop()

    def test_full_system_lifecycle(self, hello_world_artifacts):
        """Test complete system lifecycle from start to stop"""
        executor = run_runtime(hello_world_artifacts)

        # Verify started
        assert executor._is_running
        assert len(executor.nodes) >= 3

        # Operate
        for i in range(10):
            result = executor.call_method("HelloService", "generate_message")
            executor.publish(
                "/Hello/MessageGenerated",
                result,
                source="HelloService"
            )

        # Verify operation
        final_stats = executor.get_stats()
        assert final_stats["is_running"]
        assert final_stats["message_bus"]["messages_published"] >= 10

        # Stop
        executor.stop()
        assert not executor._is_running
