"""
Hello World Agent - Simple demonstration of GraphBus agent structure.

This agent demonstrates:
- Basic agent structure inheriting from GraphBusNode
- Using schema_method decorator for type-safe methods
- Method invocation for direct calls
"""

from graphbus_core import GraphBusNode, schema_method


class HelloAgent(GraphBusNode):
    """
    A simple agent that says hello.

    This demonstrates the basic GraphBus agent pattern.
    """

    def __init__(self):
        """Initialize the HelloAgent."""
        super().__init__()
        self.greeting_count = 0

    @schema_method(
        input_schema={"name": str},
        output_schema={"message": str, "greeting_number": int, "greeted": str}
    )
    def say_hello(self, name: str = "World") -> dict:
        """
        Say hello to someone.

        Args:
            name: The name to greet (default: "World")

        Returns:
            dict: A greeting message with metadata
        """
        self.greeting_count += 1

        message = f"Hello, {name}!"
        response = {
            "message": message,
            "greeting_number": self.greeting_count,
            "greeted": name
        }

        return response

    @schema_method(
        input_schema={},
        output_schema={"total_greetings": int, "agent_name": str, "status": str}
    )
    def get_stats(self) -> dict:
        """
        Get statistics about this agent's activity.

        Returns:
            dict: Agent statistics
        """
        return {
            "total_greetings": self.greeting_count,
            "agent_name": "HelloAgent",
            "status": "active"
        }
