"""Error handling utilities for CLI commands."""

import click
import sys
from typing import Optional, Dict, Any, List

from .colors import error, warning, info
from .suggestions import CommandSuggester, ContextualHelpProvider


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


def create_intelligent_error(
    error_class: type[CLIError],
    message: str,
    command: str = None,
    context: Dict[str, Any] = None,
    exit_code: int = 1
) -> CLIError:
    """Create an error with intelligent suggestions.
    
    Args:
        error_class: Error class to instantiate
        message: Error message
        command: Command context
        context: Additional context information
        exit_code: Exit code for the error
        
    Returns:
        Error instance with intelligent suggestions
    """
    context = context or {}
    if command:
        context['command'] = command
    
    # Get intelligent suggestions
    suggester = CommandSuggester()
    context_help = ContextualHelpProvider()
    
    # Get error-based suggestions
    error_suggestions = suggester.suggest_based_on_error(message, context)
    
    # Get contextual help
    help_info = context_help.get_contextual_help(
        command=command,
        error_context={'type': 'general', 'message': message}
    )
    
    # Combine suggestions
    all_suggestions = error_suggestions + help_info.get('troubleshooting', [])
    unique_suggestions = list(dict.fromkeys(all_suggestions))  # Remove duplicates
    
    # Create error with suggestions
    error = error_class(message, exit_code, unique_suggestions)
    error.context = context
    
    return error


def suggest_command_correction(user_input: str, available_commands: List[str] = None) -> List[str]:
    """Get command correction suggestions.
    
    Args:
        user_input: The command user typed
        available_commands: Available commands list
        
    Returns:
        List of correction suggestions
    """
    suggester = CommandSuggester()
    return suggester.suggest_command_fix(user_input, available_commands)


def get_contextual_help_for_error(
    command: str = None, 
    error_message: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Get contextual help for an error situation.
    
    Args:
        command: Command being executed
        error_message: Error message text
        context: Additional context
        
    Returns:
        Dictionary with help information
    """
    context_help = ContextualHelpProvider()
    error_context = context or {}
    if error_message:
        error_context.update({'message': error_message, 'type': 'general'})
    
    return context_help.get_contextual_help(command, error_context)


def handle_cli_error(error_instance: CLIError):
    """Handle CLI errors with helpful output and intelligent suggestions.
    
    Args:
        error_instance: The CLI error to handle
    """
    # Print main error message
    click.echo(error(error_instance.message), err=True)
    
    # Get intelligent suggestions if none provided
    suggestions = error_instance.suggestions
    if not suggestions:
        suggester = CommandSuggester()
        context_help = ContextualHelpProvider()
        
        # Try to get context-aware suggestions
        context = getattr(error_instance, 'context', {})
        intelligent_suggestions = suggester.suggest_based_on_error(
            error_instance.message, context
        )
        
        if intelligent_suggestions:
            suggestions = intelligent_suggestions
        else:
            # Get general contextual help
            help_info = context_help.get_contextual_help(
                command=context.get('command'),
                error_context={'type': 'general', 'message': error_instance.message}
            )
            suggestions = help_info.get('troubleshooting', [])
    
    # Print suggestions if available
    if suggestions:
        click.echo(info("Suggestions:"), err=True)
        for suggestion in suggestions:
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
        # Get intelligent suggestions
        suggester = CommandSuggester()
        context_help = ContextualHelpProvider()
        
        base_suggestions = [
            "Run 'beginnings new <project-name>' to create a new project",
            "Ensure you're in the project root directory",
            "Check that configuration files exist (app.yaml or config/app.yaml)"
        ]
        
        # Add context-aware suggestions
        help_info = context_help.get_contextual_help(
            command='validate',
            error_context={'type': 'project_validation', 'path': path}
        )
        additional_suggestions = help_info.get('troubleshooting', [])
        
        all_suggestions = base_suggestions + additional_suggestions
        
        error = ProjectError(
            f"Directory '{path}' does not appear to be a beginnings project",
            suggestions=all_suggestions
        )
        error.context = {'command': 'validate', 'path': path}
        raise error


def validate_configuration_file(config_path: str) -> None:
    """Validate that a configuration file exists and is readable.
    
    Args:
        config_path: Path to configuration file
        
    Raises:
        ConfigurationError: If file doesn't exist or isn't readable
    """
    import os
    
    suggester = CommandSuggester()
    context_help = ContextualHelpProvider()
    
    if not os.path.exists(config_path):
        # Get intelligent suggestions for missing file
        help_info = context_help.get_contextual_help(
            command='config',
            error_context={'type': 'file_not_found', 'path': config_path}
        )
        
        base_suggestions = [
            "Check the file path is correct",
            "Ensure the configuration file exists",
            "Use --config-dir to specify custom configuration directory"
        ]
        
        error_suggestions = suggester.suggest_based_on_error(
            f"Configuration file not found: {config_path}",
            {'command': 'config', 'file_path': config_path}
        )
        
        all_suggestions = base_suggestions + error_suggestions + help_info.get('troubleshooting', [])
        
        error = ConfigurationError(
            f"Configuration file not found: {config_path}",
            suggestions=list(dict.fromkeys(all_suggestions))  # Remove duplicates
        )
        error.context = {'command': 'config', 'file_path': config_path, 'error_type': 'not_found'}
        raise error
    
    if not os.path.isfile(config_path):
        error = ConfigurationError(
            f"Configuration path is not a file: {config_path}"
        )
        error.context = {'command': 'config', 'file_path': config_path, 'error_type': 'not_file'}
        raise error
    
    try:
        with open(config_path, 'r') as f:
            f.read(1)  # Try to read at least one character
    except PermissionError:
        # Get intelligent suggestions for permission error
        error_suggestions = suggester.suggest_based_on_error(
            "Permission denied",
            {'command': 'config', 'file_path': config_path}
        )
        
        base_suggestions = [
            "Check file permissions",
            "Ensure you have read access to the file"
        ]
        
        all_suggestions = base_suggestions + error_suggestions
        
        error = ConfigurationError(
            f"Permission denied reading configuration file: {config_path}",
            suggestions=list(dict.fromkeys(all_suggestions))
        )
        error.context = {'command': 'config', 'file_path': config_path, 'error_type': 'permission'}
        raise error
    except Exception as e:
        # Get intelligent suggestions for general read error
        error_suggestions = suggester.suggest_based_on_error(
            str(e),
            {'command': 'config', 'file_path': config_path}
        )
        
        suggestions = ["Check file format and encoding", "Verify file is not corrupted"] + error_suggestions
        
        error = ConfigurationError(
            f"Error reading configuration file: {e}",
            suggestions=suggestions
        )
        error.context = {'command': 'config', 'file_path': config_path, 'error_type': 'read_error', 'exception': str(e)}
        raise error