"""
Tests for graphbus TUI — Text User Interface for agent orchestration.

TDD-first: Define TUI behavior, then implement.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json
import yaml


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_graphbus_dir(tmp_path):
    """Create a minimal .graphbus/ directory for testing."""
    graphbus = tmp_path / ".graphbus"
    graphbus.mkdir()
    (graphbus / "agents").mkdir()
    
    # Create graph.yaml
    graph = {
        "agents": [
            {
                "name": "APIAgent",
                "description": "REST API",
                "model_tier": "medium",
                "model_provider": "anthropic",
            },
            {
                "name": "DataAgent",
                "description": "Data processing",
                "model_tier": "light",
                "model_provider": "ollama",
            },
        ],
        "edges": [
            {"from": "APIAgent", "to": "DataAgent", "type": "depends_on"}
        ],
    }
    (graphbus / "graph.yaml").write_text(yaml.dump(graph))
    
    # Create agent YAMLs
    api_agent = {
        "name": "APIAgent",
        "description": "REST API",
        "source_files": ["api/routes.py"],
        "system_prompt": "You are APIAgent",
        "model_tier": "medium",
        "model_provider": "anthropic",
    }
    (graphbus / "agents" / "APIAgent.yaml").write_text(yaml.dump(api_agent))
    
    return graphbus


@pytest.fixture
def home_graphbus_dir(tmp_path):
    """Create ~/.graphbus/ structure with projects."""
    home = tmp_path / "home_graphbus"
    home.mkdir()
    
    projects = home / "projects"
    projects.mkdir()
    
    # Create a sample project
    proj = projects / "myapp_abc123"
    proj.mkdir()
    (proj / "context.json").write_text(json.dumps({
        "project_path": "/home/user/myapp",
        "project_id": "myapp_abc123",
    }))
    (proj / "negotiations").mkdir()
    
    return home


# ─── Module: TUI State Management ─────────────────────────────────────────────

class TestTUIStateManager:
    """Tests for TUI state (current project, selected agent, etc.)."""
    
    def test_state_manager_init(self):
        from graphbus_cli.tui.state import TUIState
        state = TUIState()
        assert state.current_project is None
        assert state.selected_agent is None
    
    def test_state_manager_set_project(self, sample_graphbus_dir):
        from graphbus_cli.tui.state import TUIState
        state = TUIState()
        state.set_project(sample_graphbus_dir)
        assert state.current_project == sample_graphbus_dir
    
    def test_state_manager_load_graph(self, sample_graphbus_dir):
        from graphbus_cli.tui.state import TUIState
        state = TUIState()
        state.set_project(sample_graphbus_dir)
        graph = state.get_graph()
        assert graph is not None
        assert len(graph["agents"]) == 2
        assert graph["agents"][0]["name"] == "APIAgent"
    
    def test_state_manager_select_agent(self, sample_graphbus_dir):
        from graphbus_cli.tui.state import TUIState
        state = TUIState()
        state.set_project(sample_graphbus_dir)
        state.select_agent("APIAgent")
        assert state.selected_agent == "APIAgent"
    
    def test_state_manager_get_agent_details(self, sample_graphbus_dir):
        from graphbus_cli.tui.state import TUIState
        state = TUIState()
        state.set_project(sample_graphbus_dir)
        agent = state.get_agent_details("APIAgent")
        assert agent["name"] == "APIAgent"
        assert agent["model_tier"] == "medium"


# ─── Module: Graph Visualization ─────────────────────────────────────────────

class TestGraphVisualizer:
    """Tests for agent graph ASCII rendering."""
    
    def test_render_simple_graph(self, sample_graphbus_dir):
        from graphbus_cli.tui.graph import render_graph
        graph = yaml.safe_load((sample_graphbus_dir / "graph.yaml").read_text())
        output = render_graph(graph)
        assert "APIAgent" in output
        assert "DataAgent" in output
    
    def test_render_includes_edges(self, sample_graphbus_dir):
        from graphbus_cli.tui.graph import render_graph
        graph = yaml.safe_load((sample_graphbus_dir / "graph.yaml").read_text())
        output = render_graph(graph)
        assert "→" in output or "->" in output  # Edge indicator
    
    def test_render_shows_model_tiers(self, sample_graphbus_dir):
        from graphbus_cli.tui.graph import render_graph
        graph = yaml.safe_load((sample_graphbus_dir / "graph.yaml").read_text())
        output = render_graph(graph)
        assert "medium" in output or "light" in output  # Tier info
    
    def test_render_complex_graph(self):
        from graphbus_cli.tui.graph import render_graph
        graph = {
            "agents": [
                {"name": "A", "model_tier": "light"},
                {"name": "B", "model_tier": "medium"},
                {"name": "C", "model_tier": "heavy"},
            ],
            "edges": [
                {"from": "A", "to": "B"},
                {"from": "B", "to": "C"},
                {"from": "A", "to": "C"},
            ],
        }
        output = render_graph(graph)
        assert "A" in output and "B" in output and "C" in output


# ─── Module: Model Tier Editor ───────────────────────────────────────────────

class TestModelTierEditor:
    """Tests for interactive model tier editing."""
    
    def test_list_models_for_tier(self):
        from graphbus_cli.tui.model_editor import get_available_models
        light_models = get_available_models("light")
        assert len(light_models) > 0
        assert "gemma-3-4b" in light_models or "gemma" in str(light_models).lower()
    
    def test_validate_model_assignment(self):
        from graphbus_cli.tui.model_editor import validate_model
        assert validate_model("claude-haiku-4-5", "medium") is True
        assert validate_model("invalid-model-xyz", "medium") is False
    
    def test_apply_model_override(self, sample_graphbus_dir):
        from graphbus_cli.tui.model_editor import apply_override
        apply_override(sample_graphbus_dir, "APIAgent", "heavy", "claude-sonnet-4-6")
        config_path = sample_graphbus_dir / "model-config.yaml"
        assert config_path.exists()
        config = yaml.safe_load(config_path.read_text())
        assert config["overrides"]["APIAgent"]["model"] == "claude-sonnet-4-6"
    
    def test_revert_override(self, sample_graphbus_dir):
        from graphbus_cli.tui.model_editor import apply_override, revert_override
        apply_override(sample_graphbus_dir, "APIAgent", "heavy", "claude-sonnet-4-6")
        revert_override(sample_graphbus_dir, "APIAgent")
        config_path = sample_graphbus_dir / "model-config.yaml"
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text()) or {}
            assert "APIAgent" not in config.get("overrides", {})


# ─── Module: Project Browser ─────────────────────────────────────────────────

class TestProjectBrowser:
    """Tests for listing and switching projects."""
    
    def test_list_projects(self, home_graphbus_dir):
        from graphbus_cli.tui.projects import list_projects
        projects = list_projects(home_graphbus_dir)
        assert len(projects) > 0
        assert projects[0]["id"] == "myapp_abc123"
    
    def test_get_project_path(self, home_graphbus_dir):
        from graphbus_cli.tui.projects import get_project_info
        info = get_project_info(home_graphbus_dir, "myapp_abc123")
        assert info["project_id"] == "myapp_abc123"
        assert info["project_path"] == "/home/user/myapp"
    
    def test_project_not_found(self, home_graphbus_dir):
        from graphbus_cli.tui.projects import get_project_info
        with pytest.raises(ValueError, match="Project not found"):
            get_project_info(home_graphbus_dir, "nonexistent")


# ─── Module: Ingest Runner ───────────────────────────────────────────────────

class TestIngestRunner:
    """Tests for running ingest from TUI."""
    
    def test_ingest_project(self):
        from graphbus_cli.tui.ingest_runner import run_ingest_interactive
        # Should accept a path and home_dir, return result
        assert callable(run_ingest_interactive)
    
    def test_ingest_result_parsing(self):
        from graphbus_cli.tui.ingest_runner import parse_ingest_result
        result = {
            "agents": ["APIAgent", "DataAgent"],
            "edges": [("APIAgent", "DataAgent")],
            "files_analyzed": 42,
        }
        parsed = parse_ingest_result(result)
        assert parsed["agent_count"] == 2
        assert parsed["edge_count"] == 1


# ─── Module: Negotiation Status Monitor ──────────────────────────────────────

class TestNegotiationMonitor:
    """Tests for viewing negotiation status."""
    
    def test_load_negotiation_history(self, sample_graphbus_dir):
        from graphbus_cli.tui.negotiation import load_negotiation_summary
        # Should load from .graphbus/negotiations.json if it exists
        result = load_negotiation_summary(sample_graphbus_dir)
        assert isinstance(result, (dict, list, type(None)))
    
    def test_format_negotiation_status(self):
        from graphbus_cli.tui.negotiation import format_negotiation_display
        status = {
            "status": "in_progress",
            "round": 2,
            "proposals": 5,
            "accepted": 3,
        }
        output = format_negotiation_display(status)
        assert "in_progress" in output.lower() or "round" in output.lower()


# ─── Integration: Full TUI Screen ────────────────────────────────────────────

class TestTUIScreen:
    """Tests for the main TUI screen."""
    
    def test_tui_loads_without_error(self):
        from graphbus_cli.tui.main import TUIApp
        # Should be importable and instantiable
        assert TUIApp is not None
    
    def test_tui_has_required_screens(self):
        from graphbus_cli.tui.main import TUIApp
        # Should have screens for: graph, model editor, projects, etc.
        assert hasattr(TUIApp, "SCREENS") or hasattr(TUIApp, "screens")
    
    @pytest.mark.skip(reason="Requires textual test runner")
    def test_tui_key_bindings(self):
        from graphbus_cli.tui.main import TUIApp
        # Should respond to keyboard: arrows, enter, escape, etc.
        pass


# ─── CLI Command ─────────────────────────────────────────────────────────────

class TestTUICommand:
    """Tests for `graphbus tui` CLI command."""
    
    def test_tui_command_exists(self):
        from graphbus_cli.commands.tui import tui
        assert callable(tui)
    
    def test_tui_registers(self):
        from graphbus_cli.commands.tui import register
        assert callable(register)
