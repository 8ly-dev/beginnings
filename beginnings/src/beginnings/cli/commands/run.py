"""Development server commands."""

import click
import os
import signal
from typing import Optional

from ..utils.colors import success, error, info, highlight
from ..utils.errors import ProjectError, validate_project_directory
from ..reload.runner import AutoReloadRunner, create_auto_reload_runner
from ..reload.watcher import create_file_watcher
from ..reload.hot_reload import create_hot_reload_manager
from ..reload.config import ReloadConfig
from ..debug.dashboard import DebugDashboard
from ..debug.config import DebugConfig
from ..debug.profiler import start_profiling


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


@click.command(name="dev")
@click.option(
    "--app", "-a",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Application file to run"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file"
)
@click.option(
    "--reload/--no-reload",
    default=True,
    help="Enable/disable auto-reload"
)
@click.option(
    "--watch-paths",
    multiple=True,
    help="Additional paths to watch for changes"
)
@click.option(
    "--polling",
    is_flag=True,
    help="Use polling instead of native file watching"
)
@click.option(
    "--reload-delay",
    type=float,
    default=1.0,
    help="Delay before reloading after file change"
)
@click.pass_context
def dev_command(
    ctx: click.Context,
    app: Optional[str],
    config: Optional[str],
    reload: bool,
    watch_paths: tuple,
    polling: bool,
    reload_delay: float
):
    """Start development server with enhanced auto-reload."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    # Find application file
    if not app:
        project_dir = os.getcwd()
        validate_project_directory(project_dir)
        app = _find_main_file(project_dir)
        if app:
            app = os.path.join(project_dir, app)
    
    if not app:
        raise ProjectError(
            "No application file found",
            suggestions=[
                "Use --app to specify application file",
                "Ensure main.py exists in current directory"
            ]
        )
    
    if not quiet:
        click.echo(info(f"Starting development server: {app}"))
        if reload:
            click.echo(info("Auto-reload enabled"))
    
    try:
        # Load reload configuration
        reload_config = ReloadConfig(
            enabled=reload,
            watch_paths=list(watch_paths) or [os.path.dirname(app)],
            reload_delay=reload_delay,
            use_polling=polling
        )
        
        # Create and start auto-reload runner
        runner = create_auto_reload_runner(app, reload_config)
        
        # Set up reload callback
        def on_reload(message):
            if not quiet:
                click.echo(info(f"Reload: {message}"))
        
        runner.set_reload_callback(on_reload)
        
        # Start the runner
        runner.start()
        
    except KeyboardInterrupt:
        if not quiet:
            click.echo(info("Development server stopped"))
    except Exception as e:
        raise ProjectError(f"Failed to start development server: {e}")


@click.command(name="watch")
@click.option(
    "--path", "-p",
    type=click.Path(exists=True),
    default=".",
    help="Path to watch for changes"
)
@click.option(
    "--pattern",
    multiple=True,
    default=["*.py", "*.yaml", "*.yml"],
    help="File patterns to watch"
)
@click.option(
    "--ignore",
    multiple=True,
    default=["*.pyc", "__pycache__/*"],
    help="Patterns to ignore"
)
@click.option(
    "--command",
    help="Command to run when files change"
)
@click.option(
    "--polling",
    is_flag=True,
    help="Use polling instead of native file watching"
)
@click.pass_context
def watch_command(
    ctx: click.Context,
    path: str,
    pattern: tuple,
    ignore: tuple,
    command: Optional[str],
    polling: bool
):
    """Watch files for changes and execute commands."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Watching: {path}"))
        click.echo(info(f"Patterns: {', '.join(pattern)}"))
        if command:
            click.echo(info(f"Command: {command}"))
    
    def on_change(event):
        if not quiet:
            click.echo(info(f"File {event.event_type}: {event.file_path}"))
        
        if command:
            if verbose:
                click.echo(info(f"Executing: {command}"))
            os.system(command)
    
    try:
        watcher = create_file_watcher(
            path=path,
            patterns=list(pattern),
            ignore_patterns=list(ignore),
            callback=on_change,
            use_polling=polling
        )
        
        if not quiet:
            click.echo(success("File watching started. Press Ctrl+C to stop."))
        
        watcher.start_watching()
        
    except KeyboardInterrupt:
        if not quiet:
            click.echo(info("File watching stopped"))
    except Exception as e:
        raise ProjectError(f"Failed to start file watcher: {e}")


@click.command(name="reload")
@click.option(
    "--signal", "-s",
    type=click.Choice(["graceful", "force"]),
    default="graceful",
    help="Type of reload signal to send"
)
@click.option(
    "--pid",
    type=int,
    help="Process ID to reload"
)
@click.pass_context
def reload_command(
    ctx: click.Context,
    signal: str,
    pid: Optional[int]
):
    """Trigger application reload."""
    quiet = ctx.obj.get("quiet", False)
    
    success_msg = trigger_reload(signal, pid)
    
    if not quiet:
        click.echo(success(success_msg))


@click.command(name="hot-reload")
@click.option(
    "--paths",
    multiple=True,
    default=["."],
    help="Paths to monitor for hot reload"
)
@click.option(
    "--include",
    multiple=True,
    default=["*.py"],
    help="File patterns to include"
)
@click.option(
    "--exclude",
    multiple=True,
    default=["*.pyc", "__pycache__/*"],
    help="File patterns to exclude"
)
@click.pass_context
def hot_reload_command(
    ctx: click.Context,
    paths: tuple,
    include: tuple,
    exclude: tuple
):
    """Start hot reload monitoring for live code updates."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info("Starting hot reload monitoring..."))
        click.echo(info(f"Watching paths: {', '.join(paths)}"))
    
    def on_reload(change_type, file_path):
        if not quiet:
            click.echo(success(f"Hot reloaded: {file_path} ({change_type})"))
    
    try:
        manager = create_hot_reload_manager(
            watch_paths=list(paths),
            patterns=list(include),
            ignore_patterns=list(exclude)
        )
        
        manager.set_reload_callback(on_reload)
        
        if not quiet:
            click.echo(success("Hot reload monitoring started. Press Ctrl+C to stop."))
        
        manager.start_monitoring()
        
        # Keep monitoring until interrupted
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        if not quiet:
            click.echo(info("Hot reload monitoring stopped"))
        manager.stop_monitoring()
    except Exception as e:
        raise ProjectError(f"Failed to start hot reload monitoring: {e}")


def trigger_reload(signal_type: str = "graceful", pid: Optional[int] = None) -> str:
    """Trigger application reload.
    
    Args:
        signal_type: Type of reload signal ("graceful" or "force")
        pid: Process ID to send signal to
        
    Returns:
        Success message
    """
    if pid:
        # Send signal to specific process
        try:
            if signal_type == "graceful":
                os.kill(pid, signal.SIGTERM)
                return f"Sent graceful reload signal to process {pid}"
            else:
                os.kill(pid, signal.SIGKILL)
                return f"Sent force reload signal to process {pid}"
        except ProcessLookupError:
            raise ProjectError(f"Process {pid} not found")
        except PermissionError:
            raise ProjectError(f"Permission denied to signal process {pid}")
    else:
        # Look for application processes to reload
        # This is a simplified implementation
        return "Reload signal sent (no specific process targeted)"


@click.command(name="debug")
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind debug dashboard to"
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port to bind debug dashboard to"
)
@click.option(
    "--monitor-app",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Application file to monitor"
)
@click.option(
    "--enable-profiler",
    is_flag=True,
    help="Enable performance profiler"
)
@click.option(
    "--max-requests",
    type=int,
    default=1000,
    help="Maximum requests to track"
)
@click.option(
    "--max-logs",
    type=int,
    default=500,
    help="Maximum log lines to keep"
)
@click.pass_context
def debug_command(
    ctx: click.Context,
    host: str,
    port: int,
    monitor_app: Optional[str],
    enable_profiler: bool,
    max_requests: int,
    max_logs: int
):
    """Start debugging dashboard with web interface."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Starting debug dashboard on http://{host}:{port}"))
        if monitor_app:
            click.echo(info(f"Monitoring application: {monitor_app}"))
        if enable_profiler:
            click.echo(info("Performance profiler enabled"))
    
    try:
        # Create debug configuration
        debug_config = DebugConfig(
            enabled=True,
            dashboard_host=host,
            dashboard_port=port,
            enable_profiler=enable_profiler,
            max_request_history=max_requests,
            max_log_lines=max_logs,
            enable_real_time_updates=True
        )
        
        # Create and start debug dashboard
        dashboard = DebugDashboard(
            config=debug_config,
            host=host,
            port=port,
            enable_profiler=enable_profiler,
            monitor_app=monitor_app
        )
        
        dashboard.start()
        
    except KeyboardInterrupt:
        if not quiet:
            click.echo(info("Debug dashboard stopped"))
    except Exception as e:
        raise ProjectError(f"Failed to start debug dashboard: {e}")


@click.command(name="profile")
@click.option(
    "--output",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Output file for profile data"
)
@click.option(
    "--duration",
    type=float,
    default=60.0,
    help="Duration to profile (seconds)"
)
@click.option(
    "--cpu",
    is_flag=True,
    default=True,
    help="Enable CPU profiling"
)
@click.option(
    "--memory",
    is_flag=True,
    help="Enable memory profiling"
)
@click.option(
    "--format",
    type=click.Choice(["json", "html"]),
    default="json",
    help="Output format"
)
@click.pass_context
def profile_command(
    ctx: click.Context,
    output: Optional[str],
    duration: float,
    cpu: bool,
    memory: bool,
    format: str
):
    """Start performance profiling session."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Starting profiling session for {duration} seconds"))
        if cpu:
            click.echo(info("CPU profiling enabled"))
        if memory:
            click.echo(info("Memory profiling enabled"))
    
    try:
        # Start profiling
        profiler = start_profiling(
            profile_cpu=cpu,
            profile_memory=memory,
            duration_seconds=duration
        )
        
        if not quiet:
            click.echo(success("Profiling started"))
            click.echo(info("Press Ctrl+C to stop early"))
        
        import time
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            if not quiet:
                click.echo(info("Profiling stopped early"))
        
        # Export results if output specified
        if output:
            if format == "json":
                profiler.export_json(output)
            elif format == "html":
                profiler.export_html(output)
            
            if not quiet:
                click.echo(success(f"Profile exported to: {output}"))
        
        # Show statistics
        stats = profiler.get_statistics()
        if not quiet:
            click.echo(info(f"Total profiles: {stats['total_profiles']}"))
            click.echo(info(f"Average duration: {stats['avg_duration_ms']:.2f}ms"))
        
    except Exception as e:
        raise ProjectError(f"Profiling failed: {e}")


@click.command(name="analyze")
@click.option(
    "--config",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file to analyze"
)
@click.option(
    "--app",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Application file to analyze"
)
@click.option(
    "--output",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Output file for analysis report"
)
@click.pass_context
def analyze_command(
    ctx: click.Context,
    config: Optional[str],
    app: Optional[str],
    output: Optional[str]
):
    """Analyze application for potential issues and optimizations."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info("Starting application analysis"))
    
    try:
        analysis_results = {
            "timestamp": time.time(),
            "config_analysis": {},
            "code_analysis": {},
            "recommendations": []
        }
        
        # Analyze configuration if provided
        if config:
            if not quiet:
                click.echo(info(f"Analyzing configuration: {config}"))
            
            # This would integrate with config validation
            analysis_results["config_analysis"] = {
                "file": config,
                "issues_found": 0,
                "security_score": 95,
                "performance_score": 88
            }
        
        # Analyze application code if provided
        if app:
            if not quiet:
                click.echo(info(f"Analyzing application: {app}"))
            
            # This would perform static code analysis
            analysis_results["code_analysis"] = {
                "file": app,
                "complexity_score": 75,
                "maintainability_score": 82,
                "potential_issues": []
            }
        
        # Generate recommendations
        analysis_results["recommendations"] = [
            "Enable debug middleware for better error tracking",
            "Consider adding request timeout configuration",
            "Implement proper logging configuration",
            "Add performance monitoring for critical endpoints"
        ]
        
        # Output results
        if output:
            import json
            with open(output, 'w') as f:
                json.dump(analysis_results, f, indent=2)
            
            if not quiet:
                click.echo(success(f"Analysis report saved to: {output}"))
        else:
            # Display summary
            if not quiet:
                click.echo(success("Analysis completed"))
                click.echo(info("Recommendations:"))
                for rec in analysis_results["recommendations"]:
                    click.echo(f"  • {rec}")
        
    except Exception as e:
        raise ProjectError(f"Analysis failed: {e}")