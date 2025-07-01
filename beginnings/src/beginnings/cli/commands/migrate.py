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


# Framework-specific migration commands

@click.command(name="from-flask")
@click.option(
    "--source", "-s",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Source Flask project directory"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    required=True,
    help="Output directory for Beginnings project"
)
@click.option(
    "--preserve-structure",
    is_flag=True,
    help="Preserve original Flask project structure"
)
@click.option(
    "--convert-config",
    is_flag=True,
    default=True,
    help="Convert Flask configuration to Beginnings format"
)
@click.option(
    "--convert-auth",
    is_flag=True,
    default=True,
    help="Convert Flask authentication to Beginnings auth extension"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview migration without creating files"
)
@click.option(
    "--generate-report",
    is_flag=True,
    help="Generate detailed migration report"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def migrate_from_flask(
    ctx, source, output, preserve_structure, convert_config, convert_auth,
    dry_run, generate_report, verbose
):
    """Migrate Flask application to Beginnings framework.
    
    This command analyzes a Flask application and converts it to use the
    Beginnings framework, preserving functionality while updating to use
    Beginnings patterns and extensions.
    """
    from ...migration.frameworks.flask_migrator import FlaskMigrator
    
    try:
        
        if verbose:
            info(f"Analyzing Flask project: {source}")
        
        migrator = FlaskMigrator(
            source_dir=source,
            output_dir=output,
            preserve_structure=preserve_structure,
            convert_config=convert_config,
            convert_auth=convert_auth,
            verbose=verbose
        )
        
        # Run migration
        result = asyncio.run(migrator.migrate(dry_run=dry_run))
        
        if dry_run:
            success("Flask migration preview completed")
            info("Preview results:")
            info(f"  Routes detected: {result.get('routes_count', 0)}")
            info(f"  Blueprints detected: {result.get('blueprints_count', 0)}")
            info(f"  Templates found: {result.get('templates_count', 0)}")
            info(f"  Configuration files: {result.get('config_files', 0)}")
        else:
            success("Migration completed successfully!")
            info(f"Beginnings project created at: {highlight(output)}")
            
            if result.get('blueprints_count', 0) > 0:
                info(f"Converted {result['blueprints_count']} Flask blueprints to route modules")
            
            if result.get('auth_detected'):
                info("Flask authentication converted to Beginnings auth extension")
        
        # Generate report if requested
        if generate_report:
            report_path = Path(output) / "migration_report.md"
            migrator.generate_report(result, report_path)
            info(f"Migration report: {report_path}")
        
    except Exception as e:
        error(f"Flask migration failed: {e}")
        if verbose:
            import traceback
            error(traceback.format_exc())
        ctx.exit(1)


@click.command(name="from-django")
@click.option(
    "--source", "-s",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Source Django project directory"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    required=True,
    help="Output directory for Beginnings project"
)
@click.option(
    "--convert-models",
    is_flag=True,
    default=True,
    help="Convert Django models to equivalent data structures"
)
@click.option(
    "--convert-views",
    is_flag=True,
    default=True,
    help="Convert Django views to Beginnings routes"
)
@click.option(
    "--convert-auth",
    is_flag=True,
    default=True,
    help="Convert Django authentication to Beginnings auth extension"
)
@click.option(
    "--convert-admin",
    is_flag=True,
    help="Generate admin interface equivalent"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview migration without creating files"
)
@click.option(
    "--generate-report",
    is_flag=True,
    help="Generate detailed migration report"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def migrate_from_django(
    ctx, source, output, convert_models, convert_views, convert_auth,
    convert_admin, dry_run, generate_report, verbose
):
    """Migrate Django application to Beginnings framework.
    
    This command analyzes a Django application and converts it to use the
    Beginnings framework, including models, views, and Django-specific
    features to their Beginnings equivalents.
    """
    from ...migration.frameworks.django_migrator import DjangoMigrator
    
    try:
        
        if verbose:
            info(f"Analyzing Django project: {source}")
        
        migrator = DjangoMigrator(
            source_dir=source,
            output_dir=output,
            convert_models=convert_models,
            convert_views=convert_views,
            convert_auth=convert_auth,
            convert_admin=convert_admin,
            verbose=verbose
        )
        
        # Run migration
        result = asyncio.run(migrator.migrate(dry_run=dry_run))
        
        if dry_run:
            success("Django migration preview completed")
            info("Preview results:")
            info(f"  Apps detected: {result.get('apps_count', 0)}")
            info(f"  Models detected: {result.get('models_count', 0)}")
            info(f"  Views detected: {result.get('views_count', 0)}")
            info(f"  URLs detected: {result.get('urls_count', 0)}")
        else:
            success("Migration completed successfully!")
            info(f"Beginnings project created at: {highlight(output)}")
            
            if result.get('models_count', 0) > 0:
                info(f"Converted {result['models_count']} Django models")
            
            if result.get('admin_detected'):
                info("Django admin interface patterns preserved")
        
        # Generate report if requested
        if generate_report:
            report_path = Path(output) / "migration_report.md"
            migrator.generate_report(result, report_path)
            info(f"Migration report: {report_path}")
        
    except Exception as e:
        error(f"Django migration failed: {e}")
        if verbose:
            import traceback
            error(traceback.format_exc())
        ctx.exit(1)


@click.command(name="from-fastapi")
@click.option(
    "--source", "-s",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Source FastAPI project directory"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    required=True,
    help="Output directory for Beginnings project"
)
@click.option(
    "--preserve-structure",
    is_flag=True,
    help="Preserve original FastAPI project structure"
)
@click.option(
    "--convert-models",
    is_flag=True,
    default=True,
    help="Convert Pydantic models to Beginnings data structures"
)
@click.option(
    "--convert-auth",
    is_flag=True,
    default=True,
    help="Convert FastAPI authentication to Beginnings auth extension"
)
@click.option(
    "--convert-dependencies",
    is_flag=True,
    default=True,
    help="Convert FastAPI dependencies to Beginnings middleware"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview migration without creating files"
)
@click.option(
    "--generate-report",
    is_flag=True,
    help="Generate detailed migration report"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def migrate_from_fastapi(
    ctx, source, output, preserve_structure, convert_models, convert_auth,
    convert_dependencies, dry_run, generate_report, verbose
):
    """Migrate FastAPI application to Beginnings framework.
    
    This command analyzes a FastAPI application and converts it to use the
    Beginnings framework, preserving the API structure while adapting to
    Beginnings patterns and extensions.
    """
    from ...migration.frameworks.fastapi_migrator import FastAPIMigrator
    
    try:
        
        if verbose:
            info(f"Analyzing FastAPI project: {source}")
        
        migrator = FastAPIMigrator(
            source_dir=source,
            output_dir=output,
            preserve_structure=preserve_structure,
            convert_models=convert_models,
            convert_auth=convert_auth,
            convert_dependencies=convert_dependencies,
            verbose=verbose
        )
        
        # Run migration
        result = asyncio.run(migrator.migrate(dry_run=dry_run))
        
        if dry_run:
            success("FastAPI migration preview completed")
            info("Preview results:")
            info(f"  Routes detected: {result.get('routes_count', 0)}")
            info(f"  Routers detected: {result.get('routers_count', 0)}")
            info(f"  Models detected: {result.get('models_count', 0)}")
            info(f"  Dependencies detected: {result.get('dependencies_count', 0)}")
        else:
            success("Migration completed successfully!")
            info(f"Beginnings project created at: {highlight(output)}")
            
            if result.get('routers_count', 0) > 0:
                info(f"Converted {result['routers_count']} FastAPI routers to route modules")
            
            if result.get('auth_detected'):
                info("FastAPI authentication converted to Beginnings auth extension")
        
        # Generate report if requested
        if generate_report:
            report_path = Path(output) / "migration_report.md"
            migrator.generate_report(result, report_path)
            info(f"Migration report: {report_path}")
        
    except Exception as e:
        error(f"FastAPI migration failed: {e}")
        if verbose:
            import traceback
            error(traceback.format_exc())
        ctx.exit(1)


# Register commands
migrate_group.add_command(run_migrations)
migrate_group.add_command(rollback_migrations)
migrate_group.add_command(migration_status)
migrate_group.add_command(list_migrations)
migrate_group.add_command(validate_migrations)
migrate_group.add_command(create_migration)
migrate_group.add_command(migration_report)
migrate_group.add_command(backup_migrations)

# Register framework migration commands
migrate_group.add_command(migrate_from_flask)
migrate_group.add_command(migrate_from_django)
migrate_group.add_command(migrate_from_fastapi)