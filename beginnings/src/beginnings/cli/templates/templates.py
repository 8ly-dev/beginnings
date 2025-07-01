"""Template configurations for different project types."""

import click
from typing import Dict, Any


AVAILABLE_TEMPLATES = {
    "minimal": {
        "name": "Minimal",
        "description": "Core framework only, no extensions",
        "features": {
            "include_html": True,
            "include_api": False,
            "include_auth": False,
            "include_csrf": False,
            "include_rate_limiting": False,
            "include_security_headers": False,
            "include_staging_config": False,
        }
    },
    "standard": {
        "name": "Standard",
        "description": "Common extensions (auth, CSRF, security headers)",
        "features": {
            "include_html": True,
            "include_api": True,
            "include_auth": True,
            "include_csrf": True,
            "include_rate_limiting": False,
            "include_security_headers": True,
            "include_staging_config": True,
        }
    },
    "api": {
        "name": "API",
        "description": "API-focused with rate limiting and authentication",
        "features": {
            "include_html": False,
            "include_api": True,
            "include_auth": True,
            "include_csrf": False,  # Not needed for API-only
            "include_rate_limiting": True,
            "include_security_headers": True,
            "include_staging_config": True,
        }
    },
    "full": {
        "name": "Full",
        "description": "All bundled extensions with complete configuration",
        "features": {
            "include_html": True,
            "include_api": True,
            "include_auth": True,
            "include_csrf": True,
            "include_rate_limiting": True,
            "include_security_headers": True,
            "include_staging_config": True,
        }
    },
    "custom": {
        "name": "Custom",
        "description": "Interactive selection of features",
        "features": {}  # Will be filled by interactive wizard
    }
}


def get_template_config(template_name: str) -> Dict[str, Any]:
    """Get configuration for specified template.
    
    Args:
        template_name: Name of template
        
    Returns:
        Template configuration dictionary
        
    Raises:
        ValueError: If template name is unknown
    """
    if template_name not in AVAILABLE_TEMPLATES:
        available = ", ".join(AVAILABLE_TEMPLATES.keys())
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")
    
    return AVAILABLE_TEMPLATES[template_name].copy()


def get_interactive_selections() -> Dict[str, Any]:
    """Get user selections through interactive prompts.
    
    Returns:
        Dictionary of user selections
    """
    
    selections = {}
    
    # Framework features
    click.echo("\n" + click.style("Framework Features:", fg="cyan", bold=True))
    selections["include_html"] = click.confirm("Include HTML routes?", default=True)
    selections["include_api"] = click.confirm("Include API routes?", default=True)
    
    # Extensions
    click.echo("\n" + click.style("Security Extensions:", fg="cyan", bold=True))
    selections["include_auth"] = click.confirm("Include authentication?", default=True)
    
    if selections["include_auth"]:
        click.echo("  Authentication providers will include session and JWT support")
    
    if selections["include_html"]:
        selections["include_csrf"] = click.confirm("Include CSRF protection?", default=True)
    else:
        selections["include_csrf"] = False
    
    selections["include_rate_limiting"] = click.confirm("Include rate limiting?", default=True)
    selections["include_security_headers"] = click.confirm("Include security headers?", default=True)
    
    # Environment setup
    click.echo("\n" + click.style("Environment Setup:", fg="cyan", bold=True))
    selections["include_staging_config"] = click.confirm("Include staging configuration?", default=True)
    
    # Dependencies
    if selections["include_auth"]:
        click.echo("\n" + click.style("Note:", fg="yellow") + " Authentication will include session management")
    
    if selections["include_csrf"] and not selections["include_auth"]:
        click.echo(click.style("Warning:", fg="yellow") + " CSRF protection works best with authentication")
    
    return selections


def validate_feature_dependencies(selections: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and resolve feature dependencies.
    
    Args:
        selections: User selections
        
    Returns:
        Updated selections with dependencies resolved
    """
    # CSRF requires sessions (part of auth)
    if selections.get("include_csrf", False) and not selections.get("include_auth", False):
        click.echo(click.style("Info:", fg="blue") + " CSRF protection requires authentication, enabling auth...")
        selections["include_auth"] = True
    
    # API routes benefit from rate limiting
    if selections.get("include_api", False) and not selections.get("include_rate_limiting", False):
        if click.confirm("API routes detected. Include rate limiting for protection?", default=True):
            selections["include_rate_limiting"] = True
    
    # HTML routes benefit from CSRF
    if selections.get("include_html", False) and not selections.get("include_csrf", False):
        if click.confirm("HTML routes detected. Include CSRF protection?", default=True):
            selections["include_csrf"] = True
            if not selections.get("include_auth", False):
                selections["include_auth"] = True
    
    return selections


def get_security_recommendations(selections: Dict[str, Any]) -> None:
    """Display security recommendations based on selections.
    
    Args:
        selections: User selections
    """
    
    recommendations = []
    
    if not selections.get("include_security_headers", False):
        recommendations.append("Consider enabling security headers for protection against common attacks")
    
    if selections.get("include_api", False) and not selections.get("include_rate_limiting", False):
        recommendations.append("API endpoints should have rate limiting to prevent abuse")
    
    if selections.get("include_html", False) and not selections.get("include_csrf", False):
        recommendations.append("HTML forms should have CSRF protection")
    
    if selections.get("include_auth", False):
        recommendations.append("Remember to configure strong secrets for JWT and sessions in production")
    
    if recommendations:
        click.echo("\n" + click.style("Security Recommendations:", fg="yellow", bold=True))
        for rec in recommendations:
            click.echo(f"  • {rec}")


def create_environment_configs(selections: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Create environment-specific configurations.
    
    Args:
        selections: User selections
        
    Returns:
        Dictionary of environment configurations
    """
    configs = {}
    
    # Development configuration
    configs["dev"] = {
        "app": {
            "debug": True
        }
    }
    
    # Add auth development settings
    if selections.get("include_auth", False):
        configs["dev"]["auth"] = {
            "providers": {
                "session": {
                    "cookie_secure": False,  # Allow HTTP in development
                },
                "jwt": {
                    "token_expire_minutes": 1440  # 24 hours for development
                }
            }
        }
    
    # Staging configuration (if requested)
    if selections.get("include_staging_config", False):
        configs["staging"] = {
            "app": {
                "debug": False
            }
        }
        
        if selections.get("include_auth", False):
            configs["staging"]["auth"] = {
                "providers": {
                    "session": {
                        "cookie_secure": True,
                    },
                    "jwt": {
                        "token_expire_minutes": 60  # 1 hour for staging
                    }
                }
            }
    
    return configs