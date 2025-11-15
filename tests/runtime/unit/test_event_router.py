"""
Unit tests for EventRouter
"""

import pytest
from graphbus_core.runtime.event_router import EventRouter
from graphbus_core.runtime.message_bus import MessageBus
from graphbus_core.model.message import Event
from graphbus_core.model.topic import Topic, Subscription
from graphbus_core.node_base import GraphBusNode


class MockNode(GraphBusNode):
    """Mock node for testing event handlers"""

    def __init__(self):
        super().__init__(bus=None, memory=None)
        self.name = "MockNode"
        self.calls = []

    def handler_no_params(self):
        """Handler with no parameters"""
        self.calls.append(("handler_no_params", None))

    def handler_one_param(self, payload):
        """Handler with one parameter (payload dict)"""
        self.calls.append(("handler_one_param", payload))

    def handler_event_param(self, event: Event, extra: str = "default"):
        """Handler with Event parameter (multiple params triggers Event passing)"""
        self.calls.append(("handler_event_param", event))

    def handler_that_errors(self, payload):
        """Handler that raises an error"""
        raise ValueError("Test error")


class TestEventRouter:
    """Tests for EventRouter"""

    def test_initialization(self):
        """Test EventRouter initialization"""
        bus = MessageBus()
        nodes = {"node1": MockNode()}
        router = EventRouter(bus, nodes)

        assert router.bus == bus
        assert router.nodes == nodes
        assert len(router._handlers) == 0

    def test_register_subscription(self):
        """Test registering a subscription"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        # Create subscription
        topic = Topic(name="/test/topic")
        subscription = Subscription(
            node_name="MockNode",
            topic=topic,
            handler_name="handler_one_param"
        )

        router.register_subscription(subscription)

        # Check handler was registered
        handlers = router.get_handlers_for_topic("/test/topic")
        assert len(handlers) == 1
        assert handlers[0] == (node, "handler_one_param")

    def test_register_subscription_node_not_found(self):
        """Test registering subscription for non-existent node"""
        bus = MessageBus()
        nodes = {}
        router = EventRouter(bus, nodes)

        topic = Topic(name="/test/topic")
        subscription = Subscription(
            node_name="NonExistent",
            topic=topic,
            handler_name="handler_one_param"
        )

        # Should print warning but not crash
        router.register_subscription(subscription)

        handlers = router.get_handlers_for_topic("/test/topic")
        assert len(handlers) == 0

    def test_register_subscription_handler_not_found(self):
        """Test registering subscription with non-existent handler"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        topic = Topic(name="/test/topic")
        subscription = Subscription(
            node_name="MockNode",
            topic=topic,
            handler_name="non_existent_handler"
        )

        # Should print warning but not crash
        router.register_subscription(subscription)

        handlers = router.get_handlers_for_topic("/test/topic")
        assert len(handlers) == 0

    def test_register_subscriptions(self):
        """Test registering multiple subscriptions"""
        bus = MessageBus()
        node1 = MockNode()
        node2 = MockNode()
        node2.name = "MockNode2"
        nodes = {"MockNode": node1, "MockNode2": node2}
        router = EventRouter(bus, nodes)

        topic1 = Topic(name="/topic1")
        topic2 = Topic(name="/topic2")

        subscriptions = [
            Subscription(node_name="MockNode", topic=topic1, handler_name="handler_one_param"),
            Subscription(node_name="MockNode2", topic=topic2, handler_name="handler_one_param")
        ]

        router.register_subscriptions(subscriptions)

        assert len(router.get_handlers_for_topic("/topic1")) == 1
        assert len(router.get_handlers_for_topic("/topic2")) == 1

    def test_route_event_to_node_no_params(self):
        """Test routing event to handler with no parameters"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        event = Event(
            event_id="test_event",
            topic="/test/topic",
            src="test",
            payload={"data": "test"}
        )

        router.route_event_to_node(node, "handler_no_params", event)

        assert len(node.calls) == 1
        assert node.calls[0][0] == "handler_no_params"

    def test_route_event_to_node_one_param(self):
        """Test routing event to handler with one parameter (payload)"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        event = Event(
            event_id="test_event",
            topic="/test/topic",
            src="test",
            payload={"data": "test"}
        )

        router.route_event_to_node(node, "handler_one_param", event)

        assert len(node.calls) == 1
        assert node.calls[0][0] == "handler_one_param"
        assert node.calls[0][1] == {"data": "test"}

    def test_route_event_to_node_event_param(self):
        """Test routing event to handler with Event parameter"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        event = Event(
            event_id="test_event",
            topic="/test/topic",
            src="test",
            payload={"data": "test"}
        )

        router.route_event_to_node(node, "handler_event_param", event)

        assert len(node.calls) == 1
        assert node.calls[0][0] == "handler_event_param"
        assert isinstance(node.calls[0][1], Event)
        assert node.calls[0][1].event_id == "test_event"

    def test_route_event_handler_error(self):
        """Test handling errors in event handlers"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        event = Event(
            event_id="test_event",
            topic="/test/topic",
            src="test",
            payload={"data": "test"}
        )

        # Should not raise, but should handle error gracefully
        router.route_event_to_node(node, "handler_that_errors", event)

        # Handler errored so no calls were recorded
        assert len(node.calls) == 0

    def test_unregister_node(self):
        """Test unregistering all handlers for a node"""
        bus = MessageBus()
        node1 = MockNode()
        node2 = MockNode()
        node2.name = "MockNode2"
        nodes = {"MockNode": node1, "MockNode2": node2}
        router = EventRouter(bus, nodes)

        topic = Topic(name="/test/topic")
        router.register_subscription(
            Subscription(node_name="MockNode", topic=topic, handler_name="handler_one_param")
        )
        router.register_subscription(
            Subscription(node_name="MockNode2", topic=topic, handler_name="handler_one_param")
        )

        assert len(router.get_handlers_for_topic("/test/topic")) == 2

        # Unregister first node
        router.unregister_node("MockNode")

        handlers = router.get_handlers_for_topic("/test/topic")
        assert len(handlers) == 1
        assert handlers[0][0].name == "MockNode2"

    def test_get_handlers_for_topic(self):
        """Test getting handlers for a specific topic"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        topic = Topic(name="/test/topic")
        router.register_subscription(
            Subscription(node_name="MockNode", topic=topic, handler_name="handler_one_param")
        )

        handlers = router.get_handlers_for_topic("/test/topic")

        assert len(handlers) == 1
        assert handlers[0] == (node, "handler_one_param")

    def test_get_handlers_for_topic_empty(self):
        """Test getting handlers for topic with no handlers"""
        bus = MessageBus()
        nodes = {}
        router = EventRouter(bus, nodes)

        handlers = router.get_handlers_for_topic("/test/topic")

        assert len(handlers) == 0

    def test_get_all_handlers(self):
        """Test getting all registered handlers"""
        bus = MessageBus()
        node = MockNode()
        nodes = {"MockNode": node}
        router = EventRouter(bus, nodes)

        topic1 = Topic(name="/topic1")
        topic2 = Topic(name="/topic2")

        router.register_subscription(
            Subscription(node_name="MockNode", topic=topic1, handler_name="handler_one_param")
        )
        router.register_subscription(
            Subscription(node_name="MockNode", topic=topic2, handler_name="handler_no_params")
        )

        all_handlers = router.get_all_handlers()

        assert len(all_handlers) == 2
        assert "/topic1" in all_handlers
        assert "/topic2" in all_handlers
