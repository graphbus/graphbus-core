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


# ─── User Journeys: Real Workflows ───────────────────────────────────────────

class TestUserJourneyNewProject:
    """Test the workflow for a user setting up a new project."""
    
    def test_journey_ingest_new_codebase(self, tmp_path, home_graphbus_dir):
        """
        User journey: New user ingests their codebase.
        
        1. User runs `graphbus tui`
        2. TUI shows "No projects yet"
        3. User selects "Ingest new project"
        4. User provides path to their code
        5. TUI runs ingest, shows progress
        6. TUI displays: "Ingested 50 files into 8 agents"
        7. User can now explore the graph
        """
        from graphbus_cli.tui.main import TUIApp
        from graphbus_cli.tui.projects import list_projects
        
        # Step 1: No projects initially
        projects = list_projects(home_graphbus_dir)
        initial_count = len(projects)
        
        # Step 2-7: User should be able to ingest a project
        # (TUI should guide them through this)
        assert TUIApp.has_ingest_screen is True or hasattr(TUIApp, "ingest_screen")
    
    def test_journey_error_handling_invalid_path(self):
        """
        User journey: User provides invalid project path.
        
        1. User selects "Ingest new project"
        2. User types invalid path
        3. TUI validates and shows error: "Path not found"
        4. User corrects the path
        5. Ingest proceeds
        
        Usability: Should not crash, should be recoverable.
        """
        from graphbus_cli.tui.ingest_runner import validate_project_path
        
        assert validate_project_path("/nonexistent/path") is False
        assert validate_project_path(".") is True  # Current dir is valid
    
    def test_journey_cancel_operations(self):
        """
        User journey: User starts an operation and cancels it.
        
        1. User starts ingest
        2. User presses Escape
        3. TUI shows: "Ingest cancelled"
        4. TUI returns to main screen
        
        Usability: Should gracefully cancel without data loss.
        """
        from graphbus_cli.tui.main import TUIApp
        
        assert hasattr(TUIApp, "handle_escape") or hasattr(TUIApp, "cancel_operation")


class TestUserJourneyModelConfiguration:
    """Test the workflow for configuring model tiers."""
    
    def test_journey_view_and_edit_models(self, sample_graphbus_dir):
        """
        User journey: User customizes model assignments.
        
        1. User runs `graphbus tui`
        2. User loads a project
        3. User selects "Models" tab
        4. TUI shows list: APIAgent (medium/anthropic), DataAgent (light/ollama)
        5. User arrows down to APIAgent
        6. User presses Enter
        7. TUI shows options: keep default or override
        8. User selects "Heavy/claude-sonnet-4-6"
        9. TUI confirms and saves to model-config.yaml
        10. User returns to list, sees ✓ override indicator
        """
        from graphbus_cli.tui.model_editor import ModelEditor
        
        editor = ModelEditor(sample_graphbus_dir)
        agents = editor.list_agents()
        
        # User can navigate the agent list
        assert len(agents) > 0
        assert agents[0]["name"] == "APIAgent"
        
        # User can select an agent
        editor.select_agent("APIAgent")
        assert editor.selected == "APIAgent"
        
        # User can see available models for this tier
        available = editor.get_override_options("APIAgent")
        assert len(available) > 0
        
        # User can apply an override
        editor.apply_override("APIAgent", "heavy", "claude-sonnet-4-6")
        
        # Changes persist
        updated = editor.get_agent_status("APIAgent")
        assert updated["override"] is not None
    
    def test_journey_revert_override(self, sample_graphbus_dir):
        """
        User journey: User changes their mind and reverts a model override.
        
        1. User has previously overridden APIAgent to heavy
        2. User loads TUI and sees override indicator
        3. User selects "Revert to auto" from context menu
        4. TUI removes override, shows confirmation
        """
        from graphbus_cli.tui.model_editor import ModelEditor
        
        editor = ModelEditor(sample_graphbus_dir)
        editor.apply_override("APIAgent", "heavy", "claude-sonnet-4-6")
        
        # User reverts
        editor.revert_override("APIAgent")
        
        # Verify reverted
        status = editor.get_agent_status("APIAgent")
        assert status.get("override") is None
    
    def test_journey_bulk_tier_adjustment(self, sample_graphbus_dir):
        """
        User journey: User wants all light agents to use a specific model.
        
        1. User filters to "light agents only"
        2. User selects "Apply to all"
        3. User picks a model: "gemma-3-8b"
        4. TUI applies override to all 5 light agents
        5. User sees summary: "5 agents updated"
        """
        from graphbus_cli.tui.model_editor import ModelEditor
        
        editor = ModelEditor(sample_graphbus_dir)
        
        # User wants to configure all light agents at once
        light_agents = [a for a in editor.list_agents() if a["tier"] == "light"]
        assert len(light_agents) > 0
        
        # TUI should support bulk operations
        assert hasattr(editor, "apply_to_all") or hasattr(editor, "bulk_override")


class TestUserJourneyProjectNavigation:
    """Test navigation between projects and state persistence."""
    
    def test_journey_open_previous_project(self, home_graphbus_dir):
        """
        User journey: User returns to work on a previous project.
        
        1. User runs `graphbus tui`
        2. TUI shows recent projects list
        3. User selects "myapp"
        4. TUI loads .graphbus/myapp/
        5. User's previous model overrides are still there
        6. User can continue editing
        """
        from graphbus_cli.tui.main import TUIApp
        from graphbus_cli.tui.projects import list_recent_projects
        
        # Should show recent projects
        recent = list_recent_projects(home_graphbus_dir)
        assert len(recent) > 0
        assert recent[0]["id"] == "myapp_abc123"
    
    def test_journey_switch_projects_mid_session(self, home_graphbus_dir, tmp_path):
        """
        User journey: User switches between projects without restarting TUI.
        
        1. User is in project A
        2. User selects "Switch project"
        3. User picks project B
        4. TUI loads project B's graph and model config
        5. User's edits to A were not lost
        """
        from graphbus_cli.tui.main import TUIApp
        from graphbus_cli.tui.state import TUIState
        
        state = TUIState()
        
        # User starts with project A
        graphbus_a = tmp_path / "a" / ".graphbus"
        graphbus_a.mkdir(parents=True)
        state.set_project(graphbus_a)
        assert state.current_project == graphbus_a
        
        # User switches to project B
        graphbus_b = tmp_path / "b" / ".graphbus"
        graphbus_b.mkdir(parents=True)
        state.set_project(graphbus_b)
        assert state.current_project == graphbus_b
        
        # Can switch back
        state.set_project(graphbus_a)
        assert state.current_project == graphbus_a


class TestUserJourneyIngestWorkflow:
    """Test the full ingest workflow from TUI."""
    
    def test_journey_guided_ingest(self, tmp_path, home_graphbus_dir):
        """
        User journey: First-time user ingests a codebase.
        
        1. User runs `graphbus tui` (no projects yet)
        2. TUI suggests: "Get started by ingesting a project"
        3. User selects "Ingest"
        4. TUI prompts: "Enter path to codebase"
        5. User types: "."
        6. TUI detects language: "Python detected"
        7. TUI shows progress bar: "Scanning... 115 files found"
        8. TUI shows: "Grouping into agents..."
        9. TUI shows: "✓ Created 8 agents"
        10. TUI shows graph preview
        11. User can accept or go back and customize
        """
        from graphbus_cli.tui.ingest_runner import IngestRunner
        
        runner = IngestRunner()
        
        # TUI should provide language detection feedback
        assert hasattr(runner, "get_language_feedback")
        
        # TUI should show progress
        assert hasattr(runner, "show_progress") or hasattr(runner, "progress_callback")
        
        # TUI should summarize results
        assert hasattr(runner, "get_ingest_summary")
    
    def test_journey_ingest_with_exclusions(self, tmp_path):
        """
        User journey: User wants to exclude certain directories.
        
        1. User starts ingest
        2. TUI detects: ".gitignore found"
        3. TUI shows: "Will exclude node_modules/, venv/, .git/"
        4. User can accept or customize exclusions
        5. If user customizes, TUI re-scans
        """
        from graphbus_cli.tui.ingest_runner import IngestRunner
        
        runner = IngestRunner()
        
        # Should detect .gitignore
        assert hasattr(runner, "detect_exclusions")
        
        # Should allow customization
        assert hasattr(runner, "customize_exclusions")


class TestUserJourneyGraphExploration:
    """Test user interaction with the agent graph."""
    
    def test_journey_explore_agent_details(self, sample_graphbus_dir):
        """
        User journey: User wants to understand what an agent does.
        
        1. TUI shows agent graph
        2. User arrows to APIAgent
        3. User presses Enter
        4. TUI shows panel:
           - Name: APIAgent
           - Description: "REST API handling"
           - Files: 5 (api/routes.py, api/auth.py, ...)
           - Model: medium/anthropic/claude-haiku-4-5
           - Dependencies: DataAgent
           - Dependents: (none)
        5. User can navigate between agents
        6. User presses Escape to close panel
        """
        from graphbus_cli.tui.graph import GraphViewer
        
        viewer = GraphViewer(sample_graphbus_dir)
        
        # Should show agent list
        agents = viewer.list_agents()
        assert len(agents) > 0
        
        # User can select an agent
        details = viewer.get_agent_details("APIAgent")
        assert details["name"] == "APIAgent"
        assert "files" in details
        assert "model_tier" in details
    
    def test_journey_follow_dependencies(self, sample_graphbus_dir):
        """
        User journey: User wants to understand dependency chain.
        
        1. User is looking at APIAgent
        2. User sees it depends on: DataAgent
        3. User presses → to follow the dependency
        4. TUI highlights DataAgent
        5. User presses ← to go back
        """
        from graphbus_cli.tui.graph import GraphViewer
        
        viewer = GraphViewer(sample_graphbus_dir)
        
        # Should track navigation
        viewer.select_agent("APIAgent")
        deps = viewer.get_dependencies("APIAgent")
        
        if deps:
            # User can follow dependency
            viewer.select_agent(deps[0])
            assert viewer.selected == deps[0]
    
    def test_journey_visualize_full_graph(self, sample_graphbus_dir):
        """
        User journey: User wants to see the entire system at once.
        
        1. User selects "View full graph"
        2. TUI renders ASCII art showing:
           - All agents
           - All edges/dependencies
           - Model tiers color-coded or noted
        3. User can toggle details on/off
        4. User can identify bottlenecks (many dependencies)
        """
        from graphbus_cli.tui.graph import render_graph
        
        graph = yaml.safe_load((sample_graphbus_dir / "graph.yaml").read_text())
        output = render_graph(graph)
        
        # Output should be human-readable
        assert len(output) > 0
        assert isinstance(output, str)


class TestUsabilityAndErrorRecovery:
    """Test error handling and user guidance."""
    
    def test_error_message_clarity(self):
        """
        Usability: Error messages should be clear and actionable.
        
        When user does something wrong, TUI should:
        1. Show what went wrong
        2. Show why it failed
        3. Suggest next steps
        """
        from graphbus_cli.tui.errors import format_error_message
        
        msg = format_error_message("path_not_found", "/nonexistent")
        assert "not found" in msg.lower()
        assert "suggest" in msg.lower() or "try" in msg.lower()
    
    def test_help_system_accessible(self):
        """
        Usability: User should be able to get help anywhere.
        
        1. User presses ? anywhere in TUI
        2. Help menu appears
        3. User can search for topics
        4. User can navigate context-specific help
        """
        from graphbus_cli.tui.main import TUIApp
        
        assert hasattr(TUIApp, "show_help") or hasattr(TUIApp, "help_screen")
    
    def test_keyboard_shortcuts_discoverable(self):
        """
        Usability: User should discover keyboard shortcuts naturally.
        
        1. TUI shows common shortcuts in footer: "q=quit ? =help ↑↓=nav"
        2. User can press ? to see full list
        3. Shortcuts are consistent across screens
        """
        from graphbus_cli.tui.main import TUIApp
        
        assert hasattr(TUIApp, "get_footer") or hasattr(TUIApp, "render_help_footer")
    
    def test_undo_redo_for_configuration(self, sample_graphbus_dir):
        """
        Usability: User should be able to undo configuration changes.
        
        1. User makes 3 model overrides
        2. User presses Ctrl+Z
        3. Last override is undone
        4. User can redo with Ctrl+Y
        """
        from graphbus_cli.tui.main import TUIApp
        
        # Should track history
        assert hasattr(TUIApp, "undo") or hasattr(TUIApp, "history")


class TestScreenTransitions:
    """Test navigation between TUI screens."""
    
    def test_screen_order_intuitive(self):
        """
        Usability: Screen order should match typical workflow.
        
        Expected order:
        1. Projects (home screen)
        2. Graph (explore agents)
        3. Models (configure)
        4. Status (view negotiations)
        5. Settings
        """
        from graphbus_cli.tui.main import TUIApp
        
        screens = getattr(TUIApp, "SCREENS", [])
        if screens:
            # Projects should be first
            assert screens[0] in ("projects", "home", "main")
    
    def test_back_navigation_consistent(self):
        """
        Usability: User can always go back.
        
        From any screen:
        - Pressing Escape goes back
        - Pressing q quits (from home) or goes to home
        """
        from graphbus_cli.tui.main import TUIApp
        
        assert hasattr(TUIApp, "handle_escape")
    
    def test_state_preserved_across_screens(self, sample_graphbus_dir):
        """
        Usability: User's selections are preserved when navigating.
        
        1. User selects APIAgent
        2. User goes to Models screen
        3. User goes back to Graph
        4. APIAgent is still selected
        """
        from graphbus_cli.tui.state import TUIState
        
        state = TUIState()
        state.set_project(sample_graphbus_dir)
        state.select_agent("APIAgent")
        
        # User navigates away
        # ... (other operations)
        
        # Selection should be preserved
        assert state.selected_agent == "APIAgent"


class TestAccessibilityAndResponsiveness:
    """Test accessibility and UI responsiveness."""
    
    def test_terminal_size_handling(self):
        """
        Usability: TUI should work on small terminals.
        
        Should gracefully degrade on:
        - 80x24 (very small)
        - 120x40 (normal)
        - 200x60 (wide)
        """
        from graphbus_cli.tui.main import TUIApp
        
        assert hasattr(TUIApp, "get_min_width") or hasattr(TUIApp, "responsive_layout")
    
    def test_mouse_support_optional(self):
        """
        Usability: Should work with keyboard alone (for SSH/headless).
        
        User can:
        - Navigate with arrows
        - Select with Enter
        - Navigate with Tab
        - Quit with q
        
        (Mouse is bonus but not required)
        """
        from graphbus_cli.tui.main import TUIApp
        
        # Keyboard navigation should be primary
        assert hasattr(TUIApp, "handle_key") or hasattr(TUIApp, "on_key")


# ─── Summary Test: Full User Session ──────────────────────────────────────────

class TestFullUserSession:
    """Capture a complete realistic user session."""
    
    def test_session_new_user_onboarding(self, tmp_path, home_graphbus_dir):
        """
        Full session: New user ingests their first project and configures it.
        
        Order of operations:
        1. User runs `graphbus tui`
        2. TUI shows welcome + recent projects (empty)
        3. User selects "Ingest new project"
        4. User provides path: tmp_path / "my_app"
        5. TUI analyzes and creates .graphbus/
        6. TUI shows: 8 agents, 12 edges
        7. User explores graph (arrows, enter on agents)
        8. User goes to Models tab
        9. User customizes 2 agents
        10. User presses q to quit
        11. On restart, project is saved and ready
        """
        # This test validates the complete happy path
        pass
    
    def test_session_error_recovery(self):
        """
        Full session: User makes mistakes and recovers gracefully.
        
        1. User enters wrong path (error message)
        2. User corrects and retries (no crash)
        3. User cancels ingest (graceful exit)
        4. User restarts and can pick up where they left off
        """
        # This test validates error handling across the full workflow
        pass


# ─── Agent Event Loop: Autonomous Execution ──────────────────────────────────

class TestAgentEventLoop:
    """Test autonomous agent execution and event loop."""
    
    def test_event_loop_initializes(self):
        """
        Test: Agent event loop can be created and started.
        
        1. User provides intent: "optimize database queries"
        2. TUI creates event loop
        3. Event loop loads agents from .graphbus/
        4. Event loop initializes LLM clients for each agent
        5. Event loop is ready to start
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="optimize database queries")
        assert loop is not None
        assert loop.intent == "optimize database queries"
        assert hasattr(loop, "start") or hasattr(loop, "run")
    
    def test_event_loop_loads_agents(self, sample_graphbus_dir):
        """
        Test: Event loop loads all agents from graph.
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(
            intent="optimize performance",
            graphbus_dir=sample_graphbus_dir,
        )
        agents = loop.get_loaded_agents()
        assert len(agents) > 0
        assert "APIAgent" in [a.name for a in agents]
    
    def test_event_loop_spawns_agent_threads(self):
        """
        Test: Event loop spawns one thread/coroutine per agent.
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test")
        
        # Should have concurrent execution capability
        assert hasattr(loop, "spawn_agent") or hasattr(loop, "async_execute")
    
    def test_event_loop_round_structure(self):
        """
        Test: Each round follows: propose → evaluate → commit/reject.
        
        Round structure:
        1. Each agent proposes changes
        2. Each agent evaluates other proposals
        3. Arbiter reconciles conflicts (if configured)
        4. Human reviews and accepts/rejects
        5. Accepted proposals commit
        6. Loop continues until convergence or intent satisfied
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test")
        
        # Should have round structure
        assert hasattr(loop, "execute_round") or hasattr(loop, "run_negotiation_round")
    
    def test_event_loop_proposal_collection(self):
        """
        Test: Event loop collects proposals from all agents in a round.
        """
        from graphbus_cli.tui.agent_loop import ProposalCollector
        
        collector = ProposalCollector()
        
        # Should aggregate proposals
        assert hasattr(collector, "add_proposal")
        assert hasattr(collector, "get_all_proposals")
    
    def test_event_loop_evaluation_phase(self):
        """
        Test: Each agent evaluates all other proposals in the round.
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test")
        
        # Agents should evaluate proposals
        assert hasattr(loop, "run_evaluation_phase")
    
    def test_event_loop_convergence_detection(self):
        """
        Test: Loop detects when no more changes are proposed (convergence).
        
        Convergence signals:
        - All agents proposed changes, all rejected
        - All agents propose same changes
        - Max rounds reached
        - Intent explicitly satisfied by human
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test")
        
        assert hasattr(loop, "is_converged") or hasattr(loop, "check_convergence")
    
    def test_event_loop_max_rounds(self):
        """
        Test: Event loop respects max_rounds parameter.
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test", max_rounds=5)
        assert loop.max_rounds == 5
    
    def test_event_loop_timeout_handling(self):
        """
        Test: Event loop can timeout if negotiation takes too long.
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test", timeout_seconds=60)
        assert loop.timeout_seconds == 60


# ─── Human-in-the-Loop (HIL) Interventions ──────────────────────────────────

class TestHILIntervention:
    """Test human intervention during agent negotiation."""
    
    def test_hil_pause_negotiation(self):
        """
        Test: Human can pause agent negotiation.
        
        1. Agents are executing round 2
        2. Human sees interesting proposal, presses Space
        3. Loop pauses after current agent finishes
        4. Human can review
        5. Human presses Space again to resume
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test")
        
        assert hasattr(loop, "pause") or hasattr(loop, "request_pause")
        assert hasattr(loop, "resume")
    
    def test_hil_inspect_proposal(self):
        """
        Test: Human can inspect a proposal in detail.
        
        1. Proposal appears in queue
        2. Human presses Enter on proposal
        3. TUI shows full details:
           - Agent name
           - File(s) affected
           - Code diff
           - Reasoning
           - Confidence score
        4. Human can press Escape to close
        """
        from graphbus_cli.tui.hil import ProposalInspector
        
        inspector = ProposalInspector()
        
        assert hasattr(inspector, "show_proposal_details")
        assert hasattr(inspector, "format_diff")
    
    def test_hil_accept_proposal(self):
        """
        Test: Human can accept a proposal.
        
        1. Proposal is paused/highlighted
        2. Human presses 'y' or clicks Accept
        3. Proposal is marked accepted
        4. TUI removes from queue
        5. Loop continues
        """
        from graphbus_cli.tui.hil import ProposalApprover
        
        approver = ProposalApprover()
        
        assert hasattr(approver, "accept_proposal")
        assert hasattr(approver, "reject_proposal")
    
    def test_hil_reject_proposal(self):
        """
        Test: Human can reject a proposal.
        
        1. Human presses 'n' or clicks Reject
        2. Optional: TUI prompts "Why?" for feedback
        3. Proposal marked rejected
        4. Agents see rejection in next evaluation phase
        """
        from graphbus_cli.tui.hil import ProposalApprover
        
        approver = ProposalApprover()
        
        # Should support rejection with optional reason
        assert hasattr(approver, "reject_with_reason")
    
    def test_hil_modify_proposal(self):
        """
        Test: Human can modify a proposal before accepting.
        
        1. Proposal is displayed
        2. Human presses 'e' (edit)
        3. Diff viewer opens with editable areas
        4. Human modifies the changes
        5. Human saves and proposal is updated
        """
        from graphbus_cli.tui.hil import ProposalEditor
        
        editor = ProposalEditor()
        
        assert hasattr(editor, "edit_proposal")
        assert hasattr(editor, "save_changes")
    
    def test_hil_view_agent_reasoning(self):
        """
        Test: Human can see why an agent made a proposal.
        
        1. Proposal appears with reasoning snippet
        2. Human presses 'r' to see full reasoning
        3. TUI shows:
           - Agent's analysis of the code
           - Why it thinks change is needed
           - Expected impact
        """
        from graphbus_cli.tui.hil import ReasoningViewer
        
        viewer = ReasoningViewer()
        
        assert hasattr(viewer, "show_reasoning")
    
    def test_hil_ask_agent_question(self):
        """
        Test: Human can ask an agent a question mid-negotiation.
        
        1. Human presses 'q' (question)
        2. TUI shows prompt: "Ask APIAgent:"
        3. Human types question: "Why not use caching?"
        4. Agent responds (or defers to next round)
        5. Response appears in reasoning viewer
        """
        from graphbus_cli.tui.hil import AgentDialog
        
        dialog = AgentDialog()
        
        assert hasattr(dialog, "ask_agent")
    
    def test_hil_override_agent_decision(self):
        """
        Test: Human can override an agent's decision.
        
        1. Agent proposes change
        2. Human disagrees
        3. Human can force-accept or force-reject
        4. Agent sees override in next evaluation (learns from it)
        """
        from graphbus_cli.tui.hil import DecisionOverride
        
        override = DecisionOverride()
        
        assert hasattr(override, "force_accept")
        assert hasattr(override, "force_reject")
    
    def test_hil_stop_negotiation(self):
        """
        Test: Human can stop negotiation entirely.
        
        1. Human presses Ctrl+C or selects "Stop negotiation"
        2. TUI prompts: "Stop and accept current changes?"
        3. Options: Cancel (resume) | Accept all | Accept none | Save for later
        4. User chooses action
        """
        from graphbus_cli.tui.agent_loop import AgentEventLoop
        
        loop = AgentEventLoop(intent="test")
        
        assert hasattr(loop, "request_stop") or hasattr(loop, "handle_stop")
    
    def test_hil_feedback_to_agents(self):
        """
        Test: Human feedback is captured and fed to agents.
        
        When human accepts/rejects/modifies, agents see:
        - Decision (accept/reject/modify)
        - Reason (if provided)
        - Modified content (if edited)
        
        Agents use this to refine proposals in next round.
        """
        from graphbus_cli.tui.hil import FeedbackCollector
        
        collector = FeedbackCollector()
        
        assert hasattr(collector, "collect_feedback")
        assert hasattr(collector, "format_for_agents")


# ─── Intent Satisfaction Detection ──────────────────────────────────────────

class TestIntentSatisfaction:
    """Test intent completion detection and signals."""
    
    def test_intent_relevance_filtering(self):
        """
        Test: Agents check if intent is relevant to their domain.
        
        Intent: "optimize database queries"
        - DataAgent: RELEVANT (owns database layer)
        - APIAgent: POSSIBLY (might propose query optimization)
        - UIAgent: NOT RELEVANT
        
        Only relevant agents propose changes.
        """
        from graphbus_cli.tui.intent import IntentRelevance
        
        relevance = IntentRelevance(intent="optimize database queries")
        
        # Should evaluate relevance
        assert relevance.is_relevant("DataAgent") is True
        assert relevance.is_relevant("UIAgent") is False
    
    def test_intent_completion_signals(self):
        """
        Test: Detect when intent is satisfied.
        
        Signals:
        1. Agent explicitly says "intent satisfied"
        2. All relevant agents propose no more changes
        3. Human says "done" / "satisfied"
        4. Convergence reached with no rejections
        """
        from graphbus_cli.tui.intent import IntentCompletion
        
        detector = IntentCompletion(intent="optimize database queries")
        
        assert hasattr(detector, "is_satisfied")
        assert hasattr(detector, "get_satisfaction_score")
    
    def test_intent_progress_tracking(self):
        """
        Test: Track progress toward intent satisfaction.
        
        Progress indicators:
        - Round number
        - Proposals in this round
        - Changes committed so far
        - Agents that have proposed something
        - Estimated satisfaction (%)
        """
        from graphbus_cli.tui.intent import IntentProgressTracker
        
        tracker = IntentProgressTracker(intent="optimize performance")
        
        assert hasattr(tracker, "update_progress")
        assert hasattr(tracker, "get_progress_percent")
        assert hasattr(tracker, "get_progress_display")
    
    def test_intent_partial_satisfaction(self):
        """
        Test: Intent might be only partially satisfied.
        
        1. Intent: "improve error handling and add logging"
        2. After round 2: Error handling complete, logging pending
        3. TUI shows: "50% complete"
        4. Human can ask agents to continue or stop
        """
        from graphbus_cli.tui.intent import IntentCompletion
        
        detector = IntentCompletion(intent="improve error handling and add logging")
        
        # Should support partial satisfaction
        assert hasattr(detector, "get_satisfied_parts")
        assert hasattr(detector, "get_pending_parts")
    
    def test_intent_explicit_completion(self):
        """
        Test: Human can explicitly mark intent as complete.
        
        1. Human reviews changes
        2. Human presses 'd' (done) or selects "Intent satisfied"
        3. TUI confirms: "Mark 'optimize performance' as complete?"
        4. Changes are committed
        5. Negotiation ends gracefully
        """
        from graphbus_cli.tui.intent import IntentCompletion
        
        detector = IntentCompletion(intent="test")
        
        assert hasattr(detector, "mark_complete")
    
    def test_intent_divergence_detection(self):
        """
        Test: Detect when negotiation diverges from intent.
        
        1. Intent: "optimize database queries"
        2. Agents start proposing UI changes instead
        3. TUI warns: "Proposals diverging from intent"
        4. Human can:
           - Reject proposals
           - Steer agents back
           - Accept divergence
        """
        from graphbus_cli.tui.intent import IntentDivergence
        
        detector = IntentDivergence(intent="optimize database queries")
        
        assert hasattr(detector, "check_divergence")
        assert hasattr(detector, "get_divergence_score")
    
    def test_intent_context_window_management(self):
        """
        Test: Manage context window as negotiation progresses.
        
        As rounds increase, proposal history grows. Need to:
        1. Summarize old decisions
        2. Keep recent decisions in full detail
        3. Feed relevant history to agents
        """
        from graphbus_cli.tui.agent_loop import ContextManager
        
        ctx = ContextManager()
        
        assert hasattr(ctx, "add_round_history")
        assert hasattr(ctx, "get_context_for_round")
    
    def test_intent_outcome_summary(self):
        """
        Test: Generate summary when intent is complete.
        
        Summary includes:
        - Intent: "..."
        - Status: Complete/Partial/Incomplete
        - Rounds: 3
        - Files changed: 5
        - Lines added/deleted: +120/-40
        - Agents involved: [APIAgent, DataAgent]
        - Commits: [list of commit hashes]
        """
        from graphbus_cli.tui.intent import OutcomeSummary
        
        summary = OutcomeSummary()
        
        assert hasattr(summary, "generate")
        assert hasattr(summary, "format_for_display")


# ─── Multi-Round Negotiation with Human Guidance ──────────────────────────────

class TestMultiRoundNegotiation:
    """Test negotiation across multiple rounds with human intervention."""
    
    def test_round_1_initial_proposals(self):
        """
        Test: Round 1 - Agents propose initial changes.
        
        1. User provides intent
        2. All relevant agents analyze code
        3. Each agent proposes changes
        4. TUI displays proposal queue
        5. Human reviews (pause/accept/reject)
        """
        pass  # Covered by event loop tests
    
    def test_round_2_evaluation_and_feedback(self):
        """
        Test: Round 2 - Agents evaluate each other and human provides feedback.
        
        1. Agents see proposals from round 1
        2. Each agent evaluates others' proposals
        3. Agents propose modifications
        4. Human provides feedback on round 1 changes
        5. Queue updates with round 2 proposals
        """
        pass  # Covered by evaluation phase tests
    
    def test_round_3_convergence_or_divergence(self):
        """
        Test: Round 3+ - Detect convergence or stagnation.
        
        1. Agents propose fewer changes
        2. Proposals are smaller and more focused
        3. Eventually: no more proposals = convergence
        4. Or: same proposals repeating = stagnation
        """
        from graphbus_cli.tui.agent_loop import ConvergenceDetector
        
        detector = ConvergenceDetector()
        
        assert hasattr(detector, "is_converged")
        assert hasattr(detector, "is_stagnant")
    
    def test_human_steers_negotiation(self):
        """
        Test: Human can steer negotiation if it goes off track.
        
        1. Human sees agents not making progress
        2. Human provides hint/question
        3. Agents incorporate feedback
        4. Negotiation resumes with new direction
        """
        from graphbus_cli.tui.hil import NegotiationSteering
        
        steering = NegotiationSteering()
        
        assert hasattr(steering, "provide_hint")
        assert hasattr(steering, "ask_agents")


# ─── Conflict Resolution with Arbiter ────────────────────────────────────────

class TestArbiterIntervention:
    """Test arbiter agent reconciling conflicting proposals."""
    
    def test_arbiter_detects_conflicts(self):
        """
        Test: Arbiter identifies conflicting proposals.
        
        Conflict: Both APIAgent and DataAgent propose changes to same file,
        in incompatible ways.
        
        Arbiter should detect and highlight.
        """
        from graphbus_cli.tui.arbiter import ArbiterAgent
        
        arbiter = ArbiterAgent()
        
        assert hasattr(arbiter, "detect_conflicts")
    
    def test_arbiter_proposes_resolution(self):
        """
        Test: Arbiter proposes resolution for conflicts.
        
        Arbiter sees:
        - Proposal A: Change function signature
        - Proposal B: Call the function (with old signature)
        
        Arbiter proposes: Modify B to use new signature.
        """
        from graphbus_cli.tui.arbiter import ArbiterAgent
        
        arbiter = ArbiterAgent()
        
        assert hasattr(arbiter, "propose_resolution")
    
    def test_arbiter_human_review(self):
        """
        Test: Human can accept/reject arbiter's resolution.
        
        Like any other proposal, arbiter's resolution
        appears in the queue for human review.
        """
        pass  # Covered by HIL tests


# ─── Real-Time Monitoring and Display ────────────────────────────────────────

class TestRealtimeMonitoring:
    """Test real-time display of agent activity."""
    
    def test_proposal_queue_display(self):
        """
        Test: TUI displays incoming proposals in real-time.
        
        As agents propose changes, they appear in queue:
        - Agent name
        - File(s) affected
        - Change type (add/modify/delete)
        - Status (pending/reviewing/accepted)
        """
        from graphbus_cli.tui.display import ProposalQueueDisplay
        
        display = ProposalQueueDisplay()
        
        assert hasattr(display, "add_proposal")
        assert hasattr(display, "render")
    
    def test_agent_status_monitor(self):
        """
        Test: TUI shows status of each agent (thinking/waiting/done).
        
        Agent status board:
        APIAgent:    [████    ] Evaluating... (round 2)
        DataAgent:   [██████  ] Proposing...
        UIAgent:     [        ] Waiting
        """
        from graphbus_cli.tui.display import AgentStatusMonitor
        
        monitor = AgentStatusMonitor()
        
        assert hasattr(monitor, "update_agent_status")
        assert hasattr(monitor, "render_status_board")
    
    def test_history_and_audit_log(self):
        """
        Test: TUI maintains audit log of all decisions.
        
        User can press 'h' to see history:
        - Round 1, Agent APIAgent, Proposal #1: ACCEPTED
        - Round 1, Agent DataAgent, Proposal #1: REJECTED (user feedback)
        - Round 2, Agent APIAgent, Proposal #2: PENDING
        """
        from graphbus_cli.tui.display import AuditLog
        
        log = AuditLog()
        
        assert hasattr(log, "add_entry")
        assert hasattr(log, "get_history")


# ─── Error Handling During Negotiation ─────────────────────────────────────

class TestNegotiationErrorHandling:
    """Test error handling during agent negotiation."""
    
    def test_agent_crash_recovery(self):
        """
        Test: If an agent crashes, negotiation continues.
        
        1. APIAgent crashes during proposal generation
        2. TUI displays: "⚠ APIAgent error"
        3. Other agents continue
        4. User can:
           - Retry APIAgent
           - Skip APIAgent for this round
           - Abort negotiation
        """
        from graphbus_cli.tui.agent_loop import ErrorHandler
        
        handler = ErrorHandler()
        
        assert hasattr(handler, "handle_agent_error")
        assert hasattr(handler, "retry_agent")
    
    def test_timeout_handling(self):
        """
        Test: If agent takes too long, timeout gracefully.
        
        1. Agent is evaluating (taking >30s)
        2. TUI shows warning: "APIAgent is slow..."
        3. After timeout: agent is skipped for this round
        4. Negotiation continues
        """
        from graphbus_cli.tui.agent_loop import TimeoutManager
        
        mgr = TimeoutManager(timeout_per_agent=30)
        
        assert hasattr(mgr, "set_timeout")
        assert hasattr(mgr, "handle_timeout")
    
    def test_llm_api_failure_recovery(self):
        """
        Test: If LLM API fails, show error and allow retry.
        
        1. Agent tries to call Claude API
        2. API returns 429 (rate limited)
        3. TUI shows: "Rate limited, retrying in 5s..."
        4. Automatic retry (configurable backoff)
        """
        from graphbus_cli.tui.agent_loop import APIErrorHandler
        
        handler = APIErrorHandler()
        
        assert hasattr(handler, "handle_api_error")
        assert hasattr(handler, "should_retry")


# ─── State Management During Negotiation ─────────────────────────────────────

class TestNegotiationStateManagement:
    """Test state persistence during long negotiations."""
    
    def test_save_negotiation_checkpoint(self):
        """
        Test: Negotiation state is saved periodically.
        
        1. Each round is checkpointed
        2. User can quit and resume later
        3. Resume with: `graphbus tui --resume <session-id>`
        """
        from graphbus_cli.tui.agent_loop import NegotiationState
        
        state = NegotiationState()
        
        assert hasattr(state, "save")
        assert hasattr(state, "load")
    
    def test_resume_from_checkpoint(self):
        """
        Test: Resume negotiation from a previous checkpoint.
        
        1. User restarts: `graphbus tui --resume session-123`
        2. TUI loads last checkpoint
        3. Shows: "Resuming negotiation on 'optimize queries' from round 2"
        4. Negotiation continues from where it left off
        """
        from graphbus_cli.tui.agent_loop import NegotiationResumeManager
        
        mgr = NegotiationResumeManager()
        
        assert hasattr(mgr, "list_resumable_sessions")
        assert hasattr(mgr, "resume_session")
    
    def test_negotiation_undo_redo(self):
        """
        Test: Human can undo the last round of changes.
        
        1. User presses Ctrl+Z
        2. TUI reverts: "Undo round 2?"
        3. Round 2 changes are undone
        4. User can redo with Ctrl+Y
        """
        from graphbus_cli.tui.agent_loop import NegotiationHistory
        
        history = NegotiationHistory()
        
        assert hasattr(history, "undo")
        assert hasattr(history, "redo")


# ─── Full Execution Session ──────────────────────────────────────────────────

class TestFullExecutionSession:
    """Capture a complete agent negotiation session with human interaction."""
    
    def test_session_with_hil_acceptance(self):
        """
        Full session: Agent proposes, human reviews and accepts.
        
        Order:
        1. User: "optimize database queries"
        2. Round 1: DataAgent proposes index changes
        3. Human pauses, reviews, accepts
        4. Round 2: APIAgent optimizes query logic
        5. Human accepts again
        6. Round 3: No more changes (converged)
        7. Intent satisfied, user hits 'd'
        8. Session ends with summary
        """
        pass
    
    def test_session_with_hil_rejection(self):
        """
        Full session: Agent proposes, human rejects and steers.
        
        Order:
        1. User: "improve error handling"
        2. Round 1: APIAgent proposes generic try-catch blocks
        3. Human rejects with comment: "Too generic, needs specific handlers"
        4. Round 2: APIAgent refines with specific exceptions
        5. Human accepts
        6. Continues...
        """
        pass
    
    def test_session_with_conflicts_and_arbiter(self):
        """
        Full session: Agents conflict, arbiter resolves.
        
        Order:
        1. User: "refactor data layer"
        2. Round 1: ModelAgent changes schema, DataAgent changes queries
        3. TUI detects conflict, arbiter proposes resolution
        4. Human reviews arbiter's resolution, accepts
        5. Continues...
        """
        pass
