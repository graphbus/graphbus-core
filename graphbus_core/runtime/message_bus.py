"""
Message Bus - Simple pub/sub routing for Runtime Mode
"""

from typing import Dict, List, Callable, Any
from collections import defaultdict, deque

from graphbus_core.model.message import Event, generate_id
from graphbus_core.model.topic import Topic


class MessageBus:
    """
    Simple synchronous message bus for Runtime Mode.

    Provides:
    - Topic-based pub/sub messaging
    - Subscription management
    - Synchronous event dispatch (no LLM, no negotiation)
    - Message history tracking
    """

    def __init__(self):
        """Initialize message bus."""
        # topic_name -> list of (handler, subscriber_name)
        self._subscriptions: Dict[str, List[tuple[Callable, str]]] = defaultdict(list)

        # Message history for debugging/monitoring.
        # deque(maxlen=N) automatically evicts the oldest entry on append
        # when full — O(1) vs the O(n) list.pop(0) that a plain list requires.
        self._max_history = 1000  # Keep last 1000 events
        self._message_history: deque[Event] = deque(maxlen=self._max_history)

        # Statistics
        self._stats = {
            "messages_published": 0,
            "messages_delivered": 0,
            "errors": 0
        }

    def subscribe(self, topic: str, handler: Callable, subscriber_name: str = "unknown") -> None:
        """
        Subscribe a handler to a topic.

        Args:
            topic: Topic name (e.g., "/Order/Created")
            handler: Callable that accepts (event: Event)
            subscriber_name: Name of subscriber (for debugging)
        """
        if not callable(handler):
            raise ValueError(f"Handler must be callable, got {type(handler)}")

        self._subscriptions[topic].append((handler, subscriber_name))
        print(f"[MessageBus] {subscriber_name} subscribed to {topic}")

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        """
        Unsubscribe a handler from a topic.

        Args:
            topic: Topic name
            handler: Handler to remove
        """
        if topic in self._subscriptions:
            self._subscriptions[topic] = [
                (h, name) for h, name in self._subscriptions[topic] if h != handler
            ]

    def publish(self, topic: str, payload: Dict[str, Any], source: str = "system") -> Event:
        """
        Publish a message to a topic.

        Args:
            topic: Topic name
            payload: Event payload data
            source: Source of the event (node name)

        Returns:
            Created Event object
        """
        # Create event
        event = Event(
            event_id=generate_id("event_"),
            topic=topic,  # Event expects string, not Topic object
            src=source,   # Event uses 'src' not 'source'
            payload=payload
        )

        # Track in history
        self._add_to_history(event)

        # Update stats
        self._stats["messages_published"] += 1

        # Dispatch to subscribers
        self.dispatch_event(event)

        return event

    def dispatch_event(self, event: Event) -> None:
        """
        Dispatch an event to all subscribers.

        Args:
            event: Event to dispatch
        """
        topic = event.topic  # Event.topic is a string
        handlers = self._subscriptions.get(topic, [])

        if not handlers:
            print(f"[MessageBus] No subscribers for topic: {topic}")
            return

        print(f"[MessageBus] Dispatching {topic} to {len(handlers)} subscriber(s)")

        for handler, subscriber_name in handlers:
            try:
                # Call handler synchronously
                handler(event)
                self._stats["messages_delivered"] += 1
                print(f"[MessageBus] ✓ Delivered to {subscriber_name}")
            except Exception as e:
                self._stats["errors"] += 1
                print(f"[MessageBus] ✗ Error in {subscriber_name}: {e}")

    def get_subscribers(self, topic: str) -> List[str]:
        """
        Get list of subscriber names for a topic.

        Args:
            topic: Topic name

        Returns:
            List of subscriber names
        """
        handlers = self._subscriptions.get(topic, [])
        return [name for _, name in handlers]

    def get_all_topics(self) -> List[str]:
        """
        Get all topics that have subscribers.

        Returns:
            List of topic names
        """
        return list(self._subscriptions.keys())

    def _add_to_history(self, event: Event) -> None:
        """Add event to history; deque(maxlen) evicts the oldest entry automatically."""
        self._message_history.append(event)

    def get_message_history(self, limit: int = 100) -> List[Event]:
        """
        Get recent message history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent Event objects (newest first)
        """
        # deque doesn't support slicing — convert to list first
        history = list(self._message_history)
        return list(reversed(history[-limit:]))

    def get_stats(self) -> Dict[str, int]:
        """
        Get message bus statistics.

        Returns:
            Dict with statistics
        """
        return {
            **self._stats,
            "total_subscriptions": sum(len(handlers) for handlers in self._subscriptions.values()),
            "topics_with_subscribers": len(self._subscriptions),
            "history_size": len(self._message_history)
        }

    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "messages_published": 0,
            "messages_delivered": 0,
            "errors": 0
        }

    def __repr__(self) -> str:
        """String representation of message bus state."""
        return (
            f"MessageBus("
            f"topics={len(self._subscriptions)}, "
            f"subscriptions={sum(len(h) for h in self._subscriptions.values())}, "
            f"published={self._stats['messages_published']}, "
            f"delivered={self._stats['messages_delivered']})"
        )
