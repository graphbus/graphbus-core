"""
Functional tests for contract management workflows
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph
import json

from graphbus_core.runtime.contracts import ContractManager
from graphbus_core.runtime.migrations import MigrationManager, Migration


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def sample_graph():
    """Create sample dependency graph"""
    graph = nx.DiGraph()
    graph.add_edge("OrderProcessor", "PaymentService")
    graph.add_edge("OrderProcessor", "InventoryService")
    graph.add_edge("PaymentService", "NotificationService")
    graph.add_edge("InventoryService", "NotificationService")
    return graph


class TestContractRegistrationWorkflow:
    """Test complete contract registration workflow"""

    def test_register_validate_workflow(self, temp_dir, sample_graph):
        """Test registering contracts and validating compatibility"""
        manager = ContractManager(storage_path=temp_dir, graph=sample_graph)

        # Register OrderProcessor contract
        order_schema = {
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
            "subscribes": ["/Payment/Completed"],
            "description": "Order processing service"
        }
        order_contract = manager.register_contract("OrderProcessor", "1.0.0", order_schema)

        # Register PaymentService contract
        payment_schema = {
            "methods": {
                "process_payment": {
                    "input": {"transaction_id": "str", "amount": "float"},
                    "output": {"status": "str"}
                }
            },
            "publishes": {
                "/Payment/Completed": {
                    "payload": {"transaction_id": "str", "status": "str"}
                }
            },
            "subscribes": ["/Order/Processed"],
            "description": "Payment processing service"
        }
        payment_contract = manager.register_contract("PaymentService", "1.0.0", payment_schema)

        # Validate compatibility
        result = manager.validate_compatibility("OrderProcessor", "PaymentService")

        assert order_contract.version == "1.0.0"
        assert payment_contract.version == "1.0.0"
        # Contracts should have matching topics
        assert "/Order/Processed" in order_contract.publishes
        assert "/Payment/Completed" in payment_contract.publishes

    def test_impact_analysis_workflow(self, temp_dir, sample_graph):
        """Test analyzing impact of schema changes"""
        manager = ContractManager(storage_path=temp_dir, graph=sample_graph)

        # Register initial contracts
        schema_v1 = {
            "methods": {
                "process": {
                    "input": {"id": "str"},
                    "output": {"status": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "v1 schema"
        }

        manager.register_contract("OrderProcessor", "1.0.0", schema_v1)
        manager.register_contract("PaymentService", "1.0.0", schema_v1)
        manager.register_contract("InventoryService", "1.0.0", schema_v1)

        # Analyze impact of OrderProcessor schema change
        schema_v2 = {
            "methods": {
                "process": {
                    "input": {"id": "str", "priority": "int"},  # Breaking change
                    "output": {"status": "str", "timestamp": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "v2 schema"
        }

        impact = manager.analyze_schema_impact("OrderProcessor", schema_v2)

        assert impact.agent_name == "OrderProcessor"
        assert impact.new_version == "2.0.0"
        # Should identify downstream agents
        assert len(impact.affected_agents) > 0

    def test_downstream_notification_workflow(self, temp_dir, sample_graph):
        """Test notifying downstream agents of changes"""
        manager = ContractManager(storage_path=temp_dir, graph=sample_graph)

        # Register contracts
        schema = {
            "methods": {},
            "publishes": {},
            "subscribes": [],
            "description": "Test schema"
        }

        manager.register_contract("OrderProcessor", "1.0.0", schema)
        manager.register_contract("PaymentService", "1.0.0", schema)
        manager.register_contract("InventoryService", "1.0.0", schema)
        manager.register_contract("NotificationService", "1.0.0", schema)

        # Notify downstream of OrderProcessor changes
        notified = manager.notify_downstream_agents("OrderProcessor", schema)

        # Should notify direct dependencies
        assert "PaymentService" in notified
        assert "InventoryService" in notified
        # Should notify transitive dependencies
        assert "NotificationService" in notified


class TestContractEvolutionWorkflow:
    """Test contract evolution and versioning workflows"""

    def test_multi_version_workflow(self, temp_dir):
        """Test managing multiple contract versions"""
        manager = ContractManager(storage_path=temp_dir)

        schema_v1 = {
            "methods": {"process": {"input": {"id": "str"}, "output": {"status": "str"}}},
            "publishes": {},
            "subscribes": [],
            "description": "v1"
        }

        schema_v2 = {
            "methods": {"process": {"input": {"id": "str", "priority": "int"}, "output": {"status": "str"}}},
            "publishes": {},
            "subscribes": [],
            "description": "v2"
        }

        schema_v3 = {
            "methods": {"process": {"input": {"id": "str", "priority": "int", "metadata": "dict"}, "output": {"status": "str"}}},
            "publishes": {},
            "subscribes": [],
            "description": "v3"
        }

        # Register versions
        manager.register_contract("TestAgent", "1.0.0", schema_v1)
        manager.register_contract("TestAgent", "2.0.0", schema_v2)
        manager.register_contract("TestAgent", "3.0.0", schema_v3)

        # Verify all versions exist
        versions = manager.get_all_versions("TestAgent")
        assert versions == ["1.0.0", "2.0.0", "3.0.0"]

        # Verify latest version
        latest = manager.get_contract("TestAgent")
        assert latest.version == "3.0.0"

        # Verify specific version retrieval
        v1 = manager.get_contract("TestAgent", "1.0.0")
        assert v1.version == "1.0.0"
        assert "priority" not in v1.methods["process"].input_schema

    def test_migration_path_workflow(self, temp_dir):
        """Test getting migration path between versions"""
        manager = ContractManager(storage_path=temp_dir)

        # Register sequential versions
        for i in range(1, 6):
            schema = {
                "methods": {},
                "publishes": {},
                "subscribes": [],
                "description": f"v{i}.0.0"
            }
            manager.register_contract("TestAgent", f"{i}.0.0", schema)

        # Get migration path
        path = manager.get_migration_path("TestAgent", "1.0.0", "5.0.0")

        assert path == ["1.0.0", "2.0.0", "3.0.0", "4.0.0", "5.0.0"]

    def test_backward_migration_path(self, temp_dir):
        """Test backward migration path"""
        manager = ContractManager(storage_path=temp_dir)

        schema = {"methods": {}, "publishes": {}, "subscribes": [], "description": "test"}
        manager.register_contract("TestAgent", "1.0.0", schema)
        manager.register_contract("TestAgent", "2.0.0", schema)
        manager.register_contract("TestAgent", "3.0.0", schema)

        # Get backward path
        path = manager.get_migration_path("TestAgent", "3.0.0", "1.0.0")

        assert path == ["3.0.0", "2.0.0", "1.0.0"]


class TestContractPersistenceWorkflow:
    """Test contract persistence workflows"""

    def test_save_load_workflow(self, temp_dir, sample_graph):
        """Test saving and loading contracts"""
        # Create manager and register contracts
        manager1 = ContractManager(storage_path=temp_dir, graph=sample_graph)

        schema = {
            "methods": {
                "process": {
                    "input": {"id": "str"},
                    "output": {"status": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "Test schema"
        }

        manager1.register_contract("Agent1", "1.0.0", schema)
        manager1.register_contract("Agent2", "1.0.0", schema)
        manager1.register_contract("Agent2", "2.0.0", schema)

        # Create new manager with same storage
        manager2 = ContractManager(storage_path=temp_dir, graph=sample_graph)

        # Verify contracts loaded
        assert manager2.get_contract("Agent1", "1.0.0") is not None
        assert manager2.get_contract("Agent2", "1.0.0") is not None
        assert manager2.get_contract("Agent2", "2.0.0") is not None

        # Verify latest version
        latest = manager2.get_contract("Agent2")
        assert latest.version == "2.0.0"

    def test_graph_serialization_workflow(self, temp_dir, sample_graph):
        """Test saving and loading dependency graph with contracts"""
        # Save graph to JSON
        graph_file = Path(temp_dir) / "graph.json"
        graph_data = json_graph.node_link_data(sample_graph)

        with open(graph_file, 'w') as f:
            json.dump(graph_data, f)

        # Load graph and create manager
        with open(graph_file, 'r') as f:
            loaded_data = json.load(f)
            loaded_graph = json_graph.node_link_graph(loaded_data)

        manager = ContractManager(storage_path=temp_dir, graph=loaded_graph)

        # Register contract
        schema = {"methods": {}, "publishes": {}, "subscribes": [], "description": "test"}
        manager.register_contract("OrderProcessor", "1.0.0", schema)

        # Verify downstream agents found via loaded graph
        notified = manager.notify_downstream_agents("OrderProcessor", schema)
        assert len(notified) > 0


class TestIntegratedContractMigrationWorkflow:
    """Test integrated contract and migration workflows"""

    def test_contract_with_migration_workflow(self, temp_dir):
        """Test coordinating contracts with migrations"""
        contract_manager = ContractManager(storage_path=f"{temp_dir}/contracts")
        migration_manager = MigrationManager(storage_path=f"{temp_dir}/migrations")

        # Register v1.0.0 contract
        schema_v1 = {
            "methods": {
                "process_order": {
                    "input": {"order_id": "str", "amount": "float"},
                    "output": {"status": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "v1 schema"
        }
        contract_manager.register_contract("OrderProcessor", "1.0.0", schema_v1)

        # Create migration to v2.0.0
        class OrderMigration(Migration):
            agent_name = "OrderProcessor"
            from_version = "1.0.0"
            to_version = "2.0.0"
            description = "Add customer_id field"

            def forward(self, payload):
                result = payload.copy()
                result['customer_id'] = 'default'
                return result

            def backward(self, payload):
                result = payload.copy()
                result.pop('customer_id', None)
                return result

            def validate(self, payload):
                return 'customer_id' in payload

        migration_manager.register_migration(OrderMigration())

        # Register v2.0.0 contract
        schema_v2 = {
            "methods": {
                "process_order": {
                    "input": {"order_id": "str", "amount": "float", "customer_id": "str"},
                    "output": {"status": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "v2 schema"
        }
        contract_manager.register_contract("OrderProcessor", "2.0.0", schema_v2)

        # Verify migration path matches contract versions
        contract_path = contract_manager.get_migration_path("OrderProcessor", "1.0.0", "2.0.0")
        assert contract_path == ["1.0.0", "2.0.0"]

        # Apply migration
        payload = {"order_id": "123", "amount": 100.0}
        result = migration_manager.apply_migration("OrderProcessor", "OrderProcessor_1.0.0_to_2.0.0", payload)

        assert result.success
        assert "customer_id" in result.payload_after

    def test_breaking_change_workflow(self, temp_dir, sample_graph):
        """Test handling breaking changes with migrations"""
        contract_manager = ContractManager(storage_path=f"{temp_dir}/contracts", graph=sample_graph)
        migration_manager = MigrationManager(storage_path=f"{temp_dir}/migrations")

        # Register v1 contracts for all agents
        schema_v1 = {
            "methods": {"process": {"input": {"id": "str"}, "output": {"status": "str"}}},
            "publishes": {},
            "subscribes": [],
            "description": "v1"
        }

        for agent in ["OrderProcessor", "PaymentService", "InventoryService"]:
            contract_manager.register_contract(agent, "1.0.0", schema_v1)

        # OrderProcessor introduces breaking change
        schema_v2 = {
            "methods": {"process": {"input": {"id": "str", "priority": "int"}, "output": {"status": "str"}}},
            "publishes": {},
            "subscribes": [],
            "description": "v2 - breaking change"
        }

        # Analyze impact before registering
        impact = contract_manager.analyze_schema_impact("OrderProcessor", schema_v2)

        assert impact.agent_name == "OrderProcessor"
        assert len(impact.affected_agents) > 0

        # Create migrations for affected agents
        for affected_agent in impact.affected_agents:
            class AdaptMigration(Migration):
                agent_name = affected_agent
                from_version = "1.0.0"
                to_version = "2.0.0"
                description = f"Adapt to OrderProcessor breaking change"

                def forward(self, payload):
                    result = payload.copy()
                    result['priority'] = 5  # Default priority
                    return result

                def backward(self, payload):
                    result = payload.copy()
                    result.pop('priority', None)
                    return result

                def validate(self, payload):
                    return True

            migration_manager.register_migration(AdaptMigration())

        # Register new contract version
        contract_manager.register_contract("OrderProcessor", "2.0.0", schema_v2)

        # Verify migration plan includes all affected agents
        planned = migration_manager.plan_migrations()
        assert len(planned) >= len(impact.affected_agents)
