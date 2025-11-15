"""
Code Migration Framework for Schema Evolution

This module provides migration management for handling schema changes between
agent versions. It uses networkx topological sort to ensure correct migration
ordering and dependency-aware scheduling.
"""

import json
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
import networkx as nx


class MigrationStatus(Enum):
    """Status of a migration"""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationResult:
    """Result of migration application"""
    success: bool
    migration_id: str
    agent_name: str
    from_version: str
    to_version: str
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    payload_before: Optional[Dict] = None
    payload_after: Optional[Dict] = None


@dataclass
class ValidationResult:
    """Result of migration validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class Migration(ABC):
    """
    Base class for migrations.
    Subclass this to define migrations between versions.
    """

    # These should be defined in subclasses
    agent_name: str = ""
    from_version: str = ""
    to_version: str = ""
    description: str = ""

    @abstractmethod
    def forward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate payload from from_version to to_version

        Args:
            payload: Input payload at from_version

        Returns:
            Migrated payload at to_version
        """
        pass

    @abstractmethod
    def backward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback payload from to_version to from_version

        Args:
            payload: Input payload at to_version

        Returns:
            Rolled back payload at from_version
        """
        pass

    def validate(self, payload: Dict[str, Any]) -> bool:
        """
        Validate that migration was successful

        Args:
            payload: Migrated payload to validate

        Returns:
            True if valid, False otherwise
        """
        return True  # Override in subclass for custom validation

    def get_id(self) -> str:
        """Get unique migration ID"""
        return f"{self.agent_name}_{self.from_version}_to_{self.to_version}"

    def __repr__(self) -> str:
        return f"Migration({self.agent_name}: {self.from_version} -> {self.to_version})"


@dataclass
class MigrationRecord:
    """Record of an applied migration"""
    migration_id: str
    agent_name: str
    from_version: str
    to_version: str
    status: MigrationStatus
    applied_at: datetime
    rolled_back_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "migration_id": self.migration_id,
            "agent_name": self.agent_name,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "status": self.status.value,
            "applied_at": self.applied_at.isoformat(),
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            "error": self.error
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MigrationRecord':
        """Create from dictionary"""
        return MigrationRecord(
            migration_id=data["migration_id"],
            agent_name=data["agent_name"],
            from_version=data["from_version"],
            to_version=data["to_version"],
            status=MigrationStatus(data["status"]),
            applied_at=datetime.fromisoformat(data["applied_at"]),
            rolled_back_at=datetime.fromisoformat(data["rolled_back_at"]) if data.get("rolled_back_at") else None,
            error=data.get("error")
        )


class MigrationCycleError(Exception):
    """Raised when a circular migration dependency is detected"""
    pass


class MigrationManager:
    """
    Manages code migrations for schema evolution.
    Uses networkx for topological sorting and dependency analysis.
    """

    def __init__(self, storage_path: str = ".graphbus/migrations"):
        """
        Initialize migration manager

        Args:
            storage_path: Directory to store migration records
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.migrations: Dict[str, Migration] = {}  # migration_id -> Migration
        self.records: Dict[str, MigrationRecord] = {}  # migration_id -> MigrationRecord

        # Load migration records
        self._load_records()

    def _load_records(self):
        """Load migration records from storage"""
        records_file = self.storage_path / "migration_history.json"
        if not records_file.exists():
            return

        try:
            with open(records_file, 'r') as f:
                data = json.load(f)
                for record_data in data:
                    record = MigrationRecord.from_dict(record_data)
                    self.records[record.migration_id] = record
        except Exception as e:
            print(f"Warning: Failed to load migration records: {e}")

    def _save_records(self):
        """Save migration records to storage"""
        records_file = self.storage_path / "migration_history.json"

        records_data = [record.to_dict() for record in self.records.values()]

        with open(records_file, 'w') as f:
            json.dump(records_data, f, indent=2)

    def register_migration(self, migration: Migration):
        """
        Register a migration

        Args:
            migration: Migration instance to register
        """
        migration_id = migration.get_id()
        self.migrations[migration_id] = migration

    def create_migration(self, agent_name: str, from_version: str, to_version: str,
                        forward_func: Optional[Callable] = None,
                        backward_func: Optional[Callable] = None,
                        validate_func: Optional[Callable] = None,
                        description: str = "") -> Migration:
        """
        Create a migration programmatically

        Args:
            agent_name: Name of agent
            from_version: Source version
            to_version: Target version
            forward_func: Optional forward migration function
            backward_func: Optional backward migration function
            validate_func: Optional validation function
            description: Migration description

        Returns:
            Migration instance
        """
        # Capture variables in enclosing scope
        _agent_name = agent_name
        _from_version = from_version
        _to_version = to_version
        _description = description
        _forward_func = forward_func
        _backward_func = backward_func
        _validate_func = validate_func

        # Create dynamic migration class with methods
        class DynamicMigration(Migration):
            agent_name = _agent_name
            from_version = _from_version
            to_version = _to_version
            description = _description

            def forward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
                if _forward_func:
                    return _forward_func(payload)
                return payload  # no-op

            def backward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
                if _backward_func:
                    return _backward_func(payload)
                return payload  # no-op

            def validate(self, payload: Dict[str, Any]) -> bool:
                if _validate_func:
                    return _validate_func(payload)
                return True  # no validation = always valid

        migration = DynamicMigration()

        self.register_migration(migration)
        return migration

    def apply_migration(self, agent_name: str, migration_id: str,
                       payload: Dict[str, Any]) -> MigrationResult:
        """
        Apply a specific migration to a payload

        Args:
            agent_name: Name of agent
            migration_id: ID of migration to apply
            payload: Payload to migrate

        Returns:
            MigrationResult with success status and transformed payload
        """
        if migration_id not in self.migrations:
            return MigrationResult(
                success=False,
                migration_id=migration_id,
                agent_name=agent_name,
                from_version="",
                to_version="",
                error=f"Migration {migration_id} not found"
            )

        migration = self.migrations[migration_id]

        try:
            # Apply forward migration
            migrated_payload = migration.forward(payload.copy())

            # Validate
            if not migration.validate(migrated_payload):
                return MigrationResult(
                    success=False,
                    migration_id=migration_id,
                    agent_name=agent_name,
                    from_version=migration.from_version,
                    to_version=migration.to_version,
                    error="Migration validation failed",
                    payload_before=payload,
                    payload_after=migrated_payload
                )

            # Record migration
            record = MigrationRecord(
                migration_id=migration_id,
                agent_name=agent_name,
                from_version=migration.from_version,
                to_version=migration.to_version,
                status=MigrationStatus.APPLIED,
                applied_at=datetime.now()
            )
            self.records[migration_id] = record
            self._save_records()

            return MigrationResult(
                success=True,
                migration_id=migration_id,
                agent_name=agent_name,
                from_version=migration.from_version,
                to_version=migration.to_version,
                payload_before=payload,
                payload_after=migrated_payload
            )

        except Exception as e:
            # Record failure
            record = MigrationRecord(
                migration_id=migration_id,
                agent_name=agent_name,
                from_version=migration.from_version,
                to_version=migration.to_version,
                status=MigrationStatus.FAILED,
                applied_at=datetime.now(),
                error=str(e)
            )
            self.records[migration_id] = record
            self._save_records()

            return MigrationResult(
                success=False,
                migration_id=migration_id,
                agent_name=agent_name,
                from_version=migration.from_version,
                to_version=migration.to_version,
                error=str(e),
                payload_before=payload
            )

    def rollback_migration(self, agent_name: str, migration_id: str,
                          payload: Dict[str, Any]) -> MigrationResult:
        """
        Rollback a migration

        Args:
            agent_name: Name of agent
            migration_id: ID of migration to rollback
            payload: Payload to rollback

        Returns:
            MigrationResult with success status and rolled back payload
        """
        if migration_id not in self.migrations:
            return MigrationResult(
                success=False,
                migration_id=migration_id,
                agent_name=agent_name,
                from_version="",
                to_version="",
                error=f"Migration {migration_id} not found"
            )

        migration = self.migrations[migration_id]

        try:
            # Apply backward migration
            rolled_back_payload = migration.backward(payload.copy())

            # Update record
            if migration_id in self.records:
                self.records[migration_id].status = MigrationStatus.ROLLED_BACK
                self.records[migration_id].rolled_back_at = datetime.now()
                self._save_records()

            return MigrationResult(
                success=True,
                migration_id=migration_id,
                agent_name=agent_name,
                from_version=migration.to_version,  # Reversed
                to_version=migration.from_version,
                payload_before=payload,
                payload_after=rolled_back_payload
            )

        except Exception as e:
            return MigrationResult(
                success=False,
                migration_id=migration_id,
                agent_name=agent_name,
                from_version=migration.to_version,
                to_version=migration.from_version,
                error=str(e),
                payload_before=payload
            )

    def get_pending_migrations(self, agent_name: Optional[str] = None) -> List[Migration]:
        """
        Get all pending migrations, ordered by networkx topological sort

        Args:
            agent_name: Optional filter by agent name

        Returns:
            List of pending migrations in execution order
        """
        # Filter migrations
        if agent_name:
            pending = [m for m_id, m in self.migrations.items()
                      if m.agent_name == agent_name and
                      (m_id not in self.records or
                       self.records[m_id].status == MigrationStatus.PENDING)]
        else:
            pending = [m for m_id, m in self.migrations.items()
                      if m_id not in self.records or
                      self.records[m_id].status == MigrationStatus.PENDING]

        if not pending:
            return []

        # Use topological sort to order migrations
        try:
            ordered = self.plan_migrations(pending)
            return ordered
        except MigrationCycleError:
            # If cycle detected, return in registration order
            return pending

    def plan_migrations(self, migrations: Optional[List[Migration]] = None) -> List[Migration]:
        """
        Use networkx to determine correct migration order

        Args:
            migrations: Optional list of migrations to plan (all if None)

        Returns:
            List of migrations in execution order

        Raises:
            MigrationCycleError: If circular dependency detected
        """
        if migrations is None:
            migrations = list(self.migrations.values())

        if not migrations:
            return []

        # Build migration dependency graph
        migration_graph = nx.DiGraph()

        # Group migrations by agent
        agent_migrations: Dict[str, List[Migration]] = {}
        for migration in migrations:
            if migration.agent_name not in agent_migrations:
                agent_migrations[migration.agent_name] = []
            agent_migrations[migration.agent_name].append(migration)

        # For each agent, create a path through versions
        for agent_name, agent_migs in agent_migrations.items():
            # Sort by version
            sorted_migs = sorted(agent_migs, key=lambda m: self._parse_version(m.from_version))

            # Add edges for sequential versions
            for i in range(len(sorted_migs) - 1):
                migration_graph.add_edge(
                    sorted_migs[i].get_id(),
                    sorted_migs[i + 1].get_id(),
                    migration=sorted_migs[i]
                )

            # Add the last migration node
            if sorted_migs:
                migration_graph.add_node(sorted_migs[-1].get_id(), migration=sorted_migs[-1])

        # Topological sort ensures correct order
        try:
            sorted_ids = list(nx.topological_sort(migration_graph))
            ordered_migrations = []

            for migration_id in sorted_ids:
                if migration_id in self.migrations:
                    ordered_migrations.append(self.migrations[migration_id])

            return ordered_migrations

        except nx.NetworkXError as e:
            raise MigrationCycleError(f"Circular migration dependency detected: {e}")

    def validate_migration_order(self) -> ValidationResult:
        """
        Validate that migration order is correct (no cycles)

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        try:
            # Try to plan all migrations
            self.plan_migrations()
        except MigrationCycleError as e:
            result.valid = False
            result.errors.append(str(e))

        # Check for version gaps
        for agent_name in set(m.agent_name for m in self.migrations.values()):
            agent_migrations = [m for m in self.migrations.values() if m.agent_name == agent_name]
            versions = sorted(set([m.from_version for m in agent_migrations] +
                                [m.to_version for m in agent_migrations]),
                            key=self._parse_version)

            # Check for gaps
            for i in range(len(versions) - 1):
                from_v = versions[i]
                to_v = versions[i + 1]

                # Check if migration exists
                migration_exists = any(
                    m.from_version == from_v and m.to_version == to_v
                    for m in agent_migrations
                )

                if not migration_exists:
                    result.warnings.append(
                        f"Missing migration for {agent_name}: {from_v} -> {to_v}"
                    )

        return result

    def get_migration_history(self, agent_name: Optional[str] = None) -> List[MigrationRecord]:
        """
        Get migration history

        Args:
            agent_name: Optional filter by agent name

        Returns:
            List of migration records
        """
        if agent_name:
            return [r for r in self.records.values() if r.agent_name == agent_name]
        return list(self.records.values())

    @staticmethod
    def _parse_version(version: str) -> tuple:
        """Parse version string for comparison"""
        try:
            parts = version.split('.')
            return tuple(int(p) for p in parts)
        except:
            return (0, 0, 0)

    def generate_migration_template(self, agent_name: str, from_version: str,
                                   to_version: str) -> str:
        """
        Generate migration class template code

        Args:
            agent_name: Agent name
            from_version: Source version
            to_version: Target version

        Returns:
            Python code template
        """
        class_name = f"{agent_name}Migration_{from_version.replace('.', '_')}_to_{to_version.replace('.', '_')}"

        template = f'''"""
Migration for {agent_name}: {from_version} -> {to_version}
"""

from typing import Dict, Any
from graphbus_core.runtime.migrations import Migration


class {class_name}(Migration):
    """TODO: Add migration description"""

    agent_name = "{agent_name}"
    from_version = "{from_version}"
    to_version = "{to_version}"
    description = "TODO: Describe what this migration does"

    def forward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate payload from {from_version} to {to_version}

        Args:
            payload: Input payload at v{from_version}

        Returns:
            Migrated payload at v{to_version}
        """
        # TODO: Implement forward migration logic
        migrated = payload.copy()

        # Example: Add new field with default value
        # migrated['new_field'] = 'default_value'

        return migrated

    def backward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback payload from {to_version} to {from_version}

        Args:
            payload: Input payload at v{to_version}

        Returns:
            Rolled back payload at v{from_version}
        """
        # TODO: Implement backward migration logic
        rolled_back = payload.copy()

        # Example: Remove field that was added in forward
        # rolled_back.pop('new_field', None)

        return rolled_back

    def validate(self, payload: Dict[str, Any]) -> bool:
        """
        Validate that migration was successful

        Args:
            payload: Migrated payload to validate

        Returns:
            True if valid, False otherwise
        """
        # TODO: Add custom validation logic
        # Example: Check required fields exist
        # return 'new_field' in payload

        return True
'''
        return template
