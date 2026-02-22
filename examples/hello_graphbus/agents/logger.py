"""
LoggerService - Logs events
"""

from graphbus_core import GraphBusNode, subscribe


class LoggerService(GraphBusNode):
    SYSTEM_PROMPT = """
    You log events when greetings are generated.
    In Build Mode, you can negotiate with other services about
    what information should be logged and in what format.
    """

    @subscribe("/Hello/MessageGenerated")
    def on_message_generated(self, event):
        """Handle message generated events."""
        name = event.get('name', 'unknown')
        if not isinstance(name, str):
            name = str(name) if name is not None else 'unknown'
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = event.get('message', event.get('text', 'unknown'))
        print(f"[LOG] [{timestamp}] Greeting generated for '{name}': {message}")
