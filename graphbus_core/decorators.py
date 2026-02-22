"""
Decorators for GraphBusNode methods and classes.

These decorators are the primary public API for annotating GraphBus agents.
They attach metadata that the build pipeline (Scanner, Extractor, Graph Builder)
reads to construct the agent graph and runtime subscriptions.

Quick reference::

    from graphbus_core.decorators import (
        schema_method,   # Type-safe method contracts
        subscribe,       # Pub/sub event handlers
        depends_on,      # Explicit inter-agent dependency edges
        agent_capability,# Build-mode capability declarations
        contract,        # Versioned API contracts for migration support
        schema_version,  # Per-handler schema version pinning
        auto_migrate,    # Automatic payload migration between schema versions
    )

"""

from functools import wraps
from typing import Callable, Any, Dict

__all__ = [
    "schema_method",
    "subscribe",
    "depends_on",
    "agent_capability",
    "contract",
    "schema_version",
    "auto_migrate",
]


def schema_method(input_schema: dict, output_schema: dict) -> Callable:
    """Declare typed input/output schema contracts for a node method.

    ``@schema_method`` serves two purposes:

    1. **Documentation** – makes the expected shapes of arguments and return
       values explicit and machine-readable.
    2. **Contract enforcement** – the :class:`~graphbus_core.runtime.contracts.ContractManager`
       uses the schema to validate payloads at runtime when contract validation
       is enabled (see ``RuntimeConfig.enable_validation``).

    The decorator attaches a ``_graphbus_schema`` attribute to the wrapped
    function.  The build pipeline reads this attribute during the extraction
    phase to include the schema in ``agents.json``.

    Args:
        input_schema: Mapping of argument names to their expected Python types
            (e.g. ``{"order_id": str, "amount": float}``).  Use ``Any`` from
            the ``typing`` module for untyped fields.
        output_schema: Mapping of return-value field names to their expected
            Python types (e.g. ``{"status": str, "transaction_id": str}``).

    Returns:
        A decorator that wraps the target method, preserving its signature and
        docstring while attaching ``_graphbus_schema`` and
        ``_graphbus_decorated`` attributes.

    Example::

        from graphbus_core.decorators import schema_method
        from graphbus_core.node_base import GraphBusNode

        class OrderService(GraphBusNode):

            @schema_method(
                input_schema={"order_id": str, "amount": float},
                output_schema={"status": str, "transaction_id": str},
            )
            def process_order(self, order_id: str, amount: float) -> dict:
                \"\"\"Process a payment order and return a transaction record.\"\"\"
                txn_id = f"txn-{order_id}"
                return {"status": "ok", "transaction_id": txn_id}

    Note:
        ``@schema_method`` does **not** perform runtime type-checking of
        arguments by itself.  Validation is opt-in via the ContractManager.
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


def subscribe(topic_name: str) -> Callable:
    """Register a node method as an event handler for a pub/sub topic.

    At runtime the :class:`~graphbus_core.runtime.event_router.EventRouter`
    inspects the handler's signature and calls it in one of three ways:

    * **No parameters** – ``handler()`` (besides ``self``).
    * **One parameter** – ``handler(payload: dict)`` where *payload* is the
      raw event payload dictionary.
    * **Two or more parameters** – ``handler(event: Event, ...)`` where *event*
      is the full :class:`~graphbus_core.model.message.Event` object.

    The decorator attaches a ``_graphbus_subscribe_topic`` attribute used by
    the Scanner/Extractor during the build phase to populate ``topics.json``.

    Args:
        topic_name: Fully-qualified topic path using slash notation, e.g.
            ``"/Order/Created"`` or ``"/Payment/Processed"``.  By convention
            topics follow the pattern ``"/<Domain>/<EventName>"``.

    Returns:
        A decorator that wraps the target method, preserving its signature and
        docstring while attaching ``_graphbus_subscribe_topic`` and
        ``_graphbus_decorated`` attributes.

    Raises:
        TypeError: If the decorated object is not callable (applied at import
            time when the class body is evaluated).

    Example::

        from graphbus_core.decorators import subscribe
        from graphbus_core.node_base import GraphBusNode

        class NotificationService(GraphBusNode):

            @subscribe("/Order/Created")
            def on_order_created(self, payload: dict) -> None:
                \"\"\"Send a confirmation email when an order is placed.\"\"\"
                order_id = payload["order_id"]
                print(f"Sending confirmation for order {order_id}")

            @subscribe("/Payment/Processed")
            def on_payment_processed(self, payload: dict) -> None:
                \"\"\"Send a receipt when payment is confirmed.\"\"\"
                print(f"Payment confirmed: {payload}")

    Note:
        A single method may **not** carry multiple ``@subscribe`` decorators.
        To subscribe to several topics use separate methods.  You may also
        list topics in the ``SUBSCRIBE`` class attribute for declarative
        subscriptions that are routed to ``handle_event``.
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


def depends_on(*dependencies: str) -> Callable:
    """Declare explicit dependency edges from one node to others in the graph.

    ``@depends_on`` is a **class decorator** (applied to a
    :class:`~graphbus_core.node_base.GraphBusNode` subclass, not a method).
    The Graph Builder uses these declarations to construct directed edges in the
    agent DAG, which determines topological execution order during the build
    negotiation phase and is visualised by ``graphbus inspect``.

    Dependencies declared via ``@depends_on`` are additive: applying the
    decorator multiple times (or combining it with ``@subscribe`` subscriptions)
    accumulates all edges.

    Args:
        *dependencies: One or more node names (strings) that this class depends
            on.  Names must match the ``class_name`` of the target
            ``GraphBusNode`` subclass as discovered by the Scanner.

    Returns:
        A class decorator that annotates the target class with a
        ``_graphbus_dependencies`` list attribute.

    Raises:
        TypeError: If applied to a non-class object.

    Example::

        from graphbus_core.decorators import depends_on, schema_method
        from graphbus_core.node_base import GraphBusNode

        @depends_on("InventoryService", "PaymentService")
        class OrderService(GraphBusNode):
            \"\"\"Orchestrates order fulfilment across Inventory and Payment.\"\"\"

            @schema_method(
                input_schema={"order_id": str},
                output_schema={"status": str},
            )
            def fulfil_order(self, order_id: str) -> dict:
                ...

    Note:
        ``@depends_on`` influences the **build-phase** negotiation order.  At
        runtime, message routing is governed solely by ``@subscribe``
        declarations and ``SUBSCRIBE`` class attributes.
    """
    def decorator(cls):
        # Attach dependency metadata to the class
        if not hasattr(cls, '_graphbus_dependencies'):
            cls._graphbus_dependencies = []
        cls._graphbus_dependencies.extend(dependencies)
        return cls

    return decorator


def agent_capability(capability: str) -> Callable:
    """Declare a named capability for an agent in Build Mode.

    Capabilities are free-form string labels that describe what kinds of
    code-improvement operations this agent is permitted to propose during LLM
    negotiation.  The Negotiation Engine can filter agents by capability to
    route proposals to agents that understand the relevant domain.

    ``@agent_capability`` is a **class decorator**.  Multiple capabilities can
    be declared by stacking the decorator.

    Args:
        capability: Human-readable capability label, e.g.
            ``"refactor_methods"``, ``"add_validation"``, or
            ``"optimise_queries"``.

    Returns:
        A class decorator that accumulates capability labels in the
        ``_graphbus_capabilities`` list attribute on the target class.

    Example::

        from graphbus_core.decorators import agent_capability
        from graphbus_core.node_base import GraphBusNode

        @agent_capability("refactor_methods")
        @agent_capability("add_validation")
        class DataService(GraphBusNode):
            \"\"\"Handles data ingestion with validation capabilities.\"\"\"
            ...

    Note:
        Capabilities are **Build Mode only** metadata.  They have no effect at
        runtime and are not included in ``agents.json`` artifacts.
    """
    def decorator(cls):
        if not hasattr(cls, '_graphbus_capabilities'):
            cls._graphbus_capabilities = []
        cls._graphbus_capabilities.append(capability)
        return cls

    return decorator


def contract(version: str, schema: Dict[str, Any]) -> Callable:
    """Attach a versioned API contract to a node class.

    A contract defines the stable, versioned interface of a
    :class:`~graphbus_core.node_base.GraphBusNode`: which methods it exposes,
    which topics it publishes to, and which topics it subscribes to.
    Contracts enable the
    :class:`~graphbus_core.runtime.contracts.ContractManager` and
    :class:`~graphbus_core.runtime.coherence.CoherenceTracker` to detect
    breaking changes between agent versions and enforce compatibility at
    runtime.

    ``@contract`` is a **class decorator**.

    Args:
        version: Semantic version string (e.g. ``"1.0.0"``, ``"2.1.3"``).
            Follows `SemVer <https://semver.org/>`_ conventions: incrementing
            the major version signals a breaking change.
        schema: Contract schema dictionary with the following optional keys:

            * ``"methods"`` (*dict*) – maps method names to their input/output
              schemas, e.g.::

                  "methods": {
                      "process_order": {
                          "input":  {"order_id": "str", "amount": "float"},
                          "output": {"status": "str", "transaction_id": "str"},
                      }
                  }

            * ``"publishes"`` (*dict*) – maps topic paths to expected payload
              schemas.
            * ``"subscribes"`` (*list*) – topic paths this agent subscribes to.
            * ``"description"`` (*str*) – human-readable description of the
              contract.

    Returns:
        A class decorator that attaches ``_graphbus_contract_version``,
        ``_graphbus_contract_schema``, and ``_graphbus_has_contract`` attributes
        to the target class.

    Example::

        from graphbus_core.decorators import contract
        from graphbus_core.node_base import GraphBusNode

        @contract(
            version="2.0.0",
            schema={
                "methods": {
                    "process_order": {
                        "input":  {"order_id": "str", "amount": "float"},
                        "output": {"status": "str", "transaction_id": "str"},
                    }
                },
                "publishes": {
                    "/Order/Processed": {
                        "payload": {"order_id": "str", "status": "str"}
                    }
                },
                "subscribes": ["/Order/Created"],
                "description": "Order processing service — v2 API",
            },
        )
        class OrderProcessor(GraphBusNode):
            ...

    Note:
        Contract schemas are persisted alongside build artifacts in
        ``.graphbus/contracts/`` and compared across builds to detect drift.
        See ``graphbus contract`` CLI command and
        :class:`~graphbus_core.runtime.migrations.MigrationEngine` for
        migration tooling.
    """
    def decorator(cls):
        # Attach contract metadata to the class
        cls._graphbus_contract_version = version
        cls._graphbus_contract_schema = schema
        cls._graphbus_has_contract = True
        return cls

    return decorator


def schema_version(version: str) -> Callable:
    """Pin a handler method to a specific schema version for schema-aware routing.

    When combined with ``@subscribe``, ``@schema_version`` tells the
    :class:`~graphbus_core.runtime.event_router.EventRouter` that this handler
    expects events whose payload conforms to the given schema version.  The
    runtime can use this to filter events or to trigger automatic migration
    before dispatching (see ``@auto_migrate``).

    Args:
        version: Schema version string this handler expects, e.g. ``"1.0.0"``.

    Returns:
        A decorator that attaches ``_graphbus_schema_version`` and
        ``_graphbus_decorated`` attributes to the wrapped method.

    Example::

        from graphbus_core.decorators import subscribe, schema_version
        from graphbus_core.node_base import GraphBusNode

        class UserService(GraphBusNode):

            @subscribe("/User/Updated")
            @schema_version("1.0.0")
            def on_user_updated_v1(self, payload: dict) -> None:
                \"\"\"Handle User/Updated events using the v1.0.0 schema.\"\"\"
                # payload is guaranteed to conform to v1.0.0
                print(f"User {payload['user_id']} updated (legacy handler)")

    Note:
        ``@schema_version`` is most useful alongside ``@auto_migrate`` to build
        a migration chain.  Without ``@auto_migrate``, the version annotation
        is purely informational and is **not** enforced at runtime by default.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._graphbus_schema_version = version
        wrapper._graphbus_decorated = True

        return wrapper

    return decorator


def auto_migrate(from_version: str, to_version: str) -> Callable:
    """Enable automatic payload migration before a handler is invoked.

    When the runtime receives an event whose schema version matches
    *from_version*, it will run the registered migration path
    ``from_version → to_version`` via the
    :class:`~graphbus_core.runtime.migrations.MigrationEngine` **before**
    dispatching the payload to the decorated handler.  This allows handlers to
    always operate on a single, up-to-date schema without embedding version
    branching logic in application code.

    ``@auto_migrate`` is typically stacked with ``@subscribe`` and (optionally)
    ``@schema_version``::

        @subscribe("/Order/Created")
        @schema_version("2.0.0")
        @auto_migrate(from_version="1.0.0", to_version="2.0.0")
        def on_order_created(self, payload):
            ...  # payload is always in v2.0.0 format

    Args:
        from_version: Schema version of the incoming event payload before
            migration (e.g. ``"1.0.0"``).
        to_version: Schema version that the handler expects after migration
            (e.g. ``"2.0.0"``).

    Returns:
        A decorator that attaches ``_graphbus_auto_migrate``,
        ``_graphbus_migrate_from``, ``_graphbus_migrate_to``, and
        ``_graphbus_decorated`` attributes to the wrapped method.

    Raises:
        ValueError: Raised by the MigrationEngine at runtime if no migration
            path exists from *from_version* to *to_version*.

    Example::

        from graphbus_core.decorators import subscribe, schema_version, auto_migrate
        from graphbus_core.node_base import GraphBusNode

        class InventoryService(GraphBusNode):
            \"\"\"Subscribes to Order events and auto-migrates legacy payloads.\"\"\"

            @subscribe("/Order/Created")
            @schema_version("2.0.0")
            @auto_migrate(from_version="1.0.0", to_version="2.0.0")
            def on_order_created(self, payload: dict) -> None:
                # payload["customer_id"] is available (added in v2.0.0)
                # even if the original event was published using v1.0.0 schema
                print(f"Order {payload['order_id']} from customer {payload['customer_id']}")

    Note:
        Migrations must be registered with the MigrationEngine using
        ``graphbus migrate register`` or programmatically.  See
        ``graphbus_core.runtime.migrations`` for the migration DSL.
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
