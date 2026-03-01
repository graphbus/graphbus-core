"""
Runtime Executor - Main entry point for Runtime Mode
"""

import importlib
import sys
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import deque

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
from graphbus_core.runtime.debugger import InteractiveDebugger
from graphbus_core.runtime.contracts import ContractManager
from graphbus_core.runtime.coherence import CoherenceTracker


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
        self.debugger: Optional[InteractiveDebugger] = None

        # Phase 4 features: Contract validation and coherence tracking
        self.contract_manager: Optional[ContractManager] = None
        self.coherence_tracker: Optional[CoherenceTracker] = None

        # Initialize contract manager if validation is enabled
        if config.enable_validation:
            contracts_dir = Path(config.artifacts_dir) / "contracts"
            if contracts_dir.exists():
                try:
                    self.contract_manager = ContractManager(storage_path=str(contracts_dir))
                except Exception as e:
                    print(f"[RuntimeExecutor] Warning: Failed to initialize contract manager: {e}")

        # Dashboard history tracking (last 1000 events/method calls)
        self._event_history: deque = deque(maxlen=1000)
        self._method_call_history: deque = deque(maxlen=1000)

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
              enable_health_monitoring: bool = False,
              enable_debugger: bool = False) -> None:
        """
        Start the runtime executor.

        Loads artifacts, initializes nodes, and sets up message bus.

        Args:
            enable_state_persistence: Enable agent state persistence
            enable_hot_reload: Enable hot reload capability
            enable_health_monitoring: Enable health monitoring
            enable_debugger: Enable interactive debugger
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

        if enable_debugger:
            self.setup_debugger()

        # Setup Phase 4 features: contract validation and coherence tracking
        self.setup_contract_validation()
        self.setup_coherence_tracking()

        self._is_running = True

        print("=" * 60)
        print(f"RUNTIME READY - {len(self.nodes)} nodes active")
        if self.state_manager:
            print("  State Persistence: ENABLED")
        if self.hot_reload_manager:
            print("  Hot Reload: ENABLED")
        if self.health_monitor:
            print("  Health Monitoring: ENABLED")
        if self.debugger:
            print("  Interactive Debugger: ENABLED")
        if self.contract_manager:
            print("  Contract Validation: ENABLED")
        if self.coherence_tracker:
            print("  Coherence Tracking: ENABLED")
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
            raise RuntimeError(
                "Runtime executor not started. Call executor.start() before invoking methods."
            )

        if node_name not in self.nodes:
            available = sorted(self.nodes.keys())
            hint = (
                f"Available nodes: {available}"
                if available
                else "No nodes are currently loaded."
            )
            raise ValueError(
                f"Node '{node_name}' not found. {hint}"
            )

        node = self.nodes[node_name]
        method = getattr(node, method_name, None)

        if method is None:
            schema_methods = list(node.get_schema_methods().keys())
            hint = (
                f"Schema methods on '{node_name}': {sorted(schema_methods)}"
                if schema_methods
                else f"'{node_name}' has no @schema_method decorated methods."
            )
            raise ValueError(
                f"Method '{method_name}' not found on node '{node_name}'. {hint}"
            )

        if not callable(method):
            raise ValueError(
                f"'{method_name}' on '{node_name}' is an attribute, not a callable method."
            )

        # Debugger hook before method call
        if self.debugger and self.debugger.enabled:
            self.debugger.on_method_call(node_name, method_name, **kwargs)

        # Log method call for dashboard
        self._log_method_call(node_name, method_name, kwargs)

        # Call the method, always recording duration even when an exception is raised.
        # Without try/finally a failed call leaves duration_ms: 0 in the dashboard,
        # hiding how long the method ran before it crashed.
        start_time = time.time()
        try:
            result = method(**kwargs)
            if self._method_call_history:
                self._method_call_history[-1]['success'] = True
            return result
        except Exception:
            raise  # re-raise unchanged; caller/health-monitor handles it
        finally:
            duration = time.time() - start_time
            if self._method_call_history:
                self._method_call_history[-1]['duration_ms'] = duration * 1000

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
            raise RuntimeError(
                "Runtime executor not started. Call executor.start() before publishing events."
            )

        if self.bus is None:
            raise RuntimeError(
                "Message bus not enabled. "
                "Pass enable_message_bus=True to RuntimeConfig (the default) to use pub/sub."
            )

        # Log event for dashboard
        self._log_event(topic, payload, source)

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
            available = sorted(self.nodes.keys())
            hint = (
                f"Available nodes: {available}"
                if available
                else "No nodes are currently loaded."
            )
            raise ValueError(f"Node '{node_name}' not found. {hint}")

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

        def monitored_call_method(node_name: str, method_name: str, **kwargs):
            try:
                result = original_call_method(node_name, method_name, **kwargs)
                self.health_monitor.record_success(node_name)
                return result
            except Exception as e:
                self.health_monitor.record_failure(node_name, e)
                raise

        self.call_method = monitored_call_method

        print(f"[RuntimeExecutor] Health monitoring ready (auto-restart: {enable_auto_restart})")

    def setup_debugger(self) -> None:
        """Setup interactive debugger."""
        print("[RuntimeExecutor] Setting up debugger...")
        self.debugger = InteractiveDebugger()
        self.debugger.enable()

        # Register callback to print when breakpoint is hit
        def on_break(frame):
            print(f"\n[DEBUGGER] Breakpoint hit: {frame.full_name}")
            print(f"[DEBUGGER] Payload: {frame.payload}")
            print(f"[DEBUGGER] Use 'continue' or 'step' in REPL to proceed\n")

        self.debugger.on_break(on_break)
        print("[RuntimeExecutor] Debugger ready")

    def save_node_state(self, node_name: str) -> None:
        """
        Save state for a specific node.

        Args:
            node_name: Name of the node to save state for

        Raises:
            ValueError: If state management is not enabled or node doesn't exist
        """
        if not self.state_manager:
            raise ValueError(
                "State management is not enabled. "
                "Call executor.start(enable_state_persistence=True) to enable it."
            )

        if node_name not in self.nodes:
            available = sorted(self.nodes.keys())
            hint = (
                f"Available nodes: {available}"
                if available
                else "No nodes are currently loaded."
            )
            raise ValueError(f"Node '{node_name}' not found. {hint}")

        node = self.nodes[node_name]
        if hasattr(node, 'get_state'):
            state = node.get_state()
            self.state_manager.save_state(node_name, state)
        else:
            raise ValueError(
                f"Node '{node_name}' does not support state persistence. "
                "Implement get_state() and set_state() on the node class to enable this feature."
            )

    def save_all_states(self) -> int:
        """
        Save state for all nodes that support it.

        Returns:
            Number of states saved

        Raises:
            ValueError: If state management is not enabled
        """
        if not self.state_manager:
            raise ValueError(
                "State management is not enabled. "
                "Call executor.start(enable_state_persistence=True) to enable it."
            )

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

    def _log_event(self, topic: str, payload: Dict[str, Any], source: str) -> None:
        """Log event for dashboard timeline."""
        event_log = {
            'timestamp': time.time(),
            'type': 'event',
            'topic': topic,
            'source': source,
            'payload_size': len(str(payload))
        }
        self._event_history.append(event_log)

    def _log_method_call(self, node_name: str, method_name: str, kwargs: Dict[str, Any]) -> None:
        """Log method call for dashboard."""
        method_log = {
            'timestamp': time.time(),
            'type': 'method_call',
            'node': node_name,
            'method': method_name,
            'args_count': len(kwargs),
            'duration_ms': 0,
            'success': False
        }
        self._method_call_history.append(method_log)

    def setup_contract_validation(self) -> None:
        """Setup contract validation for runtime."""
        # Skip if already initialized in __init__
        if self.contract_manager is not None:
            print(f"[RuntimeExecutor] Contract validation already enabled ({len(self.contract_manager.contracts)} contracts)")
            return

        contracts_dir = Path(self.config.artifacts_dir) / "contracts"

        if not contracts_dir.exists():
            print("[RuntimeExecutor] No contracts found, skipping contract validation")
            return

        try:
            self.contract_manager = ContractManager(
                storage_path=str(contracts_dir),
                graph=self.graph.graph if self.graph else None
            )
            print(f"[RuntimeExecutor] Contract validation enabled ({len(self.contract_manager.contracts)} contracts)")
        except Exception as e:
            print(f"[RuntimeExecutor] Warning: Failed to setup contract validation: {e}")

    def setup_coherence_tracking(self) -> None:
        """Setup coherence tracking for runtime."""
        coherence_dir = Path(self.config.artifacts_dir) / "coherence"

        try:
            self.coherence_tracker = CoherenceTracker(
                storage_path=str(coherence_dir),
                graph=self.graph.graph if self.graph else None
            )
            print(f"[RuntimeExecutor] Coherence tracking enabled")
        except Exception as e:
            print(f"[RuntimeExecutor] Warning: Failed to setup coherence tracking: {e}")

    def validate_interaction(self, source: str, target: str, topic: str,
                            payload: Dict[str, Any]) -> bool:
        """
        Validate an interaction between agents using contract manager.

        Args:
            source: Source agent name
            target: Target agent name
            topic: Event topic
            payload: Event payload

        Returns:
            True if valid, False otherwise
        """
        if not self.contract_manager:
            return True  # No validation if contracts not loaded

        # Track interaction for coherence
        if self.coherence_tracker:
            # Get schema version from contract (default to 1.0.0)
            source_contract = self.contract_manager.get_contract(source)
            version = source_contract.version if source_contract else "1.0.0"

            self.coherence_tracker.track_interaction(
                source=source,
                target=target,
                topic=topic,
                schema_version=version,
                payload=payload,
                successful=True
            )

        # Validate compatibility
        compatibility = self.contract_manager.validate_compatibility(source, target)

        if not compatibility.compatible:
            print(f"[RuntimeExecutor] Contract validation failed: {source} -> {target}")
            for issue in compatibility.issues:
                print(f"  - {issue.description}")
            return False

        return True

    def __repr__(self) -> str:
        """String representation of runtime executor."""
        return (
            f"RuntimeExecutor("
            f"running={self._is_running}, "
            f"nodes={len(self.nodes)}, "
            f"bus={'enabled' if self.bus else 'disabled'})"
        )


def run_runtime(
    artifacts_dir: str = ".graphbus",
    enable_message_bus: bool = True,
    enable_state_persistence: bool = False,
    enable_hot_reload: bool = False,
    enable_health_monitoring: bool = False
) -> RuntimeExecutor:
    """
    Convenience function to start runtime with default config.

    Args:
        artifacts_dir: Path to artifacts directory
        enable_message_bus: Whether to enable message bus
        enable_state_persistence: Enable agent state persistence
        enable_hot_reload: Enable hot reload capability
        enable_health_monitoring: Enable health monitoring

    Returns:
        Started RuntimeExecutor instance
    """
    config = RuntimeConfig(
        artifacts_dir=artifacts_dir,
        enable_message_bus=enable_message_bus
    )

    executor = RuntimeExecutor(config)
    executor.start(
        enable_state_persistence=enable_state_persistence,
        enable_hot_reload=enable_hot_reload,
        enable_health_monitoring=enable_health_monitoring
    )

    return executor
