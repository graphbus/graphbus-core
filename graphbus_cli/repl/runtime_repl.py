"""
Interactive REPL for GraphBus runtime
"""

import json
import cmd
from typing import Optional
from rich.syntax import Syntax
from rich.table import Table

from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_cli.utils.output import console, print_error, print_success, print_info


class RuntimeREPL(cmd.Cmd):
    """Interactive REPL for GraphBus runtime"""

    intro = "[bold cyan]GraphBus Runtime REPL[/bold cyan]\nType 'help' for available commands\n"
    prompt = "[cyan]runtime>[/cyan] "

    def __init__(self, executor: RuntimeExecutor):
        super().__init__()
        self.executor = executor
        # Use stdout as None to prevent cmd from printing
        self.use_rawinput = True

    def emptyline(self):
        """Do nothing on empty line"""
        pass

    def default(self, line):
        """Handle unknown commands"""
        console.print(f"[red]Unknown command:[/red] {line}")
        console.print("Type 'help' for available commands")

    def do_call(self, arg):
        """
        Call an agent method.

        Usage: call <agent>.<method> [json_args]

        Examples:
          call HelloService.generate_message
          call HelloService.greet {"name": "Alice"}
        """
        if not arg:
            print_error("Usage: call <agent>.<method> [json_args]")
            return

        parts = arg.split(None, 1)
        method_path = parts[0]
        args_str = parts[1] if len(parts) > 1 else "{}"

        # Parse agent.method
        if "." not in method_path:
            print_error("Invalid format. Use: agent.method")
            return

        agent_name, method_name = method_path.rsplit(".", 1)

        try:
            # Parse arguments
            args = json.loads(args_str) if args_str else {}

            # Call method
            result = self.executor.call_method(agent_name, method_name, **args)

            # Display result
            if result is not None:
                result_json = json.dumps(result, indent=2, default=str)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
            else:
                console.print("[dim]No return value[/dim]")

        except json.JSONDecodeError:
            print_error(f"Invalid JSON arguments: {args_str}")
        except Exception as e:
            print_error(f"Error calling method: {str(e)}")

    def do_publish(self, arg):
        """
        Publish an event to the message bus.

        Usage: publish <topic> <json_payload>

        Examples:
          publish /test/event {"data": "test"}
          publish /hello/greeting {"message": "Hello, World!"}
        """
        if not self.executor.bus:
            print_error("Message bus is disabled")
            return

        if not arg:
            print_error("Usage: publish <topic> <json_payload>")
            return

        parts = arg.split(None, 1)
        if len(parts) < 2:
            print_error("Usage: publish <topic> <json_payload>")
            return

        topic = parts[0]
        payload_str = parts[1]

        try:
            # Parse payload
            payload = json.loads(payload_str)

            # Publish event
            self.executor.publish(topic, payload, source="repl")

            # Get stats to show delivery
            stats = self.executor.get_stats()
            delivered = stats.get("message_bus", {}).get("messages_delivered", 0)

            print_success(f"Event published to {topic}")
            console.print(f"[dim]Delivered to handlers[/dim]")

        except json.JSONDecodeError:
            print_error(f"Invalid JSON payload: {payload_str}")
        except Exception as e:
            print_error(f"Error publishing event: {str(e)}")

    def do_stats(self, arg):
        """
        Show runtime statistics.

        Usage: stats
        """
        try:
            stats = self.executor.get_stats()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")

            table.add_row("Status", "RUNNING" if stats['is_running'] else "STOPPED")
            table.add_row("Active Nodes", str(stats['nodes_count']))

            if stats.get("message_bus"):
                bus_stats = stats["message_bus"]
                table.add_row("Messages Published", str(bus_stats.get('messages_published', 0)))
                table.add_row("Messages Delivered", str(bus_stats.get('messages_delivered', 0)))

            console.print(table)

        except Exception as e:
            print_error(f"Error getting stats: {str(e)}")

    def do_nodes(self, arg):
        """
        List all nodes.

        Usage: nodes
        """
        try:
            nodes = self.executor.get_all_nodes()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Node", style="cyan")
            table.add_column("Type", style="dim")

            for name, node in nodes.items():
                node_type = type(node).__name__
                table.add_row(name, node_type)

            console.print(table)

        except Exception as e:
            print_error(f"Error listing nodes: {str(e)}")

    def do_topics(self, arg):
        """
        List all topics and their subscribers.

        Usage: topics
        """
        if not self.executor.bus:
            print_error("Message bus is disabled")
            return

        try:
            topics = self.executor.bus.get_all_topics()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Topic", style="cyan")
            table.add_column("Subscribers", style="dim")

            for topic in sorted(topics):
                subscribers = self.executor.bus.get_subscribers(topic)
                subscriber_str = ", ".join(subscribers) if subscribers else "[none]"
                table.add_row(topic, subscriber_str)

            console.print(table)

        except Exception as e:
            print_error(f"Error listing topics: {str(e)}")

    def do_history(self, arg):
        """
        Show message history.

        Usage: history [n]

        Examples:
          history      # Show last 10 messages
          history 20   # Show last 20 messages
        """
        if not self.executor.bus:
            print_error("Message bus is disabled")
            return

        try:
            limit = int(arg) if arg else 10
            history = self.executor.bus.get_message_history(limit=limit)

            if not history:
                print_info("No messages in history")
                return

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Topic", style="cyan")
            table.add_column("Source", style="dim")
            table.add_column("Payload", style="dim", overflow="fold")

            for event in history:
                payload_str = json.dumps(event.payload, default=str)
                if len(payload_str) > 50:
                    payload_str = payload_str[:47] + "..."
                table.add_row(event.topic, event.src, payload_str)

            console.print(table)

        except ValueError:
            print_error("Invalid number for history limit")
        except Exception as e:
            print_error(f"Error getting history: {str(e)}")

    def do_reload(self, arg):
        """
        Hot reload an agent.

        Usage: reload <agent_name> [--preserve-state]

        Examples:
          reload HelloService
          reload HelloService --preserve-state
        """
        if not self.executor.hot_reload_manager:
            print_error("Hot reload is not enabled. Start runtime with --watch flag")
            return

        if not arg:
            print_error("Usage: reload <agent_name> [--preserve-state]")
            return

        parts = arg.split()
        agent_name = parts[0]
        preserve_state = "--preserve-state" in parts

        try:
            with console.status(f"[cyan]Reloading {agent_name}...[/cyan]", spinner="dots"):
                result = self.executor.hot_reload_manager.reload_agent(
                    agent_name,
                    preserve_state=preserve_state
                )

            if result["success"]:
                print_success(f"Agent '{agent_name}' reloaded successfully")
                if result.get("state_preserved"):
                    console.print("[dim]State preserved[/dim]")
                console.print(f"[dim]Previous version: {result.get('old_version', 'unknown')}[/dim]")
                console.print(f"[dim]New version: {result.get('new_version', 'unknown')}[/dim]")
            else:
                print_error(f"Failed to reload '{agent_name}': {result.get('error', 'Unknown error')}")

        except Exception as e:
            print_error(f"Error reloading agent: {str(e)}")

    def do_health(self, arg):
        """
        Show agent health status.

        Usage: health [agent_name]

        Examples:
          health              # Show all agents
          health HelloService # Show specific agent
        """
        if not self.executor.health_monitor:
            print_error("Health monitoring is not enabled. Start runtime with --enable-health-monitoring flag")
            return

        try:
            if arg:
                # Show specific agent
                agent_name = arg.strip()
                metrics = self.executor.health_monitor.get_metrics(agent_name)

                if not metrics:
                    print_error(f"No health data for agent: {agent_name}")
                    return

                console.print(f"[bold cyan]Health Status: {agent_name}[/bold cyan]\n")

                table = Table(show_header=False)
                table.add_column("Metric", style="cyan")
                table.add_column("Value")

                status_color = {
                    "healthy": "green",
                    "degraded": "yellow",
                    "failed": "red"
                }.get(metrics.status.value, "white")

                table.add_row("Status", f"[{status_color}]{metrics.status.value.upper()}[/{status_color}]")
                table.add_row("Total Calls", str(metrics.total_calls))
                table.add_row("Successful", str(metrics.successful_calls))
                table.add_row("Failed", str(metrics.failed_calls))
                table.add_row("Consecutive Failures", str(metrics.consecutive_failures))
                table.add_row("Error Rate", f"{metrics.error_rate:.1%}")
                table.add_row("Success Rate", f"{metrics.success_rate:.1%}")

                if metrics.last_error:
                    table.add_row("Last Error", str(metrics.last_error))

                console.print(table)
            else:
                # Show all agents
                all_metrics = self.executor.health_monitor.get_all_metrics()

                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Agent", style="cyan")
                table.add_column("Status")
                table.add_column("Calls", justify="right")
                table.add_column("Success Rate", justify="right")
                table.add_column("Error Rate", justify="right")

                for agent_name, metrics in sorted(all_metrics.items()):
                    status_color = {
                        "healthy": "green",
                        "degraded": "yellow",
                        "failed": "red"
                    }.get(metrics.status.value, "white")

                    status_str = f"[{status_color}]{metrics.status.value.upper()}[/{status_color}]"

                    table.add_row(
                        agent_name,
                        status_str,
                        str(metrics.total_calls),
                        f"{metrics.success_rate:.1%}",
                        f"{metrics.error_rate:.1%}"
                    )

                console.print(table)

        except Exception as e:
            print_error(f"Error getting health status: {str(e)}")

    def do_cls(self, arg):
        """
        Clear the screen.

        Usage: cls
        """
        console.clear()

    def do_help(self, arg):
        """Show help for commands"""
        if arg:
            # Show help for specific command
            super().do_help(arg)
        else:
            # Show general help
            console.print("[bold cyan]Available commands:[/bold cyan]\n")

            commands = [
                ("call <agent>.<method> [args]", "Call agent method"),
                ("publish <topic> <payload>", "Publish event to message bus"),
                ("stats", "Show runtime statistics"),
                ("nodes", "List all nodes"),
                ("topics", "List topics and subscribers"),
                ("history [n]", "Show message history"),
                ("reload <agent> [--preserve-state]", "Hot reload an agent (requires --watch)"),
                ("health [agent]", "Show agent health status (requires --enable-health-monitoring)"),
                ("cls", "Clear the screen"),
                ("clear [agent.method]", "Clear breakpoints (requires --debug)"),
                ("help [command]", "Show help"),
                ("exit", "Exit REPL"),
            ]

            for cmd, desc in commands:
                console.print(f"  [cyan]{cmd:30}[/cyan] {desc}")

            console.print("\n[dim]For detailed help on a command, use: help <command>[/dim]")

    def do_exit(self, arg):
        """
        Exit the REPL.

        Usage: exit
        """
        print_info("Exiting REPL...")
        return True

    def do_quit(self, arg):
        """Alias for exit"""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Handle Ctrl+D"""
        console.print()
        return self.do_exit(arg)

    # Debugger commands
    def do_break(self, arg):
        """
        Set a breakpoint on a method.

        Usage: break <agent>.<method> [condition]

        Examples:
          break HelloService.generate_message
          break OrderProcessor.process_order payload.get('amount') > 100
        """
        if not self.executor.debugger:
            print_error("Debugger not enabled. Start with --debug flag")
            return

        if not arg:
            # List breakpoints
            breakpoints = self.executor.debugger.list_breakpoints()
            if not breakpoints:
                console.print("[dim]No breakpoints set[/dim]")
                return

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Breakpoint", style="cyan")
            table.add_column("Condition", style="yellow")
            table.add_column("Hits", justify="right")
            table.add_column("Enabled", justify="center")

            for bp in breakpoints:
                table.add_row(
                    bp.full_name,
                    bp.condition or "-",
                    str(bp.hit_count),
                    "✓" if bp.enabled else "✗"
                )

            console.print(table)
            return

        # Parse agent.method [condition]
        parts = arg.split(None, 1)
        method_path = parts[0]
        condition = parts[1] if len(parts) > 1 else None

        if "." not in method_path:
            print_error("Invalid format. Use: agent.method")
            return

        agent_name, method_name = method_path.rsplit(".", 1)

        try:
            bp = self.executor.debugger.add_breakpoint(agent_name, method_name, condition)
            print_success(f"Breakpoint set on {bp.full_name}")
            if condition:
                console.print(f"[dim]Condition: {condition}[/dim]")
        except Exception as e:
            print_error(f"Error setting breakpoint: {str(e)}")

    def do_continue(self, arg):
        """
        Continue execution to next breakpoint.

        Usage: continue
        """
        if not self.executor.debugger:
            print_error("Debugger not enabled")
            return

        try:
            self.executor.debugger.continue_execution()
            print_info("Continuing execution...")
        except Exception as e:
            print_error(f"Error: {str(e)}")

    def do_step(self, arg):
        """
        Step to next method call.

        Usage: step
        """
        if not self.executor.debugger:
            print_error("Debugger not enabled")
            return

        try:
            self.executor.debugger.step()
            print_info("Stepping...")
        except Exception as e:
            print_error(f"Error: {str(e)}")

    def do_inspect(self, arg):
        """
        Inspect current execution frame.

        Usage: inspect [payload|locals]

        Examples:
          inspect          # Show current frame
          inspect payload  # Show payload
          inspect locals   # Show local variables
        """
        if not self.executor.debugger:
            print_error("Debugger not enabled")
            return

        frame = self.executor.debugger.get_current_frame()
        if not frame:
            print_info("No current execution frame")
            return

        if not arg or arg == "frame":
            # Show frame info
            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("Agent", frame.agent_name)
            table.add_row("Method", frame.method_name)
            table.add_row("Timestamp", frame.timestamp.strftime("%H:%M:%S.%f"))

            console.print(table)

        elif arg == "payload":
            # Show payload
            if frame.payload is not None:
                payload_json = json.dumps(frame.payload, indent=2, default=str)
                syntax = Syntax(payload_json, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
            else:
                console.print("[dim]No payload[/dim]")

        elif arg == "locals":
            # Show local variables
            if frame.local_vars:
                locals_json = json.dumps(frame.local_vars, indent=2, default=str)
                syntax = Syntax(locals_json, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
            else:
                console.print("[dim]No local variables[/dim]")

        else:
            print_error(f"Unknown inspect target: {arg}")

    def do_trace(self, arg):
        """
        Show execution trace.

        Usage: trace [limit]

        Examples:
          trace      # Show last 20 calls
          trace 50   # Show last 50 calls
        """
        if not self.executor.debugger:
            print_error("Debugger not enabled")
            return

        try:
            limit = int(arg) if arg else 20
        except ValueError:
            print_error("Invalid limit. Use: trace [limit]")
            return

        trace = self.executor.debugger.get_execution_trace(limit)

        if not trace:
            print_info("No execution trace available")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Time", style="cyan")
        table.add_column("Agent.Method", style="yellow")
        table.add_column("Payload", style="dim")

        for i, frame in enumerate(trace, 1):
            payload_str = str(frame.payload)[:40]
            if len(str(frame.payload)) > 40:
                payload_str += "..."

            table.add_row(
                str(i),
                frame.timestamp.strftime("%H:%M:%S.%f")[:-3],
                frame.full_name,
                payload_str
            )

        console.print(table)

    def do_clear(self, arg):
        """
        Clear breakpoints.

        Usage: clear [agent.method]

        Examples:
          clear                              # Clear all breakpoints
          clear HelloService.generate_message  # Clear specific breakpoint
        """
        if not self.executor.debugger:
            print_error("Debugger not enabled")
            return

        if not arg:
            # Clear all
            self.executor.debugger.clear_breakpoints()
            print_success("All breakpoints cleared")
            return

        # Clear specific breakpoint
        if "." not in arg:
            print_error("Invalid format. Use: agent.method")
            return

        agent_name, method_name = arg.rsplit(".", 1)

        if self.executor.debugger.remove_breakpoint(agent_name, method_name):
            print_success(f"Breakpoint removed: {arg}")
        else:
            print_error(f"No breakpoint found: {arg}")

    def precmd(self, line):
        """Process line before execution"""
        # Strip whitespace
        return line.strip()

    def postcmd(self, stop, line):
        """Process after command execution"""
        if not stop:
            console.print()  # Add blank line after each command
        return stop


def start_repl(executor: RuntimeExecutor):
    """Start the interactive REPL"""
    repl = RuntimeREPL(executor)

    # Print intro
    console.print(repl.intro)

    # Run REPL loop
    try:
        repl.cmdloop()
    except KeyboardInterrupt:
        console.print("\n")
        print_info("Exiting REPL...")
