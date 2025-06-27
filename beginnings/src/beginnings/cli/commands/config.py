"""Configuration management commands."""

import click
from typing import Optional

from ..utils.colors import success, error, info, highlight
from ..utils.errors import ConfigurationError, validate_configuration_file


@click.group(name="config")
def config_group():
    """Configuration management commands.
    
    Validate, display, and analyze beginnings configuration files.
    """
    pass


@config_group.command(name="validate")
@click.option(
    "--env",
    type=str,
    help="Environment to validate (overrides global --env)"
)
@click.option(
    "--include-security",
    is_flag=True,
    help="Include security audit in validation"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format"
)
@click.option(
    "--fix-warnings",
    is_flag=True,
    help="Auto-fix non-critical issues"
)
@click.pass_context
def validate_command(
    ctx: click.Context,
    env: Optional[str],
    include_security: bool,
    output_format: str,
    fix_warnings: bool
):
    """Validate configuration files for the current environment.
    
    Performs comprehensive validation including:
    - YAML syntax and structure
    - Schema validation
    - Include directive validation
    - Extension configuration validation
    - Optional security audit
    """
    # Use environment from command option or global context
    target_env = env or ctx.obj.get("env")
    config_dir = ctx.obj.get("config_dir")
    verbose = ctx.obj.get("verbose", False)
    
    click.echo(info(f"Validating configuration for environment: {target_env or 'production'}"))
    
    try:
        # Import here to avoid circular imports
        from ...config.enhanced_loader import load_config_with_includes
        from ...config.validator import ConfigValidator
        
        # Load configuration
        if verbose:
            click.echo(info("Loading configuration..."))
        
        config = load_config_with_includes(config_dir or "config", target_env)
        
        # Validate configuration
        validator = ConfigValidator()
        validation_result = validator.validate(config, include_security=include_security)
        
        if output_format == "json":
            import json
            click.echo(json.dumps(validation_result, indent=2))
        else:
            _display_validation_result(validation_result, verbose)
        
        # Auto-fix warnings if requested
        if fix_warnings and validation_result.get("warnings"):
            _auto_fix_warnings(validation_result["warnings"], config_dir, target_env)
        
        # Exit with error code if validation failed
        if validation_result.get("errors"):
            raise click.Abort()
            
    except Exception as e:
        raise ConfigurationError(
            f"Configuration validation failed: {e}",
            suggestions=[
                "Check YAML syntax is valid",
                "Verify all included files exist",
                "Ensure configuration schema is correct"
            ]
        )


@config_group.command(name="show")
@click.option(
    "--env",
    type=str,
    help="Environment to show (overrides global --env)"
)
@click.option(
    "--section",
    type=str,
    help="Show specific configuration section"
)
@click.option(
    "--resolved",
    is_flag=True,
    help="Show with environment variables resolved"
)
@click.option(
    "--source",
    is_flag=True,
    help="Show source file for each setting"
)
@click.pass_context
def show_command(
    ctx: click.Context,
    env: Optional[str],
    section: Optional[str],
    resolved: bool,
    source: bool
):
    """Display merged configuration for specified environment.
    
    Shows the final configuration after merging all includes
    and applying environment-specific overrides.
    """
    target_env = env or ctx.obj.get("env")
    config_dir = ctx.obj.get("config_dir")
    
    click.echo(info(f"Configuration for environment: {target_env or 'production'}"))
    
    try:
        from ...config.enhanced_loader import load_config_with_includes
        
        config = load_config_with_includes(config_dir or "config", target_env)
        
        if section:
            config = config.get(section, {})
            if not config:
                click.echo(error(f"Section '{section}' not found in configuration"))
                raise click.Abort()
        
        # Display configuration
        import yaml
        click.echo("\n" + highlight("Configuration:"))
        click.echo(yaml.dump(config, default_flow_style=False, indent=2))
        
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")


@config_group.command(name="diff")
@click.argument("env1", type=str)
@click.argument("env2", type=str)
@click.option(
    "--section",
    type=str,
    help="Compare specific configuration section"
)
@click.option(
    "--changes-only",
    is_flag=True,
    help="Show only differences"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["unified", "side-by-side"]),
    default="unified",
    help="Diff format"
)
@click.pass_context
def diff_command(
    ctx: click.Context,
    env1: str,
    env2: str,
    section: Optional[str],
    changes_only: bool,
    output_format: str
):
    """Compare configuration between two environments.
    
    Shows differences in configuration between specified environments.
    """
    config_dir = ctx.obj.get("config_dir")
    
    click.echo(info(f"Comparing configuration: {env1} vs {env2}"))
    
    try:
        from ...config.enhanced_loader import load_config_with_includes
        
        config1 = load_config_with_includes(config_dir or "config", env1)
        config2 = load_config_with_includes(config_dir or "config", env2)
        
        if section:
            config1 = config1.get(section, {})
            config2 = config2.get(section, {})
        
        # Perform diff
        _show_config_diff(config1, config2, env1, env2, output_format, changes_only)
        
    except Exception as e:
        raise ConfigurationError(f"Failed to compare configurations: {e}")


def _display_validation_result(result: dict, verbose: bool):
    """Display validation results in human-readable format."""
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    info_items = result.get("info", [])
    
    if not errors and not warnings:
        click.echo(success("Configuration validation passed"))
        return
    
    if errors:
        click.echo(error(f"Found {len(errors)} error(s):"))
        for error_item in errors:
            click.echo(f"  ✗ {error_item}")
    
    if warnings:
        click.echo(f"\n" + highlight(f"Found {len(warnings)} warning(s):"))
        for warning in warnings:
            click.echo(f"  ⚠ {warning}")
    
    if verbose and info_items:
        click.echo(f"\n" + info("Additional information:"))
        for info_item in info_items:
            click.echo(f"  ℹ {info_item}")


def _auto_fix_warnings(warnings: list, config_dir: Optional[str], env: Optional[str]):
    """Auto-fix configuration warnings where possible."""
    click.echo(info("Auto-fixing warnings..."))
    
    # This would contain logic to automatically fix common configuration issues
    # For now, just show what would be fixed
    for warning in warnings:
        if "deprecated" in warning.lower():
            click.echo(f"  • Would fix deprecated setting: {warning}")
        elif "missing" in warning.lower():
            click.echo(f"  • Would add missing setting: {warning}")


def _show_config_diff(config1: dict, config2: dict, env1: str, env2: str, format_type: str, changes_only: bool):
    """Show configuration differences."""
    import yaml
    
    # Convert to YAML strings for comparison
    yaml1 = yaml.dump(config1, default_flow_style=False, indent=2)
    yaml2 = yaml.dump(config2, default_flow_style=False, indent=2)
    
    # Simple line-by-line comparison
    lines1 = yaml1.splitlines()
    lines2 = yaml2.splitlines()
    
    if lines1 == lines2:
        click.echo(success("Configurations are identical"))
        return
    
    # Show unified diff
    import difflib
    
    diff_lines = list(difflib.unified_diff(
        lines1,
        lines2,
        fromfile=f"{env1}",
        tofile=f"{env2}",
        lineterm=""
    ))
    
    if changes_only:
        diff_lines = [line for line in diff_lines if line.startswith(('+', '-', '@@'))]
    
    for line in diff_lines:
        if line.startswith('+'):
            click.echo(click.style(line, fg='green'))
        elif line.startswith('-'):
            click.echo(click.style(line, fg='red'))
        elif line.startswith('@@'):
            click.echo(click.style(line, fg='cyan'))
        else:
            click.echo(line)