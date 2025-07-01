"""Migration management commands."""

import click
import asyncio
import json
from typing import Optional
from pathlib import Path

from ..utils.colors import success, error, info, highlight, warning
from ..utils.errors import ProjectError
from ...migration.registry import MigrationRegistry
from ...migration.runner import MigrationRunner
from ...migration.database import DatabaseMigrationRunner
from ...migration.code import CodeMigrationRunner
from ...migration.config import ConfigMigrationRunner
from ...migration.utils import MigrationUtils


@click.group(name="migrate")
def migrate_group():
    """Database and code migration commands."""
    pass


@click.command(name="run")
@click.option(
    "--target", "-t",
    help="Target version to migrate to"
)
@click.option(
    "--migration", "-m",
    multiple=True,
    help="Specific migration IDs to run"
)
@click.option(
    "--dry-run", "-d",
    is_flag=True,
    help="Preview migrations without executing"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force execution even with warnings"
)
@click.option(
    "--parallel", "-p",
    is_flag=True,
    help="Run independent migrations in parallel"
)
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.pass_context
def run_migrations(ctx, target, migration, dry_run, force, parallel, migration_path):
    """Run pending migrations."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        runner = MigrationRunner(registry)
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        if not registry.get_all_migrations():
            info("No migrations found")
            return
        
        # Run migrations
        migration_ids = list(migration) if migration else None
        
        if dry_run:
            info("Running migration preview...")
        else:
            info("Running migrations...")
        
        results = asyncio.run(runner.run_migrations(
            target_version=target,
            migration_ids=migration_ids,
            dry_run=dry_run,
            force=force,
            parallel=parallel
        ))
        
        # Display results
        if dry_run:
            success("Migration preview completed")
        else:
            success(f"Migrations completed: {len(results)} executed")
        
        for result in results:
            if result.is_success():
                if dry_run:
                    info(f"  Preview: {result.migration_id}")
                else:
                    success(f"  ✓ {result.migration_id}")
            else:
                error(f"  ✗ {result.migration_id}: {result.error_message}")
        
    except Exception as e:
        error(f"Migration failed: {e}")
        ctx.exit(1)


@click.command(name="rollback")
@click.option(
    "--target", "-t",
    help="Target version to rollback to"
)
@click.option(
    "--count", "-c",
    type=int,
    help="Number of migrations to rollback"
)
@click.option(
    "--migration", "-m",
    multiple=True,
    help="Specific migration IDs to rollback"
)
@click.option(
    "--dry-run", "-d",
    is_flag=True,
    help="Preview rollback without executing"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force rollback even with warnings"
)
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.pass_context
def rollback_migrations(ctx, target, count, migration, dry_run, force, migration_path):
    """Rollback migrations."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        runner = MigrationRunner(registry)
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        if dry_run:
            info("Running rollback preview...")
        else:
            warning("Rolling back migrations...")
        
        # Rollback migrations
        migration_ids = list(migration) if migration else None
        
        results = asyncio.run(runner.rollback_migrations(
            target_version=target,
            count=count,
            migration_ids=migration_ids,
            dry_run=dry_run,
            force=force
        ))
        
        # Display results
        if dry_run:
            success("Rollback preview completed")
        else:
            success(f"Rollback completed: {len(results)} migrations rolled back")
        
        for result in results:
            if result.is_success():
                if dry_run:
                    info(f"  Preview: {result.migration_id}")
                else:
                    success(f"  ✓ {result.migration_id}")
            else:
                error(f"  ✗ {result.migration_id}: {result.error_message}")
        
    except Exception as e:
        error(f"Rollback failed: {e}")
        ctx.exit(1)


@click.command(name="status")
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed status information"
)
def migration_status(migration_path, verbose):
    """Show migration status."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        runner = MigrationRunner(registry)
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        # Get status
        status = asyncio.run(runner.get_migration_status())
        
        # Display status
        info("Migration Status:")
        info(f"  Total migrations: {status['total_migrations']}")
        info(f"  Applied: {status['applied_migrations']}")
        info(f"  Pending: {status['pending_migrations']}")
        
        if verbose and status['pending_migration_ids']:
            info("\nPending migrations:")
            for migration_id in status['pending_migration_ids']:
                info(f"  - {migration_id}")
        
        if verbose and status['applied_migration_ids']:
            info("\nApplied migrations:")
            for migration_id in status['applied_migration_ids']:
                success(f"  ✓ {migration_id}")
        
        if status['last_execution']:
            last_exec = status['last_execution']
            info(f"\nLast execution: {last_exec['migration_id']} ({last_exec['status']})")
        
    except Exception as e:
        error(f"Failed to get migration status: {e}")


@click.command(name="list")
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed migration information"
)
@click.option(
    "--type", "-t",
    help="Filter by migration type"
)
@click.option(
    "--tag",
    help="Filter by tag"
)
def list_migrations(migration_path, verbose, type, tag):
    """List available migrations."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        migrations = registry.get_all_migrations()
        
        # Apply filters
        if type:
            migrations = [m for m in migrations if type.lower() in m.__class__.__name__.lower()]
        
        if tag:
            migrations = [m for m in migrations if tag in m.tags]
        
        if not migrations:
            info("No migrations found")
            return
        
        # Display migrations
        output = registry.list_migrations(verbose=verbose)
        click.echo(output)
        
    except Exception as e:
        error(f"Failed to list migrations: {e}")


@click.command(name="validate")
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.option(
    "--migration", "-m",
    multiple=True,
    help="Specific migration IDs to validate"
)
def validate_migrations(migration_path, migration):
    """Validate migrations."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        runner = MigrationRunner(registry)
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        # Validate migrations
        migration_ids = list(migration) if migration else None
        validation_results = asyncio.run(runner.validate_migrations(migration_ids))
        
        # Display results
        has_errors = False
        
        for migration_id, errors in validation_results.items():
            if errors:
                has_errors = True
                error(f"Migration {migration_id}:")
                for err in errors:
                    error(f"  - {err}")
            else:
                success(f"✓ {migration_id}")
        
        if has_errors:
            error("Validation failed for some migrations")
        else:
            success("All migrations are valid")
        
    except Exception as e:
        error(f"Validation failed: {e}")


@click.command(name="create")
@click.argument("description")
@click.option(
    "--type", "-t",
    type=click.Choice(["database", "code", "config"]),
    default="database",
    help="Type of migration to create"
)
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to save migration file"
)
@click.option(
    "--template",
    help="Template file to use"
)
def create_migration(description, type, migration_path, template):
    """Create a new migration."""
    try:
        # Generate migration ID
        migration_id = MigrationUtils.generate_migration_id(description)
        
        # Create migration directory if it doesn't exist
        migration_dir = Path(migration_path)
        migration_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension
        extensions = {
            "database": ".sql",
            "code": ".py",
            "config": ".json"
        }
        
        file_extension = extensions[type]
        file_path = migration_dir / f"{migration_id}{file_extension}"
        
        # Create migration template
        if template and Path(template).exists():
            # Use custom template
            content = Path(template).read_text(encoding='utf-8')
            content = content.format(
                migration_id=migration_id,
                description=description
            )
        else:
            # Use built-in template
            content = MigrationUtils.create_migration_template(
                type, migration_id, description
            )
        
        # Write migration file
        file_path.write_text(content, encoding='utf-8')
        
        success(f"Created {type} migration: {file_path}")
        info(f"Migration ID: {migration_id}")
        info(f"Description: {description}")
        
    except Exception as e:
        error(f"Failed to create migration: {e}")


@click.command(name="report")
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.option(
    "--output", "-o",
    help="Output file path"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Report format"
)
def migration_report(migration_path, output, format):
    """Generate migration analysis report."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        migrations = registry.get_all_migrations()
        
        if not migrations:
            info("No migrations found")
            return
        
        # Generate report
        if format == "json":
            impact = MigrationUtils.estimate_migration_impact(migrations)
            report_data = {
                "summary": impact,
                "migrations": [m.to_dict() for m in migrations]
            }
            report_content = json.dumps(report_data, indent=2)
        else:
            report_content = MigrationUtils.generate_migration_report(migrations)
        
        # Output report
        if output:
            Path(output).write_text(report_content, encoding='utf-8')
            success(f"Report saved to: {output}")
        else:
            click.echo(report_content)
        
    except Exception as e:
        error(f"Failed to generate report: {e}")


@click.command(name="backup")
@click.option(
    "--migration-path",
    default="migrations",
    help="Path to migration files"
)
@click.option(
    "--output", "-o",
    help="Backup file path"
)
def backup_migrations(migration_path, output):
    """Create backup of migrations."""
    try:
        # Initialize migration system
        registry = MigrationRegistry([migration_path])
        
        # Discover migrations
        asyncio.run(registry.discover_migrations())
        
        migrations = registry.get_all_migrations()
        
        if not migrations:
            info("No migrations found")
            return
        
        # Create backup
        backup_path = MigrationUtils.create_migration_backup(migrations, output)
        
        success(f"Migration backup created: {backup_path}")
        info(f"Backed up {len(migrations)} migrations")
        
    except Exception as e:
        error(f"Failed to create backup: {e}")


# Register commands
migrate_group.add_command(run_migrations)
migrate_group.add_command(rollback_migrations)
migrate_group.add_command(migration_status)
migrate_group.add_command(list_migrations)
migrate_group.add_command(validate_migrations)
migrate_group.add_command(create_migration)
migrate_group.add_command(migration_report)
migrate_group.add_command(backup_migrations)