"""
Event Router - Routes events to node handlers in Runtime Mode
"""

from typing import Dict, List, Callable
import inspect

from graphbus_core.model.message import Event
from graphbus_core.model.topic import Subscription
from graphbus_core.node_base import GraphBusNode
from graphbus_core.runtime.message_bus import MessageBus


class EventRouter:
    """
    Routes events from MessageBus to appropriate node handlers.

    Responsibilities:
    - Connect node subscriptions to message bus
    - Find and invoke handler methods on nodes
    - Handle errors gracefully
    - Support @subscribe decorator and SUBSCRIBE class attribute
    """

    def __init__(self, bus: MessageBus, nodes: Dict[str, GraphBusNode]):
        """
        Initialize event router.

        Args:
            bus: MessageBus instance
            nodes: Dict of node_name -> GraphBusNode instance
        """
        self.bus = bus
        self.nodes = nodes
        self._handlers: Dict[str, List[tuple[GraphBusNode, str]]] = {}  # topic -> [(node, method_name)]

    def register_subscriptions(self, subscriptions: List[Subscription]) -> None:
        """
        Register all subscriptions from build artifacts.

        Args:
            subscriptions: List of Subscription objects from artifacts
        """
        for subscription in subscriptions:
            self.register_subscription(subscription)

    def register_subscription(self, subscription: Subscription) -> None:
        """
        Register a single subscription.

        Args:
            subscription: Subscription object
        """
        topic = subscription.topic.name
        node_name = subscription.node_name
        handler_name = subscription.handler_name

        # Get the node instance
        if node_name not in self.nodes:
            print(f"[EventRouter] Warning: Node '{node_name}' not found, skipping subscription to {topic}")
            return

        node = self.nodes[node_name]

        # Find the handler method
        handler_method = getattr(node, handler_name, None)
        if handler_method is None:
            print(f"[EventRouter] Warning: Handler '{handler_name}' not found on {node_name}")
            return

        if not callable(handler_method):
            print(f"[EventRouter] Warning: Handler '{handler_name}' on {node_name} is not callable")
            return

        # Track handler
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append((node, handler_name))

        # Create wrapper to route to the handler
        def event_handler(event: Event):
            self.route_event_to_node(node, handler_name, event)

        # Subscribe to message bus
        self.bus.subscribe(topic, event_handler, subscriber_name=node_name)

        print(f"[EventRouter] Registered {node_name}.{handler_name}() for {topic}")

    def route_event_to_node(self, node: GraphBusNode, handler_name: str, event: Event) -> None:
        """
        Route an event to a specific node handler.

        Args:
            node: GraphBusNode instance
            handler_name: Name of handler method
            event: Event to deliver
        """
        try:
            handler = getattr(node, handler_name)

            # Inspect handler signature to determine how to call it
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())

            # Remove 'self' parameter (it's a bound method)
            # The handler is already bound to the node instance
            if len(params) == 0:
                # No parameters (just self, already bound)
                handler()
            elif len(params) == 1:
                # One parameter: pass payload dict by default
                # (Most handlers expect the payload, not the Event object)
                handler(event.payload)
            else:
                # Multiple parameters or unclear - default to passing event
                handler(event)

        except Exception as e:
            print(f"[EventRouter] Error executing {node.name}.{handler_name}(): {e}")
            import traceback
            traceback.print_exc()

    def get_handlers_for_topic(self, topic: str) -> List[tuple[GraphBusNode, str]]:
        """
        Get all handlers registered for a topic.

        Args:
            topic: Topic name

        Returns:
            List of (node, handler_name) tuples
        """
        return self._handlers.get(topic, [])

    def get_all_handlers(self) -> Dict[str, List[tuple[GraphBusNode, str]]]:
        """
        Get all registered handlers.

        Returns:
            Dict of topic -> [(node, handler_name)]
        """
        return self._handlers.copy()

    def unregister_node(self, node_name: str) -> None:
        """
        Unregister all handlers for a specific node.

        Args:
            node_name: Name of node to unregister
        """
        for topic, handlers in list(self._handlers.items()):
            self._handlers[topic] = [
                (node, handler) for node, handler in handlers
                if node.name != node_name
            ]
            # Remove topic if no handlers left
            if not self._handlers[topic]:
                del self._handlers[topic]

    def __repr__(self) -> str:
        """String representation of router state."""
        total_handlers = sum(len(handlers) for handlers in self._handlers.values())
        return (
            f"EventRouter("
            f"topics={len(self._handlers)}, "
            f"handlers={total_handlers}, "
            f"nodes={len(self.nodes)})"
        )
