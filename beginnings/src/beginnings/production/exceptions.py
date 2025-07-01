"""Exception classes for production utilities."""

from __future__ import annotations

from typing import Optional, Dict, Any


class ProductionError(Exception):
    """Base exception for production utilities errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SecretNotFoundError(ProductionError):
    """Exception raised when a secret is not found."""
    
    def __init__(self, secret_name: str, vault_path: Optional[str] = None):
        message = f"Secret '{secret_name}' not found"
        if vault_path:
            message += f" at path '{vault_path}'"
        
        super().__init__(message, {
            'secret_name': secret_name,
            'vault_path': vault_path
        })
        self.secret_name = secret_name
        self.vault_path = vault_path


class ConfigurationError(ProductionError):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str, config_section: Optional[str] = None, validation_errors: Optional[list] = None):
        super().__init__(message, {
            'config_section': config_section,
            'validation_errors': validation_errors or []
        })
        self.config_section = config_section
        self.validation_errors = validation_errors or []


class EnvironmentValidationError(ProductionError):
    """Exception raised for environment validation errors."""
    
    def __init__(self, environment_name: str, validation_errors: list):
        message = f"Environment '{environment_name}' validation failed"
        super().__init__(message, {
            'environment_name': environment_name,
            'validation_errors': validation_errors
        })
        self.environment_name = environment_name
        self.validation_errors = validation_errors