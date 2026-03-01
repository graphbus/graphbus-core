"""
Unit tests for MessageBus
"""

import pytest
from graphbus_core.runtime.message_bus import MessageBus
from graphbus_core.model.message import Event


class TestMessageBus:
    """Tests for MessageBus"""

    def test_initialization(self):
        """Test MessageBus initialization"""
        bus = MessageBus()

        assert len(bus._subscriptions) == 0
        assert len(bus._message_history) == 0
        assert bus._stats["messages_published"] == 0

    def test_subscribe(self):
        """Test subscribing to a topic"""
        bus = MessageBus()
        called = []

        def handler(event):
            called.append(event)

        bus.subscribe("/test/topic", handler, "TestSubscriber")

        assert "/test/topic" in bus._subscriptions
        assert len(bus._subscriptions["/test/topic"]) == 1

    def test_subscribe_invalid_handler(self):
        """Test subscribing with non-callable handler"""
        bus = MessageBus()

        with pytest.raises(ValueError):
            bus.subscribe("/test/topic", "not_callable", "TestSubscriber")

    def test_unsubscribe(self):
        """Test unsubscribing from a topic"""
        bus = MessageBus()

        def handler(event):
            pass

        bus.subscribe("/test/topic", handler, "TestSubscriber")
        assert len(bus._subscriptions["/test/topic"]) == 1

        bus.unsubscribe("/test/topic", handler)
        assert len(bus._subscriptions["/test/topic"]) == 0

    def test_publish(self):
        """Test publishing a message"""
        bus = MessageBus()
        received_events = []

        def handler(event):
            received_events.append(event)

        bus.subscribe("/test/topic", handler, "TestSubscriber")

        # Publish message
        event = bus.publish("/test/topic", {"data": "test"}, source="test")

        # Verify event was created
        assert isinstance(event, Event)
        assert event.topic == "/test/topic"
        assert event.payload == {"data": "test"}
        assert event.src == "test"

        # Verify handler was called
        assert len(received_events) == 1
        assert received_events[0] == event

        # Verify stats
        assert bus._stats["messages_published"] == 1
        assert bus._stats["messages_delivered"] == 1

    def test_publish_no_subscribers(self):
        """Test publishing to topic with no subscribers"""
        bus = MessageBus()

        event = bus.publish("/empty/topic", {"data": "test"})

        assert isinstance(event, Event)
        assert bus._stats["messages_published"] == 1
        assert bus._stats["messages_delivered"] == 0

    def test_publish_multiple_subscribers(self):
        """Test publishing to topic with multiple subscribers"""
        bus = MessageBus()
        received_1 = []
        received_2 = []

        def handler1(event):
            received_1.append(event)

        def handler2(event):
            received_2.append(event)

        bus.subscribe("/test/topic", handler1, "Subscriber1")
        bus.subscribe("/test/topic", handler2, "Subscriber2")

        event = bus.publish("/test/topic", {"data": "test"})

        # Both handlers should receive the event
        assert len(received_1) == 1
        assert len(received_2) == 1
        assert bus._stats["messages_delivered"] == 2

    def test_handler_error(self):
        """Test handling errors in subscriber"""
        bus = MessageBus()

        def broken_handler(event):
            raise ValueError("Test error")

        bus.subscribe("/test/topic", broken_handler, "BrokenSubscriber")

        # Should not raise, but should track error
        bus.publish("/test/topic", {"data": "test"})

        assert bus._stats["errors"] == 1

    def test_get_subscribers(self):
        """Test getting subscribers for a topic"""
        bus = MessageBus()

        def handler1(event):
            pass

        def handler2(event):
            pass

        bus.subscribe("/test/topic", handler1, "Sub1")
        bus.subscribe("/test/topic", handler2, "Sub2")

        subscribers = bus.get_subscribers("/test/topic")
        assert len(subscribers) == 2
        assert "Sub1" in subscribers
        assert "Sub2" in subscribers

    def test_get_all_topics(self):
        """Test getting all topics with subscribers"""
        bus = MessageBus()

        def handler(event):
            pass

        bus.subscribe("/topic1", handler, "Sub1")
        bus.subscribe("/topic2", handler, "Sub2")

        topics = bus.get_all_topics()
        assert len(topics) == 2
        assert "/topic1" in topics
        assert "/topic2" in topics

    def test_message_history(self):
        """Test message history tracking"""
        bus = MessageBus()

        # Publish several messages
        bus.publish("/topic1", {"msg": 1})
        bus.publish("/topic2", {"msg": 2})
        bus.publish("/topic3", {"msg": 3})

        history = bus.get_message_history()
        assert len(history) == 3

        # History should be newest first
        assert history[0].payload["msg"] == 3
        assert history[1].payload["msg"] == 2
        assert history[2].payload["msg"] == 1

    def test_message_history_limit(self):
        """Test message history respects max size"""
        bus = MessageBus(max_history=5)

        # Publish more messages than max
        for i in range(10):
            bus.publish(f"/topic{i}", {"msg": i})

        # Should only keep last 5
        assert len(bus._message_history) == 5

    def test_get_stats(self):
        """Test getting statistics"""
        bus = MessageBus()

        def handler(event):
            pass

        bus.subscribe("/test", handler, "Sub1")
        bus.publish("/test", {"data": "test"})

        stats = bus.get_stats()

        assert stats["messages_published"] == 1
        assert stats["messages_delivered"] == 1
        assert stats["errors"] == 0
        assert stats["total_subscriptions"] == 1
        assert stats["topics_with_subscribers"] == 1

    def test_clear_history(self):
        """Test clearing message history"""
        bus = MessageBus()
        bus.publish("/test", {"data": "test"})

        assert len(bus._message_history) == 1

        bus.clear_history()
        assert len(bus._message_history) == 0

    def test_reset_stats(self):
        """Test resetting statistics"""
        bus = MessageBus()
        bus.publish("/test", {"data": "test"})

        assert bus._stats["messages_published"] == 1

        bus.reset_stats()
        assert bus._stats["messages_published"] == 0
        assert bus._stats["messages_delivered"] == 0
        assert bus._stats["errors"] == 0
