"""
PrinterService - Prints messages to console
"""

from graphbus_core import GraphBusNode, schema_method


class PrinterService(GraphBusNode):
    SYSTEM_PROMPT = """
    You print messages to the console.
    In Build Mode, you can propose adding formatting capabilities
    like colors or styling to improve output readability.
    """

    @schema_method(
        input_schema={"message": str},
        output_schema={}
    )
    def print_message(self, message: str):
        """Print a message to the console."""
        print(message)
        return {}
