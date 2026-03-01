"""
Unit tests for graphbus_core.decorators

Covers all public decorators:
- schema_method
- subscribe
- depends_on
- agent_capability
- contract
- schema_version
- auto_migrate
"""

import pytest
from functools import wraps

from graphbus_core.decorators import (
    schema_method,
    subscribe,
    depends_on,
    agent_capability,
    contract,
    schema_version,
    auto_migrate,
)
from graphbus_core.node_base import GraphBusNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _PlainNode(GraphBusNode):
    """Minimal concrete node used by several tests."""

    def plain_method(self):
        return "plain"


# ---------------------------------------------------------------------------
# schema_method
# ---------------------------------------------------------------------------

class TestSchemaMethod:
    """Tests for @schema_method decorator."""

    def test_attaches_schema_metadata(self):
        """Decorated function should carry _graphbus_schema."""

        class OrderService(GraphBusNode):
            @schema_method(
                input_schema={"order_id": str, "amount": float},
                output_schema={"status": str, "transaction_id": str},
            )
            def process_order(self, order_id: str, amount: float) -> dict:
                return {"status": "ok", "transaction_id": f"txn-{order_id}"}

        method = OrderService.process_order
        assert hasattr(method, "_graphbus_schema")
        assert method._graphbus_schema["input"] == {"order_id": str, "amount": float}
        assert method._graphbus_schema["output"] == {"status": str, "transaction_id": str}

    def test_sets_decorated_flag(self):
        """Decorated function should set _graphbus_decorated = True."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={}, output_schema={"msg": str})
            def greet(self):
                return {"msg": "hello"}

        assert Svc.greet._graphbus_decorated is True

    def test_preserves_function_name(self):
        """@wraps should preserve __name__."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={"x": int}, output_schema={"y": int})
            def double(self, x: int) -> dict:
                return {"y": x * 2}

        assert Svc.double.__name__ == "double"

    def test_preserves_docstring(self):
        """@wraps should preserve __doc__."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={}, output_schema={})
            def do_thing(self):
                """Does a thing."""
                pass

        assert "Does a thing" in Svc.do_thing.__doc__

    def test_method_still_callable(self):
        """The decorated method must still execute normally."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={"x": int}, output_schema={"result": int})
            def square(self, x: int) -> dict:
                return {"result": x ** 2}

        svc = Svc()
        assert svc.square(4) == {"result": 16}

    def test_empty_schemas_accepted(self):
        """Empty input/output schemas should be accepted without error."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={}, output_schema={})
            def noop(self):
                pass

        assert Svc.noop._graphbus_schema["input"] == {}
        assert Svc.noop._graphbus_schema["output"] == {}

    def test_discovered_by_get_schema_methods(self):
        """GraphBusNode.get_schema_methods() should include the decorated method."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={"n": int}, output_schema={"result": int})
            def compute(self, n: int) -> dict:
                return {"result": n}

        methods = Svc.get_schema_methods()
        assert "compute" in methods
        assert methods["compute"]["input"] == {"n": int}

    def test_multiple_schema_methods_on_one_class(self):
        """Multiple @schema_method decorators on the same class all appear."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={"a": int}, output_schema={"b": int})
            def method_a(self, a: int) -> dict:
                return {"b": a}

            @schema_method(input_schema={"x": str}, output_schema={"y": str})
            def method_b(self, x: str) -> dict:
                return {"y": x}

        methods = Svc.get_schema_methods()
        assert "method_a" in methods
        assert "method_b" in methods


# ---------------------------------------------------------------------------
# subscribe
# ---------------------------------------------------------------------------

class TestSubscribe:
    """Tests for @subscribe decorator."""

    def test_attaches_topic_metadata(self):
        """Decorated method should carry _graphbus_subscribe_topic."""

        class Svc(GraphBusNode):
            @subscribe("/Order/Created")
            def on_order_created(self, payload: dict) -> None:
                pass

        assert Svc.on_order_created._graphbus_subscribe_topic == "/Order/Created"

    def test_sets_decorated_flag(self):
        """Decorated method should set _graphbus_decorated = True."""

        class Svc(GraphBusNode):
            @subscribe("/Payment/Processed")
            def on_payment(self, payload: dict) -> None:
                pass

        assert Svc.on_payment._graphbus_decorated is True

    def test_preserves_function_name(self):
        class Svc(GraphBusNode):
            @subscribe("/User/Updated")
            def on_user_updated(self, payload: dict) -> None:
                pass

        assert Svc.on_user_updated.__name__ == "on_user_updated"

    def test_preserves_docstring(self):
        class Svc(GraphBusNode):
            @subscribe("/Item/Deleted")
            def on_item_deleted(self, payload: dict) -> None:
                """Handle item deletion events."""
                pass

        assert "Handle item deletion" in Svc.on_item_deleted.__doc__

    def test_method_still_callable(self):
        """The decorated handler must still execute normally."""
        results = []

        class Svc(GraphBusNode):
            @subscribe("/Test/Event")
            def on_test(self, payload: dict) -> None:
                results.append(payload)

        svc = Svc()
        svc.on_test({"key": "value"})
        assert results == [{"key": "value"}]

    def test_discovered_by_get_subscriptions(self):
        """GraphBusNode.get_subscriptions() should include the subscribed topic."""

        class Svc(GraphBusNode):
            @subscribe("/Foo/Bar")
            def on_foo(self, payload: dict) -> None:
                pass

        assert "/Foo/Bar" in Svc.get_subscriptions()

    def test_multiple_handlers_different_topics(self):
        """Each @subscribe on a separate method registers its own topic."""

        class Svc(GraphBusNode):
            @subscribe("/Alpha/Done")
            def on_alpha(self, payload: dict) -> None:
                pass

            @subscribe("/Beta/Done")
            def on_beta(self, payload: dict) -> None:
                pass

        subs = Svc.get_subscriptions()
        assert "/Alpha/Done" in subs
        assert "/Beta/Done" in subs

    def test_combined_with_schema_method(self):
        """@subscribe and @schema_method can coexist on different methods."""

        class Svc(GraphBusNode):
            @schema_method(input_schema={}, output_schema={"msg": str})
            def produce(self):
                return {"msg": "hi"}

            @subscribe("/Msg/Sent")
            def on_msg_sent(self, payload: dict) -> None:
                pass

        assert "produce" in Svc.get_schema_methods()
        assert "/Msg/Sent" in Svc.get_subscriptions()


# ---------------------------------------------------------------------------
# depends_on
# ---------------------------------------------------------------------------

class TestDependsOn:
    """Tests for @depends_on class decorator."""

    def test_attaches_dependencies(self):
        """Decorated class should have _graphbus_dependencies."""

        @depends_on("InventoryService", "PaymentService")
        class OrderService(GraphBusNode):
            pass

        assert "InventoryService" in OrderService._graphbus_dependencies
        assert "PaymentService" in OrderService._graphbus_dependencies

    def test_single_dependency(self):
        @depends_on("AuthService")
        class UserService(GraphBusNode):
            pass

        assert "AuthService" in UserService._graphbus_dependencies

    def test_discovered_by_get_dependencies(self):
        @depends_on("LoggingService")
        class ReportService(GraphBusNode):
            pass

        deps = ReportService.get_dependencies()
        assert "LoggingService" in deps

    def test_stacking_accumulates_dependencies(self):
        """Stacking @depends_on twice accumulates all dependencies."""

        @depends_on("ServiceC")
        @depends_on("ServiceA", "ServiceB")
        class CompositeService(GraphBusNode):
            pass

        deps = CompositeService.get_dependencies()
        assert "ServiceA" in deps
        assert "ServiceB" in deps
        assert "ServiceC" in deps

    def test_does_not_affect_other_classes(self):
        """@depends_on should only annotate the decorated class."""

        @depends_on("Dep1")
        class ServiceWithDep(GraphBusNode):
            pass

        class ServiceWithoutDep(GraphBusNode):
            pass

        assert "Dep1" in ServiceWithDep.get_dependencies()
        assert "Dep1" not in ServiceWithoutDep.get_dependencies()

    def test_returns_same_class(self):
        """@depends_on must return the class itself (not a wrapper)."""

        @depends_on("SomeDep")
        class MyService(GraphBusNode):
            pass

        assert MyService.__name__ == "MyService"


# ---------------------------------------------------------------------------
# agent_capability
# ---------------------------------------------------------------------------

class TestAgentCapability:
    """Tests for @agent_capability class decorator."""

    def test_attaches_capability(self):
        @agent_capability("refactor_methods")
        class DataService(GraphBusNode):
            pass

        assert "refactor_methods" in DataService._graphbus_capabilities

    def test_stacking_accumulates_capabilities(self):
        @agent_capability("optimise_queries")
        @agent_capability("add_validation")
        @agent_capability("refactor_methods")
        class DataService(GraphBusNode):
            pass

        caps = DataService.get_capabilities()
        assert "refactor_methods" in caps
        assert "add_validation" in caps
        assert "optimise_queries" in caps

    def test_discovered_by_get_capabilities(self):
        @agent_capability("cache_results")
        class CachingService(GraphBusNode):
            pass

        assert "cache_results" in CachingService.get_capabilities()

    def test_returns_same_class(self):
        @agent_capability("some_cap")
        class CapService(GraphBusNode):
            pass

        assert CapService.__name__ == "CapService"

    def test_does_not_bleed_across_classes(self):
        @agent_capability("unique_cap")
        class WithCap(GraphBusNode):
            pass

        class WithoutCap(GraphBusNode):
            pass

        assert "unique_cap" in WithCap.get_capabilities()
        assert "unique_cap" not in WithoutCap.get_capabilities()


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------

class TestContract:
    """Tests for @contract class decorator."""

    def test_attaches_version(self):
        @contract(version="1.0.0", schema={"description": "test"})
        class Svc(GraphBusNode):
            pass

        assert Svc._graphbus_contract_version == "1.0.0"

    def test_attaches_schema(self):
        schema = {
            "methods": {"process": {"input": {"id": "str"}, "output": {"ok": "bool"}}},
            "description": "my contract",
        }

        @contract(version="2.0.0", schema=schema)
        class Svc(GraphBusNode):
            pass

        assert Svc._graphbus_contract_schema == schema

    def test_sets_has_contract_flag(self):
        @contract(version="1.0.0", schema={})
        class Svc(GraphBusNode):
            pass

        assert Svc._graphbus_has_contract is True

    def test_returns_same_class(self):
        @contract(version="1.0.0", schema={})
        class Svc(GraphBusNode):
            pass

        assert Svc.__name__ == "Svc"

    def test_full_contract_schema(self):
        schema = {
            "methods": {
                "process_order": {
                    "input": {"order_id": "str", "amount": "float"},
                    "output": {"status": "str"},
                }
            },
            "publishes": {"/Order/Processed": {"payload": {"order_id": "str"}}},
            "subscribes": ["/Order/Created"],
            "description": "Order v2 API",
        }

        @contract(version="2.0.0", schema=schema)
        class OrderProcessor(GraphBusNode):
            pass

        assert OrderProcessor._graphbus_contract_version == "2.0.0"
        assert "methods" in OrderProcessor._graphbus_contract_schema
        assert "publishes" in OrderProcessor._graphbus_contract_schema
        assert "subscribes" in OrderProcessor._graphbus_contract_schema


# ---------------------------------------------------------------------------
# schema_version
# ---------------------------------------------------------------------------

class TestSchemaVersion:
    """Tests for @schema_version method decorator."""

    def test_attaches_version_metadata(self):
        class Svc(GraphBusNode):
            @subscribe("/User/Updated")
            @schema_version("1.0.0")
            def on_user_updated_v1(self, payload: dict) -> None:
                pass

        assert Svc.on_user_updated_v1._graphbus_schema_version == "1.0.0"

    def test_sets_decorated_flag(self):
        class Svc(GraphBusNode):
            @schema_version("2.3.1")
            def some_handler(self, payload: dict) -> None:
                pass

        assert Svc.some_handler._graphbus_decorated is True

    def test_preserves_function_name(self):
        class Svc(GraphBusNode):
            @schema_version("1.0.0")
            def my_handler(self, payload: dict) -> None:
                pass

        assert Svc.my_handler.__name__ == "my_handler"

    def test_method_still_callable(self):
        results = []

        class Svc(GraphBusNode):
            @schema_version("1.0.0")
            def my_handler(self, payload: dict) -> None:
                results.append(payload)

        svc = Svc()
        svc.my_handler({"x": 1})
        assert results == [{"x": 1}]


# ---------------------------------------------------------------------------
# auto_migrate
# ---------------------------------------------------------------------------

class TestAutoMigrate:
    """Tests for @auto_migrate method decorator."""

    def test_attaches_migration_metadata(self):
        class Svc(GraphBusNode):
            @subscribe("/Order/Created")
            @schema_version("2.0.0")
            @auto_migrate(from_version="1.0.0", to_version="2.0.0")
            def on_order(self, payload: dict) -> None:
                pass

        assert Svc.on_order._graphbus_auto_migrate is True
        assert Svc.on_order._graphbus_migrate_from == "1.0.0"
        assert Svc.on_order._graphbus_migrate_to == "2.0.0"

    def test_sets_decorated_flag(self):
        class Svc(GraphBusNode):
            @auto_migrate(from_version="1.0.0", to_version="2.0.0")
            def my_handler(self, payload: dict) -> None:
                pass

        assert Svc.my_handler._graphbus_decorated is True

    def test_preserves_function_name(self):
        class Svc(GraphBusNode):
            @auto_migrate(from_version="1.0.0", to_version="2.0.0")
            def migrated_handler(self, payload: dict) -> None:
                pass

        assert Svc.migrated_handler.__name__ == "migrated_handler"

    def test_method_still_callable(self):
        results = []

        class Svc(GraphBusNode):
            @auto_migrate(from_version="1.0.0", to_version="2.0.0")
            def my_handler(self, payload: dict) -> None:
                results.append(payload)

        svc = Svc()
        svc.my_handler({"field": "value"})
        assert results == [{"field": "value"}]

    def test_stacked_decorators_all_preserved(self):
        """All three decorator attributes survive when all three are stacked."""

        class InventorySvc(GraphBusNode):
            @subscribe("/Order/Created")
            @schema_version("2.0.0")
            @auto_migrate(from_version="1.0.0", to_version="2.0.0")
            def on_order_created(self, payload: dict) -> None:
                pass

        m = InventorySvc.on_order_created
        assert m._graphbus_subscribe_topic == "/Order/Created"
        assert m._graphbus_schema_version == "2.0.0"
        assert m._graphbus_auto_migrate is True
        assert m._graphbus_migrate_from == "1.0.0"
        assert m._graphbus_migrate_to == "2.0.0"
