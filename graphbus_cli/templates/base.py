"""
Base template class for project templates
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class Template(ABC):
    """Base class for project templates"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Template name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Template description"""
        pass

    @abstractmethod
    def create_project(self, project_path: Path, project_name: str) -> None:
        """
        Create project from template.

        Args:
            project_path: Path where project should be created
            project_name: Name of the project
        """
        pass

    def _create_directory_structure(self, project_path: Path) -> None:
        """Create standard directory structure"""
        (project_path / "agents").mkdir(parents=True)
        (project_path / "tests").mkdir(parents=True)
        (project_path / ".graphbus").mkdir(parents=True, exist_ok=True)

    def _write_file(self, file_path: Path, content: str) -> None:
        """Write content to file"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    def _render_template(self, template: str, **kwargs) -> str:
        """
        Simple template rendering.

        Args:
            template: Template string with {{variable}} placeholders
            **kwargs: Variables to substitute

        Returns:
            Rendered template
        """
        result = template
        for key, value in kwargs.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
