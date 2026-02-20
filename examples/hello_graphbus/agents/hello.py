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
        input_schema={"name": str},
        output_schema={"message": str}
    )
    def generate_message(self, name="World"):
        """Generate a personalized greeting message."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("'name' must be a non-empty string")
        return {"message": f"Hello, {name}!"}
