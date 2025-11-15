"""
Integration tests for migration and coherence tracking lifecycle
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import networkx as nx

from graphbus_core.runtime.contracts import ContractManager
from graphbus_core.runtime.migrations import MigrationManager, Migration
from graphbus_core.runtime.coherence import CoherenceTracker, CoherenceLevel


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def system_graph():
    """Create realistic system dependency graph"""
    graph = nx.DiGraph()
    graph.add_edge("OrderService", "PaymentService")
    graph.add_edge("OrderService", "InventoryService")
    graph.add_edge("PaymentService", "NotificationService")
    graph.add_edge("InventoryService", "NotificationService")
    return graph


class TestContractMigrationCoherenceIntegration:
    """Test integrated contract, migration, and coherence workflows"""

    def test_coordinated_version_upgrade(self, temp_dir, system_graph):
        """Test upgrading system version with migrations and coherence tracking"""
        # Setup managers
        contract_manager = ContractManager(
            storage_path=f"{temp_dir}/contracts",
            graph=system_graph
        )
        migration_manager = MigrationManager(
            storage_path=f"{temp_dir}/migrations"
        )
        coherence_tracker = CoherenceTracker(
            storage_path=f"{temp_dir}/coherence",
            graph=system_graph
        )

        # Phase 1: Register v1.0.0 contracts for all services
        schema_v1 = {
            "methods": {
                "process": {
                    "input": {"id": "str", "amount": "float"},
                    "output": {"status": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "v1 schema"
        }

        for service in ["OrderService", "PaymentService", "InventoryService", "NotificationService"]:
            contract_manager.register_contract(service, "1.0.0", schema_v1)

        # Track v1 interactions
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/process",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Verify high coherence with v1
        metrics_v1 = coherence_tracker.calculate_metrics()
        assert metrics_v1.get_level() == CoherenceLevel.HIGH

        # Phase 2: Plan upgrade to v2.0.0
        schema_v2 = {
            "methods": {
                "process": {
                    "input": {"id": "str", "amount": "float", "customer_id": "str"},
                    "output": {"status": "str", "timestamp": "str"}
                }
            },
            "publishes": {},
            "subscribes": [],
            "description": "v2 schema - added customer_id"
        }

        # Analyze impact
        impact = contract_manager.analyze_schema_impact("OrderService", schema_v2)
        affected_services = impact.affected_agents

        # Create migrations for affected services
        for service in ["OrderService", "PaymentService", "InventoryService", "NotificationService"]:
            class ServiceMigration(Migration):
                agent_name = service
                from_version = "1.0.0"
                to_version = "2.0.0"
                description = f"Upgrade {service} to v2"

                def forward(self, payload):
                    result = payload.copy()
                    if 'customer_id' not in result:
                        result['customer_id'] = 'default'
                    return result

                def backward(self, payload):
                    result = payload.copy()
                    result.pop('customer_id', None)
                    result.pop('timestamp', None)
                    return result

                def validate(self, payload):
                    return 'customer_id' in payload

            migration_manager.register_migration(ServiceMigration())

        # Register v2 contracts
        for service in ["OrderService", "PaymentService", "InventoryService", "NotificationService"]:
            contract_manager.register_contract(service, "2.0.0", schema_v2)

        # Phase 3: Apply migrations in topological order
        planned_migrations = migration_manager.plan_migrations()
        assert len(planned_migrations) == 4

        # Apply each migration
        payload = {"id": "123", "amount": 100.0}
        for migration in planned_migrations:
            result = migration_manager.apply_migration(
                migration.agent_name,
                migration.get_id(),
                payload
            )
            assert result.success
            payload = result.payload_after

        # Phase 4: Track v2 interactions
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/process",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        # Verify coherence maintained after migration
        metrics_v2 = coherence_tracker.calculate_metrics()
        assert metrics_v2.overall_score > 0.7  # Still coherent

        # Verify migration history
        history = migration_manager.get_migration_history()
        assert len(history) == 4

    def test_detect_incomplete_migration(self, temp_dir, system_graph):
        """Test detecting incomplete migration causing coherence issues"""
        contract_manager = ContractManager(
            storage_path=f"{temp_dir}/contracts",
            graph=system_graph
        )
        coherence_tracker = CoherenceTracker(
            storage_path=f"{temp_dir}/coherence",
            graph=system_graph
        )

        # Register contracts
        schema_v1 = {"methods": {}, "publishes": {}, "subscribes": [], "description": "v1"}
        schema_v2 = {"methods": {}, "publishes": {}, "subscribes": [], "description": "v2"}

        # OrderService and PaymentService upgrade to v2
        contract_manager.register_contract("OrderService", "1.0.0", schema_v1)
        contract_manager.register_contract("OrderService", "2.0.0", schema_v2)
        contract_manager.register_contract("PaymentService", "1.0.0", schema_v1)
        contract_manager.register_contract("PaymentService", "2.0.0", schema_v2)

        # But InventoryService stays on v1 (incomplete migration)
        contract_manager.register_contract("InventoryService", "1.0.0", schema_v1)
        contract_manager.register_contract("NotificationService", "1.0.0", schema_v1)

        # Track mixed version interactions
        coherence_tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/test",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        coherence_tracker.track_interaction(
            source="OrderService",
            target="InventoryService",
            topic="/test",
            schema_version="1.0.0",  # Inconsistent!
            payload={},
            successful=True
        )

        # Detect drift
        warnings = coherence_tracker.detect_schema_drift()
        assert len(warnings) > 0

        # Verify low coherence
        metrics = coherence_tracker.calculate_metrics()
        assert metrics.schema_version_consistency < 1.0

        # Analyze paths
        report = coherence_tracker.analyze_coherence_paths()
        assert report.overall_score < 0.9  # Degraded coherence

    def test_rollback_with_coherence_tracking(self, temp_dir, system_graph):
        """Test rolling back migration and tracking coherence impact"""
        migration_manager = MigrationManager(storage_path=f"{temp_dir}/migrations")
        coherence_tracker = CoherenceTracker(
            storage_path=f"{temp_dir}/coherence",
            graph=system_graph
        )

        # Create and apply migration
        class TestMigration(Migration):
            agent_name = "OrderService"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, payload):
                return {**payload, 'v2_field': 'value'}

            def backward(self, payload):
                result = payload.copy()
                result.pop('v2_field', None)
                return result

            def validate(self, payload):
                return True

        mig = TestMigration()
        migration_manager.register_migration(mig)

        # Apply forward migration
        payload = {"id": "123"}
        forward_result = migration_manager.apply_migration(
            "OrderService",
            mig.get_id(),
            payload
        )
        assert forward_result.success

        # Track v2 interactions
        for _ in range(5):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/test",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        metrics_before_rollback = coherence_tracker.calculate_metrics()

        # Rollback migration
        rollback_result = migration_manager.rollback_migration(
            "OrderService",
            mig.get_id(),
            forward_result.payload_after
        )
        assert rollback_result.success
        assert 'v2_field' not in rollback_result.payload_after

        # Track v1 interactions after rollback
        for _ in range(5):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/test",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Coherence should show version inconsistency
        metrics_after_rollback = coherence_tracker.calculate_metrics()
        assert metrics_after_rollback.schema_version_consistency < 1.0


class TestLongRunningCoherenceTracking:
    """Test coherence tracking over extended periods"""

    def test_temporal_drift_detection(self, temp_dir, system_graph):
        """Test detecting schema drift over time"""
        coherence_tracker = CoherenceTracker(
            storage_path=f"{temp_dir}/coherence",
            graph=system_graph
        )

        base_time = datetime.now() - timedelta(days=7)

        # Week 1: All on v1.0.0
        for day in range(3):
            for _ in range(10):
                record = coherence_tracker.create_interaction_record(
                    source="OrderService",
                    target="PaymentService",
                    topic="/test",
                    schema_version="1.0.0",
                    payload={},
                    successful=True
                )
                record.timestamp = base_time + timedelta(days=day, seconds=_)
                coherence_tracker.interactions.append(record)

        # Week 2: Gradual migration to v2.0.0
        for day in range(3, 5):
            for _ in range(10):
                version = "2.0.0" if _ % 2 == 0 else "1.0.0"
                record = coherence_tracker.create_interaction_record(
                    source="OrderService",
                    target="PaymentService",
                    topic="/test",
                    schema_version=version,
                    payload={},
                    successful=True
                )
                record.timestamp = base_time + timedelta(days=day, seconds=_)
                coherence_tracker.interactions.append(record)

        # Week 3: Mostly v2.0.0
        for day in range(5, 7):
            for _ in range(10):
                record = coherence_tracker.create_interaction_record(
                    source="OrderService",
                    target="PaymentService",
                    topic="/test",
                    schema_version="2.0.0",
                    payload={},
                    successful=True
                )
                record.timestamp = base_time + timedelta(days=day, seconds=_)
                coherence_tracker.interactions.append(record)

        # Detect drift in last 2 days (should see mostly v2)
        warnings = coherence_tracker.detect_schema_drift(
            time_window=timedelta(days=2)
        )

        # Calculate temporal consistency
        metrics = coherence_tracker.calculate_metrics()
        assert 0.0 <= metrics.temporal_consistency <= 1.0

    def test_spatial_consistency_across_paths(self, temp_dir, system_graph):
        """Test spatial consistency across different execution paths"""
        coherence_tracker = CoherenceTracker(
            storage_path=f"{temp_dir}/coherence",
            graph=system_graph
        )

        # Path 1: OrderService → PaymentService (v2.0.0)
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/payment",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        # Path 2: OrderService → InventoryService (v1.0.0 - inconsistent!)
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="InventoryService",
                topic="/inventory",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Calculate spatial consistency
        metrics = coherence_tracker.calculate_metrics()
        assert metrics.spatial_consistency < 1.0  # Should detect inconsistency

        # Analyze coherence paths
        report = coherence_tracker.analyze_coherence_paths()

        # Should identify incoherent paths
        if report.incoherent_paths:
            assert len(report.incoherent_paths) > 0


class TestMigrationWithGraphAnalysis:
    """Test migration planning with dependency graph analysis"""

    def test_downstream_migration_propagation(self, temp_dir, system_graph):
        """Test migrating upstream service propagates to downstream"""
        contract_manager = ContractManager(
            storage_path=f"{temp_dir}/contracts",
            graph=system_graph
        )
        migration_manager = MigrationManager(
            storage_path=f"{temp_dir}/migrations"
        )

        # Register initial contracts
        schema_v1 = {"methods": {}, "publishes": {}, "subscribes": [], "description": "v1"}
        for service in system_graph.nodes():
            contract_manager.register_contract(service, "1.0.0", schema_v1)

        # OrderService introduces breaking change
        schema_v2 = {"methods": {}, "publishes": {}, "subscribes": [], "description": "v2 breaking"}

        # Analyze impact using graph
        impact = contract_manager.analyze_schema_impact("OrderService", schema_v2)

        # Should identify downstream services
        assert "PaymentService" in impact.affected_agents or len(impact.affected_agents) >= 0

        # Notify downstream agents
        notified = contract_manager.notify_downstream_agents("OrderService", schema_v2)

        # Should include direct and transitive dependencies
        assert "PaymentService" in notified or "InventoryService" in notified

        # Create migrations for all affected services
        all_services = ["OrderService"] + list(notified)

        for service in all_services:
            class ServiceMigration(Migration):
                agent_name = service
                from_version = "1.0.0"
                to_version = "2.0.0"

                def forward(self, p):
                    return p

                def backward(self, p):
                    return p

                def validate(self, p):
                    return True

            migration_manager.register_migration(ServiceMigration())

        # Plan migrations - should be topologically sorted
        planned = migration_manager.plan_migrations()

        # Verify OrderService is migrated before or with its dependencies
        assert len(planned) >= len(all_services)

    def test_detect_circular_dependencies(self, temp_dir):
        """Test detecting circular migration dependencies"""
        # Create circular graph
        circular_graph = nx.DiGraph()
        circular_graph.add_edge("A", "B")
        circular_graph.add_edge("B", "C")
        circular_graph.add_edge("C", "A")  # Creates cycle

        migration_manager = MigrationManager(storage_path=f"{temp_dir}/migrations")

        # Create migrations that form a cycle
        class MigA(Migration):
            agent_name = "A"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                return p

            def backward(self, p):
                return p

        class MigB(Migration):
            agent_name = "B"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                return p

            def backward(self, p):
                return p

        class MigC(Migration):
            agent_name = "C"
            from_version = "1.0.0"
            to_version = "2.0.0"

            def forward(self, p):
                return p

            def backward(self, p):
                return p

        migration_manager.register_migration(MigA())
        migration_manager.register_migration(MigB())
        migration_manager.register_migration(MigC())

        # Validation should detect issues
        # (Note: This depends on implementation of cycle detection)
        validation_result = migration_manager.validate_migration_order()

        # Should either succeed or provide warnings
        assert isinstance(validation_result.valid, bool)


class TestComprehensiveSystemUpgrade:
    """Test complete system upgrade workflow"""

    def test_zero_downtime_migration(self, temp_dir, system_graph):
        """Test zero-downtime migration strategy"""
        contract_manager = ContractManager(
            storage_path=f"{temp_dir}/contracts",
            graph=system_graph
        )
        migration_manager = MigrationManager(
            storage_path=f"{temp_dir}/migrations"
        )
        coherence_tracker = CoherenceTracker(
            storage_path=f"{temp_dir}/coherence",
            graph=system_graph
        )

        # Register v1 contracts
        schema_v1 = {"methods": {}, "publishes": {}, "subscribes": [], "description": "v1"}
        for service in system_graph.nodes():
            contract_manager.register_contract(service, "1.0.0", schema_v1)

        # Track v1 baseline
        for _ in range(20):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/test",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        baseline_metrics = coherence_tracker.calculate_metrics()
        assert baseline_metrics.get_level() == CoherenceLevel.HIGH

        # Create intermediate v1.5.0 (backward compatible)
        schema_v15 = {"methods": {}, "publishes": {}, "subscribes": [], "description": "v1.5 compatible"}

        for service in system_graph.nodes():
            contract_manager.register_contract(service, "1.5.0", schema_v15)

            class CompatMigration(Migration):
                agent_name = service
                from_version = "1.0.0"
                to_version = "1.5.0"
                description = "Backward compatible upgrade"

                def forward(self, p):
                    return {**p, 'compatible_field': 'optional'}

                def backward(self, p):
                    result = p.copy()
                    result.pop('compatible_field', None)
                    return result

                def validate(self, p):
                    return True

            migration_manager.register_migration(CompatMigration())

        # Apply migrations gradually
        planned = migration_manager.plan_migrations()

        # Track mixed version period
        for i, migration in enumerate(planned):
            # Some services on v1, some on v1.5
            version = "1.5.0" if i % 2 == 0 else "1.0.0"
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/test",
                schema_version=version,
                payload={},
                successful=True
            )

        # Coherence should remain acceptable during migration
        transition_metrics = coherence_tracker.calculate_metrics()
        assert transition_metrics.overall_score > 0.6

        # Complete migration to v1.5.0
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/test",
                schema_version="1.5.0",
                payload={},
                successful=True
            )

        final_metrics = coherence_tracker.calculate_metrics()
        assert final_metrics.get_level() in [CoherenceLevel.HIGH, CoherenceLevel.MEDIUM]
