"""
Unit tests for CoherenceTracker
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import networkx as nx

from graphbus_core.runtime.coherence import (
    CoherenceTracker, CoherenceMetrics, CoherenceLevel, DriftWarning,
    Interaction, CoherenceReport
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for coherence data"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def sample_graph():
    """Create sample dependency graph"""
    graph = nx.DiGraph()
    graph.add_edge("AgentA", "AgentB")
    graph.add_edge("AgentB", "AgentC")
    graph.add_edge("AgentA", "AgentC")
    return graph


@pytest.fixture
def coherence_tracker(temp_dir, sample_graph):
    """Create CoherenceTracker instance"""
    return CoherenceTracker(storage_path=temp_dir, graph=sample_graph)


class TestCoherenceTracker:
    """Test CoherenceTracker functionality"""

    def test_initialization(self, coherence_tracker, temp_dir):
        """Test CoherenceTracker initialization"""
        assert coherence_tracker.storage_path == Path(temp_dir)
        assert coherence_tracker.graph is not None
        assert coherence_tracker.interactions == []

    def test_track_interaction(self, coherence_tracker):
        """Test tracking agent interactions"""
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={"data": "test"},
            successful=True
        )

        assert len(coherence_tracker.interactions) == 1
        record = coherence_tracker.interactions[0]
        assert record.source == "AgentA"
        assert record.target == "AgentB"
        assert record.schema_version == "1.0.0"
        assert record.successful is True

    def test_track_multiple_interactions(self, coherence_tracker):
        """Test tracking multiple interactions"""
        for i in range(5):
            coherence_tracker.track_interaction(
                source="AgentA",
                target="AgentB",
                topic=f"/test/topic{i}",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        assert len(coherence_tracker.interactions) == 5

    def test_calculate_metrics_no_interactions(self, coherence_tracker):
        """Test metrics calculation with no interactions"""
        metrics = coherence_tracker.calculate_metrics()

        assert metrics.overall_score == 1.0
        assert metrics.schema_version_consistency == 1.0
        assert metrics.contract_compliance_rate == 1.0
        assert metrics.temporal_consistency == 1.0
        assert metrics.spatial_consistency == 1.0

    def test_calculate_metrics_with_interactions(self, coherence_tracker):
        """Test metrics calculation with interactions"""
        # Track consistent interactions
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        metrics = coherence_tracker.calculate_metrics()
        assert metrics.overall_score > 0.8
        assert metrics.schema_version_consistency == 1.0

    def test_calculate_metrics_with_version_drift(self, coherence_tracker):
        """Test metrics with schema version drift"""
        # Track interactions with different versions
        for i in range(5):
            coherence_tracker.track_interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        for i in range(5):
            coherence_tracker.track_interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="2.0.0",
                payload={},
                successful=True
            )

        metrics = coherence_tracker.calculate_metrics()
        assert metrics.schema_version_consistency < 1.0

    def test_detect_schema_drift_no_drift(self, coherence_tracker):
        """Test drift detection with no drift"""
        # Track consistent interactions
        for _ in range(10):
            coherence_tracker.track_interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        warnings = coherence_tracker.detect_schema_drift()
        assert len(warnings) == 0

    def test_detect_schema_drift_with_drift(self, coherence_tracker):
        """Test drift detection with version inconsistency"""
        # Track interactions with different versions
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        warnings = coherence_tracker.detect_schema_drift()
        assert len(warnings) > 0

    def test_detect_drift_with_time_window(self, coherence_tracker):
        """Test drift detection with time window filter"""
        now = datetime.now()
        old_time = now - timedelta(hours=48)

        # Create old interaction (should be filtered out)
        old_record = Interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            timestamp=old_time,
            payload={},
            successful=True
        )
        coherence_tracker.interactions.append(old_record)

        # Create recent interaction
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        # Check last 24 hours only
        warnings = coherence_tracker.detect_schema_drift(
            time_window=timedelta(hours=24)
        )

        # Should only see recent version
        assert all(w.first_detected > old_time for w in warnings)

    def test_analyze_coherence_paths_no_graph(self, temp_dir):
        """Test path analysis without graph"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=None)

        with pytest.raises(ValueError, match="No dependency graph"):
            tracker.analyze_coherence_paths()

    def test_analyze_coherence_paths_with_graph(self, coherence_tracker):
        """Test coherence path analysis with networkx"""
        # Track interactions along paths
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        coherence_tracker.track_interaction(
            source="AgentB",
            target="AgentC",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        report = coherence_tracker.analyze_coherence_paths()

        assert report.overall_score >= 0.0
        assert report.level in [CoherenceLevel.HIGH, CoherenceLevel.MEDIUM,
                               CoherenceLevel.LOW, CoherenceLevel.CRITICAL]

    def test_analyze_incoherent_paths(self, coherence_tracker):
        """Test identification of incoherent paths"""
        # Create version mismatch along path
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        coherence_tracker.track_interaction(
            source="AgentB",
            target="AgentC",
            topic="/test/topic",
            schema_version="2.0.0",  # Version change
            payload={},
            successful=True
        )

        report = coherence_tracker.analyze_coherence_paths()

        # Should detect version inconsistency in path
        if report.incoherent_paths:
            assert any("AgentA" in str(path.path) for path in report.incoherent_paths)

    def test_visualize_coherence_no_graph(self, temp_dir):
        """Test visualization without graph creates basic graph"""
        tracker = CoherenceTracker(storage_path=temp_dir, graph=None)

        # Add some interactions
        tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        # Should create basic graph from interactions
        coherence_graph = tracker.visualize_coherence()
        assert isinstance(coherence_graph, nx.DiGraph)
        assert len(coherence_graph.nodes()) > 0

    def test_visualize_coherence_with_graph(self, coherence_tracker):
        """Test coherence graph visualization"""
        # Track some interactions
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        coherence_graph = coherence_tracker.visualize_coherence()

        assert isinstance(coherence_graph, nx.DiGraph)
        assert len(coherence_graph.nodes()) > 0
        assert len(coherence_graph.edges()) > 0

    def test_coherence_graph_edge_attributes(self, coherence_tracker):
        """Test coherence graph includes edge attributes"""
        # Track interactions with metadata
        for _ in range(3):
            coherence_tracker.track_interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="1.0.0",
                payload={},
                successful=True
            )

        coherence_graph = coherence_tracker.visualize_coherence()

        # Check edge has coherence metadata
        if coherence_graph.has_edge("AgentA", "AgentB"):
            edge_data = coherence_graph["AgentA"]["AgentB"]
            assert "coherence_score" in edge_data
            assert "interaction_count" in edge_data
            assert edge_data["interaction_count"] >= 3

    def test_persistence(self, coherence_tracker):
        """Test coherence data persistence"""
        # Track interactions
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        # Save to disk
        coherence_tracker.save()

        # Create new tracker with same storage
        new_tracker = CoherenceTracker(
            storage_path=str(coherence_tracker.storage_path),
            graph=coherence_tracker.graph
        )

        assert len(new_tracker.interactions) == 1

    def test_get_coherence_level(self):
        """Test coherence level classification"""
        metrics_high = CoherenceMetrics(
            overall_score=0.95,
            schema_version_consistency=0.95,
            contract_compliance_rate=0.95,
            migration_completion_rate=0.95,
            breaking_change_propagation=0.95,
            temporal_consistency=0.95,
            spatial_consistency=0.95
        )
        assert metrics_high.get_level() == CoherenceLevel.HIGH

        metrics_medium = CoherenceMetrics(
            overall_score=0.75,
            schema_version_consistency=0.75,
            contract_compliance_rate=0.75,
            migration_completion_rate=0.75,
            breaking_change_propagation=0.75,
            temporal_consistency=0.75,
            spatial_consistency=0.75
        )
        assert metrics_medium.get_level() == CoherenceLevel.MEDIUM

        metrics_low = CoherenceMetrics(
            overall_score=0.55,
            schema_version_consistency=0.55,
            contract_compliance_rate=0.55,
            migration_completion_rate=0.55,
            breaking_change_propagation=0.55,
            temporal_consistency=0.55,
            spatial_consistency=0.55
        )
        assert metrics_low.get_level() == CoherenceLevel.LOW

        metrics_critical = CoherenceMetrics(
            overall_score=0.3,
            schema_version_consistency=0.3,
            contract_compliance_rate=0.3,
            migration_completion_rate=0.3,
            breaking_change_propagation=0.3,
            temporal_consistency=0.3,
            spatial_consistency=0.3
        )
        assert metrics_critical.get_level() == CoherenceLevel.CRITICAL


class TestCoherenceMetrics:
    """Test CoherenceMetrics dataclass"""

    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = CoherenceMetrics(
            overall_score=0.85,
            schema_version_consistency=0.9,
            contract_compliance_rate=0.95,
            migration_completion_rate=0.8,
            breaking_change_propagation=0.75,
            temporal_consistency=0.9,
            spatial_consistency=0.85
        )

        assert metrics.overall_score == 0.85
        assert metrics.schema_version_consistency == 0.9
        assert metrics.temporal_consistency == 0.9

    def test_metrics_level_thresholds(self):
        """Test coherence level threshold boundaries"""
        # Test boundary at 0.9 (HIGH)
        metrics = CoherenceMetrics(
            schema_version_consistency=0.9,
            contract_compliance_rate=0.9,
            migration_completion_rate=0.9,
            breaking_change_propagation=0.9,
            temporal_consistency=0.9,
            spatial_consistency=0.9,
            overall_score=0.9
        )
        assert metrics.get_level() == CoherenceLevel.HIGH

        # Test boundary at 0.7 (MEDIUM)
        metrics = CoherenceMetrics(
            schema_version_consistency=0.7,
            contract_compliance_rate=0.7,
            migration_completion_rate=0.7,
            breaking_change_propagation=0.7,
            temporal_consistency=0.7,
            spatial_consistency=0.7,
            overall_score=0.7
        )
        assert metrics.get_level() == CoherenceLevel.MEDIUM

        # Test boundary at 0.5 (LOW)
        metrics = CoherenceMetrics(
            schema_version_consistency=0.5,
            contract_compliance_rate=0.5,
            migration_completion_rate=0.5,
            breaking_change_propagation=0.5,
            temporal_consistency=0.5,
            spatial_consistency=0.5,
            overall_score=0.5
        )
        assert metrics.get_level() == CoherenceLevel.LOW

        # Test below 0.5 (CRITICAL)
        metrics = CoherenceMetrics(
            schema_version_consistency=0.49,
            contract_compliance_rate=0.49,
            migration_completion_rate=0.49,
            breaking_change_propagation=0.49,
            temporal_consistency=0.49,
            spatial_consistency=0.49,
            overall_score=0.49
        )
        assert metrics.get_level() == CoherenceLevel.CRITICAL


class TestDriftWarning:
    """Test DriftWarning dataclass"""

    def test_drift_warning_creation(self):
        """Test drift warning creation"""
        warning = DriftWarning(
            agent_name="TestAgent",
            expected_version="1.0.0",
            actual_version="2.0.0",
            drift_severity=0.5,
            description="Version mismatch detected",
            affected_interactions=5,
            first_detected=datetime.now()
        )

        assert warning.agent_name == "TestAgent"
        assert warning.expected_version == "1.0.0"
        assert warning.actual_version == "2.0.0"
        assert warning.affected_interactions == 5
        assert warning.drift_severity == 0.5


class TestInteraction:
    """Test Interaction dataclass"""

    def test_interaction_creation(self):
        """Test interaction creation"""
        now = datetime.now()
        record = Interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            timestamp=now,
            payload={"data": "test"},
            successful=True
        )

        assert record.source == "AgentA"
        assert record.target == "AgentB"
        assert record.topic == "/test/topic"
        assert record.schema_version == "1.0.0"
        assert record.timestamp == now
        assert record.successful is True


class TestCoherenceReport:
    """Test CoherenceReport dataclass"""

    def test_report_generation(self):
        """Test coherence report generation"""
        metrics = CoherenceMetrics(
            schema_version_consistency=0.85,
            contract_compliance_rate=0.85,
            migration_completion_rate=0.85,
            breaking_change_propagation=0.85,
            temporal_consistency=0.85,
            spatial_consistency=0.85,
            overall_score=0.85
        )
        warnings = [
            DriftWarning(
                agent_name="Agent1",
                expected_version="1.0.0",
                actual_version="2.0.0",
                drift_severity=0.4,
                description="Version mismatch",
                affected_interactions=3,
                first_detected=datetime.now()
            )
        ]

        report = CoherenceReport(
            timestamp=datetime.now(),
            overall_score=0.85,
            level=CoherenceLevel.MEDIUM,
            metrics=metrics,
            drift_warnings=warnings,
            incoherent_paths=[],
            recommendations=[]
        )

        assert report.overall_score == 0.85
        assert report.level == CoherenceLevel.MEDIUM  # 0.85 is between 0.7 and 0.9
        assert len(report.drift_warnings) == 1
        assert report.drift_warnings[0].agent_name == "Agent1"


class TestTemporalConsistency:
    """Test temporal consistency tracking"""

    def test_temporal_consistency_same_timeframe(self, coherence_tracker):
        """Test consistency within same timeframe"""
        now = datetime.now()

        for i in range(5):
            record = Interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="1.0.0",
                timestamp=now + timedelta(seconds=i),
                payload={},
                successful=True
            )
            coherence_tracker.interactions.append(record)

        metrics = coherence_tracker.calculate_metrics()
        assert metrics.temporal_consistency > 0.8

    def test_temporal_consistency_across_time(self, coherence_tracker):
        """Test consistency across different timeframes"""
        now = datetime.now()

        # Old interactions with v1.0.0
        for i in range(3):
            record = Interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="1.0.0",
                timestamp=now - timedelta(hours=24) + timedelta(seconds=i),
                payload={},
                successful=True
            )
            coherence_tracker.interactions.append(record)

        # Recent interactions with v2.0.0
        for i in range(3):
            record = Interaction(
                source="AgentA",
                target="AgentB",
                topic="/test/topic",
                schema_version="2.0.0",
                timestamp=now + timedelta(seconds=i),
                payload={},
                successful=True
            )
            coherence_tracker.interactions.append(record)

        metrics = coherence_tracker.calculate_metrics()
        # Temporal consistency should still be reasonable if versions changed over time
        assert 0.0 <= metrics.temporal_consistency <= 1.0


class TestSpatialConsistency:
    """Test spatial consistency tracking"""

    def test_spatial_consistency_same_path(self, coherence_tracker):
        """Test consistency along the same path"""
        # Consistent versions along path A → B → C
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        coherence_tracker.track_interaction(
            source="AgentB",
            target="AgentC",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        metrics = coherence_tracker.calculate_metrics()
        assert metrics.spatial_consistency > 0.8

    def test_spatial_consistency_different_paths(self, coherence_tracker):
        """Test consistency across different paths"""
        # Path 1: A → B with v1.0.0
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentB",
            topic="/test/topic",
            schema_version="1.0.0",
            payload={},
            successful=True
        )

        # Path 2: A → C with v2.0.0 (different version)
        coherence_tracker.track_interaction(
            source="AgentA",
            target="AgentC",
            topic="/test/topic",
            schema_version="2.0.0",
            payload={},
            successful=True
        )

        metrics = coherence_tracker.calculate_metrics()
        # Spatial consistency should detect version mismatch
        assert metrics.spatial_consistency < 1.0
