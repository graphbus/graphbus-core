"""
Unit tests for StateManager
"""

import pytest
import json
from pathlib import Path

from graphbus_core.runtime.state import StateManager


class TestStateManager:
    """Test StateManager for agent state persistence"""

    @pytest.fixture
    def state_dir(self, tmp_path):
        """Temporary state directory"""
        return str(tmp_path / "test_state")

    @pytest.fixture
    def manager(self, state_dir):
        """StateManager instance"""
        return StateManager(state_dir)

    def test_initialization(self, state_dir):
        """Test StateManager initialization"""
        manager = StateManager(state_dir)

        assert manager.state_dir == Path(state_dir)
        assert manager.state_dir.exists()

    def test_save_state(self, manager):
        """Test saving agent state"""
        state = {"counter": 42, "data": {"key": "value"}}

        manager.save_state("TestAgent", state)

        # Verify file exists
        state_file = manager.state_dir / "TestAgent.json"
        assert state_file.exists()

        # Verify content
        with open(state_file) as f:
            saved_data = json.load(f)

        assert saved_data["node_name"] == "TestAgent"
        assert saved_data["state"] == state
        assert "timestamp" in saved_data
        assert "version" in saved_data

    def test_save_state_invalid_type(self, manager):
        """Test saving non-dict state raises error"""
        with pytest.raises(ValueError, match="State must be a dictionary"):
            manager.save_state("TestAgent", "not a dict")

    def test_save_state_non_serializable(self, manager):
        """Test saving non-JSON-serializable state raises error"""
        class NonSerializable:
            pass

        state = {"obj": NonSerializable()}

        with pytest.raises(ValueError, match="not JSON-serializable"):
            manager.save_state("TestAgent", state)

    def test_load_state(self, manager):
        """Test loading agent state"""
        state = {"counter": 42, "data": {"key": "value"}}
        manager.save_state("TestAgent", state)

        loaded_state = manager.load_state("TestAgent")

        assert loaded_state == state

    def test_load_state_nonexistent(self, manager):
        """Test loading state for non-existent agent returns empty dict"""
        loaded_state = manager.load_state("NonExistentAgent")

        assert loaded_state == {}

    def test_load_state_corrupted_file(self, manager, state_dir):
        """Test loading corrupted state file raises error"""
        # Create corrupted file
        state_file = Path(state_dir) / "CorruptedAgent.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(ValueError, match="Corrupted state file"):
            manager.load_state("CorruptedAgent")

    def test_load_state_invalid_format(self, manager, state_dir):
        """Test loading state file with invalid format raises error"""
        # Create file with wrong structure
        state_file = Path(state_dir) / "InvalidAgent.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump({"wrong": "structure"}, f)

        with pytest.raises(ValueError, match="Invalid state file format"):
            manager.load_state("InvalidAgent")

    def test_clear_state(self, manager):
        """Test clearing agent state"""
        state = {"counter": 42}
        manager.save_state("TestAgent", state)

        result = manager.clear_state("TestAgent")

        assert result is True
        assert manager.load_state("TestAgent") == {}

    def test_clear_state_nonexistent(self, manager):
        """Test clearing non-existent state returns False"""
        result = manager.clear_state("NonExistentAgent")

        assert result is False

    def test_list_saved_states(self, manager):
        """Test listing all saved states"""
        manager.save_state("Agent1", {"data": 1})
        manager.save_state("Agent2", {"data": 2})
        manager.save_state("Agent3", {"data": 3})

        saved_states = manager.list_saved_states()

        assert len(saved_states) == 3
        assert "Agent1" in saved_states
        assert "Agent2" in saved_states
        assert "Agent3" in saved_states

    def test_list_saved_states_empty(self, manager):
        """Test listing states when none exist"""
        saved_states = manager.list_saved_states()

        assert saved_states == []

    def test_get_state_metadata(self, manager):
        """Test getting state metadata"""
        state = {"counter": 42}
        manager.save_state("TestAgent", state)

        metadata = manager.get_state_metadata("TestAgent")

        assert metadata is not None
        assert metadata["node_name"] == "TestAgent"
        assert "timestamp" in metadata
        assert "version" in metadata
        assert "file_size" in metadata
        assert metadata["file_size"] > 0

    def test_get_state_metadata_nonexistent(self, manager):
        """Test getting metadata for non-existent state returns None"""
        metadata = manager.get_state_metadata("NonExistentAgent")

        assert metadata is None

    def test_clear_all_states(self, manager):
        """Test clearing all states"""
        manager.save_state("Agent1", {"data": 1})
        manager.save_state("Agent2", {"data": 2})
        manager.save_state("Agent3", {"data": 3})

        count = manager.clear_all_states()

        assert count == 3
        assert manager.list_saved_states() == []

    def test_clear_all_states_empty(self, manager):
        """Test clearing all states when none exist"""
        count = manager.clear_all_states()

        assert count == 0

    def test_export_state(self, manager, tmp_path):
        """Test exporting state to file"""
        state = {"counter": 42, "data": "test"}
        manager.save_state("TestAgent", state)

        export_file = tmp_path / "exported_state.json"
        manager.export_state("TestAgent", str(export_file))

        assert export_file.exists()

        with open(export_file) as f:
            exported = json.load(f)

        assert exported == state

    def test_export_state_nonexistent(self, manager, tmp_path):
        """Test exporting non-existent state raises error"""
        export_file = tmp_path / "exported_state.json"

        with pytest.raises(ValueError, match="No state found"):
            manager.export_state("NonExistentAgent", str(export_file))

    def test_import_state(self, manager, tmp_path):
        """Test importing state from file"""
        state = {"counter": 42, "data": "test"}
        import_file = tmp_path / "import_state.json"

        with open(import_file, 'w') as f:
            json.dump(state, f)

        manager.import_state("TestAgent", str(import_file))

        loaded_state = manager.load_state("TestAgent")
        assert loaded_state == state

    def test_import_state_invalid_file(self, manager, tmp_path):
        """Test importing from invalid file raises error"""
        import_file = tmp_path / "invalid.json"

        with open(import_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(ValueError, match="Failed to import state"):
            manager.import_state("TestAgent", str(import_file))

    def test_import_state_non_dict(self, manager, tmp_path):
        """Test importing non-dict state raises error"""
        import_file = tmp_path / "invalid.json"

        with open(import_file, 'w') as f:
            json.dump(["not", "a", "dict"], f)

        with pytest.raises(ValueError, match="must be a dictionary"):
            manager.import_state("TestAgent", str(import_file))

    def test_sanitize_node_name(self, manager):
        """Test that node names with special characters are sanitized"""
        state = {"data": "test"}

        # Save with slashes in name
        manager.save_state("Namespace/Agent", state)

        # Verify file created with sanitized name
        state_file = manager.state_dir / "Namespace_Agent.json"
        assert state_file.exists()

        # Verify can load back
        loaded = manager.load_state("Namespace/Agent")
        assert loaded == state

    def test_state_persistence_across_instances(self, state_dir):
        """Test that state persists across StateManager instances"""
        # Save with first instance
        manager1 = StateManager(state_dir)
        state = {"counter": 42}
        manager1.save_state("TestAgent", state)

        # Load with second instance
        manager2 = StateManager(state_dir)
        loaded_state = manager2.load_state("TestAgent")

        assert loaded_state == state

    def test_overwrite_existing_state(self, manager):
        """Test that saving state overwrites existing state"""
        manager.save_state("TestAgent", {"counter": 1})
        manager.save_state("TestAgent", {"counter": 2})

        loaded_state = manager.load_state("TestAgent")

        assert loaded_state == {"counter": 2}

    def test_complex_nested_state(self, manager):
        """Test saving and loading complex nested state"""
        state = {
            "counter": 42,
            "nested": {
                "level1": {
                    "level2": {
                        "data": [1, 2, 3],
                        "flags": {"flag1": True, "flag2": False}
                    }
                }
            },
            "list_data": [
                {"id": 1, "value": "a"},
                {"id": 2, "value": "b"}
            ]
        }

        manager.save_state("ComplexAgent", state)
        loaded_state = manager.load_state("ComplexAgent")

        assert loaded_state == state
