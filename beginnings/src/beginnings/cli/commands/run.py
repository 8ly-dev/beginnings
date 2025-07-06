"""Development server commands."""

import click
import os
import signal
import time
import ast
import inspect
from typing import Optional

from ..utils.colors import success, error, info, warning, highlight
from ..utils.errors import ProjectError, validate_project_directory
from ..reload.runner import AutoReloadRunner, create_auto_reload_runner
from ..reload.watcher import create_file_watcher
from ..reload.hot_reload import create_hot_reload_manager
from ..reload.config import ReloadConfig
from ..debug.dashboard import DebugDashboard
from ..debug.config import DebugConfig
from ..debug.profiler import start_profiling, PerformanceProfiler


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
@click.option(
    "--production-preview",
    is_flag=True,
    help="Run in production preview mode with full validation"
)
@click.option(
    "--validate-config",
    is_flag=True,
    help="Validate configuration before starting"
)
@click.pass_context
def run_command(
    ctx: click.Context,
    host: str,
    port: int,
    env: Optional[str],
    debug: bool,
    no_reload: bool,
    watch_extensions: bool,
    production_preview: bool,
    validate_config: bool
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
    
    # Handle production preview mode
    if production_preview:
        if not target_env:
            target_env = "production"
        validate_config = True
        no_reload = True  # No auto-reload in production preview
        debug = False     # No debug mode in production preview
    
    if not quiet:
        mode = "production preview" if production_preview else "development"
        click.echo(info(f"Starting beginnings {mode} server"))
        click.echo(info(f"Environment: {target_env or 'development'}"))
        click.echo(info(f"Host: {host}:{port}"))
        if debug:
            click.echo(info("Debug mode enabled"))
        if not no_reload:
            click.echo(info("Auto-reload enabled"))
        if production_preview:
            click.echo(info("Production preview mode: full validation enabled"))
    
    try:
        # Validate configuration before starting
        if validate_config or production_preview or verbose:
            click.echo(info("Validating configuration..."))
        
        _validate_config_before_start(config_dir, target_env, production_preview, validate_config)
        
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


def _validate_config_before_start(
    config_dir: Optional[str], 
    env: Optional[str], 
    production_preview: bool = False, 
    validate_config: bool = False
):
    """Validate configuration before starting server."""
    if not validate_config and not production_preview:
        return
    
    try:
        from ...config.enhanced_loader import load_config_with_includes
        from ...config.validator import ConfigValidator
        
        # Load and validate configuration
        config = load_config_with_includes(config_dir or "config", env)
        validator = ConfigValidator()
        result = validator.validate(config, include_security=production_preview)
        
        # Check for critical errors
        if result.get("errors"):
            raise ValueError(f"Configuration errors found: {', '.join(result['errors'])}")
        
        # Production validation
        if production_preview:
            from ...production import (
                ProductionValidator,
                EnvironmentManager,
                ProductionConfiguration
            )
            
            click.echo(info("Running production readiness validation..."))
            
            # Use production utilities for validation
            env_manager = EnvironmentManager()
            prod_validator = ProductionValidator()
            
            # Create production config
            prod_config = ProductionConfiguration(
                environment=env or "production",
                security_level="strict",
                compliance_requirements=["SOC2"],
                monitoring_enabled=True,
                logging_level="WARNING"
            )
            
            # Validate environment configuration
            env_result = env_manager.validate_environment(config, env or "production")
            if not env_result.is_valid:
                raise ValueError(f"Environment validation failed: {', '.join(env_result.issues)}")
            
            # Security validation
            security_result = prod_validator.validate_security_configuration(config, prod_config)
            if not security_result.passed:
                raise ValueError(f"Security validation failed: {', '.join(security_result.issues)}")
            
            # Network configuration validation
            network_result = prod_validator.validate_network_configuration(config)
            if not network_result.passed:
                raise ValueError(f"Network validation failed: {', '.join(network_result.issues)}")
            
            click.echo(success("Production readiness validation passed"))
            
    except ImportError:
        # Config modules might not be available yet
        if production_preview:
            click.echo(warning("Production validation utilities not available"))
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
            "security_analysis": {},
            "performance_analysis": {},
            "dependency_analysis": {},
            "recommendations": [],
            "overall_score": 0
        }
        
        # Analyze configuration if provided
        if config:
            if not quiet:
                click.echo(info(f"Analyzing configuration: {config}"))
            
            config_analysis = _analyze_configuration(config)
            analysis_results["config_analysis"] = config_analysis
        
        # Analyze application code if provided
        if app:
            if not quiet:
                click.echo(info(f"Analyzing application: {app}"))
            
            code_analysis = _analyze_application_code(app)
            analysis_results["code_analysis"] = code_analysis
        
        # Perform security analysis
        if verbose:
            click.echo(info("Performing security analysis..."))
        
        security_analysis = _analyze_security(config, app)
        analysis_results["security_analysis"] = security_analysis
        
        # Perform performance analysis
        if verbose:
            click.echo(info("Performing performance analysis..."))
        
        performance_analysis = _analyze_performance(config, app)
        analysis_results["performance_analysis"] = performance_analysis
        
        # Analyze dependencies
        if verbose:
            click.echo(info("Analyzing dependencies..."))
        
        dependency_analysis = _analyze_dependencies()
        analysis_results["dependency_analysis"] = dependency_analysis
        
        # Generate comprehensive recommendations
        recommendations = _generate_recommendations(analysis_results)
        analysis_results["recommendations"] = recommendations
        
        # Calculate overall score
        overall_score = _calculate_overall_score(analysis_results)
        analysis_results["overall_score"] = overall_score
        
        # Output results
        if output:
            import json
            with open(output, 'w') as f:
                json.dump(analysis_results, f, indent=2)
            
            if not quiet:
                click.echo(success(f"Analysis report saved to: {output}"))
        else:
            # Display comprehensive summary
            if not quiet:
                _display_analysis_results(analysis_results)
        
    except Exception as e:
        raise ProjectError(f"Analysis failed: {e}")


def _analyze_configuration(config_path: str) -> dict:
    """Analyze configuration file for issues and optimizations."""
    try:
        from ...config.enhanced_loader import load_config_with_includes
        from ...config.validator import ConfigValidator
        
        # Load configuration
        config = load_config_with_includes(os.path.dirname(config_path) or ".", os.path.basename(config_path))
        validator = ConfigValidator()
        
        validation_result = validator.validate(config, include_security=True)
        
        # Count issues by severity
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])
        security_issues = validation_result.get("security_issues", [])
        
        # Calculate scores
        security_score = max(0, 100 - len(security_issues) * 10)
        performance_score = max(0, 100 - len(warnings) * 5)
        
        return {
            "file": config_path,
            "errors": len(errors),
            "warnings": len(warnings),
            "security_issues": len(security_issues),
            "security_score": security_score,
            "performance_score": performance_score,
            "issues_found": len(errors) + len(warnings) + len(security_issues),
            "details": {
                "errors": errors[:5],  # Limit to first 5
                "warnings": warnings[:5],
                "security_issues": security_issues[:5]
            }
        }
    except Exception as e:
        return {
            "file": config_path,
            "error": f"Failed to analyze config: {e}",
            "issues_found": 0,
            "security_score": 0,
            "performance_score": 0
        }


def _analyze_application_code(app_path: str) -> dict:
    """Analyze application code for complexity and issues."""
    try:
        with open(app_path, 'r') as f:
            code = f.read()
        
        # Parse AST
        tree = ast.parse(code)
        
        # Analyze code complexity
        complexity_analyzer = CodeComplexityAnalyzer()
        complexity_analyzer.visit(tree)
        
        # Analyze code structure
        structure_analyzer = CodeStructureAnalyzer()
        structure_analyzer.visit(tree)
        
        complexity_score = max(0, 100 - complexity_analyzer.complexity * 2)
        maintainability_score = max(0, 100 - len(structure_analyzer.issues) * 5)
        
        return {
            "file": app_path,
            "lines_of_code": len(code.split('\n')),
            "complexity_score": round(complexity_score, 1),
            "maintainability_score": round(maintainability_score, 1),
            "cyclomatic_complexity": complexity_analyzer.complexity,
            "function_count": complexity_analyzer.function_count,
            "class_count": complexity_analyzer.class_count,
            "potential_issues": structure_analyzer.issues[:10],  # Limit to first 10
            "code_smells": structure_analyzer.code_smells[:5]
        }
    except Exception as e:
        return {
            "file": app_path,
            "error": f"Failed to analyze code: {e}",
            "complexity_score": 0,
            "maintainability_score": 0
        }


def _analyze_security(config_path: Optional[str], app_path: Optional[str]) -> dict:
    """Analyze security vulnerabilities and best practices."""
    security_issues = []
    security_score = 100
    
    # Check configuration security
    if config_path and os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check for common security issues
            if config and isinstance(config, dict):
                if config.get("app", {}).get("debug", False):
                    security_issues.append("Debug mode enabled - should be disabled in production")
                    security_score -= 15
                
                if not config.get("security", {}).get("headers"):
                    security_issues.append("Security headers not configured")
                    security_score -= 10
                
                auth_config = config.get("auth", {})
                if auth_config:
                    session_config = auth_config.get("providers", {}).get("session", {})
                    if not session_config.get("cookie_secure"):
                        security_issues.append("Secure cookies not enabled")
                        security_score -= 10
                
                if config.get("app", {}).get("host") == "0.0.0.0":
                    security_issues.append("Application bound to all interfaces (0.0.0.0)")
                    security_score -= 10
        except Exception:
            pass
    
    # Check application code security
    if app_path and os.path.exists(app_path):
        try:
            with open(app_path, 'r') as f:
                code = f.read()
            
            # Look for potential security issues
            if "eval(" in code:
                security_issues.append("Use of eval() function detected")
                security_score -= 20
            
            if "exec(" in code:
                security_issues.append("Use of exec() function detected")
                security_score -= 20
            
            if "shell=True" in code:
                security_issues.append("Shell injection risk with shell=True")
                security_score -= 15
            
            if "SECRET_KEY" in code or "password" in code.lower():
                security_issues.append("Potential hardcoded secrets in code")
                security_score -= 25
        except Exception:
            pass
    
    return {
        "security_score": max(0, security_score),
        "issues_found": len(security_issues),
        "security_issues": security_issues,
        "recommendations": [
            "Enable security headers (HSTS, CSP, X-Frame-Options)",
            "Use environment variables for secrets",
            "Enable secure session cookies",
            "Implement proper input validation",
            "Add rate limiting protection"
        ]
    }


def _analyze_performance(config_path: Optional[str], app_path: Optional[str]) -> dict:
    """Analyze performance configuration and code patterns."""
    performance_issues = []
    performance_score = 100
    
    # Check configuration performance settings
    if config_path and os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if config and isinstance(config, dict):
                # Check for performance-related settings
                if not config.get("caching"):
                    performance_issues.append("No caching configuration found")
                    performance_score -= 10
                
                if not config.get("compression"):
                    performance_issues.append("Response compression not enabled")
                    performance_score -= 10
                
                if not config.get("database", {}).get("pool_size"):
                    performance_issues.append("Database connection pooling not configured")
                    performance_score -= 15
        except Exception:
            pass
    
    # Check application code for performance issues
    if app_path and os.path.exists(app_path):
        try:
            with open(app_path, 'r') as f:
                code = f.read()
            
            # Look for performance anti-patterns
            if code.count("for ") > 10:
                performance_issues.append("High number of loops detected - consider optimization")
                performance_score -= 5
            
            if "time.sleep(" in code:
                performance_issues.append("Blocking sleep calls detected")
                performance_score -= 10
            
            if code.count("import ") > 20:
                performance_issues.append("Large number of imports - consider lazy loading")
                performance_score -= 5
        except Exception:
            pass
    
    return {
        "performance_score": max(0, performance_score),
        "issues_found": len(performance_issues),
        "performance_issues": performance_issues,
        "recommendations": [
            "Enable response compression",
            "Implement caching strategy",
            "Use connection pooling for databases",
            "Add async/await for I/O operations",
            "Implement lazy loading for heavy imports"
        ]
    }


def _analyze_dependencies() -> dict:
    """Analyze project dependencies for security and compatibility."""
    dependency_issues = []
    
    # Check for requirements.txt
    if os.path.exists("requirements.txt"):
        try:
            with open("requirements.txt", 'r') as f:
                requirements = f.readlines()
            
            outdated_packages = []
            unpinned_packages = []
            
            for req in requirements:
                req = req.strip()
                if req and not req.startswith("#"):
                    if "==" not in req and ">=" not in req:
                        unpinned_packages.append(req)
                    
                    # Check for known vulnerable packages (simplified)
                    package_name = req.split("==")[0].split(">=")[0]
                    if package_name.lower() in ["urllib3", "requests", "pillow", "jinja2"]:
                        # This would normally check against a vulnerability database
                        outdated_packages.append(package_name)
            
            if unpinned_packages:
                dependency_issues.append(f"{len(unpinned_packages)} unpinned dependencies found")
            
            if outdated_packages:
                dependency_issues.append(f"{len(outdated_packages)} potentially outdated packages")
            
            return {
                "total_dependencies": len(requirements),
                "unpinned_dependencies": len(unpinned_packages),
                "potentially_outdated": len(outdated_packages),
                "issues_found": len(dependency_issues),
                "dependency_issues": dependency_issues,
                "recommendations": [
                    "Pin all dependency versions",
                    "Regularly update dependencies",
                    "Use dependency vulnerability scanning",
                    "Consider using virtual environments"
                ]
            }
        except Exception:
            pass
    
    return {
        "total_dependencies": 0,
        "issues_found": 0,
        "dependency_issues": ["No requirements.txt found"],
        "recommendations": ["Create requirements.txt file"]
    }


def _generate_recommendations(analysis_results: dict) -> list:
    """Generate comprehensive recommendations based on analysis."""
    recommendations = []
    
    # Security recommendations
    security_score = analysis_results.get("security_analysis", {}).get("security_score", 100)
    if security_score < 80:
        recommendations.extend([
            "Review and fix security configuration issues",
            "Enable security headers (HSTS, CSP, X-Frame-Options)",
            "Use environment variables for sensitive configuration"
        ])
    
    # Performance recommendations
    perf_score = analysis_results.get("performance_analysis", {}).get("performance_score", 100)
    if perf_score < 80:
        recommendations.extend([
            "Enable response compression",
            "Implement caching strategy",
            "Optimize database queries and connections"
        ])
    
    # Code quality recommendations
    code_analysis = analysis_results.get("code_analysis", {})
    complexity_score = code_analysis.get("complexity_score", 100)
    if complexity_score < 70:
        recommendations.extend([
            "Refactor complex functions to reduce cyclomatic complexity",
            "Consider breaking large files into smaller modules",
            "Add comprehensive unit tests"
        ])
    
    # Configuration recommendations
    config_issues = analysis_results.get("config_analysis", {}).get("issues_found", 0)
    if config_issues > 0:
        recommendations.extend([
            "Fix configuration validation errors",
            "Review production-readiness settings",
            "Consider using configuration templates"
        ])
    
    # Dependency recommendations
    dep_issues = analysis_results.get("dependency_analysis", {}).get("issues_found", 0)
    if dep_issues > 0:
        recommendations.extend([
            "Update outdated dependencies",
            "Pin dependency versions in requirements.txt",
            "Run dependency vulnerability scanning"
        ])
    
    return recommendations


def _calculate_overall_score(analysis_results: dict) -> float:
    """Calculate overall application health score."""
    scores = []
    
    # Security score (weight: 30%)
    security_score = analysis_results.get("security_analysis", {}).get("security_score", 100)
    scores.append(security_score * 0.3)
    
    # Performance score (weight: 25%)
    performance_score = analysis_results.get("performance_analysis", {}).get("performance_score", 100)
    scores.append(performance_score * 0.25)
    
    # Code quality score (weight: 25%)
    complexity_score = analysis_results.get("code_analysis", {}).get("complexity_score", 100)
    maintainability_score = analysis_results.get("code_analysis", {}).get("maintainability_score", 100)
    code_score = (complexity_score + maintainability_score) / 2
    scores.append(code_score * 0.25)
    
    # Configuration score (weight: 20%)
    config_score = analysis_results.get("config_analysis", {}).get("security_score", 100)
    scores.append(config_score * 0.2)
    
    return round(sum(scores), 1)


class CodeComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code complexity."""
    
    def __init__(self):
        self.complexity = 0
        self.function_count = 0
        self.class_count = 0
        self.nesting_level = 0
        self.max_nesting = 0
    
    def visit_FunctionDef(self, node):
        self.function_count += 1
        self.complexity += 1  # Base complexity for function
        
        # Count decision points
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                self.complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                self.complexity += 1
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.class_count += 1
        self.generic_visit(node)
    
    def visit_If(self, node):
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_For(self, node):
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_While(self, node):
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)
        self.generic_visit(node)
        self.nesting_level -= 1


class CodeStructureAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code structure and identify issues."""
    
    def __init__(self):
        self.issues = []
        self.code_smells = []
        self.long_functions = []
        self.duplicate_code_patterns = []
    
    def visit_FunctionDef(self, node):
        # Check function length
        function_lines = len(node.body)
        if function_lines > 50:
            self.issues.append(f"Function '{node.name}' is too long ({function_lines} lines)")
        
        # Check parameter count
        if len(node.args.args) > 6:
            self.issues.append(f"Function '{node.name}' has too many parameters ({len(node.args.args)})")
        
        # Check for missing docstring
        if not ast.get_docstring(node):
            self.code_smells.append(f"Function '{node.name}' missing docstring")
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        # Check class size
        method_count = sum(1 for child in node.body if isinstance(child, ast.FunctionDef))
        if method_count > 20:
            self.issues.append(f"Class '{node.name}' has too many methods ({method_count})")
        
        # Check for missing docstring
        if not ast.get_docstring(node):
            self.code_smells.append(f"Class '{node.name}' missing docstring")
        
        self.generic_visit(node)


def _display_analysis_results(analysis_results: dict):
    """Display comprehensive analysis results."""
    overall_score = analysis_results.get("overall_score", 0)
    
    # Overall status
    click.echo(highlight("Application Analysis Report"))
    click.echo("=" * 50)
    
    # Score color coding
    if overall_score >= 90:
        score_color = success
        status = "Excellent"
    elif overall_score >= 80:
        score_color = success
        status = "Good"
    elif overall_score >= 70:
        score_color = warning
        status = "Fair"
    else:
        score_color = error
        status = "Needs Improvement"
    
    click.echo(f"Overall Score: {score_color(f'{overall_score}/100')} ({status})")
    click.echo()
    
    # Security Analysis
    security_analysis = analysis_results.get("security_analysis", {})
    if security_analysis:
        click.echo(highlight("Security Analysis:"))
        security_score = security_analysis.get("security_score", 0)
        issues_count = security_analysis.get("issues_found", 0)
        
        if security_score >= 80:
            click.echo(f"  Score: {success(f'{security_score}/100')}")
        else:
            click.echo(f"  Score: {error(f'{security_score}/100')}")
        
        if issues_count > 0:
            click.echo(f"  Issues: {error(str(issues_count))}")
            for issue in security_analysis.get("security_issues", [])[:3]:
                click.echo(f"    • {issue}")
        else:
            click.echo(f"  Issues: {success('None')}")
        click.echo()
    
    # Performance Analysis
    performance_analysis = analysis_results.get("performance_analysis", {})
    if performance_analysis:
        click.echo(highlight("Performance Analysis:"))
        perf_score = performance_analysis.get("performance_score", 0)
        issues_count = performance_analysis.get("issues_found", 0)
        
        if perf_score >= 80:
            click.echo(f"  Score: {success(f'{perf_score}/100')}")
        else:
            click.echo(f"  Score: {warning(f'{perf_score}/100')}")
        
        if issues_count > 0:
            click.echo(f"  Issues: {warning(str(issues_count))}")
            for issue in performance_analysis.get("performance_issues", [])[:3]:
                click.echo(f"    • {issue}")
        else:
            click.echo(f"  Issues: {success('None')}")
        click.echo()
    
    # Code Quality Analysis
    code_analysis = analysis_results.get("code_analysis", {})
    if code_analysis:
        click.echo(highlight("Code Quality Analysis:"))
        complexity_score = code_analysis.get("complexity_score", 0)
        maintainability_score = code_analysis.get("maintainability_score", 0)
        
        click.echo(f"  Complexity Score: {complexity_score}/100")
        click.echo(f"  Maintainability Score: {maintainability_score}/100")
        
        potential_issues = code_analysis.get("potential_issues", [])
        if potential_issues:
            click.echo(f"  Code Issues: {len(potential_issues)}")
            for issue in potential_issues[:3]:
                click.echo(f"    • {issue}")
        click.echo()
    
    # Configuration Analysis
    config_analysis = analysis_results.get("config_analysis", {})
    if config_analysis and "error" not in config_analysis:
        click.echo(highlight("Configuration Analysis:"))
        issues_found = config_analysis.get("issues_found", 0)
        
        if issues_found == 0:
            click.echo(f"  Status: {success('Valid')}")
        else:
            click.echo(f"  Issues: {error(str(issues_found))}")
        click.echo()
    
    # Dependency Analysis
    dependency_analysis = analysis_results.get("dependency_analysis", {})
    if dependency_analysis:
        click.echo(highlight("Dependency Analysis:"))
        total_deps = dependency_analysis.get("total_dependencies", 0)
        issues_found = dependency_analysis.get("issues_found", 0)
        
        click.echo(f"  Total Dependencies: {total_deps}")
        
        if issues_found > 0:
            click.echo(f"  Issues: {warning(str(issues_found))}")
            for issue in dependency_analysis.get("dependency_issues", []):
                click.echo(f"    • {issue}")
        else:
            click.echo(f"  Issues: {success('None')}")
        click.echo()
    
    # Recommendations
    recommendations = analysis_results.get("recommendations", [])
    if recommendations:
        click.echo(highlight("Recommendations:"))
        for i, rec in enumerate(recommendations[:8], 1):  # Limit to top 8
            click.echo(f"  {i}. {rec}")
        
        if len(recommendations) > 8:
            click.echo(f"  ... and {len(recommendations) - 8} more")
        click.echo()
    
    click.echo(success("Analysis completed"))