"""Development server commands."""

import click
import os
from typing import Optional

from ..utils.colors import success, error, info, highlight
from ..utils.errors import ProjectError, validate_project_directory


@click.command(name="run")
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host to bind to"
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port to bind to"
)
@click.option(
    "--env",
    type=str,
    help="Environment to run (overrides global --env)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode"
)
@click.option(
    "--no-reload",
    is_flag=True,
    help="Disable auto-reload"
)
@click.option(
    "--watch-extensions",
    is_flag=True,
    help="Watch extension files for changes"
)
@click.pass_context
def run_command(
    ctx: click.Context,
    host: str,
    port: int,
    env: Optional[str],
    debug: bool,
    no_reload: bool,
    watch_extensions: bool
):
    """Start the development server.
    
    Runs the beginnings application with auto-reload and enhanced debugging
    features for development. The server will automatically restart when
    files change, validate configuration, and provide helpful error messages.
    """
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    config_dir = ctx.obj.get("config_dir")
    target_env = env or ctx.obj.get("env")
    
    # Validate we're in a beginnings project
    project_dir = os.getcwd()
    validate_project_directory(project_dir)
    
    if not quiet:
        click.echo(info(f"Starting beginnings development server"))
        click.echo(info(f"Environment: {target_env or 'production'}"))
        click.echo(info(f"Host: {host}:{port}"))
        if debug:
            click.echo(info("Debug mode enabled"))
        if not no_reload:
            click.echo(info("Auto-reload enabled"))
    
    try:
        # Validate configuration before starting
        if verbose:
            click.echo(info("Validating configuration..."))
        
        _validate_config_before_start(config_dir, target_env)
        
        if verbose:
            click.echo(success("Configuration validation passed"))
        
        # Start the server
        _start_development_server(
            project_dir=project_dir,
            host=host,
            port=port,
            env=target_env,
            config_dir=config_dir,
            debug=debug,
            reload=not no_reload,
            watch_extensions=watch_extensions,
            verbose=verbose,
            quiet=quiet
        )
        
    except Exception as e:
        raise ProjectError(
            f"Failed to start development server: {e}",
            suggestions=[
                "Check configuration files are valid",
                "Ensure port is not already in use",
                "Verify project structure is correct",
                "Run 'beginnings config validate' for detailed errors"
            ]
        )


def _validate_config_before_start(config_dir: Optional[str], env: Optional[str]):
    """Validate configuration before starting server."""
    try:
        from ...config.enhanced_loader import load_config_with_includes
        from ...config.validator import ConfigValidator
        
        # Load and validate configuration
        config = load_config_with_includes(config_dir or "config", env)
        validator = ConfigValidator()
        result = validator.validate(config, include_security=False)
        
        # Check for critical errors
        if result.get("errors"):
            raise ValueError(f"Configuration errors found: {', '.join(result['errors'])}")
            
    except ImportError:
        # Config modules might not be available yet
        pass
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def _start_development_server(
    project_dir: str,
    host: str,
    port: int,
    env: Optional[str],
    config_dir: Optional[str],
    debug: bool,
    reload: bool,
    watch_extensions: bool,
    verbose: bool,
    quiet: bool
):
    """Start the development server with specified options."""
    import uvicorn
    import sys
    
    # Find main application file
    main_file = _find_main_file(project_dir)
    
    if not main_file:
        raise ProjectError(
            "No main application file found",
            suggestions=[
                "Ensure main.py exists in project root",
                "Or create app.py with application instance",
                "Check project structure with 'beginnings config show'"
            ]
        )
    
    # Set environment variables for server
    if env:
        os.environ["BEGINNINGS_ENV"] = env
    if config_dir:
        os.environ["BEGINNINGS_CONFIG_DIR"] = config_dir
    if debug:
        os.environ["BEGINNINGS_DEBUG"] = "true"
    
    # Determine app module and variable
    app_module = main_file.replace(".py", "").replace("/", ".")
    app_variable = "app"
    
    # Build uvicorn configuration
    uvicorn_config = {
        "app": f"{app_module}:{app_variable}",
        "host": host,
        "port": port,
        "reload": reload,
        "log_level": "debug" if verbose else "info",
        "access_log": not quiet
    }
    
    # Add watch paths for reload
    if reload and watch_extensions:
        watch_dirs = [project_dir]
        # Add common extension directories
        for ext_dir in ["extensions", "plugins", "src"]:
            ext_path = os.path.join(project_dir, ext_dir)
            if os.path.exists(ext_path):
                watch_dirs.append(ext_path)
        uvicorn_config["reload_dirs"] = watch_dirs
    
    if not quiet:
        click.echo(success("Starting server..."))
        click.echo(info(f"Application: {app_module}:{app_variable}"))
        click.echo(info(f"Visit: http://{host}:{port}"))
        if reload:
            click.echo(info("Press Ctrl+C to stop"))
        click.echo()
    
    # Start uvicorn server
    try:
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        if not quiet:
            click.echo(info("Server stopped"))
    except Exception as e:
        raise ProjectError(f"Server failed to start: {e}")


def _find_main_file(project_dir: str) -> Optional[str]:
    """Find the main application file."""
    candidates = ["main.py", "app.py", "run.py", "server.py"]
    
    for candidate in candidates:
        full_path = os.path.join(project_dir, candidate)
        if os.path.exists(full_path):
            return candidate
    
    return None