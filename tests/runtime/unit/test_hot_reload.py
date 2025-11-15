"""
Unit tests for HotReloadManager
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from graphbus_core.runtime.hot_reload import HotReloadManager
from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.topic import Topic, Subscription
from graphbus_core.node_base import GraphBusNode


class MockAgent(GraphBusNode):
    """Mock agent for testing"""

    def __init__(self):
        super().__init__()
        self.state_data = {}

    def get_state(self):
        return self.state_data

    def set_state(self, state):
        self.state_data = state

    def on_test_event(self, payload):
        pass


class TestHotReloadManager:
    """Test HotReloadManager for dynamic agent updates"""

    @pytest.fixture
    def mock_executor(self):
        """Mock RuntimeExecutor"""
        executor = Mock()
        executor.nodes = {
            "TestAgent": MockAgent()
        }
        executor.agents = []
        executor.message_bus = Mock()
        executor.event_router = Mock()
        return executor

    @pytest.fixture
    def agent_def(self):
        """Mock agent definition"""
        agent_def = Mock(spec=AgentDefinition)
        agent_def.name = "TestAgent"
        agent_def.module = "test_module"
        agent_def.class_name = "MockAgent"
        agent_def.subscriptions = []
        return agent_def

    @pytest.fixture
    def manager(self, mock_executor):
        """HotReloadManager instance"""
        return HotReloadManager(mock_executor)

    def test_initialization(self, mock_executor):
        """Test HotReloadManager initialization"""
        manager = HotReloadManager(mock_executor)

        assert manager.executor == mock_executor
        assert isinstance(manager.reload_history, list)
        assert len(manager.reload_history) == 0
        assert isinstance(manager.module_timestamps, dict)

    def test_reload_agent_not_found(self, manager):
        """Test reloading non-existent agent raises error"""
        with pytest.raises(ValueError, match="not found in runtime"):
            manager.reload_agent("NonExistentAgent")

    def test_reload_agent_no_definition(self, manager, mock_executor):
        """Test reloading agent without definition raises error"""
        mock_executor.agents = []

        with pytest.raises(ValueError, match="definition.*not found"):
            manager.reload_agent("TestAgent")

    @patch('importlib.reload')
    def test_reload_agent_success(self, mock_reload, manager, mock_executor, agent_def):
        """Test successful agent reload"""
        # Setup
        mock_executor.agents = [agent_def]

        # Create a proper module mock
        import types
        test_module = types.ModuleType('test_module')
        test_module.MockAgent = MockAgent

        # Mock the reloaded module
        reloaded_module = types.ModuleType('test_module')
        reloaded_module.MockAgent = MockAgent
        mock_reload.return_value = reloaded_module

        with patch('sys.modules', {'test_module': test_module}):
            # Reload
            result = manager.reload_agent("TestAgent", preserve_state=False)

            assert result["success"] is True
            assert result["node_name"] == "TestAgent"
            assert result["module"] == "test_module"
            assert result["class"] == "MockAgent"
            assert "timestamp" in result

    @patch('importlib.reload')
    def test_reload_agent_with_state_preservation(self, mock_reload, manager, mock_executor, agent_def):
        """Test agent reload with state preservation"""
        # Setup
        mock_executor.agents = [agent_def]
        old_agent = mock_executor.nodes["TestAgent"]
        old_agent.state_data = {"counter": 42}

        # Create proper module mock
        import types
        test_module = types.ModuleType('test_module')
        test_module.MockAgent = MockAgent

        # Mock the reloaded module
        reloaded_module = types.ModuleType('test_module')
        reloaded_module.MockAgent = MockAgent
        mock_reload.return_value = reloaded_module

        with patch('sys.modules', {'test_module': test_module}):
            # Reload
            result = manager.reload_agent("TestAgent", preserve_state=True)

            assert result["success"] is True
            assert result["state_preserved"] is True

            # Verify new agent has old state
            new_agent = mock_executor.nodes["TestAgent"]
            assert new_agent.state_data == {"counter": 42}

    @patch('importlib.reload')
    @patch('sys.modules', {'test_module': Mock()})
    def test_reload_agent_module_not_in_sys_modules(self, mock_reload, manager, mock_executor, agent_def):
        """Test reloading agent when module not in sys.modules"""
        mock_executor.agents = [agent_def]

        with patch('sys.modules', {}):
            with pytest.raises(ValueError, match="not found in sys.modules"):
                manager.reload_agent("TestAgent")

    @patch('importlib.reload')
    def test_reload_agent_class_not_found(self, mock_reload, manager, mock_executor, agent_def):
        """Test reloading when class not in reloaded module"""
        mock_executor.agents = [agent_def]

        # Create proper module mock
        import types
        test_module = types.ModuleType('test_module')
        test_module.MockAgent = MockAgent

        # Mock module without the class
        reloaded_module = types.ModuleType('test_module')
        # Don't add MockAgent to reloaded_module
        mock_reload.return_value = reloaded_module

        with patch('sys.modules', {'test_module': test_module}):
            with pytest.raises(ValueError, match="not found in reloaded module"):
                manager.reload_agent("TestAgent")

    @patch('importlib.reload')
    def test_reload_agent_with_subscriptions(self, mock_reload, manager, mock_executor, agent_def):
        """Test agent reload re-registers subscriptions"""
        # Setup subscriptions
        subscription = Mock()
        subscription.topic = Mock()
        subscription.topic.name = "/test/topic"
        subscription.handler_name = "on_test_event"
        agent_def.subscriptions = [subscription]
        mock_executor.agents = [agent_def]

        # Create proper module mock
        import types
        test_module = types.ModuleType('test_module')
        test_module.MockAgent = MockAgent

        # Mock the reloaded module
        reloaded_module = types.ModuleType('test_module')
        reloaded_module.MockAgent = MockAgent
        mock_reload.return_value = reloaded_module

        with patch('sys.modules', {'test_module': test_module}):
            # Reload
            result = manager.reload_agent("TestAgent")

            assert result["success"] is True

            # Verify unsubscribe was called for old handler
            mock_executor.event_router.unsubscribe.assert_called_once_with(
                "/test/topic", "TestAgent"
            )

            # Verify subscribe was called for new handler
            mock_executor.event_router.subscribe.assert_called_once()

    @patch('importlib.reload')
    def test_reload_agent_failure_recorded(self, mock_reload, manager, mock_executor, agent_def):
        """Test that failed reload is recorded in history"""
        mock_executor.agents = [agent_def]
        mock_reload.side_effect = Exception("Reload failed")

        with pytest.raises(ValueError, match="Failed to reload"):
            manager.reload_agent("TestAgent")

        # Verify failure recorded
        assert len(manager.reload_history) == 1
        assert manager.reload_history[0]["success"] is False
        assert "error" in manager.reload_history[0]

    def test_get_reload_history(self, manager):
        """Test getting reload history"""
        # Add some history entries
        manager.reload_history = [
            {"node_name": "Agent1", "timestamp": "2025-01-01T00:00:00", "success": True},
            {"node_name": "Agent2", "timestamp": "2025-01-01T00:01:00", "success": True},
            {"node_name": "Agent3", "timestamp": "2025-01-01T00:02:00", "success": False}
        ]

        history = manager.get_reload_history()

        assert len(history) == 3
        # Most recent first
        assert history[0]["node_name"] == "Agent3"
        assert history[-1]["node_name"] == "Agent1"

    def test_get_reload_history_filtered(self, manager):
        """Test getting reload history filtered by node name"""
        manager.reload_history = [
            {"node_name": "Agent1", "success": True},
            {"node_name": "Agent2", "success": True},
            {"node_name": "Agent1", "success": False}
        ]

        history = manager.get_reload_history(node_name="Agent1")

        assert len(history) == 2
        assert all(h["node_name"] == "Agent1" for h in history)

    def test_get_reload_history_with_limit(self, manager):
        """Test getting reload history with limit"""
        manager.reload_history = [
            {"node_name": f"Agent{i}", "success": True}
            for i in range(20)
        ]

        history = manager.get_reload_history(limit=5)

        assert len(history) == 5

    def test_can_reload_agent_success(self, manager, mock_executor, agent_def):
        """Test can_reload_agent returns True for valid agent"""
        mock_executor.agents = [agent_def]

        with patch('sys.modules', {'test_module': Mock()}):
            can_reload, reason = manager.can_reload_agent("TestAgent")

            assert can_reload is True
            assert reason is None

    def test_can_reload_agent_not_found(self, manager):
        """Test can_reload_agent returns False for non-existent agent"""
        can_reload, reason = manager.can_reload_agent("NonExistentAgent")

        assert can_reload is False
        assert "not found" in reason

    def test_can_reload_agent_no_definition(self, manager, mock_executor):
        """Test can_reload_agent returns False when definition not found"""
        mock_executor.agents = []

        can_reload, reason = manager.can_reload_agent("TestAgent")

        assert can_reload is False
        assert "definition not found" in reason

    def test_can_reload_agent_module_not_loaded(self, manager, mock_executor, agent_def):
        """Test can_reload_agent returns False when module not loaded"""
        mock_executor.agents = [agent_def]

        with patch('sys.modules', {}):
            can_reload, reason = manager.can_reload_agent("TestAgent")

            assert can_reload is False
            assert "not loaded" in reason

    @patch('importlib.reload')
    def test_reload_all_agents(self, mock_reload, manager, mock_executor):
        """Test reloading all agents"""
        # Setup multiple agents
        agent1 = Mock(spec=['name', 'module', 'class_name', 'subscriptions'])
        agent1.name = "Agent1"
        agent1.module = "mod1"
        agent1.class_name = "Agent1"
        agent1.subscriptions = []

        agent2 = Mock(spec=['name', 'module', 'class_name', 'subscriptions'])
        agent2.name = "Agent2"
        agent2.module = "mod2"
        agent2.class_name = "Agent2"
        agent2.subscriptions = []

        mock_executor.agents = [agent1, agent2]
        mock_executor.nodes = {
            "Agent1": MockAgent(),
            "Agent2": MockAgent()
        }

        # Create proper module mocks
        import types
        mod1 = types.ModuleType('mod1')
        mod1.Agent1 = MockAgent
        mod2 = types.ModuleType('mod2')
        mod2.Agent2 = MockAgent

        # Mock reloaded modules
        def create_mock_module(class_name):
            module = types.ModuleType('module')
            setattr(module, class_name, MockAgent)
            return module

        mock_reload.side_effect = [
            create_mock_module("Agent1"),
            create_mock_module("Agent2")
        ]

        with patch('sys.modules', {'mod1': mod1, 'mod2': mod2}):
            result = manager.reload_all_agents()

            # Debug output
            if result["failed"] > 0:
                for detail in result["details"]:
                    if not detail.get("success"):
                        print(f"Failed to reload {detail['node_name']}: {detail.get('error')}")

            assert result["total"] == 2
            assert result["succeeded"] == 2
            assert result["failed"] == 0
            assert len(result["details"]) == 2

    @patch('importlib.reload')
    def test_reload_all_agents_partial_failure(self, mock_reload, manager, mock_executor):
        """Test reload_all_agents with some failures"""
        # Setup agents
        agent1 = Mock(spec=['name', 'module', 'class_name', 'subscriptions'])
        agent1.name = "Agent1"
        agent1.module = "mod1"
        agent1.class_name = "Agent1"
        agent1.subscriptions = []

        agent2 = Mock(spec=['name', 'module', 'class_name', 'subscriptions'])
        agent2.name = "Agent2"
        agent2.module = "mod2"
        agent2.class_name = "Agent2"
        agent2.subscriptions = []

        mock_executor.agents = [agent1, agent2]
        mock_executor.nodes = {
            "Agent1": MockAgent(),
            "Agent2": MockAgent()
        }

        # Create proper module mocks
        import types
        mod1 = types.ModuleType('mod1')
        mod1.Agent1 = MockAgent

        # First reload succeeds, second fails
        reloaded = types.ModuleType('mod1')
        reloaded.Agent1 = MockAgent
        mock_reload.return_value = reloaded

        with patch('sys.modules', {'mod1': mod1}):
            result = manager.reload_all_agents()

            assert result["total"] == 2
            assert result["succeeded"] == 1
            assert result["failed"] == 1

    def test_watch_changes_requires_watchdog(self, manager):
        """Test that watch_changes raises error without watchdog"""
        with patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(ImportError, match="requires 'watchdog' package"):
                manager.watch_changes("/some/path")

    def test_stop_watching(self, manager):
        """Test stopping file watching"""
        mock_observer = Mock()
        manager.observer = mock_observer

        manager.stop_watching()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert not hasattr(manager, 'observer')

    def test_stop_watching_not_started(self, manager):
        """Test stop_watching when not watching"""
        # Should not raise error
        manager.stop_watching()
