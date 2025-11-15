"""
Functional tests for message flow and event routing
"""

import pytest
from graphbus_core.runtime.message_bus import MessageBus
from graphbus_core.runtime.event_router import EventRouter
from graphbus_core.model.message import Event
from graphbus_core.model.topic import Topic, Subscription
from graphbus_core.node_base import GraphBusNode


class ProducerNode(GraphBusNode):
    """Mock producer node"""

    def __init__(self):
        super().__init__(bus=None, memory=None)
        self.name = "ProducerNode"
        self.produced = []

    def produce(self, data):
        """Produce data and publish event"""
        self.produced.append(data)
        if self.bus:
            self.bus.publish("/data/produced", {"data": data}, source=self.name)
        return data


class ConsumerNode(GraphBusNode):
    """Mock consumer node"""

    def __init__(self):
        super().__init__(bus=None, memory=None)
        self.name = "ConsumerNode"
        self.consumed = []

    def on_data_produced(self, payload):
        """Handle data produced event"""
        self.consumed.append(payload)
        if self.bus:
            self.bus.publish("/data/consumed", payload, source=self.name)


class ProcessorNode(GraphBusNode):
    """Mock processor node"""

    def __init__(self):
        super().__init__(bus=None, memory=None)
        self.name = "ProcessorNode"
        self.processed = []

    def on_data_consumed(self, payload):
        """Handle data consumed event"""
        processed = {**payload, "processed": True}
        self.processed.append(processed)
        if self.bus:
            self.bus.publish("/data/processed", processed, source=self.name)


class TestMessageFlowWorkflow:
    """Test complete message flow workflows"""

    def test_simple_pub_sub_flow(self):
        """Test simple publish-subscribe flow"""
        bus = MessageBus()
        consumer = ConsumerNode()
        consumer.bus = bus

        nodes = {"ConsumerNode": consumer}
        router = EventRouter(bus, nodes)

        # Register subscription
        topic = Topic(name="/data/produced")
        subscription = Subscription(
            node_name="ConsumerNode",
            topic=topic,
            handler_name="on_data_produced"
        )
        router.register_subscription(subscription)

        # Set router as dispatcher
        bus._dispatcher = router

        # Publish event
        event = bus.publish("/data/produced", {"data": "test"}, source="producer")

        # Verify event was received
        assert len(consumer.consumed) == 1
        assert consumer.consumed[0]["data"] == "test"

        # Verify stats (consumer also publishes /data/consumed event)
        stats = bus.get_stats()
        assert stats["messages_published"] == 2  # produced + consumed events
        assert stats["messages_delivered"] == 1  # only one handler received original event

    def test_producer_consumer_flow(self):
        """Test producer-consumer message flow"""
        bus = MessageBus()
        producer = ProducerNode()
        consumer = ConsumerNode()

        producer.bus = bus
        consumer.bus = bus

        nodes = {"ConsumerNode": consumer}
        router = EventRouter(bus, nodes)

        # Register consumer
        topic = Topic(name="/data/produced")
        router.register_subscription(
            Subscription(node_name="ConsumerNode", topic=topic, handler_name="on_data_produced")
        )
        bus._dispatcher = router

        # Producer produces data
        result = producer.produce("test_data")

        # Verify producer
        assert result == "test_data"
        assert "test_data" in producer.produced

        # Verify consumer received and published next event
        assert len(consumer.consumed) == 1
        assert consumer.consumed[0]["data"] == "test_data"

        # Verify two events published (produced + consumed)
        stats = bus.get_stats()
        assert stats["messages_published"] == 2

    def test_three_node_pipeline_flow(self):
        """Test three-node pipeline flow"""
        bus = MessageBus()
        producer = ProducerNode()
        consumer = ConsumerNode()
        processor = ProcessorNode()

        producer.bus = bus
        consumer.bus = bus
        processor.bus = bus

        nodes = {
            "ConsumerNode": consumer,
            "ProcessorNode": processor
        }
        router = EventRouter(bus, nodes)

        # Register handlers
        topic1 = Topic(name="/data/produced")
        topic2 = Topic(name="/data/consumed")
        router.register_subscriptions([
            Subscription(node_name="ConsumerNode", topic=topic1, handler_name="on_data_produced"),
            Subscription(node_name="ProcessorNode", topic=topic2, handler_name="on_data_consumed")
        ])
        bus._dispatcher = router

        # Start pipeline
        producer.produce("pipeline_data")

        # Verify full pipeline
        assert len(producer.produced) == 1
        assert len(consumer.consumed) == 1
        assert len(processor.processed) == 1

        # Verify data transformation
        assert processor.processed[0]["data"] == "pipeline_data"
        assert processor.processed[0]["processed"] is True

        # Verify three events published
        stats = bus.get_stats()
        assert stats["messages_published"] == 3  # produced, consumed, processed

    def test_multiple_consumers_flow(self):
        """Test message flow with multiple consumers"""
        bus = MessageBus()
        producer = ProducerNode()
        consumer1 = ConsumerNode()
        consumer2 = ConsumerNode()

        producer.bus = bus
        consumer1.bus = bus
        consumer1.name = "Consumer1"
        consumer2.bus = bus
        consumer2.name = "Consumer2"

        nodes = {
            "Consumer1": consumer1,
            "Consumer2": consumer2
        }
        router = EventRouter(bus, nodes)

        # Register both consumers
        topic = Topic(name="/data/produced")
        router.register_subscriptions([
            Subscription(node_name="Consumer1", topic=topic, handler_name="on_data_produced"),
            Subscription(node_name="Consumer2", topic=topic, handler_name="on_data_produced")
        ])
        bus._dispatcher = router

        # Produce data
        producer.produce("shared_data")

        # Both consumers should receive
        assert len(consumer1.consumed) == 1
        assert len(consumer2.consumed) == 1

        # Verify message delivered to 2 handlers
        stats = bus.get_stats()
        assert stats["messages_delivered"] == 2

    def test_message_history_flow(self):
        """Test message history tracking through flow"""
        bus = MessageBus()
        producer = ProducerNode()
        consumer = ConsumerNode()

        producer.bus = bus
        consumer.bus = bus

        nodes = {"ConsumerNode": consumer}
        router = EventRouter(bus, nodes)

        topic = Topic(name="/data/produced")
        router.register_subscription(
            Subscription(node_name="ConsumerNode", topic=topic, handler_name="on_data_produced")
        )
        bus._dispatcher = router

        # Produce multiple messages
        for i in range(5):
            producer.produce(f"data_{i}")

        # Check history
        history = bus.get_message_history()
        assert len(history) >= 5  # At least 5 produced + consumed events

        # History should be newest first
        assert "/data/consumed" in history[0].topic or "/data/produced" in history[0].topic

    def test_high_volume_message_flow(self):
        """Test message flow with high volume"""
        bus = MessageBus()
        consumer = ConsumerNode()
        consumer.bus = bus

        nodes = {"ConsumerNode": consumer}
        router = EventRouter(bus, nodes)

        topic = Topic(name="/test")
        router.register_subscription(
            Subscription(node_name="ConsumerNode", topic=topic, handler_name="on_data_produced")
        )
        bus._dispatcher = router

        # Publish 100 messages
        for i in range(100):
            bus.publish("/test", {"data": i}, source="test")

        # All should be received
        assert len(consumer.consumed) == 100

        # Stats should match
        stats = bus.get_stats()
        assert stats["messages_published"] >= 100
        assert stats["messages_delivered"] >= 100
