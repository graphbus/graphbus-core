"""
Agent State Management

Provides persistence for agent state across runtime restarts.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class StateManager:
    """
    Manages agent state persistence to disk.

    Supports saving and loading agent state as JSON files,
    enabling agents to preserve their state across restarts.
    """

    def __init__(self, state_dir: str = ".graphbus/state"):
        """
        Initialize StateManager.

        Args:
            state_dir: Directory to store state files (default: .graphbus/state)
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, node_name: str, state: Dict[str, Any]) -> None:
        """
        Save agent state to persistent storage.

        Args:
            node_name: Name of the agent node
            state: State dictionary to save

        Raises:
            ValueError: If state is not JSON-serializable
        """
        if not isinstance(state, dict):
            raise ValueError(f"State must be a dictionary, got {type(state)}")

        state_file = self._get_state_file(node_name)

        # Add metadata
        state_with_meta = {
            "node_name": node_name,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
            "state": state
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state_with_meta, f, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError(f"State is not JSON-serializable: {e}")

    def load_state(self, node_name: str) -> Dict[str, Any]:
        """
        Load agent state from persistent storage.

        Args:
            node_name: Name of the agent node

        Returns:
            State dictionary, or empty dict if no state exists

        Raises:
            ValueError: If state file is corrupted
        """
        state_file = self._get_state_file(node_name)

        if not state_file.exists():
            return {}

        try:
            with open(state_file, 'r') as f:
                state_with_meta = json.load(f)

            # Validate structure
            if not isinstance(state_with_meta, dict) or 'state' not in state_with_meta:
                raise ValueError(f"Invalid state file format for {node_name}")

            return state_with_meta['state']

        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted state file for {node_name}: {e}")

    def clear_state(self, node_name: str) -> bool:
        """
        Clear persisted state for an agent.

        Args:
            node_name: Name of the agent node

        Returns:
            True if state was cleared, False if no state existed
        """
        state_file = self._get_state_file(node_name)

        if state_file.exists():
            state_file.unlink()
            return True
        return False

    def list_saved_states(self) -> list[str]:
        """
        List all agents with saved state.

        Returns:
            List of agent names that have saved state
        """
        if not self.state_dir.exists():
            return []

        return [
            f.stem  # filename without .json extension
            for f in self.state_dir.glob("*.json")
        ]

    def get_state_metadata(self, node_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about saved state without loading the full state.

        Args:
            node_name: Name of the agent node

        Returns:
            Metadata dict with timestamp and version, or None if no state exists
        """
        state_file = self._get_state_file(node_name)

        if not state_file.exists():
            return None

        try:
            with open(state_file, 'r') as f:
                state_with_meta = json.load(f)

            return {
                "node_name": state_with_meta.get("node_name"),
                "timestamp": state_with_meta.get("timestamp"),
                "version": state_with_meta.get("version"),
                "file_size": state_file.stat().st_size
            }
        except (json.JSONDecodeError, OSError):
            return None

    def clear_all_states(self) -> int:
        """
        Clear all persisted states.

        Returns:
            Number of state files cleared
        """
        count = 0
        if self.state_dir.exists():
            for state_file in self.state_dir.glob("*.json"):
                state_file.unlink()
                count += 1
        return count

    def _get_state_file(self, node_name: str) -> Path:
        """Get the path to a state file for a given node."""
        # Sanitize node name for filesystem
        safe_name = node_name.replace("/", "_").replace("\\", "_")
        return self.state_dir / f"{safe_name}.json"

    def export_state(self, node_name: str, output_file: str) -> None:
        """
        Export agent state to a specific file.

        Args:
            node_name: Name of the agent node
            output_file: Path to export file

        Raises:
            ValueError: If no state exists for the agent
        """
        state = self.load_state(node_name)
        if not state:
            raise ValueError(f"No state found for agent '{node_name}'")

        with open(output_file, 'w') as f:
            json.dump(state, f, indent=2)

    def import_state(self, node_name: str, input_file: str) -> None:
        """
        Import agent state from a file.

        Args:
            node_name: Name of the agent node
            input_file: Path to import file

        Raises:
            ValueError: If import file is invalid
        """
        try:
            with open(input_file, 'r') as f:
                state = json.load(f)

            if not isinstance(state, dict):
                raise ValueError("Imported state must be a dictionary")

            self.save_state(node_name, state)

        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to import state: {e}")
