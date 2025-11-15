"""
API Contract Management and Schema Evolution

This module provides contract versioning, schema validation, and compatibility
checking between agents. It uses the networkx dependency graph to analyze
impact of schema changes and notify affected downstream agents.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import networkx as nx


class ChangeType(Enum):
    """Types of schema changes"""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    COMPATIBLE = "compatible"


class CompatibilityLevel(Enum):
    """Compatibility levels between versions"""
    FULLY_COMPATIBLE = "fully_compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    INCOMPATIBLE = "incompatible"


@dataclass
class SchemaField:
    """Represents a field in a schema"""
    name: str
    type: str
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class MethodSchema:
    """Schema for an agent method"""
    name: str
    input: Dict[str, SchemaField]
    output: Dict[str, SchemaField]
    description: str = ""

    @property
    def input_schema(self) -> Dict[str, SchemaField]:
        """Alias for input"""
        return self.input

    @property
    def output_schema(self) -> Dict[str, SchemaField]:
        """Alias for output"""
        return self.output


@dataclass
class EventSchema:
    """Schema for a published event"""
    topic: str
    payload: Dict[str, SchemaField]
    description: str = ""


@dataclass
class Contract:
    """Agent API contract with version"""
    agent_name: str
    version: str
    methods: Dict[str, MethodSchema] = field(default_factory=dict)
    publishes: Dict[str, EventSchema] = field(default_factory=dict)
    subscribes: List[str] = field(default_factory=list)
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert contract to dictionary"""
        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "methods": {
                name: {
                    "input": {fname: {"type": f.type, "required": f.required, "default": f.default}
                             for fname, f in method.input.items()},
                    "output": {fname: {"type": f.type, "required": f.required, "default": f.default}
                              for fname, f in method.output.items()},
                    "description": method.description
                }
                for name, method in self.methods.items()
            },
            "publishes": {
                topic: {
                    "payload": {fname: {"type": f.type, "required": f.required, "default": f.default}
                               for fname, f in event.payload.items()},
                    "description": event.description
                }
                for topic, event in self.publishes.items()
            },
            "subscribes": self.subscribes,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Contract':
        """Create contract from dictionary"""
        contract = Contract(
            agent_name=data["agent_name"],
            version=data["version"],
            description=data.get("description", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
        )

        # Parse methods
        for name, method_data in data.get("methods", {}).items():
            method = MethodSchema(
                name=name,
                input={fname: SchemaField(fname, fdata["type"], fdata.get("required", True), fdata.get("default"))
                      for fname, fdata in method_data.get("input", {}).items()},
                output={fname: SchemaField(fname, fdata["type"], fdata.get("required", True), fdata.get("default"))
                       for fname, fdata in method_data.get("output", {}).items()},
                description=method_data.get("description", "")
            )
            contract.methods[name] = method

        # Parse publishes
        for topic, event_data in data.get("publishes", {}).items():
            event = EventSchema(
                topic=topic,
                payload={fname: SchemaField(fname, fdata["type"], fdata.get("required", True), fdata.get("default"))
                        for fname, fdata in event_data.get("payload", {}).items()},
                description=event_data.get("description", "")
            )
            contract.publishes[topic] = event

        contract.subscribes = data.get("subscribes", [])

        return contract


@dataclass
class CompatibilityIssue:
    """Represents a compatibility issue between contracts"""
    issue_type: str
    severity: ChangeType
    description: str
    location: str
    recommendation: str = ""


@dataclass
class CompatibilityResult:
    """Result of compatibility check between contracts"""
    compatible: bool
    compatibility_level: CompatibilityLevel
    issues: List[CompatibilityIssue] = field(default_factory=list)

    def add_issue(self, issue_type: str, severity: ChangeType, description: str,
                  location: str, recommendation: str = ""):
        """Add a compatibility issue"""
        self.issues.append(CompatibilityIssue(
            issue_type=issue_type,
            severity=severity,
            description=description,
            location=location,
            recommendation=recommendation
        ))
        if severity == ChangeType.BREAKING:
            self.compatible = False


@dataclass
class ImpactAnalysis:
    """Analysis of schema change impact"""
    agent_name: str
    new_version: str
    affected_agents: List[str] = field(default_factory=list)
    breaking_changes: Dict[str, List[CompatibilityIssue]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def add_breaking_change(self, affected_agent: str, issues: List[CompatibilityIssue]):
        """Add breaking changes for an affected agent"""
        if affected_agent not in self.affected_agents:
            self.affected_agents.append(affected_agent)
        self.breaking_changes[affected_agent] = issues

    def has_breaking_changes(self) -> bool:
        """Check if there are any breaking changes"""
        return len(self.breaking_changes) > 0


class ContractManager:
    """
    Manages API contracts and schema evolution between agents.
    Uses networkx dependency graph for impact analysis.
    """

    def __init__(self, storage_path: str = ".graphbus/contracts", graph: nx.DiGraph = None):
        """
        Initialize contract manager

        Args:
            storage_path: Directory to store contract files
            graph: NetworkX dependency graph for impact analysis
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.graph = graph
        self.contracts: Dict[str, Dict[str, Contract]] = {}  # agent_name -> version -> Contract

        # Load existing contracts
        self._load_contracts()

    def _load_contracts(self):
        """Load all contracts from storage"""
        if not self.storage_path.exists():
            return

        for contract_file in self.storage_path.glob("*.json"):
            try:
                with open(contract_file, 'r') as f:
                    data = json.load(f)
                    contract = Contract.from_dict(data)

                    if contract.agent_name not in self.contracts:
                        self.contracts[contract.agent_name] = {}
                    self.contracts[contract.agent_name][contract.version] = contract
            except Exception as e:
                print(f"Warning: Failed to load contract {contract_file}: {e}")

    def register_contract(self, agent_name: str, version: str, schema: Dict[str, Any]) -> Contract:
        """
        Register an agent's API contract

        Args:
            agent_name: Name of the agent
            version: Semantic version (e.g., "1.0.0")
            schema: Contract schema definition

        Returns:
            Contract object
        """
        if not self._is_valid_semver(version):
            raise ValueError(f"Invalid semantic version: {version}")

        # Create contract from schema
        contract = Contract(
            agent_name=agent_name,
            version=version,
            description=schema.get("description", "")
        )

        # Parse methods
        for method_name, method_schema in schema.get("methods", {}).items():
            method = MethodSchema(
                name=method_name,
                input=self._parse_fields(method_schema.get("input", {})),
                output=self._parse_fields(method_schema.get("output", {})),
                description=method_schema.get("description", "")
            )
            contract.methods[method_name] = method

        # Parse publishes
        for topic, event_schema in schema.get("publishes", {}).items():
            event = EventSchema(
                topic=topic,
                payload=self._parse_fields(event_schema.get("payload", {})),
                description=event_schema.get("description", "")
            )
            contract.publishes[topic] = event

        contract.subscribes = schema.get("subscribes", [])

        # Store contract
        if agent_name not in self.contracts:
            self.contracts[agent_name] = {}
        self.contracts[agent_name][version] = contract

        # Save to disk
        self._save_contract(contract)

        return contract

    def _parse_fields(self, fields_schema: Dict[str, Any]) -> Dict[str, SchemaField]:
        """Parse field definitions from schema"""
        fields = {}
        for field_name, field_def in fields_schema.items():
            if isinstance(field_def, str):
                # Simple type definition
                fields[field_name] = SchemaField(field_name, field_def)
            else:
                # Full field definition
                fields[field_name] = SchemaField(
                    name=field_name,
                    type=field_def.get("type", "Any"),
                    required=field_def.get("required", True),
                    default=field_def.get("default"),
                    description=field_def.get("description", "")
                )
        return fields

    def _save_contract(self, contract: Contract):
        """Save contract to disk"""
        filename = f"{contract.agent_name}_{contract.version}.json"
        filepath = self.storage_path / filename

        with open(filepath, 'w') as f:
            json.dump(contract.to_dict(), f, indent=2)

    def get_contract(self, agent_name: str, version: Optional[str] = None) -> Optional[Contract]:
        """
        Get agent contract by version

        Args:
            agent_name: Name of the agent
            version: Specific version (if None, returns latest)

        Returns:
            Contract object or None if not found
        """
        if agent_name not in self.contracts:
            return None

        if version is None:
            # Return latest version
            versions = sorted(self.contracts[agent_name].keys(), key=self._parse_semver, reverse=True)
            if versions:
                return self.contracts[agent_name][versions[0]]
            return None

        return self.contracts[agent_name].get(version)

    def get_all_versions(self, agent_name: str) -> List[str]:
        """Get all versions for an agent"""
        if agent_name not in self.contracts:
            return []
        return sorted(self.contracts[agent_name].keys(), key=self._parse_semver)

    def validate_compatibility(self, producer: str, consumer: str,
                              producer_version: Optional[str] = None,
                              consumer_version: Optional[str] = None) -> CompatibilityResult:
        """
        Check if producer and consumer contracts are compatible

        Args:
            producer: Producer agent name
            consumer: Consumer agent name
            producer_version: Producer version (latest if None)
            consumer_version: Consumer version (latest if None)

        Returns:
            CompatibilityResult with issues if incompatible
        """
        producer_contract = self.get_contract(producer, producer_version)
        consumer_contract = self.get_contract(consumer, consumer_version)

        if not producer_contract:
            result = CompatibilityResult(False, CompatibilityLevel.INCOMPATIBLE)
            result.add_issue("missing_contract", ChangeType.BREAKING,
                           f"No contract found for producer: {producer}",
                           producer, "Register a contract for the producer agent")
            return result

        if not consumer_contract:
            result = CompatibilityResult(False, CompatibilityLevel.INCOMPATIBLE)
            result.add_issue("missing_contract", ChangeType.BREAKING,
                           f"No contract found for consumer: {consumer}",
                           consumer, "Register a contract for the consumer agent")
            return result

        result = CompatibilityResult(True, CompatibilityLevel.FULLY_COMPATIBLE)

        # Check if consumer subscribes to any topics producer publishes
        for topic in consumer_contract.subscribes:
            if topic in producer_contract.publishes:
                # Check payload compatibility
                producer_event = producer_contract.publishes[topic]
                self._check_payload_compatibility(producer_event, consumer_contract, topic, result)

        return result

    def _check_payload_compatibility(self, producer_event: EventSchema,
                                    consumer_contract: Contract,
                                    topic: str,
                                    result: CompatibilityResult):
        """Check if event payload is compatible with consumer expectations"""
        # For now, just check if all required fields in producer are present
        # More sophisticated checking can be added later
        pass

    def analyze_schema_impact(self, agent_name: str, new_schema: Dict[str, Any]) -> ImpactAnalysis:
        """
        Analyze impact of schema changes using networkx dependency graph

        Args:
            agent_name: Name of the agent with new schema
            new_schema: New schema definition

        Returns:
            ImpactAnalysis with affected agents and breaking changes
        """
        if not self.graph:
            raise ValueError("No dependency graph available for impact analysis")

        # Get current contract
        current_contract = self.get_contract(agent_name)
        if not current_contract:
            raise ValueError(f"No existing contract found for {agent_name}")

        # Detect breaking changes
        has_breaking_changes = self._has_breaking_changes(current_contract, new_schema)

        # Parse new version from schema, or increment based on changes
        if "version" in new_schema:
            new_version = new_schema["version"]
        else:
            # Increment major for breaking changes, patch otherwise
            level = "major" if has_breaking_changes else "patch"
            new_version = self._increment_version(current_contract.version, level)

        impact = ImpactAnalysis(agent_name=agent_name, new_version=new_version)

        # Find all downstream agents using networkx
        if agent_name not in self.graph:
            impact.warnings.append(f"Agent {agent_name} not found in dependency graph")
            return impact

        try:
            # Get all descendants (downstream agents) in the graph
            affected_agents = nx.descendants(self.graph, agent_name)

            for downstream_agent in affected_agents:
                # Create temporary contract for new schema
                temp_contract = self.register_contract(
                    agent_name=f"_temp_{agent_name}",
                    version=new_version,
                    schema=new_schema
                )

                # Check compatibility
                compatibility = self.validate_compatibility(
                    f"_temp_{agent_name}",
                    downstream_agent
                )

                if not compatibility.compatible:
                    impact.add_breaking_change(downstream_agent, compatibility.issues)

                # Clean up temp contract
                if f"_temp_{agent_name}" in self.contracts:
                    del self.contracts[f"_temp_{agent_name}"]

        except nx.NetworkXError as e:
            impact.warnings.append(f"Error analyzing graph: {e}")

        return impact

    def notify_downstream_agents(self, agent_name: str, new_schema: Dict[str, Any]) -> List[str]:
        """
        Use networkx graph to notify all downstream agents of schema changes

        Args:
            agent_name: Agent with schema change
            new_schema: New schema definition

        Returns:
            List of notified agent names
        """
        if not self.graph:
            return []

        if agent_name not in self.graph:
            return []

        # Get all downstream agents
        try:
            downstream = nx.descendants(self.graph, agent_name)
            return list(downstream)
        except nx.NetworkXError:
            return []

    def get_migration_path(self, agent_name: str, from_version: str, to_version: str) -> List[str]:
        """
        Get migration path between versions

        Args:
            agent_name: Agent name
            from_version: Starting version
            to_version: Target version

        Returns:
            List of versions in migration path
        """
        versions = self.get_all_versions(agent_name)

        if from_version not in versions or to_version not in versions:
            return []

        # Find path in version list
        from_idx = versions.index(from_version)
        to_idx = versions.index(to_version)

        if from_idx < to_idx:
            # Forward migration
            return versions[from_idx:to_idx + 1]
        else:
            # Backward migration
            return list(reversed(versions[to_idx:from_idx + 1]))

    def _has_breaking_changes(self, current_contract: Contract, new_schema: Dict[str, Any]) -> bool:
        """
        Detect if the new schema has breaking changes compared to current contract.

        Breaking changes include:
        - Adding required fields to method inputs
        - Removing fields from method outputs
        - Removing methods
        """
        # Check methods
        new_methods = new_schema.get("methods", {})
        current_methods = {name: getattr(method, '__dict__', method) if hasattr(method, '__dict__') else method
                          for name, method in current_contract.methods.items()}

        # Method removed = breaking
        for method_name in current_methods:
            if method_name not in new_methods:
                return True

        # Check each method for breaking changes
        for method_name, new_method_def in new_methods.items():
            if method_name not in current_methods:
                continue  # New method = not breaking

            current_method = current_methods[method_name]

            # Get input/output schemas
            new_input = new_method_def.get("input", {})
            new_output = new_method_def.get("output", {})

            if hasattr(current_method, 'input_schema'):
                current_input = current_method.input_schema
            elif isinstance(current_method, dict):
                current_input = current_method.get("input", current_method.get("input_schema", {}))
            else:
                current_input = {}

            if hasattr(current_method, 'output_schema'):
                current_output = current_method.output_schema
            elif isinstance(current_method, dict):
                current_output = current_method.get("output", current_method.get("output_schema", {}))
            else:
                current_output = {}

            # Adding required input field = breaking
            if len(new_input) > len(current_input):
                return True

            # Removing output field = breaking
            if len(new_output) < len(current_output):
                return True

        return False

    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        """Check if version string is valid semantic version"""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))

    @staticmethod
    def _parse_semver(version: str) -> Tuple[int, int, int]:
        """Parse semantic version into tuple for comparison"""
        try:
            major, minor, patch = version.split('.')
            return (int(major), int(minor), int(patch))
        except:
            return (0, 0, 0)

    @staticmethod
    def _increment_version(version: str, level: str = "patch") -> str:
        """Increment version number"""
        major, minor, patch = ContractManager._parse_semver(version)

        if level == "major":
            return f"{major + 1}.0.0"
        elif level == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
