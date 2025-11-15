"""
HelloService - Generates greeting messages
"""

from graphbus_core import GraphBusNode, schema_method


class HelloService(GraphBusNode):
    SYSTEM_PROMPT = """
    You generate greeting messages.
    In Build Mode, you can negotiate with other services to improve
    the greeting format and content.
    """

    @schema_method(
        input_schema={},
        output_schema={"message": str}
    )
    def generate_message(self):
        """Generate a simple greeting message."""
        return {"message": "Hello, World!"}
