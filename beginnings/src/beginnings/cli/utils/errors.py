"""Error handling utilities for CLI commands."""

import click
import sys
from typing import Optional

from .colors import error, warning, info


class CLIError(Exception):
    """Base exception for CLI-related errors."""
    
    def __init__(self, message: str, exit_code: int = 1, suggestions: Optional[list] = None):
        self.message = message
        self.exit_code = exit_code
        self.suggestions = suggestions or []
        super().__init__(message)


class ConfigurationError(CLIError):
    """Configuration-related CLI error."""
    pass


class ProjectError(CLIError):
    """Project management error."""
    pass


class ValidationError(CLIError):
    """Validation error."""
    pass


def handle_cli_error(error_instance: CLIError):
    """Handle CLI errors with helpful output.
    
    Args:
        error_instance: The CLI error to handle
    """
    # Print main error message
    click.echo(error(error_instance.message), err=True)
    
    # Print suggestions if available
    if error_instance.suggestions:
        click.echo(info("Suggestions:"), err=True)
        for suggestion in error_instance.suggestions:
            click.echo(f"  • {suggestion}", err=True)
    
    # Exit with appropriate code
    sys.exit(error_instance.exit_code)


def validate_project_directory(path: str) -> None:
    """Validate that a directory looks like a beginnings project.
    
    Args:
        path: Path to validate
        
    Raises:
        ProjectError: If directory doesn't appear to be a beginnings project
    """
    import os
    
    config_indicators = ["app.yaml", "config/app.yaml", "pyproject.toml"]
    
    found_indicators = []
    for indicator in config_indicators:
        full_path = os.path.join(path, indicator)
        if os.path.exists(full_path):
            found_indicators.append(indicator)
    
    if not found_indicators:
        raise ProjectError(
            f"Directory '{path}' does not appear to be a beginnings project",
            suggestions=[
                "Run 'beginnings new <project-name>' to create a new project",
                "Ensure you're in the project root directory",
                "Check that configuration files exist (app.yaml or config/app.yaml)"
            ]
        )


def validate_configuration_file(config_path: str) -> None:
    """Validate that a configuration file exists and is readable.
    
    Args:
        config_path: Path to configuration file
        
    Raises:
        ConfigurationError: If file doesn't exist or isn't readable
    """
    import os
    
    if not os.path.exists(config_path):
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            suggestions=[
                "Check the file path is correct",
                "Ensure the configuration file exists",
                "Use --config-dir to specify custom configuration directory"
            ]
        )
    
    if not os.path.isfile(config_path):
        raise ConfigurationError(
            f"Configuration path is not a file: {config_path}"
        )
    
    try:
        with open(config_path, 'r') as f:
            f.read(1)  # Try to read at least one character
    except PermissionError:
        raise ConfigurationError(
            f"Permission denied reading configuration file: {config_path}",
            suggestions=[
                "Check file permissions",
                "Ensure you have read access to the file"
            ]
        )
    except Exception as e:
        raise ConfigurationError(
            f"Error reading configuration file: {e}"
        )