"""Main CLI entry point for the beginnings framework."""

import click
from typing import Optional

# Import performance optimizations early
from .utils.performance import (
    setup_performance_optimizations, monitor_performance, 
    PerformanceContext, fast_loader
)

# Set up performance optimizations immediately
setup_performance_optimizations()

# Lazy imports for better startup performance
def _import_config_group():
    from .commands.config import config_group
    return config_group

def _import_new_command():
    from .commands.new import new_command
    return new_command

def _import_run_commands():
    from .commands.run import (
        run_command, dev_command, watch_command, reload_command, hot_reload_command,
        debug_command, profile_command, analyze_command
    )
    return {
        'run': run_command,
        'dev': dev_command, 
        'watch': watch_command,
        'reload': reload_command,
        'hot_reload': hot_reload_command,
        'debug': debug_command,
        'profile': profile_command,
        'analyze': analyze_command
    }

def _import_extension_group():
    from .commands.extension import extension_group
    return extension_group

def _import_docs_group():
    from .commands.docs import docs_group
    return docs_group

def _import_migrate_group():
    from .commands.migrate import migrate_group
    return migrate_group

def _import_deploy_group():
    from .commands.deploy import deploy_group
    return deploy_group

# Register lazy command loaders
fast_loader.register_command('config', _import_config_group)
fast_loader.register_command('new', _import_new_command)
fast_loader.register_command('run_commands', _import_run_commands)
fast_loader.register_command('extension', _import_extension_group)
fast_loader.register_command('docs', _import_docs_group)
fast_loader.register_command('migrate', _import_migrate_group)
fast_loader.register_command('deploy', _import_deploy_group)

# Import utilities (these are lightweight)
from .utils.colors import Colors, format_message
from .utils.errors import CLIError, handle_cli_error


@click.group(name="beginnings")
@click.option(
    "--config-dir",
    "-c",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Configuration directory path",
    envvar="BEGINNINGS_CONFIG_DIR"
)
@click.option(
    "--env",
    "-e", 
    type=str,
    help="Environment name (dev, staging, production)",
    envvar="BEGINNINGS_ENV"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-error output"
)
@click.option(
    "--performance",
    is_flag=True,
    help="Enable performance monitoring"
)
@click.pass_context
@monitor_performance("CLI initialization", 50)
def cli(ctx: click.Context, config_dir: Optional[str], env: Optional[str], verbose: bool, quiet: bool, performance: bool):
    """Beginnings web framework command-line interface.
    
    Provides tools for project management, configuration validation,
    development server, and extension development.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options in context
    ctx.obj["config_dir"] = config_dir
    ctx.obj["env"] = env
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["performance"] = performance
    
    # Set up error handling
    ctx.obj["handle_error"] = handle_cli_error


# Lazy command registration for faster startup
def _register_commands():
    """Register all CLI commands using lazy loading."""
    with PerformanceContext("Command registration"):
        # Add command groups
        cli.add_command(fast_loader.get_command('config'))
        cli.add_command(fast_loader.get_command('new'))
        cli.add_command(fast_loader.get_command('extension'))
        cli.add_command(fast_loader.get_command('docs'))
        cli.add_command(fast_loader.get_command('migrate'))
        cli.add_command(fast_loader.get_command('deploy'))
        
        # Add run commands
        run_commands = fast_loader.get_command('run_commands')
        cli.add_command(run_commands['run'])
        cli.add_command(run_commands['dev'])
        cli.add_command(run_commands['watch'])
        cli.add_command(run_commands['reload'])
        cli.add_command(run_commands['hot_reload'])
        cli.add_command(run_commands['debug'])
        cli.add_command(run_commands['profile'])
        cli.add_command(run_commands['analyze'])

# Register commands on first access
_commands_registered = False

def _ensure_commands_registered():
    """Ensure commands are registered before CLI execution."""
    global _commands_registered
    if not _commands_registered:
        _register_commands()
        _commands_registered = True


@monitor_performance("CLI execution", 100)
def main():
    """Main entry point for the CLI."""
    try:
        # Ensure commands are registered before execution
        _ensure_commands_registered()
        
        # Execute CLI with performance monitoring
        with PerformanceContext("CLI execution"):
            cli()
            
    except CLIError as e:
        handle_cli_error(e)
    except Exception as e:
        click.echo(format_message(f"Unexpected error: {e}", Colors.RED), err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()