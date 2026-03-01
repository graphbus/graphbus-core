"""
Namespaced Message Bus — extends MessageBus with namespace isolation.

Agents in different namespaces cannot see each other's messages unless
explicitly bridged.
"""

from collections import defaultdict
from typing import Callable, Optional

from graphbus_core.runtime.message_bus import MessageBus
from graphbus_core.model.message import Event


class NamespacedMessageBus:
    """Message bus with namespace isolation.

    Each namespace gets its own isolated bus. Cross-namespace communication
    requires explicit bridges.
    """

    def __init__(self):
        self._buses: dict[str, MessageBus] = {}
        self._bridges: list[dict] = []  # [{from_ns, from_topic, to_ns, to_topic}]
        self._default_namespace = "default"

    def get_bus(self, namespace: str = None) -> MessageBus:
        """Get or create the message bus for a namespace."""
        ns = namespace or self._default_namespace
        if ns not in self._buses:
            self._buses[ns] = MessageBus()
        return self._buses[ns]

    def subscribe(
        self,
        topic: str,
        handler: Callable,
        subscriber_name: str = "unknown",
        namespace: str = None,
    ) -> None:
        """Subscribe to a topic within a namespace."""
        bus = self.get_bus(namespace)
        bus.subscribe(topic, handler, subscriber_name)

    def publish(
        self,
        topic: str,
        data: dict,
        publisher_name: str = "unknown",
        namespace: str = None,
    ) -> None:
        """Publish to a topic within a namespace.

        Also forwards to bridged namespaces if configured.
        """
        ns = namespace or self._default_namespace
        bus = self.get_bus(ns)
        event = Event(topic=topic, data=data, source=publisher_name)
        bus.publish(topic, data, publisher_name)

        # Check bridges
        for bridge in self._bridges:
            if bridge["from_ns"] == ns and bridge["from_topic"] == topic:
                target_bus = self.get_bus(bridge["to_ns"])
                target_bus.publish(
                    bridge["to_topic"],
                    data,
                    f"{publisher_name}@{ns}",
                )

    def add_bridge(
        self,
        from_namespace: str,
        from_topic: str,
        to_namespace: str,
        to_topic: str = None,
    ) -> None:
        """Bridge a topic from one namespace to another.

        Messages published to from_topic in from_namespace will be
        forwarded to to_topic in to_namespace.
        """
        self._bridges.append({
            "from_ns": from_namespace,
            "from_topic": from_topic,
            "to_ns": to_namespace,
            "to_topic": to_topic or from_topic,
        })

    def remove_bridge(self, from_namespace: str, from_topic: str, to_namespace: str) -> bool:
        """Remove a bridge."""
        for i, b in enumerate(self._bridges):
            if b["from_ns"] == from_namespace and b["from_topic"] == from_topic and b["to_ns"] == to_namespace:
                self._bridges.pop(i)
                return True
        return False

    @property
    def namespaces(self) -> list[str]:
        """List all active namespaces."""
        return list(self._buses.keys())

    @property
    def bridges(self) -> list[dict]:
        """List all configured bridges."""
        return list(self._bridges)

    def get_stats(self) -> dict:
        """Get stats across all namespaces."""
        return {
            "namespaces": {
                ns: bus._stats for ns, bus in self._buses.items()
            },
            "bridge_count": len(self._bridges),
        }
