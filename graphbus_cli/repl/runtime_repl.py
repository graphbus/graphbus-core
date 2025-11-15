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

    def do_clear(self, arg):
        """
        Clear the screen.

        Usage: clear
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
                ("clear", "Clear the screen"),
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
