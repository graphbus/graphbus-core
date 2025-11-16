"""
Init command - Initialize new GraphBus projects from templates
"""

import click
from pathlib import Path
import shutil

from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header
)
from graphbus_cli.templates import get_template, list_templates


@click.command()
@click.argument('project_name')
@click.option(
    '--template',
    type=click.Choice(['basic', 'chatbot', 'workflow', 'microservices', 'etl'], case_sensitive=False),
    default='basic',
    help='Project template to use'
)
@click.option(
    '--output-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='.',
    help='Output directory (default: current directory)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing directory'
)
def init(project_name: str, template: str, output_dir: str, force: bool):
    """
    Initialize a new GraphBus project from a template.

    \b
    Creates a new project directory with a complete GraphBus application
    structure, including example agents, configuration, and tests.

    \b
    Available Templates:
      basic         - Simple 3-agent example (recommended for beginners)
      chatbot       - LLM-powered chatbot with specialized agents
      workflow      - Approval workflow with multiple stages
      microservices - Multi-service architecture with API gateway
      etl           - Data pipeline with extractors, transformers, loaders

    \b
    Examples:
      graphbus init my-project                    # Create basic project
      graphbus init my-bot --template chatbot
      graphbus init my-workflow --template workflow
      graphbus init my-app --template microservices
      graphbus init pipeline --template etl --output-dir ~/projects
    """
    output_path = Path(output_dir).resolve()
    project_path = output_path / project_name

    # Check if directory exists
    if project_path.exists():
        if not force:
            print_error(f"Directory '{project_path}' already exists. Use --force to overwrite.")
            raise click.Abort()

        print_info(f"Removing existing directory: {project_path}")
        shutil.rmtree(project_path)

    print_header(f"Initializing GraphBus Project: {project_name}")
    print_info(f"Template: {template}")
    print_info(f"Location: {project_path}")
    console.print()

    try:
        # Get template
        template_obj = get_template(template)

        # Create project from template
        with console.status("[cyan]Creating project structure...[/cyan]", spinner="dots"):
            template_obj.create_project(project_path, project_name)

        console.print()
        print_success(f"Project '{project_name}' created successfully!")
        console.print()

        # Show next steps
        print_header("Next Steps")
        console.print(f"1. [cyan]cd {project_name}[/cyan]")
        console.print(f"2. [cyan]pip install -r requirements.txt[/cyan]")
        console.print(f"3. [cyan]graphbus build agents/[/cyan]")
        console.print(f"4. [cyan]graphbus run .graphbus[/cyan]")
        console.print()
        console.print(f"[dim]See {project_name}/README.md for more information[/dim]")

    except Exception as e:
        print_error(f"Failed to create project: {str(e)}")
        raise click.Abort()


@click.command('list-templates')
def list_templates_cmd():
    """
    List available project templates.

    \b
    Shows all available templates that can be used with 'graphbus init'.
    """
    print_header("Available Templates")

    templates = list_templates()

    for name, description in templates.items():
        console.print(f"[cyan]{name:15}[/cyan] {description}")
