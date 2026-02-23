"""
Hot Reload Manager

Enables dynamic reloading of agent code without restarting the runtime.
"""

import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone


class HotReloadManager:
    """
    Manages hot reloading of agent code.

    Allows agents to be updated without restarting the entire runtime,
    preserving connections and state.
    """

    def __init__(self, runtime_executor):
        """
        Initialize HotReloadManager.

        Args:
            runtime_executor: RuntimeExecutor instance to manage
        """
        self.executor = runtime_executor
        self.reload_history: list[Dict[str, Any]] = []
        self.module_timestamps: Dict[str, float] = {}

    def reload_agent(self, node_name: str, preserve_state: bool = True) -> Dict[str, Any]:
        """
        Reload a specific agent.

        Args:
            node_name: Name of the agent to reload
            preserve_state: Whether to preserve agent state across reload

        Returns:
            Dict with reload status and metadata

        Raises:
            ValueError: If agent doesn't exist or reload fails
        """
        # Get current node
        if node_name not in self.executor.nodes:
            raise ValueError(f"Agent '{node_name}' not found in runtime")

        old_node = self.executor.nodes[node_name]

        # Save state if requested
        saved_state = None
        if preserve_state and hasattr(old_node, 'get_state'):
            try:
                saved_state = old_node.get_state()
            except Exception as e:
                # State capture failed — hot reload will continue but state will
                # not be restored. Log so the caller knows data may be lost.
                print(f"[HotReload] Warning: Failed to capture state for '{node_name}' "
                      f"before reload — state will not be restored: {e}")

        # Get agent definition
        agent_def = None
        for agent in self.executor.agents:
            if agent.name == node_name:
                agent_def = agent
                break

        if not agent_def:
            raise ValueError(f"Agent definition for '{node_name}' not found")

        try:
            # Reload the module
            module_name = agent_def.module
            if module_name in sys.modules:
                old_module = sys.modules[module_name]
                reloaded_module = importlib.reload(old_module)
            else:
                raise ValueError(f"Module '{module_name}' not found in sys.modules")

            # Get the new class
            class_name = agent_def.class_name
            if not hasattr(reloaded_module, class_name):
                raise ValueError(f"Class '{class_name}' not found in reloaded module")

            new_class = getattr(reloaded_module, class_name)

            # Unregister old subscriptions
            for sub in agent_def.subscriptions:
                topic_name = sub.topic.name if hasattr(sub.topic, 'name') else sub.topic
                if hasattr(self.executor, 'event_router'):
                    self.executor.event_router.unsubscribe(topic_name, node_name)

            # Create new instance
            new_node = new_class()

            # Set message bus if available
            if hasattr(self.executor, 'message_bus'):
                new_node.message_bus = self.executor.message_bus

            # Restore state if saved
            if saved_state and hasattr(new_node, 'set_state'):
                try:
                    new_node.set_state(saved_state)
                except Exception as e:
                    # Log so the caller knows state was not carried over; the new
                    # instance starts fresh rather than failing the whole reload.
                    print(f"[HotReload] Warning: Failed to restore state for '{node_name}' "
                          f"after reload — node will start with default state: {e}")

            # Replace node in executor
            self.executor.nodes[node_name] = new_node

            # Re-register subscriptions
            for sub in agent_def.subscriptions:
                topic_name = sub.topic.name if hasattr(sub.topic, 'name') else sub.topic
                handler_name = sub.handler_name

                if hasattr(self.executor, 'event_router') and hasattr(new_node, handler_name):
                    handler = getattr(new_node, handler_name)
                    self.executor.event_router.subscribe(topic_name, node_name, handler)

            # Record reload
            reload_info = {
                "node_name": node_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "module": module_name,
                "class": class_name,
                "state_preserved": saved_state is not None,
                "success": True
            }
            self.reload_history.append(reload_info)

            return reload_info

        except Exception as e:
            # Record failed reload
            reload_info = {
                "node_name": node_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False
            }
            self.reload_history.append(reload_info)
            raise ValueError(f"Failed to reload agent '{node_name}': {e}")

    def reload_all_agents(self, preserve_state: bool = True) -> Dict[str, Any]:
        """
        Reload all agents in the runtime.

        Args:
            preserve_state: Whether to preserve agent state

        Returns:
            Dict with summary of reload results
        """
        results = {
            "total": len(self.executor.nodes),
            "succeeded": 0,
            "failed": 0,
            "details": []
        }

        for node_name in list(self.executor.nodes.keys()):
            try:
                reload_info = self.reload_agent(node_name, preserve_state)
                results["succeeded"] += 1
                results["details"].append(reload_info)
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "node_name": node_name,
                    "error": str(e),
                    "success": False
                })

        return results

    def get_reload_history(self, node_name: Optional[str] = None, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get reload history.

        Args:
            node_name: Optional filter by agent name
            limit: Maximum number of entries to return

        Returns:
            List of reload history entries
        """
        history = self.reload_history

        if node_name:
            history = [h for h in history if h.get("node_name") == node_name]

        # Return most recent entries
        return list(reversed(history[-limit:]))

    def watch_changes(self, agents_dir: str, callback: Optional[Callable] = None) -> None:
        """
        Watch for file changes and trigger auto-reload.

        Note: This requires the 'watchdog' package to be installed.

        Args:
            agents_dir: Directory to watch for changes
            callback: Optional callback function called after reload

        Raises:
            ImportError: If watchdog package is not installed
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            raise ImportError(
                "Hot reload watch mode requires 'watchdog' package. "
                "Install with: pip install watchdog"
            )

        class AgentChangeHandler(FileSystemEventHandler):
            def __init__(self, reload_manager):
                self.reload_manager = reload_manager
                self.last_reload = {}

            def on_modified(self, event):
                if event.is_directory or not event.src_path.endswith('.py'):
                    return

                # Debounce: only reload if >2 seconds since last reload
                now = datetime.now(timezone.utc).timestamp()
                if event.src_path in self.last_reload:
                    if now - self.last_reload[event.src_path] < 2.0:
                        return

                self.last_reload[event.src_path] = now

                # Try to determine which agent to reload
                file_path = Path(event.src_path)
                module_name = file_path.stem

                # Find matching agents
                for node_name, node in self.reload_manager.executor.nodes.items():
                    node_module = node.__class__.__module__
                    if module_name in node_module:
                        try:
                            print(f"Detected change in {file_path.name}, reloading {node_name}...")
                            result = self.reload_manager.reload_agent(node_name)
                            if result.get("success"):
                                print(f"✓ Successfully reloaded {node_name}")
                                if callback:
                                    callback(node_name, result)
                            else:
                                print(f"✗ Failed to reload {node_name}: {result.get('error')}")
                        except Exception as e:
                            print(f"✗ Error reloading {node_name}: {e}")

        handler = AgentChangeHandler(self)
        observer = Observer()
        observer.schedule(handler, agents_dir, recursive=True)
        observer.start()

        # Store observer for later cleanup
        self.observer = observer

        print(f"Watching {agents_dir} for changes...")
        print("Press Ctrl+C to stop watching")

    def stop_watching(self) -> None:
        """Stop watching for file changes."""
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()
            delattr(self, 'observer')

    def can_reload_agent(self, node_name: str) -> tuple[bool, Optional[str]]:
        """
        Check if an agent can be safely reloaded.

        Args:
            node_name: Name of the agent

        Returns:
            Tuple of (can_reload, reason_if_not)
        """
        if node_name not in self.executor.nodes:
            return False, f"Agent '{node_name}' not found"

        # Check if agent definition exists
        agent_def = None
        for agent in self.executor.agents:
            if agent.name == node_name:
                agent_def = agent
                break

        if not agent_def:
            return False, f"Agent definition not found"

        # Check if module is in sys.modules
        if agent_def.module not in sys.modules:
            return False, f"Module '{agent_def.module}' not loaded"

        # Check if there are in-flight messages (future enhancement)
        # For now, always allow reload
        return True, None
