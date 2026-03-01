"""
graphbus ingest — convert any codebase into .graphbus/ agent definitions.
"""

import click
from pathlib import Path


@click.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--strategy", default="directory", help="Boundary detection strategy (directory|llm)")
@click.option("--home-dir", default=None, type=click.Path(), help="Override ~/.graphbus/ location")
def ingest(path, strategy, home_dir):
    """Ingest a codebase and generate .graphbus/ agent definitions."""
    from graphbus_core.ingest.pipeline import run_ingest

    project_path = Path(path).resolve()
    home = Path(home_dir) if home_dir else None

    click.echo(f"Ingesting {project_path}...")

    result = run_ingest(
        project_path=project_path,
        home_dir=home,
        strategy=strategy,
    )

    click.echo(f"\n✅ Ingested {result['files_analyzed']} files into {len(result['agents'])} agents:")
    for agent in result["agents"]:
        click.echo(f"  • {agent}")

    if result["edges"]:
        click.echo(f"\nDependency edges:")
        for from_a, to_a in result["edges"]:
            click.echo(f"  {from_a} → {to_a}")

    click.echo(f"\nOutput: {result['graphbus_dir']}")


def register(cli):
    """Register the ingest command with the CLI."""
    cli.add_command(ingest)
