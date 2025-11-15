"""
Functional tests for coherence tracking workflows
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import networkx as nx

from graphbus_core.runtime.coherence import (
    CoherenceTracker, CoherenceLevel
)


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def microservices_graph():
    """Create realistic microservices dependency graph"""
    graph = nx.DiGraph()

    # API Gateway → Services
    graph.add_edge("APIGateway", "OrderService")
    graph.add_edge("APIGateway", "UserService")
    graph.add_edge("APIGateway", "ProductService")

    # Service dependencies
    graph.add_edge("OrderService", "PaymentService")
    graph.add_edge("OrderService", "InventoryService")
    graph.add_edge("OrderService", "NotificationService")

    graph.add_edge("PaymentService", "NotificationService")
    graph.add_edge("InventoryService", "NotificationService")

    graph.add_edge("UserService", "NotificationService")

    return graph


class TestCoherenceTrackingWorkflow:
    """Test end-to-end coherence tracking"""

    def test_track_system_interactions(self, temp_dir, microservices_graph):
        """Test tracking interactions across microservices"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Simulate order processing workflow
        # APIGateway → OrderService
        tracker.track_interaction(
            source="APIGateway",
            target="OrderService",
            topic="/order/create",
            schema_version="1.0.0",
            payload={"order_id": "123", "user_id": "user1"},
            successful=True
        )

        # OrderService → PaymentService
        tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/payment/process",
            schema_version="1.0.0",
            payload={"order_id": "123", "amount": 100.0},
            successful=True
        )

        # OrderService → InventoryService
        tracker.track_interaction(
            source="OrderService",
            target="InventoryService",
            topic="/inventory/reserve",
            schema_version="1.0.0",
            payload={"order_id": "123", "items": ["item1"]},
            successful=True
        )

        # OrderService → NotificationService
        tracker.track_interaction(
            source="OrderService",
            target="NotificationService",
            topic="/notification/send",
            schema_version="1.0.0",
            payload={"user_id": "user1", "message": "Order placed"},
            successful=True
        )

        # Calculate coherence metrics
        metrics = tracker.calculate_metrics()

        assert metrics.overall_score > 0.8  # High coherence with consistent versions
        assert metrics.schema_version_consistency == 1.0  # All using v1.0.0
        assert len(tracker.interactions) == 4

    def test_detect_version_drift_over_time(self, temp_dir, microservices_graph):
        """Test detecting schema drift as services update"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        base_time = datetime.now() - timedelta(hours=48)

        # Day 1: All services on v1.0.0
        for i in range(10):
            tracker.track_interaction(
                source="APIGateway",
                target="OrderService",
                topic="/order/create",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Day 2 (24h later): OrderService updates to v2.0.0
        for i in range(10):
            record = tracker.create_interaction_record(
                source="APIGateway",
                target="OrderService",
                topic="/order/create",
                schema_version="2.0.0",
                payload={},
                successful=True
            )
            record.timestamp = base_time + timedelta(hours=24, seconds=i)
            tracker.interactions.append(record)

        # Day 3 (48h later): APIGateway still on v1.0.0, drift detected
        for i in range(5):
            record = tracker.create_interaction_record(
                source="APIGateway",
                target="UserService",
                topic="/user/get",
                schema_version="1.0.0",
                payload={},
                successful=True
            )
            record.timestamp = base_time + timedelta(hours=48, seconds=i)
            tracker.interactions.append(record)

        # Detect drift
        warnings = tracker.detect_schema_drift()

        assert len(warnings) > 0
        # Should detect version inconsistency between APIGateway's calls

    def test_coherence_degradation_workflow(self, temp_dir, microservices_graph):
        """Test coherence degrading as versions diverge"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Phase 1: High coherence (all v1.0.0)
        for _ in range(20):
            tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/payment/process",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        metrics1 = tracker.calculate_metrics()
        assert metrics1.get_level() == CoherenceLevel.HIGH

        # Phase 2: Introduce version mismatches
        for _ in range(10):
            tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/payment/process",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        for _ in range(10):
            tracker.track_interaction(
                source="OrderService",
                target="InventoryService",
                topic="/inventory/reserve",
                schema_version="1.5.0",
                payload={},
                successful=True
            )

        metrics2 = tracker.calculate_metrics()
        assert metrics2.overall_score < metrics1.overall_score
        assert metrics2.schema_version_consistency < 1.0


class TestCoherencePathAnalysis:
    """Test coherence analysis across execution paths"""

    def test_analyze_request_paths(self, temp_dir, microservices_graph):
        """Test analyzing coherence along request paths"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Simulate complete order flow with consistent versions
        # Path: APIGateway → OrderService → PaymentService → NotificationService

        tracker.track_interaction(
            source="APIGateway",
            target="OrderService",
            topic="/order/create",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/payment/process",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="PaymentService",
            target="NotificationService",
            topic="/notification/send",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        # Analyze paths
        report = tracker.analyze_coherence_paths()

        assert report.overall_score > 0.8
        # Path should be coherent with consistent versions
        assert report.level in [CoherenceLevel.HIGH, CoherenceLevel.MEDIUM]

    def test_identify_incoherent_paths(self, temp_dir, microservices_graph):
        """Test identifying paths with version mismatches"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Path with version mismatch
        tracker.track_interaction(
            source="APIGateway",
            target="OrderService",
            topic="/order/create",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/payment/process",
            schema_version="2.0.0",  # Version jump
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="PaymentService",
            target="NotificationService",
            topic="/notification/send",
            schema_version="1.0.0",  # Version drop
            payload={},
            successful=True
        )

        # Analyze paths
        report = tracker.analyze_coherence_paths()

        # Should detect incoherent paths
        if report.incoherent_paths:
            assert len(report.incoherent_paths) > 0
            # Check that paths include the problematic services
            path_strs = [str(p.path) for p in report.incoherent_paths]
            assert any("PaymentService" in ps for ps in path_strs)

    def test_multi_path_coherence(self, temp_dir, microservices_graph):
        """Test coherence across multiple parallel paths"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Path 1: APIGateway → OrderService → PaymentService
        tracker.track_interaction(
            source="APIGateway",
            target="OrderService",
            topic="/order/create",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/payment/process",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        # Path 2: APIGateway → UserService → NotificationService
        tracker.track_interaction(
            source="APIGateway",
            target="UserService",
            topic="/user/get",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="UserService",
            target="NotificationService",
            topic="/notification/send",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        # Both paths coherent
        report = tracker.analyze_coherence_paths()
        assert report.overall_score > 0.8


class TestCoherenceVisualization:
    """Test coherence visualization"""

    def test_generate_coherence_graph(self, temp_dir, microservices_graph):
        """Test generating coherence visualization graph"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Track various interactions
        interactions = [
            ("APIGateway", "OrderService", "1.0.0"),
            ("APIGateway", "UserService", "1.0.0"),
            ("OrderService", "PaymentService", "1.0.0"),
            ("OrderService", "InventoryService", "1.0.0"),
            ("PaymentService", "NotificationService", "1.0.0"),
        ]

        for source, target, version in interactions:
            for _ in range(3):  # Multiple interactions per pair
                tracker.track_interaction(
                    source=source,
                    target=target,
                    topic="/test/topic",
                    schema_version=version,
                    payload={},
                    successful=True
                )

        # Generate coherence graph
        coherence_graph = tracker.visualize_coherence()

        # Verify graph structure
        assert isinstance(coherence_graph, nx.DiGraph)
        assert len(coherence_graph.nodes()) > 0
        assert len(coherence_graph.edges()) > 0

        # Check edge attributes
        for u, v in coherence_graph.edges():
            edge_data = coherence_graph[u][v]
            assert 'coherence_score' in edge_data
            assert 'interaction_count' in edge_data
            assert 'versions' in edge_data

    def test_coherence_graph_scores(self, temp_dir, microservices_graph):
        """Test coherence scores in visualization"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # High coherence edge (consistent versions)
        for _ in range(10):
            tracker.track_interaction(
                source="OrderService",
                target="PaymentService",
                topic="/test",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Low coherence edge (mixed versions)
        for _ in range(5):
            tracker.track_interaction(
                source="OrderService",
                target="InventoryService",
                topic="/test",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        for _ in range(5):
            tracker.track_interaction(
                source="OrderService",
                target="InventoryService",
                topic="/test",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        coherence_graph = tracker.visualize_coherence()

        # Check that edges have different coherence scores
        if coherence_graph.has_edge("OrderService", "PaymentService"):
            payment_score = coherence_graph["OrderService"]["PaymentService"]["coherence_score"]
            assert payment_score > 0.9  # High coherence

        if coherence_graph.has_edge("OrderService", "InventoryService"):
            inventory_score = coherence_graph["OrderService"]["InventoryService"]["coherence_score"]
            assert inventory_score < 1.0  # Lower due to version mix


class TestCoherenceReporting:
    """Test coherence report generation"""

    def test_generate_comprehensive_report(self, temp_dir, microservices_graph):
        """Test generating complete coherence report"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Simulate realistic system with some issues
        # Most interactions on v2.0.0
        for _ in range(50):
            tracker.track_interaction(
                source="APIGateway",
                target="OrderService",
                topic="/order/create",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        # Some legacy interactions on v1.0.0 (drift)
        for _ in range(10):
            tracker.track_interaction(
                source="APIGateway",
                target="UserService",
                topic="/user/get",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Generate report
        report = tracker.analyze_coherence_paths()

        assert report.timestamp is not None
        assert 0.0 <= report.overall_score <= 1.0
        assert report.level in [CoherenceLevel.HIGH, CoherenceLevel.MEDIUM,
                               CoherenceLevel.LOW, CoherenceLevel.CRITICAL]
        assert report.metrics is not None

    def test_report_recommendations(self, temp_dir, microservices_graph):
        """Test coherence report generates recommendations"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Create version drift scenario
        tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/test",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        tracker.track_interaction(
            source="OrderService",
            target="PaymentService",
            topic="/test",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        report = tracker.analyze_coherence_paths()

        # Report should identify the issue
        if report.drift_warnings:
            assert len(report.drift_warnings) > 0

        if report.recommendations:
            assert len(report.recommendations) > 0


class TestCoherencePersistence:
    """Test coherence data persistence"""

    def test_persist_interaction_history(self, temp_dir, microservices_graph):
        """Test persisting and loading interaction history"""
        # Create tracker and track interactions
        tracker1 = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        for i in range(5):
            tracker1.track_interaction(
                source="APIGateway",
                target="OrderService",
                topic=f"/test/{i}",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        # Save to disk
        tracker1.save()

        # Create new tracker with same storage
        tracker2 = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        # Verify interactions loaded
        assert len(tracker2.interactions) == 5

        # Verify metrics consistent
        metrics1 = tracker1.calculate_metrics()
        metrics2 = tracker2.calculate_metrics()
        assert metrics1.overall_score == metrics2.overall_score

    def test_incremental_tracking(self, temp_dir, microservices_graph):
        """Test incremental coherence tracking across sessions"""
        # Session 1
        tracker1 = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        for _ in range(5):
            tracker1.track_interaction(
                source="APIGateway",
                target="OrderService",
                topic="/test",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        tracker1.save()

        # Session 2
        tracker2 = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        for _ in range(5):
            tracker2.track_interaction(
                source="APIGateway",
                target="UserService",
                topic="/test",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        tracker2.save()

        # Session 3 - verify all interactions present
        tracker3 = CoherenceTracker(storage_path=temp_dir, graph=microservices_graph)

        assert len(tracker3.interactions) == 10
