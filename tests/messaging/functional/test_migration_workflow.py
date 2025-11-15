"""
Functional tests for migration management workflows
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from graphbus_core.runtime.migrations import (
    MigrationManager, Migration, MigrationStatus
)


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


class TestMigrationChainWorkflow:
    """Test chaining multiple migrations"""

    def test_sequential_migration_chain(self, temp_dir):
        """Test applying sequential migrations"""
        manager = MigrationManager(storage_path=temp_dir)

        # Create migration chain: 1.0.0 → 1.1.0 → 2.0.0 → 2.1.0
        class Mig1to11(Migration):
            agent_name = "OrderProcessor"
            from_version = "1.0.0"
            to_version = "1.1.0"
            description = "Add status field"

            def forward(self, payload):
                result = payload.copy()
                result['status'] = 'pending'
                return result

            def backward(self, payload):
                result = payload.copy()
                result.pop('status', None)
                return result

            def validate(self, payload):
                return 'status' in payload

        class Mig11to20(Migration):
            agent_name = "OrderProcessor"
            from_version = "1.1.0"
            to_version = "2.0.0"
            description = "Rename amount to total"

            def forward(self, payload):
                result = payload.copy()
                if 'amount' in result:
                    result['total'] = result.pop('amount')
                return result

            def backward(self, payload):
                result = payload.copy()
                if 'total' in result:
                    result['amount'] = result.pop('total')
                return result

            def validate(self, payload):
                return 'total' in payload

        class Mig20to21(Migration):
            agent_name = "OrderProcessor"
            from_version = "2.0.0"
            to_version = "2.1.0"
            description = "Add metadata"

            def forward(self, payload):
                result = payload.copy()
                result['metadata'] = {}
                return result

            def backward(self, payload):
                result = payload.copy()
                result.pop('metadata', None)
                return result

            def validate(self, payload):
                return 'metadata' in payload

        # Register migrations
        mig1 = Mig1to11()
        mig2 = Mig11to20()
        mig3 = Mig20to21()

        manager.register_migration(mig1)
        manager.register_migration(mig2)
        manager.register_migration(mig3)

        # Apply migration chain
        payload = {"order_id": "123", "amount": 100.0}

        # Apply 1.0.0 → 1.1.0
        result1 = manager.apply_migration("OrderProcessor", mig1.get_id(), payload)
        assert result1.success
        assert result1.payload_after['status'] == 'pending'

        # Apply 1.1.0 → 2.0.0
        result2 = manager.apply_migration("OrderProcessor", mig2.get_id(), result1.payload_after)
        assert result2.success
        assert 'total' in result2.payload_after
        assert 'amount' not in result2.payload_after

        # Apply 2.0.0 → 2.1.0
        result3 = manager.apply_migration("OrderProcessor", mig3.get_id(), result2.payload_after)
        assert result3.success
        assert 'metadata' in result3.payload_after

        # Verify final payload
        final_payload = result3.payload_after
        assert final_payload['order_id'] == "123"
        assert final_payload['total'] == 100.0
        assert final_payload['status'] == 'pending'
        assert 'metadata' in final_payload

    def test_migration_rollback_chain(self, temp_dir):
        """Test rolling back migration chain"""
        manager = MigrationManager(storage_path=temp_dir)

        # Create simple migration chain
        class Mig1(Migration):
            agent_name = "Agent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                result = p.copy()
                result['field_a'] = 'added'
                return result

            def backward(self, p):
                result = p.copy()
                result.pop('field_a', None)
                return result

            def validate(self, p):
                return True

        class Mig2(Migration):
            agent_name = "Agent"
            from_version = "2.0.0"
            to_version = "3.0.0"

            def forward(self, p):
                result = p.copy()
                result['field_b'] = 'added'
                return result

            def backward(self, p):
                result = p.copy()
                result.pop('field_b', None)
                return result

            def validate(self, p):
                return True

        mig1 = Mig1()
        mig2 = Mig2()
        manager.register_migration(mig1)
        manager.register_migration(mig2)

        # Apply forward
        payload = {"id": "123"}
        result1 = manager.apply_migration("Agent", mig1.get_id(), payload)
        result2 = manager.apply_migration("Agent", mig2.get_id(), result1.payload_after)

        assert result2.payload_after == {"id": "123", "field_a": "added", "field_b": "added"}

        # Rollback second migration
        rollback2 = manager.rollback_migration("Agent", mig2.get_id(), result2.payload_after)
        assert rollback2.success
        assert rollback2.payload_after == {"id": "123", "field_a": "added"}

        # Rollback first migration
        rollback1 = manager.rollback_migration("Agent", mig1.get_id(), rollback2.payload_after)
        assert rollback1.success
        assert rollback1.payload_after == {"id": "123"}


class TestMigrationOrderingWorkflow:
    """Test migration ordering with topological sort"""

    def test_complex_dependency_ordering(self, temp_dir):
        """Test ordering complex migration dependencies"""
        manager = MigrationManager(storage_path=temp_dir)

        # Create migrations with complex dependencies
        migrations = []

        # Agent A: 1.0.0 → 2.0.0 → 3.0.0
        class A1to2(Migration):
            agent_name = "AgentA"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p): return p
            def backward(self, p): return p

        class A2to3(Migration):
            agent_name = "AgentA"
            from_version = "2.0.0"
            to_version = "3.0.0"

            def forward(self, p): return p
            def backward(self, p): return p

        # Agent B: 1.0.0 → 2.0.0
        class B1to2(Migration):
            agent_name = "AgentB"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p): return p
            def backward(self, p): return p

        # Agent C: 1.0.0 → 1.1.0 → 2.0.0
        class C1to11(Migration):
            agent_name = "AgentC"
            from_version = "1.0.0"
            to_version = "1.1.0"

            def forward(self, p): return p
            def backward(self, p): return p

        class C11to2(Migration):
            agent_name = "AgentC"
            from_version = "1.1.0"
            to_version = "2.0.0"

            def forward(self, p): return p
            def backward(self, p): return p

        # Register in random order
        manager.register_migration(A2to3())
        manager.register_migration(C11to2())
        manager.register_migration(B1to2())
        manager.register_migration(A1to2())
        manager.register_migration(C1to11())

        # Plan migrations - should be topologically sorted
        planned = manager.plan_migrations()

        # Verify ordering constraints
        agent_a_migrations = [m for m in planned if m.agent_name == "AgentA"]
        assert len(agent_a_migrations) == 2
        assert agent_a_migrations[0].from_version == "1.0.0"
        assert agent_a_migrations[1].from_version == "2.0.0"

        agent_c_migrations = [m for m in planned if m.agent_name == "AgentC"]
        assert len(agent_c_migrations) == 2
        assert agent_c_migrations[0].from_version == "1.0.0"
        assert agent_c_migrations[1].from_version == "1.1.0"

    def test_multi_agent_parallel_migrations(self, temp_dir):
        """Test parallel migrations for different agents"""
        manager = MigrationManager(storage_path=temp_dir)

        # Create migrations for multiple agents that can run in parallel
        class AgentAMig(Migration):
            agent_name = "AgentA"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                result = p.copy()
                result['agent_a_field'] = 'value'
                return result

            def backward(self, p):
                result = p.copy()
                result.pop('agent_a_field', None)
                return result

            def validate(self, p):
                return 'agent_a_field' in p

        class AgentBMig(Migration):
            agent_name = "AgentB"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                result = p.copy()
                result['agent_b_field'] = 'value'
                return result

            def backward(self, p):
                result = p.copy()
                result.pop('agent_b_field', None)
                return result

            def validate(self, p):
                return 'agent_b_field' in p

        class AgentCMig(Migration):
            agent_name = "AgentC"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                result = p.copy()
                result['agent_c_field'] = 'value'
                return result

            def backward(self, p):
                result = p.copy()
                result.pop('agent_c_field', None)
                return result

            def validate(self, p):
                return 'agent_c_field' in p

        # Register migrations
        mig_a = AgentAMig()
        mig_b = AgentBMig()
        mig_c = AgentCMig()

        manager.register_migration(mig_a)
        manager.register_migration(mig_b)
        manager.register_migration(mig_c)

        # Apply migrations for each agent independently
        payload_a = {"agent": "A", "data": "test"}
        payload_b = {"agent": "B", "data": "test"}
        payload_c = {"agent": "C", "data": "test"}

        result_a = manager.apply_migration("AgentA", mig_a.get_id(), payload_a)
        result_b = manager.apply_migration("AgentB", mig_b.get_id(), payload_b)
        result_c = manager.apply_migration("AgentC", mig_c.get_id(), payload_c)

        assert result_a.success and 'agent_a_field' in result_a.payload_after
        assert result_b.success and 'agent_b_field' in result_b.payload_after
        assert result_c.success and 'agent_c_field' in result_c.payload_after


class TestMigrationValidationWorkflow:
    """Test migration validation workflows"""

    def test_validate_before_apply(self, temp_dir):
        """Test validating migrations before applying"""
        manager = MigrationManager(storage_path=temp_dir)

        # Create migration with validation
        class ValidatedMigration(Migration):
            agent_name = "Agent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, payload):
                result = payload.copy()
                result['validated_field'] = 'value'
                return result

            def backward(self, payload):
                result = payload.copy()
                result.pop('validated_field', None)
                return result

            def validate(self, payload):
                # Validation requires specific field
                return 'validated_field' in payload

        mig = ValidatedMigration()
        manager.register_migration(mig)

        # Validate migration order
        validation_result = manager.validate_migration_order()
        assert validation_result.valid

        # Apply migration
        payload = {"id": "123"}
        result = manager.apply_migration("Agent", mig.get_id(), payload)

        assert result.success
        assert result.payload_after['validated_field'] == 'value'

    def test_validation_failure_handling(self, temp_dir):
        """Test handling validation failures"""
        manager = MigrationManager(storage_path=temp_dir)

        class FailingMigration(Migration):
            agent_name = "Agent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, payload):
                # Don't add required field
                return payload

            def backward(self, payload):
                return payload

            def validate(self, payload):
                # Validation requires field that forward() doesn't add
                return 'required_field' in payload

        mig = FailingMigration()
        manager.register_migration(mig)

        # Apply migration - should fail validation
        payload = {"id": "123"}
        result = manager.apply_migration("Agent", mig.get_id(), payload)

        assert not result.success
        assert "validation" in result.error.lower()


class TestMigrationHistoryWorkflow:
    """Test migration history tracking"""

    def test_track_migration_history(self, temp_dir):
        """Test tracking complete migration history"""
        manager = MigrationManager(storage_path=temp_dir)

        # Create and register migrations
        class Mig1(Migration):
            agent_name = "Agent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                return {**p, 'v2': True}

            def backward(self, p):
                result = p.copy()
                result.pop('v2', None)
                return result

            def validate(self, p):
                return True

        class Mig2(Migration):
            agent_name = "Agent"
            from_version = "2.0.0"
            to_version = "3.0.0"

            def forward(self, p):
                return {**p, 'v3': True}

            def backward(self, p):
                result = p.copy()
                result.pop('v3', None)
                return result

            def validate(self, p):
                return True

        mig1 = Mig1()
        mig2 = Mig2()
        manager.register_migration(mig1)
        manager.register_migration(mig2)

        # Apply migrations
        payload = {"id": "123"}
        manager.apply_migration("Agent", mig1.get_id(), payload)
        manager.apply_migration("Agent", mig2.get_id(), {"id": "123", "v2": True})

        # Check history
        history = manager.get_migration_history("Agent")

        assert len(history) == 2
        assert history[0].migration_id == mig1.get_id()
        assert history[0].status == MigrationStatus.APPLIED
        assert history[1].migration_id == mig2.get_id()
        assert history[1].status == MigrationStatus.APPLIED

    def test_history_persistence(self, temp_dir):
        """Test migration history persists across sessions"""
        # Create manager and apply migration
        manager1 = MigrationManager(storage_path=temp_dir)

        class TestMig(Migration):
            agent_name = "Agent"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                return p

            def backward(self, p):
                return p

            def validate(self, p):
                return True

        mig = TestMig()
        manager1.register_migration(mig)
        manager1.apply_migration("Agent", mig.get_id(), {})

        # Create new manager with same storage
        manager2 = MigrationManager(storage_path=temp_dir)

        # Verify history persisted
        history = manager2.get_migration_history()
        assert len(history) == 1
        assert history[0].migration_id == mig.get_id()


class TestProgrammaticMigrationWorkflow:
    """Test programmatic migration creation"""

    def test_create_migration_from_functions(self, temp_dir):
        """Test creating migrations from functions"""
        manager = MigrationManager(storage_path=temp_dir)

        def forward_func(payload: Dict[str, Any]) -> Dict[str, Any]:
            result = payload.copy()
            result['new_field'] = 'default_value'
            return result

        def backward_func(payload: Dict[str, Any]) -> Dict[str, Any]:
            result = payload.copy()
            result.pop('new_field', None)
            return result

        def validate_func(payload: Dict[str, Any]) -> bool:
            return 'new_field' in payload

        # Create migration programmatically
        migration = manager.create_migration(
            "TestAgent",
            "1.0.0",
            "2.0.0",
            forward_func=forward_func,
            backward_func=backward_func,
            validate_func=validate_func,
            description="Add new_field"
        )

        # Apply migration
        payload = {"id": "123"}
        result = manager.apply_migration("TestAgent", migration.get_id(), payload)

        assert result.success
        assert result.payload_after['new_field'] == 'default_value'

        # Rollback migration
        rollback_result = manager.rollback_migration("TestAgent", migration.get_id(), result.payload_after)
        assert rollback_result.success
        assert 'new_field' not in rollback_result.payload_after

    def test_template_generation_workflow(self, temp_dir):
        """Test migration template generation"""
        manager = MigrationManager(storage_path=temp_dir)

        template = manager.generate_migration_template(
            "OrderProcessor",
            "1.0.0",
            "2.0.0"
        )

        # Verify template contains expected elements
        assert "OrderProcessor" in template
        assert "1.0.0" in template
        assert "2.0.0" in template
        assert "def forward" in template
        assert "def backward" in template
        assert "def validate" in template
        assert "class" in template
        assert "Migration" in template
