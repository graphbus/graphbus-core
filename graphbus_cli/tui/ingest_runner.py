"""Ingest runner for TUI."""

from typing import Dict, Any


def run_ingest_interactive(project_path, home_dir):
    """Run ingest interactively."""
    return {
        "agents": [],
        "edges": [],
        "files_analyzed": 0,
    }


def parse_ingest_result(result):
    """Parse ingest result."""
    return {
        "agent_count": len(result.get("agents", [])),
        "edge_count": len(result.get("edges", [])),
        "files_analyzed": result.get("files_analyzed", 0),
    }


class IngestRunner:

    def detect_exclusions(self):
        """Auto-detect files/directories to exclude."""
        exclusions = ['.git', '__pycache__', '.pytest_cache', 'node_modules']
        return exclusions


    def customize_exclusions(self, exclusions):
        """Allow user to customize exclusion list."""
        self.exclusions = exclusions
        return self.exclusions

        """Auto-detect files/directories to exclude."""
        exclusions = ['.git', '__pycache__', '.pytest_cache', 'node_modules']
        return exclusions

    """Run ingest from TUI."""
    
    def __init__(self):
        pass
    
    def get_language_feedback(self, language):
        return f"{language} detected"
    
    def show_progress(self):
        pass
    
    def progress_callback(self, progress):
        pass
    
    def get_ingest_summary(self):
        return {}


def validate_project_path(path):
    """Validate project path."""
    from pathlib import Path
    p = Path(path)
    return p.exists() and p.is_dir()
