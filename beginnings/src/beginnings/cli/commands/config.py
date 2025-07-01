"""Configuration management commands."""

import click
import os
import yaml
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from ..utils.colors import success, error, info, warning, highlight
from ..utils.errors import ConfigurationError
from ..templates.security import validate_security_settings


@click.group(name="config")
def config_group():
    """Configuration management commands."""
    pass


@config_group.command(name="validate")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file to validate"
)
@click.option(
    "--security-audit",
    is_flag=True,
    help="Perform security audit during validation"
)
@click.pass_context
def validate_command(ctx: click.Context, config: Optional[str], security_audit: bool):
    """Validate configuration file against schema and security best practices."""
    if not config:
        config = _find_config_file()
    
    try:
        click.echo(info(f"Validating configuration: {highlight(config)}"))
        
        # Load configuration
        merged_config = _load_config(config)
        
        validation_errors = []
        security_issues = []
        
        # Basic structure validation
        basic_errors = _validate_basic_structure(merged_config)
        validation_errors.extend(basic_errors)
        
        # Security validation
        if security_audit:
            security_issues = validate_security_settings(merged_config)
        
        # Report results
        if validation_errors:
            click.echo(error("✗ Configuration validation failed"))
            for err in validation_errors:
                click.echo(f"  • {err}")
            
        if security_issues:
            _report_security_issues(security_issues)
        
        if not validation_errors and not security_issues:
            click.echo(success("✓ Configuration is valid"))
            if security_audit:
                click.echo(success("✓ No security issues detected"))
            return
        
        # Exit with error if issues found
        ctx.exit(1)
        
    except Exception as e:
        raise ConfigurationError(f"Validation failed: {e}")


@config_group.command(name="show")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file to show"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["yaml", "json", "pretty"]),
    default="pretty",
    help="Output format"
)
@click.option(
    "--mask-secrets",
    is_flag=True,
    default=True,
    help="Mask sensitive values in output"
)
@click.pass_context
def show_command(ctx: click.Context, config: Optional[str], format: str, mask_secrets: bool):
    """Show merged configuration with all includes resolved."""
    if not config:
        config = _find_config_file()
    
    try:
        # Only show info message for pretty format
        if format == "pretty":
            click.echo(info(f"Configuration from: {highlight(config)}"))
        
        # Load configuration
        merged_config = _load_config(config)
        
        # Mask secrets
        if mask_secrets:
            merged_config = _mask_secrets(merged_config)
        
        # Output in requested format
        if format == "json":
            click.echo(json.dumps(merged_config, indent=2))
        elif format == "yaml":
            click.echo(yaml.dump(merged_config, default_flow_style=False))
        else:  # pretty
            _print_pretty_config(merged_config)
            
    except Exception as e:
        raise ConfigurationError(f"Failed to show configuration: {e}")


@config_group.command(name="audit")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file to audit"
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning", "info"]),
    help="Minimum severity level to report"
)
@click.option(
    "--compliance",
    type=click.Choice(["owasp", "nist", "pci"]),
    help="Check compliance against security standard"
)
@click.pass_context
def audit_command(ctx: click.Context, config: Optional[str], severity: Optional[str], compliance: Optional[str]):
    """Perform comprehensive security audit of configuration."""
    if not config:
        config = _find_config_file()
    
    try:
        click.echo(info(f"Auditing configuration: {highlight(config)}"))
        
        # Load configuration
        merged_config = _load_config(config)
        
        # Perform security audit
        security_issues = validate_security_settings(merged_config)
        
        # Filter by severity
        if severity:
            severity_levels = {"error": 0, "warning": 1, "info": 2}
            min_level = severity_levels[severity]
            security_issues = [
                issue for issue in security_issues 
                if severity_levels.get(issue[0], 0) <= min_level
            ]
        
        # Check compliance
        compliance_issues = []
        if compliance:
            compliance_issues = _check_compliance(merged_config, compliance)
        
        # Output results
        click.echo(f"\n{highlight('Security Audit Results')}")
        click.echo("=" * 50)
        
        if security_issues or compliance_issues:
            total_issues = len(security_issues) + len(compliance_issues)
            click.echo(error(f"✗ {total_issues} issues found"))
            
            # Show issues by severity
            for level in ["error", "warning", "info"]:
                level_issues = [issue for issue in security_issues if issue[0] == level]
                if level_issues:
                    click.echo(f"\n{_get_severity_icon(level)} {level.upper()} ({len(level_issues)} issues):")
                    for _, setting, message in level_issues:
                        click.echo(f"  • {setting}: {message}")
            
            if compliance_issues:
                click.echo(f"\n{error('COMPLIANCE VIOLATIONS')} ({len(compliance_issues)} issues):")
                for issue in compliance_issues:
                    click.echo(f"  • {issue}")
            
            ctx.exit(1)
        else:
            click.echo(success("✓ No security issues detected"))
            if compliance:
                click.echo(success(f"✓ {compliance.upper()} compliance verified"))
            
    except Exception as e:
        raise ConfigurationError(f"Audit failed: {e}")


@config_group.command(name="fix")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file to fix"
)
@click.option(
    "--type",
    type=click.Choice(["security", "performance", "all"]),
    default="all",
    help="Type of issues to fix"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be fixed without making changes"
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before making changes"
)
@click.pass_context
def fix_command(ctx: click.Context, config: Optional[str], type: str, dry_run: bool, backup: bool):
    """Auto-fix common configuration issues."""
    if not config:
        config = _find_config_file()
    
    try:
        click.echo(info(f"Analyzing configuration: {highlight(config)}"))
        
        # Load configuration
        with open(config) as f:
            original_config = yaml.safe_load(f)
        
        # Identify fixable issues
        fixes = _identify_fixes(original_config, type)
        
        if not fixes:
            click.echo(success("✓ No fixable issues found"))
            return
        
        # Show what will be fixed
        click.echo(f"\n{highlight('Identified Issues')}:")
        for fix in fixes:
            status = "Would fix" if dry_run else "Will fix"
            click.echo(f"  • {status}: {fix['description']}")
        
        if dry_run:
            click.echo(info("\nDry run mode - no changes made"))
            return
        
        # Confirm changes
        if not click.confirm(f"\nApply {len(fixes)} fixes?"):
            click.echo("Cancelled")
            return
        
        # Create backup
        if backup:
            backup_path = f"{config}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(config, backup_path)
            click.echo(info(f"Backup created: {highlight(backup_path)}"))
        
        # Apply fixes
        fixed_config = _apply_fixes(original_config, fixes)
        
        # Write updated configuration
        with open(config, "w") as f:
            yaml.dump(fixed_config, f, default_flow_style=False, sort_keys=False)
        
        click.echo(success(f"✓ Fixed {len(fixes)} issues"))
        click.echo(info("Run 'beginnings config validate' to verify changes"))
        
    except Exception as e:
        raise ConfigurationError(f"Fix failed: {e}")


@config_group.command(name="generate")
@click.option(
    "--template",
    type=click.Choice(["development", "staging", "production", "minimal"]),
    help="Configuration template to use"
)
@click.option(
    "--environment", "-e",
    type=click.Choice(["development", "staging", "production"]),
    help="Target environment"
)
@click.option(
    "--features",
    help="Comma-separated list of features to include"
)
@click.option(
    "--output", "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    help="Output file path"
)
@click.pass_context
def generate_command(ctx: click.Context, template: Optional[str], environment: Optional[str], 
                    features: Optional[str], output: str):
    """Generate configuration file from template."""
    try:
        click.echo(info(f"Generating configuration: {highlight(output)}"))
        
        # Parse features
        feature_list = []
        if features:
            feature_list = [f.strip() for f in features.split(",")]
        
        # Determine template
        if not template and environment:
            template = environment
        elif not template:
            template = "development"
        
        # Generate configuration
        config = _generate_config_from_template(template, feature_list, environment)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
        
        # Write configuration
        with open(output, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        click.echo(success(f"✓ Configuration generated: {highlight(output)}"))
        
        # Show summary
        click.echo(f"\n{highlight('Configuration Summary')}:")
        click.echo(f"  Template: {template}")
        if environment:
            click.echo(f"  Environment: {environment}")
        if feature_list:
            click.echo(f"  Features: {', '.join(feature_list)}")
        
    except Exception as e:
        raise ConfigurationError(f"Generation failed: {e}")


@config_group.command(name="diff")
@click.argument("config1", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument("config2", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option(
    "--format",
    type=click.Choice(["unified", "context", "side-by-side"]),
    default="unified",
    help="Diff output format"
)
@click.pass_context
def diff_command(ctx: click.Context, config1: str, config2: str, format: str):
    """Compare two configuration files."""
    try:
        # Load both configurations
        config1_data = _load_config(config1)
        config2_data = _load_config(config2)
        
        # Generate diff
        diff_result = _generate_config_diff(config1_data, config2_data, config1, config2, format)
        
        if diff_result:
            click.echo(diff_result)
        else:
            click.echo(success("✓ Configurations are identical"))
            
    except Exception as e:
        raise ConfigurationError(f"Diff failed: {e}")


# Helper functions

def _load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration with support for includes."""
    if os.path.isfile(config_path):
        # Load the file first
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        
        # Check if it has includes
        if isinstance(config_data, dict) and "include" in config_data:
            # Simple include processing for single files
            config_dir = os.path.dirname(config_path)
            if not config_dir:
                config_dir = "."
            
            # Load included files manually
            base_config = {}
            for include_file in config_data.get("include", []):
                include_path = os.path.join(config_dir, include_file)
                if os.path.exists(include_path):
                    with open(include_path) as f:
                        included_data = yaml.safe_load(f)
                        if isinstance(included_data, dict):
                            _deep_update(base_config, included_data)
            
            # Apply current file's config on top
            current_config = {k: v for k, v in config_data.items() if k != "include"}
            _deep_update(base_config, current_config)
            return base_config
        else:
            return config_data
    else:
        # Directory - use enhanced loader
        from ...config.enhanced_loader import load_config_with_includes
        return load_config_with_includes(config_path)


def _deep_update(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
    """Deep update one dictionary with another."""
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            _deep_update(base_dict[key], value)
        else:
            base_dict[key] = value


def _find_config_file() -> str:
    """Find configuration file in standard locations."""
    candidates = [
        "config/app.yaml",
        "config/app.yml", 
        "app.yaml",
        "app.yml",
        "beginnings.yaml",
        "beginnings.yml"
    ]
    
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    
    raise ConfigurationError(
        "No configuration file found. Use --config to specify location."
    )


def _validate_basic_structure(config: Dict[str, Any]) -> List[str]:
    """Validate basic configuration structure."""
    errors = []
    
    # Check required top-level sections
    if "app" not in config:
        errors.append("Missing required 'app' section")
    elif not isinstance(config["app"], dict):
        errors.append("'app' section must be a dictionary")
    else:
        app = config["app"]
        if "name" not in app:
            errors.append("Missing required 'app.name' field")
    
    # Validate extensions format
    if "extensions" in config:
        extensions = config["extensions"]
        if not isinstance(extensions, list):
            errors.append("'extensions' must be a list")
        else:
            for i, ext in enumerate(extensions):
                if not isinstance(ext, str):
                    errors.append(f"Extension {i} must be a string")
    
    return errors


def _report_security_issues(issues: List[Tuple[str, str, str]]):
    """Report security issues in formatted output."""
    if not issues:
        return
    
    click.echo(warning("⚠ Security issues detected:"))
    
    # Group by severity
    by_severity = {"error": [], "warning": [], "info": []}
    for level, setting, message in issues:
        by_severity[level].append((setting, message))
    
    for level, level_issues in by_severity.items():
        if level_issues:
            icon = _get_severity_icon(level)
            click.echo(f"\n{icon} {level.upper()} ({len(level_issues)} issues):")
            for setting, message in level_issues:
                click.echo(f"  • {setting}: {message}")


def _get_severity_icon(level: str) -> str:
    """Get colored icon for severity level."""
    icons = {
        "error": error("✗"),
        "warning": warning("⚠"),
        "info": info("ℹ")
    }
    return icons.get(level, "•")


def _mask_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive values in configuration."""
    import copy
    
    masked_config = copy.deepcopy(config)
    secret_keys = [
        "secret", "password", "token", "key", "credential", 
        "api_key", "private_key", "cert", "certificate"
    ]
    
    def mask_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if any(secret in key.lower() for secret in secret_keys):
                    if isinstance(value, str) and len(value) > 4:
                        obj[key] = f"{value[:4]}{'*' * (len(value) - 4)}"
                    else:
                        obj[key] = "[MASKED]"
                else:
                    mask_recursive(value, current_path)
        elif isinstance(obj, list):
            for item in obj:
                mask_recursive(item, path)
    
    mask_recursive(masked_config)
    return masked_config


def _print_pretty_config(config: Dict[str, Any], indent: int = 0):
    """Print configuration in pretty format."""
    for key, value in config.items():
        if isinstance(value, dict):
            click.echo("  " * indent + highlight(f"{key}:"))
            _print_pretty_config(value, indent + 1)
        elif isinstance(value, list):
            click.echo("  " * indent + highlight(f"{key}:"))
            for item in value:
                if isinstance(item, dict):
                    _print_pretty_config(item, indent + 1)
                else:
                    click.echo("  " * (indent + 1) + f"- {item}")
        else:
            click.echo("  " * indent + f"{highlight(key)}: {value}")


def _check_compliance(config: Dict[str, Any], standard: str) -> List[str]:
    """Check configuration against compliance standards."""
    issues = []
    
    if standard == "owasp":
        # OWASP security checks
        if config.get("app", {}).get("debug", False):
            issues.append("OWASP: Debug mode should be disabled in production")
        
        auth_config = config.get("auth", {})
        if auth_config:
            session_config = auth_config.get("providers", {}).get("session", {})
            if not session_config.get("cookie_secure", False):
                issues.append("OWASP: Secure cookies required for session management")
            if not session_config.get("cookie_httponly", False):
                issues.append("OWASP: HttpOnly cookies required to prevent XSS")
    
    elif standard == "nist":
        # NIST Cybersecurity Framework checks
        if not config.get("security", {}).get("headers"):
            issues.append("NIST: Security headers not configured")
        
        if not config.get("rate_limiting"):
            issues.append("NIST: Rate limiting not configured for DoS protection")
    
    elif standard == "pci":
        # PCI DSS checks (basic)
        if config.get("app", {}).get("host") == "0.0.0.0":
            issues.append("PCI: Application should not bind to all interfaces")
        
        if not config.get("security", {}).get("headers", {}).get("strict_transport_security"):
            issues.append("PCI: HTTPS enforcement (HSTS) required")
    
    return issues


def _identify_fixes(config: Dict[str, Any], fix_type: str) -> List[Dict[str, Any]]:
    """Identify issues that can be automatically fixed."""
    fixes = []
    
    if fix_type in ["security", "all"]:
        # Check for weak secrets
        auth_config = config.get("auth", {})
        if auth_config:
            session_config = auth_config.get("providers", {}).get("session", {})
            secret = session_config.get("secret_key", "")
            if isinstance(secret, str) and len(secret) < 32:
                fixes.append({
                    "type": "security",
                    "path": "auth.providers.session.secret_key",
                    "description": "Generate strong session secret (32+ characters)",
                    "action": "generate_secret"
                })
            
            if not session_config.get("cookie_secure", True):
                fixes.append({
                    "type": "security",
                    "path": "auth.providers.session.cookie_secure",
                    "description": "Enable secure cookies",
                    "action": "set_boolean",
                    "value": True
                })
        
        # Check debug mode
        if config.get("app", {}).get("debug", False):
            fixes.append({
                "type": "security", 
                "path": "app.debug",
                "description": "Disable debug mode for production",
                "action": "set_boolean",
                "value": False
            })
        
        # Check host binding
        if config.get("app", {}).get("host") == "0.0.0.0":
            fixes.append({
                "type": "security",
                "path": "app.host",
                "description": "Change host binding from 0.0.0.0 to 127.0.0.1",
                "action": "set_value",
                "value": "127.0.0.1"
            })
    
    return fixes


def _apply_fixes(config: Dict[str, Any], fixes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply fixes to configuration."""
    import copy
    
    fixed_config = copy.deepcopy(config)
    
    for fix in fixes:
        path_parts = fix["path"].split(".")
        current = fixed_config
        
        # Navigate to parent
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Apply fix
        key = path_parts[-1]
        if fix["action"] == "generate_secret":
            from src.beginnings.cli.templates.security import generate_secure_secret
            current[key] = generate_secure_secret(32)
        elif fix["action"] in ["set_boolean", "set_value"]:
            current[key] = fix["value"]
    
    return fixed_config


def _generate_config_from_template(template: str, features: List[str], environment: Optional[str]) -> Dict[str, Any]:
    """Generate configuration from template."""
    # Base configuration
    config = {
        "app": {
            "name": "beginnings-app",
            "debug": template == "development",
            "host": "127.0.0.1",
            "port": 8000
        }
    }
    
    # Add features
    if "auth" in features:
        config["extensions"] = config.get("extensions", [])
        config["extensions"].append("beginnings.extensions.auth:AuthExtension")
        config["auth"] = {
            "providers": {
                "session": {
                    "secret_key": "${SESSION_SECRET}",
                    "cookie_secure": template != "development",
                    "cookie_httponly": True,
                    "cookie_samesite": "strict"
                }
            }
        }
    
    if "csrf" in features:
        config["extensions"] = config.get("extensions", [])
        config["extensions"].append("beginnings.extensions.csrf:CSRFExtension")
        config["csrf"] = {
            "enabled": True,
            "secure_cookie": template != "development"
        }
    
    if "rate-limiting" in features:
        config["extensions"] = config.get("extensions", [])
        config["extensions"].append("beginnings.extensions.rate_limiting:RateLimitExtension")
        config["rate_limiting"] = {
            "global": {
                "requests": 1000 if template == "development" else 500,
                "window_seconds": 3600
            }
        }
    
    # Environment-specific settings
    if template == "production":
        config["app"]["debug"] = False
        if "security" not in config:
            config["security"] = {
                "headers": {
                    "x_frame_options": "DENY",
                    "x_content_type_options": "nosniff",
                    "strict_transport_security": {
                        "max_age": 31536000,
                        "include_subdomains": True
                    }
                }
            }
    
    return config


def _generate_config_diff(config1: Dict[str, Any], config2: Dict[str, Any], 
                         path1: str, path2: str, format: str) -> str:
    """Generate diff between two configurations."""
    import difflib
    
    # Convert to strings for diffing
    yaml1 = yaml.dump(config1, default_flow_style=False, sort_keys=True)
    yaml2 = yaml.dump(config2, default_flow_style=False, sort_keys=True)
    
    lines1 = yaml1.splitlines(keepends=True)
    lines2 = yaml2.splitlines(keepends=True)
    
    if format == "unified":
        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=path1,
            tofile=path2,
            lineterm=""
        )
    elif format == "context":
        diff = difflib.context_diff(
            lines1, lines2,
            fromfile=path1,
            tofile=path2,
            lineterm=""
        )
    else:  # side-by-side
        diff = difflib.side_by_side_diff(lines1, lines2)
    
    return "".join(diff)