"""Error handling."""

def format_error_message(error_type, context):
    """Format error message with helpful context."""
    messages = {
        "path_not_found": f"Path not found: {context}\nTry checking if the file or directory exists.",
        "permission_denied": f"Permission denied: {context}\nTry running with appropriate permissions.",
        "invalid_config": f"Invalid configuration: {context}\nCheck your settings and try again.",
    }
    
    if error_type in messages:
        return messages[error_type]
    
    # Default format
    formatted_type = error_type.replace("_", " ").title()
    return f"{formatted_type}: {context}\nSomething went wrong. Please try again."


class ErrorHandler:
    """Error handler for TUI."""
    
    def __init__(self):
        self.errors = []
    
    def add_error(self, error_type, context):
        msg = format_error_message(error_type, context)
        self.errors.append(msg)
        return msg
    
    def clear(self):
        self.errors = []
    
    def get_last(self):
        return self.errors[-1] if self.errors else None
