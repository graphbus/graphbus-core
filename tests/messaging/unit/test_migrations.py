"""
Unit tests for MigrationManager
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from graphbus_core.runtime.migrations import (
    MigrationManager, Migration, MigrationStatus, MigrationCycleError
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for migrations"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def migration_manager(temp_dir):
    """Create MigrationManager instance"""
    return MigrationManager(storage_path=temp_dir)


class SampleMigration(Migration):
    """Sample migration for testing"""
    agent_name = "TestAgent"
    from_version = "1.0.0"
    to_version = "2.0.0"
    description = "Test migration"

    def forward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = payload.copy()
        result['new_field'] = 'default'
        return result

    def backward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = payload.copy()
        result.pop('new_field', None)
        return result

    def validate(self, payload: Dict[str, Any]) -> bool:
        return 'new_field' in payload


class TestMigrationManager:
    """Test MigrationManager functionality"""

    def test_initialization(self, migration_manager, temp_dir):
        """Test MigrationManager initialization"""
        assert migration_manager.storage_path == Path(temp_dir)
        assert migration_manager.migrations == {}
        assert migration_manager.records == {}

    def test_register_migration(self, migration_manager):
        """Test migration registration"""
        migration = SampleMigration()
        migration_manager.register_migration(migration)

        migration_id = migration.get_id()
        assert migration_id in migration_manager.migrations
        assert migration_manager.migrations[migration_id] == migration

    def test_create_migration(self, migration_manager):
        """Test programmatic migration creation"""
        def forward_func(payload):
            payload['migrated'] = True
            return payload

        def backward_func(payload):
            payload.pop('migrated', None)
            return payload

        migration = migration_manager.create_migration(
            "Agent",
            "1.0.0",
            "2.0.0",
            forward_func=forward_func,
            backward_func=backward_func,
            description="Test"
        )

        assert migration.agent_name == "Agent"
        assert migration.from_version == "1.0.0"
        assert migration.to_version == "2.0.0"

    def test_apply_migration_success(self, migration_manager):
        """Test successful migration application"""
        migration = SampleMigration()
        migration_manager.register_migration(migration)

        payload = {"order_id": "123", "amount": 100.0}
        result = migration_manager.apply_migration(
            "TestAgent",
            migration.get_id(),
            payload
        )

        assert result.success
        assert result.payload_after['new_field'] == 'default'
        assert 'order_id' in result.payload_after

    def test_apply_migration_validation_failure(self, migration_manager):
        """Test migration with validation failure"""
        class FailingMigration(Migration):
            agent_name = "TestAgent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, payload):
                return payload  # Don't add required field

            def backward(self, payload):
                return payload

            def validate(self, payload):
                return 'required_field' in payload  # Will fail

        migration = FailingMigration()
        migration_manager.register_migration(migration)

        payload = {"data": "test"}
        result = migration_manager.apply_migration(
            "TestAgent",
            migration.get_id(),
            payload
        )

        assert not result.success
        assert "validation failed" in result.error.lower()

    def test_apply_migration_not_found(self, migration_manager):
        """Test applying non-existent migration"""
        result = migration_manager.apply_migration(
            "TestAgent",
            "nonexistent_migration",
            {}
        )

        assert not result.success
        assert "not found" in result.error.lower()

    def test_rollback_migration(self, migration_manager):
        """Test migration rollback"""
        migration = SampleMigration()
        migration_manager.register_migration(migration)

        # First apply forward
        payload = {"order_id": "123"}
        apply_result = migration_manager.apply_migration(
            "TestAgent",
            migration.get_id(),
            payload
        )
        assert apply_result.success

        # Then rollback
        rollback_result = migration_manager.rollback_migration(
            "TestAgent",
            migration.get_id(),
            apply_result.payload_after
        )

        assert rollback_result.success
        assert 'new_field' not in rollback_result.payload_after

    def test_get_pending_migrations(self, migration_manager):
        """Test getting pending migrations"""
        migration1 = SampleMigration()
        migration_manager.register_migration(migration1)

        pending = migration_manager.get_pending_migrations("TestAgent")
        assert len(pending) == 1
        assert pending[0].agent_name == "TestAgent"

    def test_plan_migrations_ordering(self, migration_manager):
        """Test migration planning with topological sort"""
        # Create migrations in non-sequential order
        class Migration2(Migration):
            agent_name = "Agent"
            from_version = "2.0.0"
            to_version = "3.0.0"

            def forward(self, p): return p
            def backward(self, p): return p

        class Migration1(Migration):
            agent_name = "Agent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p): return p
            def backward(self, p): return p

        mig2 = Migration2()
        mig1 = Migration1()

        migration_manager.register_migration(mig2)  # Register in reverse order
        migration_manager.register_migration(mig1)

        planned = migration_manager.plan_migrations()

        # Should be ordered correctly by topological sort
        assert len(planned) >= 2
        # Find indices
        idx1 = next(i for i, m in enumerate(planned) if m.from_version == "1.0.0")
        idx2 = next(i for i, m in enumerate(planned) if m.from_version == "2.0.0")
        assert idx1 < idx2  # mig1 should come before mig2

    def test_validate_migration_order_success(self, migration_manager):
        """Test migration order validation success"""
        migration = SampleMigration()
        migration_manager.register_migration(migration)

        result = migration_manager.validate_migration_order()
        assert result.valid

    def test_get_migration_history(self, migration_manager):
        """Test getting migration history"""
        migration = SampleMigration()
        migration_manager.register_migration(migration)

        # Apply migration
        migration_manager.apply_migration(
            "TestAgent",
            migration.get_id(),
            {}
        )

        history = migration_manager.get_migration_history("TestAgent")
        assert len(history) == 1
        assert history[0].agent_name == "TestAgent"
        assert history[0].status == MigrationStatus.APPLIED

    def test_migration_persistence(self, migration_manager):
        """Test migration history persistence"""
        migration = SampleMigration()
        migration_manager.register_migration(migration)

        # Apply migration
        migration_manager.apply_migration(
            "TestAgent",
            migration.get_id(),
            {}
        )

        # Create new manager with same storage
        new_manager = MigrationManager(storage_path=str(migration_manager.storage_path))
        history = new_manager.get_migration_history()

        assert len(history) == 1

    def test_generate_migration_template(self, migration_manager):
        """Test migration template generation"""
        template = migration_manager.generate_migration_template(
            "OrderProcessor",
            "1.0.0",
            "2.0.0"
        )

        assert "OrderProcessor" in template
        assert "1.0.0" in template
        assert "2.0.0" in template
        assert "def forward" in template
        assert "def backward" in template
        assert "def validate" in template


class TestMigration:
    """Test Migration base class"""

    def test_migration_get_id(self):
        """Test migration ID generation"""
        migration = SampleMigration()
        migration_id = migration.get_id()

        assert migration_id == "TestAgent_1.0.0_to_2.0.0"

    def test_migration_repr(self):
        """Test migration string representation"""
        migration = SampleMigration()
        repr_str = repr(migration)

        assert "TestAgent" in repr_str
        assert "1.0.0" in repr_str
        assert "2.0.0" in repr_str


class TestMigrationOrdering:
    """Test migration ordering with networkx"""

    def test_complex_migration_chain(self, migration_manager):
        """Test complex migration chain ordering"""
        class Mig1(Migration):
            agent_name = "A"
            from_version = "1.0.0"
            to_version = "1.1.0"
            def forward(self, p): return p
            def backward(self, p): return p

        class Mig2(Migration):
            agent_name = "A"
            from_version = "1.1.0"
            to_version = "2.0.0"
            def forward(self, p): return p
            def backward(self, p): return p

        class Mig3(Migration):
            agent_name = "A"
            from_version = "2.0.0"
            to_version = "2.1.0"
            def forward(self, p): return p
            def backward(self, p): return p

        # Register in random order
        migration_manager.register_migration(Mig2())
        migration_manager.register_migration(Mig1())
        migration_manager.register_migration(Mig3())

        planned = migration_manager.plan_migrations()

        # Verify correct order
        versions = [(m.from_version, m.to_version) for m in planned if m.agent_name == "A"]
        assert ("1.0.0", "1.1.0") in versions
        assert ("1.1.0", "2.0.0") in versions
        assert ("2.0.0", "2.1.0") in versions

        # Verify sequential
        idx1 = next(i for i, m in enumerate(planned) if m.from_version == "1.0.0")
        idx2 = next(i for i, m in enumerate(planned) if m.from_version == "1.1.0")
        idx3 = next(i for i, m in enumerate(planned) if m.from_version == "2.0.0")
        assert idx1 < idx2 < idx3
