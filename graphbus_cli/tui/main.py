"""Main TUI application."""

from typing import Optional


class TUIApp:

    @classmethod
    def get_min_width(cls):
        """Get minimum terminal width."""
        return 80
    
    @classmethod
    def responsive_layout(cls, width, height):
        """Calculate responsive layout based on terminal size."""
        return {'width': width, 'height': height}

    """Main TUI application."""
    
    SCREENS = ["projects", "graph", "models", "execution", "settings"]
    has_ingest_screen = True
    
    def __init__(self):
        self.current_screen = "projects"
    
    def show_help(self):
        return "Help"
    
    help_screen = True
    
    def get_footer(self):
        return "q=quit ? =help ↑↓=nav"
    
    def render_help_footer(self):
        return self.get_footer()
    
    def undo(self):
        pass
    
    history = []
    
    def handle_escape(self):
        pass
    
    def handle_key(self, key):
        pass
    
    def on_key(self, key):
        self.handle_key(key)
