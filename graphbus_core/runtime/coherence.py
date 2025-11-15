"""
Long-Form Coherence Tracking

This module tracks and maintains coherence across agent interactions over time,
detecting schema drift and using networkx to analyze consistency along execution paths.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import networkx as nx


class CoherenceLevel(Enum):
    """Coherence level classifications"""
    HIGH = "high"                # 0.9-1.0
    MEDIUM = "medium"            # 0.7-0.9
    LOW = "low"                  # 0.5-0.7
    CRITICAL = "critical"        # 0.0-0.5


@dataclass
class Interaction:
    """Record of an interaction between agents"""
    source: str
    target: str
    topic: str
    schema_version: str
    payload: Dict[str, Any]
    timestamp: datetime
    successful: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "source": self.source,
            "target": self.target,
            "topic": self.topic,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "successful": self.successful,
            "error": self.error
        }


@dataclass
class DriftWarning:
    """Warning about schema drift"""
    agent_name: str
    expected_version: str
    actual_version: str
    drift_severity: float  # 0-1
    description: str
    affected_interactions: int
    first_detected: datetime


@dataclass
class IncoherentPath:
    """Represents an incoherent execution path"""
    path: List[str]
    coherence_score: float
    issues: List[str]
    recommendation: str


@dataclass
class UpdateRecommendation:
    """Recommendation for maintaining coherence"""
    agent_name: str
    current_version: str
    recommended_version: str
    priority: str  # "high", "medium", "low"
    reason: str
    affected_agents: List[str]


@dataclass
class CoherenceMetrics:
    """Coherence metrics for an agent or system"""
    schema_version_consistency: float  # 0-1
    contract_compliance_rate: float    # 0-1
    migration_completion_rate: float   # 0-1
    breaking_change_propagation: float # 0-1
    temporal_consistency: float        # 0-1
    spatial_consistency: float         # 0-1
    overall_score: float              # 0-1

    def get_level(self) -> CoherenceLevel:
        """Get coherence level based on score"""
        score = self.overall_score
        if score >= 0.9:
            return CoherenceLevel.HIGH
        elif score >= 0.7:
            return CoherenceLevel.MEDIUM
        elif score >= 0.5:
            return CoherenceLevel.LOW
        else:
            return CoherenceLevel.CRITICAL


@dataclass
class CoherenceReport:
    """Comprehensive coherence report"""
    timestamp: datetime
    overall_score: float
    level: CoherenceLevel
    metrics: CoherenceMetrics
    drift_warnings: List[DriftWarning] = field(default_factory=list)
    incoherent_paths: List[IncoherentPath] = field(default_factory=list)
    recommendations: List[UpdateRecommendation] = field(default_factory=list)


class CoherenceTracker:
    """
    Tracks and maintains coherence across agent interactions.
    Uses networkx for path analysis and consistency checking.
    """

    def __init__(self, storage_path: str = ".graphbus/coherence", graph: nx.DiGraph = None):
        """
        Initialize coherence tracker

        Args:
            storage_path: Directory to store coherence data
            graph: NetworkX dependency graph for path analysis
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.graph = graph

        # Interaction history
        self.interactions: List[Interaction] = []

        # Agent version tracking
        self.agent_versions: Dict[str, List[Tuple[str, datetime]]] = defaultdict(list)

        # Schema version tracking per topic
        self.topic_versions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Load persisted data if available
        self._load_data()

        # Coherence threshold
        self.coherence_threshold = 0.8

    def _load_data(self):
        """Load coherence data from storage"""
        interactions_file = self.storage_path / "interactions.json"
        if interactions_file.exists():
            try:
                with open(interactions_file, 'r') as f:
                    data = json.load(f)
                    for item in data[-10000:]:  # Keep last 10000 interactions
                        interaction = Interaction(
                            source=item["source"],
                            target=item["target"],
                            topic=item["topic"],
                            schema_version=item["schema_version"],
                            payload=item["payload"],
                            timestamp=datetime.fromisoformat(item["timestamp"]),
                            successful=item.get("successful", True),
                            error=item.get("error")
                        )
                        self.interactions.append(interaction)

                        # Rebuild topic_versions tracking
                        self.topic_versions[interaction.topic][interaction.schema_version] += 1
            except Exception as e:
                print(f"Warning: Failed to load interactions: {e}")

    def _save_data(self):
        """Save coherence data to storage"""
        interactions_file = self.storage_path / "interactions.json"

        # Keep last 10000 interactions
        recent_interactions = self.interactions[-10000:]
        data = [i.to_dict() for i in recent_interactions]

        with open(interactions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def save(self):
        """Public method to save coherence data"""
        self._save_data()

    def create_interaction_record(self, source: str, target: str, topic: str,
                                  schema_version: str, payload: Dict[str, Any],
                                  successful: bool = True, error: Optional[str] = None) -> Interaction:
        """
        Create an Interaction record without tracking it.

        This is useful for tests that want to manipulate the timestamp
        before adding to the interactions list.

        Args:
            source: Source agent name
            target: Target agent name
            topic: Event topic
            schema_version: Schema version used
            payload: Event payload
            successful: Whether interaction was successful
            error: Error message if failed

        Returns:
            Interaction object
        """
        return Interaction(
            source=source,
            target=target,
            topic=topic,
            schema_version=schema_version,
            payload=payload,
            timestamp=datetime.now(),
            successful=successful,
            error=error
        )

    def track_interaction(self, source: str, target: str, topic: str,
                         schema_version: str, payload: Dict[str, Any],
                         successful: bool = True, error: Optional[str] = None):
        """
        Track an interaction between agents

        Args:
            source: Source agent name
            target: Target agent name
            topic: Event topic
            schema_version: Schema version used
            payload: Event payload
            successful: Whether interaction was successful
            error: Error message if failed
        """
        interaction = Interaction(
            source=source,
            target=target,
            topic=topic,
            schema_version=schema_version,
            payload=payload,
            timestamp=datetime.now(),
            successful=successful,
            error=error
        )

        self.interactions.append(interaction)

        # Track version usage
        self.topic_versions[topic][schema_version] += 1

        # Periodically save (every 100 interactions)
        if len(self.interactions) % 100 == 0:
            self._save_data()

    def detect_schema_drift(self, time_window: Optional[timedelta] = None) -> List[DriftWarning]:
        """
        Detect schema drift between agents over time

        Args:
            time_window: Optional time window to check (all time if None)

        Returns:
            List of drift warnings
        """
        warnings = []

        # Filter interactions by time window
        if time_window:
            cutoff = datetime.now() - time_window
            recent_interactions = [i for i in self.interactions if i.timestamp >= cutoff]
        else:
            recent_interactions = self.interactions

        # Group by topic
        topic_interactions: Dict[str, List[Interaction]] = defaultdict(list)
        for interaction in recent_interactions:
            topic_interactions[interaction.topic].append(interaction)

        # Check for version drift in each topic
        for topic, interactions in topic_interactions.items():
            # Find version distribution
            version_counts = defaultdict(int)
            for interaction in interactions:
                version_counts[interaction.schema_version] += 1

            # If multiple versions in use, check drift
            if len(version_counts) > 1:
                total = sum(version_counts.values())
                sorted_versions = sorted(version_counts.items(), key=lambda x: x[1], reverse=True)

                dominant_version = sorted_versions[0][0]
                dominant_count = sorted_versions[0][1]

                # Check other versions
                for version, count in sorted_versions[1:]:
                    drift_severity = count / total

                    if drift_severity > 0.1:  # More than 10% using old version
                        # Find affected agents
                        affected_agents = set(i.source for i in interactions
                                            if i.schema_version == version)

                        for agent in affected_agents:
                            first_detected = min(i.timestamp for i in interactions
                                               if i.source == agent and i.schema_version == version)

                            warnings.append(DriftWarning(
                                agent_name=agent,
                                expected_version=dominant_version,
                                actual_version=version,
                                drift_severity=drift_severity,
                                description=f"Agent using outdated schema version {version} for topic {topic}",
                                affected_interactions=count,
                                first_detected=first_detected
                            ))

        return warnings

    def get_coherence_score(self, agent_name: Optional[str] = None) -> float:
        """
        Calculate coherence score (0-1) for agent or system

        Args:
            agent_name: Optional agent name (system-wide if None)

        Returns:
            Coherence score between 0 and 1
        """
        metrics = self.calculate_metrics(agent_name)
        return metrics.overall_score

    def calculate_metrics(self, agent_name: Optional[str] = None) -> CoherenceMetrics:
        """
        Calculate detailed coherence metrics

        Args:
            agent_name: Optional agent name (system-wide if None)

        Returns:
            CoherenceMetrics object
        """
        # Filter interactions
        if agent_name:
            interactions = [i for i in self.interactions
                          if i.source == agent_name or i.target == agent_name]
        else:
            interactions = self.interactions

        if not interactions:
            # No interactions = perfect coherence (nothing to be incoherent)
            return CoherenceMetrics(
                schema_version_consistency=1.0,
                contract_compliance_rate=1.0,
                migration_completion_rate=1.0,
                breaking_change_propagation=1.0,
                temporal_consistency=1.0,
                spatial_consistency=1.0,
                overall_score=1.0
            )

        # Schema version consistency
        topic_version_consistency = []
        for topic, version_counts in self.topic_versions.items():
            if version_counts:
                total = sum(version_counts.values())
                max_count = max(version_counts.values())
                consistency = max_count / total
                topic_version_consistency.append(consistency)

        schema_consistency = sum(topic_version_consistency) / len(topic_version_consistency) if topic_version_consistency else 0

        # Contract compliance rate (successful interactions)
        successful = sum(1 for i in interactions if i.successful)
        compliance_rate = successful / len(interactions) if interactions else 0

        # Migration completion rate (placeholder - would check actual migration records)
        migration_rate = 0.85  # TODO: Calculate from migration manager

        # Breaking change propagation (placeholder)
        propagation = 0.9  # TODO: Calculate based on contract manager

        # Temporal consistency (same agent over time)
        temporal = self._calculate_temporal_consistency(agent_name, interactions)

        # Spatial consistency (different agents at same time)
        spatial = self._calculate_spatial_consistency(interactions)

        # Overall score (weighted average)
        overall = (
            schema_consistency * 0.25 +
            compliance_rate * 0.20 +
            migration_rate * 0.15 +
            propagation * 0.10 +
            temporal * 0.15 +
            spatial * 0.15
        )

        return CoherenceMetrics(
            schema_version_consistency=schema_consistency,
            contract_compliance_rate=compliance_rate,
            migration_completion_rate=migration_rate,
            breaking_change_propagation=propagation,
            temporal_consistency=temporal,
            spatial_consistency=spatial,
            overall_score=overall
        )

    def _calculate_temporal_consistency(self, agent_name: Optional[str],
                                       interactions: List[Interaction]) -> float:
        """Calculate temporal consistency (same agent over time)"""
        if not interactions:
            return 1.0

        # Group by agent
        agent_interactions: Dict[str, List[Interaction]] = defaultdict(list)
        for interaction in interactions:
            agent_interactions[interaction.source].append(interaction)

        consistency_scores = []

        for agent, agent_ints in agent_interactions.items():
            if len(agent_ints) < 2:
                continue

            # Sort by time
            sorted_ints = sorted(agent_ints, key=lambda i: i.timestamp)

            # Check version changes
            version_changes = 0
            current_version = sorted_ints[0].schema_version

            for interaction in sorted_ints[1:]:
                if interaction.schema_version != current_version:
                    version_changes += 1
                    current_version = interaction.schema_version

            # Lower score for frequent changes
            consistency = 1.0 - (version_changes / len(sorted_ints))
            consistency_scores.append(consistency)

        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0

    def _calculate_spatial_consistency(self, interactions: List[Interaction]) -> float:
        """Calculate spatial consistency (different agents at same time)"""
        if not interactions:
            return 1.0

        # Group by time windows (1 hour buckets)
        time_buckets: Dict[datetime, List[Interaction]] = defaultdict(list)

        for interaction in interactions:
            bucket = interaction.timestamp.replace(minute=0, second=0, microsecond=0)
            time_buckets[bucket].append(interaction)

        consistency_scores = []

        for bucket, bucket_ints in time_buckets.items():
            if len(bucket_ints) < 2:
                continue

            # Check version consistency within bucket
            versions = [i.schema_version for i in bucket_ints]
            unique_versions = set(versions)

            # Higher score for fewer versions in same time window
            consistency = 1.0 - ((len(unique_versions) - 1) / len(versions))
            consistency_scores.append(max(0, consistency))

        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0

    def analyze_coherence_paths(self) -> CoherenceReport:
        """
        Use networkx to analyze coherence across execution paths

        Returns:
            CoherenceReport with incoherent paths and recommendations
        """
        if not self.graph:
            raise ValueError("No dependency graph available for path analysis")

        metrics = self.calculate_metrics()
        report = CoherenceReport(
            timestamp=datetime.now(),
            overall_score=self.get_coherence_score(),
            level=metrics.get_level(),
            metrics=metrics
        )

        # Find incoherent paths
        incoherent_paths = []

        for source in self.graph.nodes():
            for target in self.graph.nodes():
                if source == target:
                    continue

                try:
                    # Get all simple paths up to length 5
                    paths = nx.all_simple_paths(self.graph, source, target, cutoff=5)

                    for path in paths:
                        score = self._check_path_coherence(path)

                        if score < self.coherence_threshold:
                            issues = self._identify_path_issues(path)
                            recommendation = self._generate_path_recommendation(path, issues)

                            incoherent_paths.append(IncoherentPath(
                                path=path,
                                coherence_score=score,
                                issues=issues,
                                recommendation=recommendation
                            ))

                except nx.NetworkXNoPath:
                    continue

        report.incoherent_paths = incoherent_paths

        # Detect drift warnings
        report.drift_warnings = self.detect_schema_drift()

        # Generate recommendations
        report.recommendations = self.recommend_updates()

        return report

    def _check_path_coherence(self, path: List[str]) -> float:
        """Check coherence along a path"""
        if len(path) < 2:
            return 1.0

        # Find interactions along this path
        path_interactions = []
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]

            matching = [inter for inter in self.interactions
                       if inter.source == source and inter.target == target]
            path_interactions.extend(matching)

        if not path_interactions:
            return 1.0  # No data, assume coherent

        # Check version consistency
        versions = [i.schema_version for i in path_interactions]
        unique_versions = set(versions)

        # Higher score for fewer versions
        base_score = 1.0 - ((len(unique_versions) - 1) / len(versions))

        # Penalize failures
        failures = sum(1 for i in path_interactions if not i.successful)
        failure_penalty = failures / len(path_interactions)

        return max(0, base_score - failure_penalty)

    def _identify_path_issues(self, path: List[str]) -> List[str]:
        """Identify issues along a path"""
        issues = []

        # Check for version mismatches
        path_interactions = []
        for i in range(len(path) - 1):
            matching = [inter for inter in self.interactions
                       if inter.source == path[i] and inter.target == path[i + 1]]
            path_interactions.extend(matching)

        if path_interactions:
            versions = set(i.schema_version for i in path_interactions)
            if len(versions) > 1:
                issues.append(f"Multiple schema versions in use: {', '.join(versions)}")

            failures = [i for i in path_interactions if not i.successful]
            if failures:
                issues.append(f"{len(failures)} failed interactions")

        return issues

    def _generate_path_recommendation(self, path: List[str], issues: List[str]) -> str:
        """Generate recommendation for fixing path coherence"""
        if not issues:
            return "No specific recommendations"

        recommendations = []

        if any("Multiple schema versions" in issue for issue in issues):
            recommendations.append(f"Synchronize schema versions across agents in path: {' -> '.join(path)}")

        if any("failed interactions" in issue for issue in issues):
            recommendations.append("Investigate and fix interaction failures")

        return "; ".join(recommendations)

    def recommend_updates(self) -> List[UpdateRecommendation]:
        """
        Recommend updates to maintain coherence

        Returns:
            List of update recommendations
        """
        recommendations = []

        # Find agents with drift
        drift_warnings = self.detect_schema_drift()

        for warning in drift_warnings:
            # Find affected downstream agents
            affected = []
            if self.graph and warning.agent_name in self.graph:
                try:
                    affected = list(nx.descendants(self.graph, warning.agent_name))
                except:
                    pass

            priority = "high" if warning.drift_severity > 0.3 else "medium" if warning.drift_severity > 0.1 else "low"

            recommendations.append(UpdateRecommendation(
                agent_name=warning.agent_name,
                current_version=warning.actual_version,
                recommended_version=warning.expected_version,
                priority=priority,
                reason=warning.description,
                affected_agents=affected
            ))

        return recommendations

    def visualize_coherence(self) -> nx.DiGraph:
        """
        Generate networkx graph showing coherence relationships

        Returns:
            NetworkX DiGraph with coherence annotations
        """
        if not self.graph:
            # Create basic graph from interactions
            coherence_graph = nx.DiGraph()

            for interaction in self.interactions:
                if not coherence_graph.has_edge(interaction.source, interaction.target):
                    coherence_graph.add_edge(interaction.source, interaction.target,
                                           interaction_count=0, versions=set(), coherence_score=0.0)

                edge_data = coherence_graph[interaction.source][interaction.target]
                edge_data['interaction_count'] += 1
                edge_data['versions'].add(interaction.schema_version)

            # Calculate coherence scores
            for source, target in coherence_graph.edges():
                matching_interactions = [i for i in self.interactions
                                       if i.source == source and i.target == target]
                if matching_interactions:
                    successful = sum(1 for i in matching_interactions if i.successful)
                    success_rate = successful / len(matching_interactions)

                    # Version consistency factor
                    versions = coherence_graph[source][target]['versions']
                    version_consistency = 1.0 if len(versions) == 1 else 0.8

                    # Overall coherence
                    coherence = success_rate * version_consistency
                    coherence_graph[source][target]['coherence_score'] = coherence

            return coherence_graph

        # Annotate existing graph with coherence data
        coherence_graph = self.graph.copy()

        for source, target in coherence_graph.edges():
            matching_interactions = [i for i in self.interactions
                                   if i.source == source and i.target == target]

            if matching_interactions:
                versions = set(i.schema_version for i in matching_interactions)
                successful = sum(1 for i in matching_interactions if i.successful)
                success_rate = successful / len(matching_interactions)

                # Version consistency factor: penalize if multiple versions are in use
                version_consistency = 1.0 if len(versions) == 1 else 0.8

                # Overall coherence is product of success rate and version consistency
                coherence = success_rate * version_consistency

                coherence_graph[source][target]['coherence_score'] = coherence
                coherence_graph[source][target]['versions'] = versions
                coherence_graph[source][target]['interaction_count'] = len(matching_interactions)
            else:
                # No interactions tracked for this edge - set defaults
                coherence_graph[source][target]['coherence_score'] = 1.0  # No evidence of issues
                coherence_graph[source][target]['versions'] = set()
                coherence_graph[source][target]['interaction_count'] = 0

        return coherence_graph
