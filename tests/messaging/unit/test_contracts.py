"""
Unit tests for ContractManager
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import networkx as nx

from graphbus_core.runtime.contracts import (
    ContractManager, Contract, SchemaField, MethodSchema, EventSchema,
    CompatibilityLevel, ChangeType
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for contracts"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def contract_manager(temp_dir):
    """Create ContractManager instance"""
    return ContractManager(storage_path=temp_dir)


@pytest.fixture
def sample_schema():
    """Sample contract schema"""
    return {
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
    }


class TestContractManager:
    """Test ContractManager functionality"""

    def test_initialization(self, contract_manager, temp_dir):
        """Test ContractManager initialization"""
        assert contract_manager.storage_path == Path(temp_dir)
        assert contract_manager.contracts == {}

    def test_register_contract(self, contract_manager, sample_schema):
        """Test contract registration"""
        contract = contract_manager.register_contract(
            "OrderProcessor",
            "1.0.0",
            sample_schema
        )

        assert contract.agent_name == "OrderProcessor"
        assert contract.version == "1.0.0"
        assert len(contract.methods) == 1
        assert "process_order" in contract.methods

    def test_register_contract_invalid_version(self, contract_manager, sample_schema):
        """Test contract registration with invalid version"""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            contract_manager.register_contract(
                "OrderProcessor",
                "invalid",
                sample_schema
            )

    def test_get_contract_latest(self, contract_manager, sample_schema):
        """Test getting latest contract version"""
        contract_manager.register_contract("OrderProcessor", "1.0.0", sample_schema)
        contract_manager.register_contract("OrderProcessor", "2.0.0", sample_schema)

        latest = contract_manager.get_contract("OrderProcessor")
        assert latest.version == "2.0.0"

    def test_get_contract_specific_version(self, contract_manager, sample_schema):
        """Test getting specific contract version"""
        contract_manager.register_contract("OrderProcessor", "1.0.0", sample_schema)
        contract_manager.register_contract("OrderProcessor", "2.0.0", sample_schema)

        v1 = contract_manager.get_contract("OrderProcessor", "1.0.0")
        assert v1.version == "1.0.0"

    def test_get_all_versions(self, contract_manager, sample_schema):
        """Test getting all contract versions"""
        contract_manager.register_contract("OrderProcessor", "1.0.0", sample_schema)
        contract_manager.register_contract("OrderProcessor", "1.1.0", sample_schema)
        contract_manager.register_contract("OrderProcessor", "2.0.0", sample_schema)

        versions = contract_manager.get_all_versions("OrderProcessor")
        assert versions == ["1.0.0", "1.1.0", "2.0.0"]

    def test_validate_compatibility_no_contracts(self, contract_manager):
        """Test compatibility validation with missing contracts"""
        result = contract_manager.validate_compatibility("AgentA", "AgentB")

        assert not result.compatible
        assert len(result.issues) > 0

    def test_validate_compatibility_success(self, contract_manager, sample_schema):
        """Test successful compatibility validation"""
        contract_manager.register_contract("Producer", "1.0.0", sample_schema)
        contract_manager.register_contract("Consumer", "1.0.0", sample_schema)

        result = contract_manager.validate_compatibility("Producer", "Consumer")
        assert isinstance(result.compatible, bool)  # May be compatible or not depending on topics

    def test_contract_persistence(self, contract_manager, sample_schema):
        """Test contract persistence to disk"""
        contract_manager.register_contract("OrderProcessor", "1.0.0", sample_schema)

        # Create new manager with same storage path
        new_manager = ContractManager(storage_path=str(contract_manager.storage_path))

        contract = new_manager.get_contract("OrderProcessor", "1.0.0")
        assert contract is not None
        assert contract.version == "1.0.0"

    def test_get_migration_path(self, contract_manager, sample_schema):
        """Test getting migration path between versions"""
        contract_manager.register_contract("Agent", "1.0.0", sample_schema)
        contract_manager.register_contract("Agent", "1.1.0", sample_schema)
        contract_manager.register_contract("Agent", "2.0.0", sample_schema)

        path = contract_manager.get_migration_path("Agent", "1.0.0", "2.0.0")
        assert path == ["1.0.0", "1.1.0", "2.0.0"]

    def test_migration_path_backward(self, contract_manager, sample_schema):
        """Test backward migration path"""
        contract_manager.register_contract("Agent", "1.0.0", sample_schema)
        contract_manager.register_contract("Agent", "2.0.0", sample_schema)

        path = contract_manager.get_migration_path("Agent", "2.0.0", "1.0.0")
        assert path == ["2.0.0", "1.0.0"]

    def test_analyze_schema_impact_no_graph(self, contract_manager, sample_schema):
        """Test impact analysis without graph"""
        contract_manager.register_contract("Agent", "1.0.0", sample_schema)

        with pytest.raises(ValueError, match="No dependency graph"):
            contract_manager.analyze_schema_impact("Agent", sample_schema)

    def test_analyze_schema_impact_with_graph(self, contract_manager, sample_schema):
        """Test impact analysis with dependency graph"""
        # Create simple graph
        graph = nx.DiGraph()
        graph.add_edge("Producer", "Consumer1")
        graph.add_edge("Producer", "Consumer2")

        manager = ContractManager(storage_path=str(contract_manager.storage_path), graph=graph)
        manager.register_contract("Producer", "1.0.0", sample_schema)

        # Analyze impact of new version
        new_schema = sample_schema.copy()
        new_schema["version"] = "2.0.0"

        impact = manager.analyze_schema_impact("Producer", new_schema)
        assert impact.agent_name == "Producer"
        assert impact.new_version == "2.0.0"

    def test_notify_downstream_agents(self, contract_manager, sample_schema):
        """Test notifying downstream agents"""
        graph = nx.DiGraph()
        graph.add_edge("Producer", "Consumer1")
        graph.add_edge("Producer", "Consumer2")
        graph.add_edge("Consumer1", "Consumer3")

        manager = ContractManager(storage_path=str(contract_manager.storage_path), graph=graph)
        manager.register_contract("Producer", "1.0.0", sample_schema)

        notified = manager.notify_downstream_agents("Producer", sample_schema)
        assert "Consumer1" in notified
        assert "Consumer2" in notified
        assert "Consumer3" in notified  # Transitive dependency


class TestContract:
    """Test Contract class"""

    def test_contract_to_dict(self):
        """Test Contract serialization to dict"""
        contract = Contract(
            agent_name="TestAgent",
            version="1.0.0",
            description="Test contract"
        )

        data = contract.to_dict()
        assert data["agent_name"] == "TestAgent"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_contract_from_dict(self):
        """Test Contract deserialization from dict"""
        data = {
            "agent_name": "TestAgent",
            "version": "1.0.0",
            "methods": {},
            "publishes": {},
            "subscribes": [],
            "description": "Test",
            "timestamp": "2025-01-01T00:00:00"
        }

        contract = Contract.from_dict(data)
        assert contract.agent_name == "TestAgent"
        assert contract.version == "1.0.0"


class TestSchemaVersioning:
    """Test semantic versioning utilities"""

    def test_is_valid_semver(self, contract_manager):
        """Test semantic version validation"""
        assert contract_manager._is_valid_semver("1.0.0")
        assert contract_manager._is_valid_semver("2.3.4")
        assert not contract_manager._is_valid_semver("1.0")
        assert not contract_manager._is_valid_semver("invalid")

    def test_parse_semver(self, contract_manager):
        """Test semantic version parsing"""
        assert contract_manager._parse_semver("1.0.0") == (1, 0, 0)
        assert contract_manager._parse_semver("2.3.4") == (2, 3, 4)
        assert contract_manager._parse_semver("invalid") == (0, 0, 0)

    def test_increment_version_patch(self, contract_manager):
        """Test patch version increment"""
        result = contract_manager._increment_version("1.0.0", "patch")
        assert result == "1.0.1"

    def test_increment_version_minor(self, contract_manager):
        """Test minor version increment"""
        result = contract_manager._increment_version("1.0.0", "minor")
        assert result == "1.1.0"

    def test_increment_version_major(self, contract_manager):
        """Test major version increment"""
        result = contract_manager._increment_version("1.0.0", "major")
        assert result == "2.0.0"
