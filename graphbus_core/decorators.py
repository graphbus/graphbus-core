"""
Decorators for GraphBusNode methods
"""

from functools import wraps
from typing import Callable, Any


def schema_method(input_schema: dict, output_schema: dict):
    """
    Decorator to mark a method with input/output schema contracts.

    Args:
        input_schema: dict mapping field names to types (e.g. {"name": str, "age": int})
        output_schema: dict mapping field names to types

    Example:
        @schema_method(
            input_schema={"message": str},
            output_schema={"status": str}
        )
        def send_message(self, message: str):
            return {"status": "sent"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach schema metadata to the function
        wrapper._graphbus_schema = {
            "input": input_schema,
            "output": output_schema,
        }
        wrapper._graphbus_decorated = True

        return wrapper

    return decorator


def subscribe(topic_name: str):
    """
    Decorator to mark a method as a subscriber to a topic.

    Args:
        topic_name: Name of the topic to subscribe to (e.g. "/Order/Created")

    Example:
        @subscribe("/Order/Created")
        def on_order_created(self, event):
            print(f"Order created: {event}")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach subscription metadata to the function
        wrapper._graphbus_subscribe_topic = topic_name
        wrapper._graphbus_decorated = True

        return wrapper

    return decorator


def depends_on(*dependencies: str):
    """
    Decorator to explicitly declare dependencies on other nodes.

    Args:
        dependencies: Names of nodes this node depends on

    Example:
        @depends_on("InventoryService", "PaymentService")
        class OrderService(GraphBusNode):
            ...
    """
    def decorator(cls):
        # Attach dependency metadata to the class
        if not hasattr(cls, '_graphbus_dependencies'):
            cls._graphbus_dependencies = []
        cls._graphbus_dependencies.extend(dependencies)
        return cls

    return decorator


def agent_capability(capability: str):
    """
    Decorator to declare agent capabilities in Build Mode.

    Args:
        capability: Name of capability (e.g. "refactor_methods", "add_validation")

    Example:
        @agent_capability("refactor_methods")
        class MyService(GraphBusNode):
            ...
    """
    def decorator(cls):
        if not hasattr(cls, '_graphbus_capabilities'):
            cls._graphbus_capabilities = []
        cls._graphbus_capabilities.append(capability)
        return cls

    return decorator
