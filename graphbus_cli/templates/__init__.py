"""
Project templates for GraphBus applications
"""

from typing import Dict
from .base import Template
from .basic import BasicTemplate
from .microservices import MicroservicesTemplate
from .etl import ETLTemplate
from .chatbot import ChatbotTemplate
from .workflow import WorkflowTemplate


_TEMPLATES: Dict[str, Template] = {
    'basic': BasicTemplate(),
    'microservices': MicroservicesTemplate(),
    'etl': ETLTemplate(),
    'chatbot': ChatbotTemplate(),
    'workflow': WorkflowTemplate(),
}


def get_template(name: str) -> Template:
    """
    Get a template by name.

    Args:
        name: Template name (basic, microservices, etl, chatbot, workflow)

    Returns:
        Template instance

    Raises:
        ValueError: If template doesn't exist
    """
    template = _TEMPLATES.get(name.lower())
    if not template:
        raise ValueError(f"Template '{name}' not found. Available: {', '.join(_TEMPLATES.keys())}")
    return template


def list_templates() -> Dict[str, str]:
    """
    List all available templates.

    Returns:
        Dict mapping template names to descriptions
    """
    return {
        name: template.description
        for name, template in _TEMPLATES.items()
    }
