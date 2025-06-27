"""Main CLI entry point for the beginnings framework."""

import click
from typing import Optional

from .commands.config import config_group
from .commands.new import new_command  
from .commands.run import run_command
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
@click.pass_context
def cli(ctx: click.Context, config_dir: Optional[str], env: Optional[str], verbose: bool, quiet: bool):
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
    
    # Set up error handling
    ctx.obj["handle_error"] = handle_cli_error


# Add command groups
cli.add_command(config_group)
cli.add_command(new_command)
cli.add_command(run_command)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except CLIError as e:
        handle_cli_error(e)
    except Exception as e:
        click.echo(format_message(f"Unexpected error: {e}", Colors.RED), err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()