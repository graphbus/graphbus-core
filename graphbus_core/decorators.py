"""
Decorators for GraphBusNode methods
"""

from functools import wraps
from typing import Callable, Any, Dict


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


def contract(version: str, schema: Dict[str, Any]):
    """
    Decorator to define an agent's API contract with versioning.

    Args:
        version: Semantic version (e.g., "1.0.0", "2.1.3")
        schema: Contract schema defining methods, publishes, subscribes

    Example:
        @contract(version="2.0.0", schema={
            "methods": {
                "process_order": {
                    "input": {"order_id": "str", "amount": "float"},
                    "output": {"status": "str", "transaction_id": "str"}
                }
            },
            "publishes": {
                "/Order/Processed": {
                    "payload": {"order_id": "str", "status": "str"}
                }
            },
            "subscribes": ["/Order/Created"],
            "description": "Order processing service"
        })
        class OrderProcessor(GraphBusNode):
            ...
    """
    def decorator(cls):
        # Attach contract metadata to the class
        cls._graphbus_contract_version = version
        cls._graphbus_contract_schema = schema
        cls._graphbus_has_contract = True
        return cls

    return decorator


def schema_version(version: str):
    """
    Decorator to mark a method/handler with a specific schema version.
    Used for schema-aware filtering and auto-migration.

    Args:
        version: Schema version this method expects (e.g., "1.0.0")

    Example:
        @subscribe("/Order/Created")
        @schema_version("1.0.0")
        def on_order_created(self, event):
            # This handler expects v1.0.0 schema
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._graphbus_schema_version = version
        wrapper._graphbus_decorated = True

        return wrapper

    return decorator


def auto_migrate(from_version: str, to_version: str):
    """
    Decorator to enable automatic payload migration for a handler.

    Args:
        from_version: Source schema version
        to_version: Target schema version

    Example:
        @subscribe("/User/Updated")
        @auto_migrate(from_version="1.0.0", to_version="2.0.0")
        def on_user_updated(self, payload):
            # Payload will be automatically migrated from v1 to v2
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._graphbus_auto_migrate = True
        wrapper._graphbus_migrate_from = from_version
        wrapper._graphbus_migrate_to = to_version
        wrapper._graphbus_decorated = True

        return wrapper

    return decorator
