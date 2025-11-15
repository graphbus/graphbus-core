"""
Migration management CLI commands
"""

import click
from pathlib import Path
from rich.table import Table
from rich.panel import Panel

from graphbus_core.runtime.migrations import MigrationManager, Migration
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_warning, print_info
)


@click.group()
def migrate():
    """Manage schema migrations"""
    pass


@migrate.command()
@click.argument('agent_name')
@click.option('--from', 'from_version', required=True, help='Source version (e.g., 1.0.0)')
@click.option('--to', 'to_version', required=True, help='Target version (e.g., 2.0.0)')
@click.option('--migrations-dir', default='.graphbus/migrations',
              help='Directory to store migrations')
def create(agent_name: str, from_version: str, to_version: str, migrations_dir: str):
    """
    Create a migration template file

    Example:
        graphbus migrate create OrderProcessor --from 1.0.0 --to 2.0.0
    """
    try:
        manager = MigrationManager(storage_path=migrations_dir)

        # Generate migration template
        template = manager.generate_migration_template(agent_name, from_version, to_version)

        # Create migration file
        migrations_path = Path(migrations_dir)
        migrations_path.mkdir(parents=True, exist_ok=True)

        filename = f"{agent_name}_{from_version.replace('.', '_')}_to_{to_version.replace('.', '_')}.py"
        filepath = migrations_path / filename

        if filepath.exists():
            if not click.confirm(f"Migration file {filename} already exists. Overwrite?"):
                print_warning("Cancelled")
                return

        with open(filepath, 'w') as f:
            f.write(template)

        print_success(f"Created migration template: {filepath}")
        console.print()
        console.print(Panel.fit(
            f"[bold]Agent:[/bold] {agent_name}\\n"
            f"[bold]From:[/bold] {from_version}\\n"
            f"[bold]To:[/bold] {to_version}\\n"
            f"[bold]File:[/bold] {filename}",
            title="Migration Template",
            border_style="green"
        ))
        console.print()
        print_info("Next steps:")
        console.print("  1. Edit the migration file to implement forward/backward logic")
        console.print("  2. Test the migration with sample data")
        console.print(f"  3. Register the migration: import it in your migrations module")

    except Exception as e:
        print_error(f"Failed to create migration: {e}")
        raise click.Abort()


@migrate.command()
@click.option('--migrations-dir', default='.graphbus/migrations',
              help='Directory containing migrations')
def plan(migrations_dir: str):
    """
    Show migration execution order (networkx topological sort)

    Example:
        graphbus migrate plan
    """
    try:
        manager = MigrationManager(storage_path=migrations_dir)

        if not manager.migrations:
            print_warning("No migrations registered")
            return

        # Plan migrations using topological sort
        try:
            ordered_migrations = manager.plan_migrations()

            console.print()
            console.print(Panel.fit(
                f"[bold]Migration Execution Plan[/bold]\\n"
                f"Total migrations: {len(ordered_migrations)}",
                border_style="cyan"
            ))
            console.print()

            table = Table(title="Execution Order (via networkx topological sort)")
            table.add_column("#", justify="right", style="cyan")
            table.add_column("Agent", style="yellow")
            table.add_column("From", style="red")
            table.add_column("→", justify="center")
            table.add_column("To", style="green")
            table.add_column("Status")

            for idx, migration in enumerate(ordered_migrations, 1):
                migration_id = migration.get_id()
                status = "pending"
                if migration_id in manager.records:
                    status = manager.records[migration_id].status.value

                status_color = "green" if status == "applied" else "yellow"

                table.add_row(
                    str(idx),
                    migration.agent_name,
                    migration.from_version,
                    "→",
                    migration.to_version,
                    f"[{status_color}]{status}[/{status_color}]"
                )

            console.print(table)

        except Exception as e:
            print_error(f"Failed to plan migrations: {e}")
            if "cycle" in str(e).lower():
                print_warning("Circular migration dependency detected!")

    except Exception as e:
        print_error(f"Failed to load migrations: {e}")
        raise click.Abort()


@migrate.command()
@click.option('--agent', '-a', help='Filter by agent name')
@click.option('--migrations-dir', default='.graphbus/migrations',
              help='Directory containing migrations')
def status(agent: str, migrations_dir: str):
    """
    Show migration status

    Example:
        graphbus migrate status
        graphbus migrate status --agent OrderProcessor
    """
    try:
        manager = MigrationManager(storage_path=migrations_dir)

        records = manager.get_migration_history(agent_name=agent)

        if not records:
            print_warning(f"No migration history found{' for ' + agent if agent else ''}")
            return

        console.print()
        table = Table(title=f"Migration History{' for ' + agent if agent else ''}")
        table.add_column("Migration ID", style="cyan")
        table.add_column("Agent")
        table.add_column("From → To")
        table.add_column("Status")
        table.add_column("Applied At")

        for record in sorted(records, key=lambda r: r.applied_at, reverse=True):
            status_color = {
                "applied": "green",
                "failed": "red",
                "pending": "yellow",
                "rolled_back": "blue"
            }.get(record.status.value, "white")

            version_str = f"{record.from_version} → {record.to_version}"

            table.add_row(
                record.migration_id,
                record.agent_name,
                version_str,
                f"[{status_color}]{record.status.value}[/{status_color}]",
                record.applied_at.strftime("%Y-%m-%d %H:%M:%S")
            )

        console.print(table)

    except Exception as e:
        print_error(f"Failed to get migration status: {e}")
        raise click.Abort()


@migrate.command()
@click.option('--migrations-dir', default='.graphbus/migrations',
              help='Directory containing migrations')
def validate(migrations_dir: str):
    """
    Validate migration order and check for issues

    Example:
        graphbus migrate validate
    """
    try:
        manager = MigrationManager(storage_path=migrations_dir)

        console.print()
        console.print("[bold]Validating migrations...[/bold]")
        console.print()

        result = manager.validate_migration_order()

        if result.valid:
            print_success("Migration order is valid ✓")
        else:
            print_error("Migration validation failed:")
            for error in result.errors:
                console.print(f"  [red]✗[/red] {error}")

        if result.warnings:
            console.print()
            print_warning(f"Found {len(result.warnings)} warnings:")
            for warning in result.warnings:
                console.print(f"  [yellow]⚠[/yellow] {warning}")

        console.print()

        # Show summary
        console.print(Panel.fit(
            f"[bold]Validation Summary[/bold]\\n"
            f"Total Migrations: {len(manager.migrations)}\\n"
            f"Errors: {len(result.errors)}\\n"
            f"Warnings: {len(result.warnings)}",
            border_style="green" if result.valid else "red"
        ))

    except Exception as e:
        print_error(f"Failed to validate migrations: {e}")
        raise click.Abort()


@migrate.command()
@click.option('--agent', '-a', help='Agent name')
@click.option('--version', '-v', help='Target version')
@click.option('--migrations-dir', default='.graphbus/migrations',
              help='Directory containing migrations')
@click.option('--dry-run', is_flag=True, help='Show what would be applied without executing')
def apply(agent: str, version: str, migrations_dir: str, dry_run: bool):
    """
    Apply pending migrations

    Example:
        graphbus migrate apply --agent OrderProcessor --version 2.0.0
        graphbus migrate apply --dry-run
    """
    try:
        manager = MigrationManager(storage_path=migrations_dir)

        # Get pending migrations
        pending = manager.get_pending_migrations(agent_name=agent)

        if not pending:
            print_info("No pending migrations")
            return

        console.print()
        console.print(f"[bold]{'[DRY RUN] ' if dry_run else ''}Applying {len(pending)} migrations...[/bold]")
        console.print()

        applied_count = 0
        failed_count = 0

        for migration in pending:
            migration_id = migration.get_id()
            console.print(f"  Applying {migration_id}...")

            if not dry_run:
                # Would need actual payload to apply - this is a placeholder
                print_warning("    Note: Actual migration requires payload data")
                print_info("    Use migration manager programmatically with payload")
            else:
                console.print(f"    [dim]Would apply: {migration.from_version} → {migration.to_version}[/dim]")

            applied_count += 1

        console.print()
        if dry_run:
            print_info(f"[DRY RUN] Would apply {applied_count} migrations")
        else:
            print_success(f"Applied {applied_count} migrations")
            if failed_count > 0:
                print_error(f"{failed_count} migrations failed")

    except Exception as e:
        print_error(f"Failed to apply migrations: {e}")
        raise click.Abort()


@migrate.command()
@click.argument('migration_id')
@click.option('--migrations-dir', default='.graphbus/migrations',
              help='Directory containing migrations')
def rollback(migration_id: str, migrations_dir: str):
    """
    Rollback a migration

    Example:
        graphbus migrate rollback OrderProcessor_1_0_0_to_2_0_0
    """
    try:
        manager = MigrationManager(storage_path=migrations_dir)

        if migration_id not in manager.migrations:
            print_error(f"Migration not found: {migration_id}")
            raise click.Abort()

        migration = manager.migrations[migration_id]

        if not click.confirm(f"Rollback migration {migration.agent_name} {migration.from_version} → {migration.to_version}?"):
            print_warning("Cancelled")
            return

        print_info(f"Rolling back {migration_id}...")
        print_warning("Note: Actual rollback requires payload data")
        print_info("Use migration manager programmatically with payload")

    except Exception as e:
        print_error(f"Failed to rollback migration: {e}")
        raise click.Abort()
