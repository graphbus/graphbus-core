"""
Runtime Executor - Main entry point for Runtime Mode
"""

import importlib
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from graphbus_core.config import RuntimeConfig
from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph
from graphbus_core.node_base import GraphBusNode
from graphbus_core.runtime.loader import ArtifactLoader
from graphbus_core.runtime.message_bus import MessageBus
from graphbus_core.runtime.event_router import EventRouter
from graphbus_core.runtime.state import StateManager
from graphbus_core.runtime.hot_reload import HotReloadManager
from graphbus_core.runtime.health import HealthMonitor


class RuntimeExecutor:
    """
    Main executor for Runtime Mode.

    Responsibilities:
    - Load build artifacts
    - Instantiate node classes
    - Connect nodes to message bus
    - Route events to handlers
    - Execute static code (no agent negotiation)
    - Provide API for method calls and event publishing
    """

    def __init__(self, config: RuntimeConfig):
        """
        Initialize runtime executor.

        Args:
            config: RuntimeConfig with artifacts directory
        """
        self.config = config
        self.loader: Optional[ArtifactLoader] = None
        self.graph: Optional[AgentGraph] = None
        self.agent_definitions: List[AgentDefinition] = []
        self.agents: List[AgentDefinition] = []  # Alias for compatibility
        self.nodes: Dict[str, GraphBusNode] = {}
        self.bus: Optional[MessageBus] = None
        self.router: Optional[EventRouter] = None
        self._is_running = False

        # Advanced features
        self.state_manager: Optional[StateManager] = None
        self.hot_reload_manager: Optional[HotReloadManager] = None
        self.health_monitor: Optional[HealthMonitor] = None

    @property
    def message_bus(self):
        """Alias for bus property."""
        return self.bus

    @property
    def event_router(self):
        """Alias for router property."""
        return self.router

    def load_artifacts(self) -> None:
        """Load build artifacts from configured directory."""
        print(f"[RuntimeExecutor] Loading artifacts from {self.config.artifacts_dir}")

        self.loader = ArtifactLoader(self.config.artifacts_dir)

        # Validate artifacts
        issues = self.loader.validate_artifacts()
        if issues:
            print(f"[RuntimeExecutor] Warning: Artifact validation found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")

        # Load all artifacts
        self.graph, self.agent_definitions, topics, subscriptions = self.loader.load_all()

        # Also set agents alias for compatibility
        self.agents = self.agent_definitions

        print(f"[RuntimeExecutor] Loaded {len(self.agent_definitions)} agents, "
              f"{len(topics)} topics, {len(subscriptions)} subscriptions")

    def initialize_nodes(self) -> Dict[str, GraphBusNode]:
        """
        Instantiate all node classes from agent definitions.

        Returns:
            Dict of node_name -> GraphBusNode instance
        """
        print("[RuntimeExecutor] Initializing nodes...")

        for agent_def in self.agent_definitions:
            try:
                # Import the module
                module = importlib.import_module(agent_def.module)

                # Get the class
                node_class = getattr(module, agent_def.class_name)

                # Verify it's a GraphBusNode subclass
                if not issubclass(node_class, GraphBusNode):
                    print(f"[RuntimeExecutor] Warning: {agent_def.class_name} is not a GraphBusNode")
                    continue

                # Instantiate the node (Runtime Mode - no bus yet, no memory)
                node = node_class(bus=None, memory=None)
                node.set_mode("runtime")

                # Set the node name for identification
                node.name = agent_def.name

                # Store instance
                self.nodes[agent_def.name] = node

                print(f"[RuntimeExecutor]   ✓ Initialized {agent_def.name}")

            except Exception as e:
                print(f"[RuntimeExecutor]   ✗ Failed to initialize {agent_def.name}: {e}")

        print(f"[RuntimeExecutor] Initialized {len(self.nodes)}/{len(self.agent_definitions)} nodes")

        return self.nodes

    def setup_message_bus(self) -> None:
        """Setup message bus and connect nodes."""
        if not self.config.enable_message_bus:
            print("[RuntimeExecutor] Message bus disabled in config")
            return

        print("[RuntimeExecutor] Setting up message bus...")

        # Create message bus
        self.bus = MessageBus()

        # Create event router
        self.router = EventRouter(self.bus, self.nodes)

        # Register all subscriptions from artifacts
        subscriptions = self.loader.load_subscriptions()
        self.router.register_subscriptions(subscriptions)

        # Update nodes to have bus reference
        for node in self.nodes.values():
            node.bus = self.bus

        print(f"[RuntimeExecutor] Message bus ready with {len(subscriptions)} subscriptions")

    def start(self, enable_state_persistence: bool = False,
              enable_hot_reload: bool = False,
              enable_health_monitoring: bool = False) -> None:
        """
        Start the runtime executor.

        Loads artifacts, initializes nodes, and sets up message bus.

        Args:
            enable_state_persistence: Enable agent state persistence
            enable_hot_reload: Enable hot reload capability
            enable_health_monitoring: Enable health monitoring
        """
        if self._is_running:
            print("[RuntimeExecutor] Already running")
            return

        print("\n" + "=" * 60)
        print("GRAPHBUS RUNTIME MODE - STARTING")
        print("=" * 60)

        # Load artifacts
        self.load_artifacts()

        # Initialize nodes
        self.initialize_nodes()

        # Setup message bus
        self.setup_message_bus()

        # Setup advanced features
        if enable_state_persistence:
            self.setup_state_management()

        if enable_hot_reload:
            self.setup_hot_reload()

        if enable_health_monitoring:
            self.setup_health_monitoring()

        self._is_running = True

        print("=" * 60)
        print(f"RUNTIME READY - {len(self.nodes)} nodes active")
        if self.state_manager:
            print("  State Persistence: ENABLED")
        if self.hot_reload_manager:
            print("  Hot Reload: ENABLED")
        if self.health_monitor:
            print("  Health Monitoring: ENABLED")
        print("=" * 60)
        print()

    def stop(self) -> None:
        """Stop the runtime executor."""
        if not self._is_running:
            print("[RuntimeExecutor] Not running")
            return

        print("[RuntimeExecutor] Stopping...")
        self._is_running = False
        print("[RuntimeExecutor] Stopped")

    def call_method(
        self,
        node_name: str,
        method_name: str,
        **kwargs
    ) -> Any:
        """
        Call a method on a node directly (bypassing message bus).

        Args:
            node_name: Name of the node
            method_name: Name of the method
            **kwargs: Method arguments

        Returns:
            Method return value

        Raises:
            ValueError: If node or method not found
        """
        if not self._is_running:
            raise RuntimeError("Runtime executor not started")

        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")

        node = self.nodes[node_name]
        method = getattr(node, method_name, None)

        if method is None:
            raise ValueError(f"Method '{method_name}' not found on node '{node_name}'")

        if not callable(method):
            raise ValueError(f"'{method_name}' on '{node_name}' is not callable")

        # Call the method
        result = method(**kwargs)
        return result

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        source: str = "runtime"
    ) -> None:
        """
        Publish an event to the message bus.

        Args:
            topic: Topic name (e.g., "/Order/Created")
            payload: Event payload
            source: Source of the event

        Raises:
            RuntimeError: If message bus not enabled
        """
        if not self._is_running:
            raise RuntimeError("Runtime executor not started")

        if self.bus is None:
            raise RuntimeError("Message bus not enabled")

        self.bus.publish(topic, payload, source)

    def get_node(self, node_name: str) -> GraphBusNode:
        """
        Get a node instance by name.

        Args:
            node_name: Name of the node

        Returns:
            GraphBusNode instance

        Raises:
            ValueError: If node not found
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")

        return self.nodes[node_name]

    def get_all_nodes(self) -> Dict[str, GraphBusNode]:
        """
        Get all node instances.

        Returns:
            Dict of node_name -> GraphBusNode
        """
        return self.nodes.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get runtime statistics.

        Returns:
            Dict with runtime stats
        """
        stats = {
            "is_running": self._is_running,
            "nodes_count": len(self.nodes),
            "agents_count": len(self.agent_definitions),
            "nodes_active": list(self.nodes.keys())
        }

        if self.bus:
            stats["message_bus"] = self.bus.get_stats()

        if self.router:
            stats["router"] = {
                "topics_count": len(self.router.get_all_handlers()),
                "handlers_count": sum(
                    len(handlers) for handlers in self.router.get_all_handlers().values()
                )
            }

        return stats

    def setup_state_management(self, state_dir: str = ".graphbus/state") -> None:
        """
        Setup state management for agents.

        Args:
            state_dir: Directory to store state files
        """
        print("[RuntimeExecutor] Setting up state management...")
        self.state_manager = StateManager(state_dir)

        # Load saved states for all nodes
        saved_states = self.state_manager.list_saved_states()
        for node_name in saved_states:
            if node_name in self.nodes:
                node = self.nodes[node_name]
                if hasattr(node, 'set_state'):
                    try:
                        state = self.state_manager.load_state(node_name)
                        node.set_state(state)
                        print(f"[RuntimeExecutor]   ✓ Restored state for {node_name}")
                    except Exception as e:
                        print(f"[RuntimeExecutor]   ⚠ Failed to restore state for {node_name}: {e}")

        print(f"[RuntimeExecutor] State management ready")

    def setup_hot_reload(self) -> None:
        """Setup hot reload manager."""
        print("[RuntimeExecutor] Setting up hot reload...")
        self.hot_reload_manager = HotReloadManager(self)
        print("[RuntimeExecutor] Hot reload ready")

    def setup_health_monitoring(self, enable_auto_restart: bool = False) -> None:
        """
        Setup health monitoring for agents.

        Args:
            enable_auto_restart: Enable automatic restart of failed agents
        """
        print("[RuntimeExecutor] Setting up health monitoring...")
        self.health_monitor = HealthMonitor(
            self,
            enable_auto_restart=enable_auto_restart
        )

        # Wrap call_method to record health metrics
        original_call_method = self.call_method

        def monitored_call_method(node_name: str, method_name: str, *args, **kwargs):
            try:
                result = original_call_method(node_name, method_name, *args, **kwargs)
                self.health_monitor.record_success(node_name)
                return result
            except Exception as e:
                self.health_monitor.record_failure(node_name, e)
                raise

        self.call_method = monitored_call_method

        print(f"[RuntimeExecutor] Health monitoring ready (auto-restart: {enable_auto_restart})")

    def save_node_state(self, node_name: str) -> None:
        """
        Save state for a specific node.

        Args:
            node_name: Name of the node to save state for

        Raises:
            ValueError: If state management is not enabled or node doesn't exist
        """
        if not self.state_manager:
            raise ValueError("State management is not enabled")

        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")

        node = self.nodes[node_name]
        if hasattr(node, 'get_state'):
            state = node.get_state()
            self.state_manager.save_state(node_name, state)
        else:
            raise ValueError(f"Node '{node_name}' does not support state persistence")

    def save_all_states(self) -> int:
        """
        Save state for all nodes that support it.

        Returns:
            Number of states saved

        Raises:
            ValueError: If state management is not enabled
        """
        if not self.state_manager:
            raise ValueError("State management is not enabled")

        count = 0
        for node_name, node in self.nodes.items():
            if hasattr(node, 'get_state'):
                try:
                    state = node.get_state()
                    self.state_manager.save_state(node_name, state)
                    count += 1
                except Exception as e:
                    print(f"Warning: Failed to save state for {node_name}: {e}")

        return count

    def __repr__(self) -> str:
        """String representation of runtime executor."""
        return (
            f"RuntimeExecutor("
            f"running={self._is_running}, "
            f"nodes={len(self.nodes)}, "
            f"bus={'enabled' if self.bus else 'disabled'})"
        )


def run_runtime(artifacts_dir: str = ".graphbus", enable_message_bus: bool = True) -> RuntimeExecutor:
    """
    Convenience function to start runtime with default config.

    Args:
        artifacts_dir: Path to artifacts directory
        enable_message_bus: Whether to enable message bus

    Returns:
        Started RuntimeExecutor instance
    """
    config = RuntimeConfig(
        artifacts_dir=artifacts_dir,
        enable_message_bus=enable_message_bus
    )

    executor = RuntimeExecutor(config)
    executor.start()

    return executor
