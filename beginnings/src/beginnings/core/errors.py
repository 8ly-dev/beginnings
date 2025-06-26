"""
Error handling and exception framework for Beginnings framework.

This module provides the error hierarchy and context reporting
for all framework components.
"""

from __future__ import annotations

from typing import Any


class BeginningsError(Exception):
    """
    Base exception class for all framework errors.
    
    All Beginnings framework exceptions inherit from this class
    to provide consistent error handling and context.
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """
        Initialize the error with message and optional context.
        
        Args:
            message: Human-readable error message
            context: Optional dictionary with error context information
        """
        super().__init__(message)
        self.context = context or {}

    def get_context(self) -> dict[str, Any]:
        """
        Get error context information.
        
        Returns:
            Dictionary containing error context
        """
        return self.context.copy()

    def add_context(self, key: str, value: Any) -> None:
        """
        Add context information to the error.
        
        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value


class ConfigurationError(BeginningsError):
    """
    Configuration loading, validation, and structure errors.
    
    Raised when configuration files cannot be loaded, parsed,
    validated, or when configuration structure is invalid.
    """

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line_number: int | None = None,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize configuration error with file context.
        
        Args:
            message: Error message
            file_path: Path to configuration file causing error
            line_number: Line number in file where error occurred
            suggestion: Suggested solution for the error
            context: Additional error context
        """
        super().__init__(message, context)

        if file_path:
            self.add_context("file_path", file_path)
        if line_number:
            self.add_context("line_number", line_number)
        if suggestion:
            self.add_context("suggestion", suggestion)

    def get_actionable_message(self) -> str:
        """
        Get error message with file location and suggested solution.
        
        Returns:
            Formatted error message with context
        """
        parts = [str(self)]

        file_path = self.context.get("file_path")
        line_number = self.context.get("line_number")

        if file_path:
            location = f"File: {file_path}"
            if line_number:
                location += f", Line: {line_number}"
            parts.append(location)

        suggestion = self.context.get("suggestion")
        if suggestion:
            parts.append(f"Suggestion: {suggestion}")

        return "\n".join(parts)


class ExtensionError(BeginningsError):
    """
    Extension loading, initialization, and runtime errors.
    
    Raised when extensions cannot be loaded, initialized,
    or when extension operations fail.
    """

    def __init__(
        self,
        message: str,
        extension_name: str | None = None,
        extension_path: str | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize extension error with extension context.
        
        Args:
            message: Error message
            extension_name: Name of the extension causing error
            extension_path: Import path of the extension
            context: Additional error context
        """
        super().__init__(message, context)

        if extension_name:
            self.add_context("extension_name", extension_name)
        if extension_path:
            self.add_context("extension_path", extension_path)


class RoutingError(BeginningsError):
    """
    Router configuration and middleware chain errors.
    
    Raised when router configuration is invalid, middleware
    chains cannot be built, or routing operations fail.
    """

    def __init__(
        self,
        message: str,
        route_path: str | None = None,
        methods: list[str] | None = None,
        router_type: str | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize routing error with route context.
        
        Args:
            message: Error message
            route_path: Route path causing error
            methods: HTTP methods for the route
            router_type: Type of router (HTML/API)
            context: Additional error context
        """
        super().__init__(message, context)

        if route_path:
            self.add_context("route_path", route_path)
        if methods:
            self.add_context("methods", methods)
        if router_type:
            self.add_context("router_type", router_type)


class ValidationError(BeginningsError):
    """
    Schema validation and security check errors.
    
    Raised when configuration or data fails validation,
    or when security checks detect potential issues.
    """

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        security_issues: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize validation error with validation context.
        
        Args:
            message: Error message
            validation_errors: List of validation error messages
            security_issues: List of security issue descriptions
            context: Additional error context
        """
        super().__init__(message, context)

        if validation_errors:
            self.add_context("validation_errors", validation_errors)
        if security_issues:
            self.add_context("security_issues", security_issues)

    def get_detailed_message(self) -> str:
        """
        Get error message with detailed validation and security issues.
        
        Returns:
            Formatted error message with all validation details
        """
        parts = [str(self)]

        validation_errors = self.context.get("validation_errors", [])
        if validation_errors:
            parts.append("Validation Errors:")
            for error in validation_errors:
                parts.append(f"  - {error}")

        security_issues = self.context.get("security_issues", [])
        if security_issues:
            parts.append("Security Issues:")
            for issue in security_issues:
                parts.append(f"  - {issue}")

        return "\n".join(parts)


# Re-export extension-specific errors for convenience
class ConfigurationIncludeError(ConfigurationError):
    """Error in configuration include processing."""


class ConfigurationConflictError(ConfigurationError):
    """Conflict detected during configuration merging."""


class ConfigurationInterpolationError(ConfigurationError):
    """Error in environment variable interpolation."""


class EnvironmentError(ConfigurationError):
    """Environment detection or configuration error."""


# Utility functions for error context
def add_file_context(error: BeginningsError, file_path: str, line_number: int | None = None) -> None:
    """
    Add file context to an error.
    
    Args:
        error: Error to add context to
        file_path: Path to the file
        line_number: Optional line number
    """
    error.add_context("file_path", file_path)
    if line_number:
        error.add_context("line_number", line_number)


def create_aggregated_error(
    base_message: str,
    errors: list[Exception],
    error_type: type[BeginningsError] = BeginningsError
) -> BeginningsError:
    """
    Create an aggregated error from multiple individual errors.
    
    Args:
        base_message: Base error message
        errors: List of individual errors
        error_type: Type of error to create
        
    Returns:
        Aggregated error with context from all individual errors
    """
    context = {
        "error_count": len(errors),
        "individual_errors": [str(error) for error in errors]
    }

    return error_type(base_message, context=context)
