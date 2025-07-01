"""Configuration classes for production utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class EnvironmentConfig:
    """Configuration for environment settings."""
    
    name: str
    app_env: str
    debug: bool
    log_level: str
    allowed_hosts: List[str] = field(default_factory=list)
    cors_origins: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    required_env_vars: List[str] = field(default_factory=list)
    health_check_url: str = "/health"
    metrics_enabled: bool = False
    
    def validate(self) -> List[str]:
        """Validate environment configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Environment name cannot be empty")
        
        if not self.app_env or not self.app_env.strip():
            errors.append("App environment cannot be empty")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            errors.append(f"Invalid log_level '{self.log_level}', must be one of: {', '.join(valid_log_levels)}")
        
        # Validate environment variable names
        for var_name in self.required_env_vars:
            if not var_name or not var_name.strip():
                errors.append("Required environment variable names cannot be empty")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'app_env': self.app_env,
            'debug': self.debug,
            'log_level': self.log_level,
            'allowed_hosts': self.allowed_hosts,
            'cors_origins': self.cors_origins,
            'environment_variables': self.environment_variables,
            'required_env_vars': self.required_env_vars,
            'health_check_url': self.health_check_url,
            'metrics_enabled': self.metrics_enabled
        }


@dataclass
class SecretConfig:
    """Configuration for secret management."""
    
    name: str
    secret_type: str
    environment: str
    vault_path: str
    rotation_enabled: bool = False
    rotation_interval_days: int = 30
    backup_enabled: bool = True
    encryption_key_id: Optional[str] = None
    encryption_algorithm: str = "AES-256-GCM"
    tags: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate secret configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Secret name cannot be empty")
        
        if not self.secret_type or not self.secret_type.strip():
            errors.append("Secret type cannot be empty")
        
        if not self.environment or not self.environment.strip():
            errors.append("Environment cannot be empty")
        
        if not self.vault_path or not self.vault_path.strip():
            errors.append("Vault path cannot be empty")
        
        if self.rotation_interval_days <= 0:
            errors.append("Rotation interval must be positive")
        
        valid_secret_types = ["password", "api_key", "certificate", "token", "connection_string"]
        if self.secret_type not in valid_secret_types:
            errors.append(f"Secret type must be one of: {', '.join(valid_secret_types)}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'secret_type': self.secret_type,
            'environment': self.environment,
            'vault_path': self.vault_path,
            'rotation_enabled': self.rotation_enabled,
            'rotation_interval_days': self.rotation_interval_days,
            'backup_enabled': self.backup_enabled,
            'encryption_key_id': self.encryption_key_id,
            'encryption_algorithm': self.encryption_algorithm,
            'tags': self.tags,
            'expires_at': self.expires_at
        }


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    
    ssl_enabled: bool = True
    force_https: bool = True
    security_headers: bool = True
    csrf_protection: bool = True
    session_secure: bool = True
    session_http_only: bool = True
    content_security_policy: Optional[str] = None
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    rate_limiting_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    def validate(self) -> List[str]:
        """Validate security configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if self.rate_limit_per_minute <= 0:
            errors.append("Rate limit per minute must be positive")
        
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        for method in self.allowed_methods:
            if method not in valid_methods:
                errors.append(f"Invalid HTTP method: {method}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'ssl_enabled': self.ssl_enabled,
            'force_https': self.force_https,
            'security_headers': self.security_headers,
            'csrf_protection': self.csrf_protection,
            'session_secure': self.session_secure,
            'session_http_only': self.session_http_only,
            'content_security_policy': self.content_security_policy,
            'allowed_methods': self.allowed_methods,
            'rate_limiting_enabled': self.rate_limiting_enabled,
            'rate_limit_per_minute': self.rate_limit_per_minute
        }


@dataclass
class ProductionConfig:
    """Complete production configuration."""
    
    project_name: str
    version: str
    environment_config: EnvironmentConfig
    security_config: Optional[SecurityConfig] = None
    monitoring_enabled: bool = True
    backup_enabled: bool = True
    logging_config: Optional[Dict[str, Any]] = None
    database_config: Optional[Dict[str, Any]] = None
    cache_config: Optional[Dict[str, Any]] = None
    
    def validate(self) -> List[str]:
        """Validate complete production configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.project_name or not self.project_name.strip():
            errors.append("project_name cannot be empty")
        
        if not self.version or not self.version.strip():
            errors.append("Version cannot be empty")
        
        # Validate environment config
        env_errors = self.environment_config.validate()
        errors.extend([f"environment: {error}" for error in env_errors])
        
        # Validate security config if present
        if self.security_config:
            security_errors = self.security_config.validate()
            errors.extend([f"security: {error}" for error in security_errors])
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'project_name': self.project_name,
            'version': self.version,
            'environment_config': self.environment_config.to_dict(),
            'security_config': self.security_config.to_dict() if self.security_config else None,
            'monitoring_enabled': self.monitoring_enabled,
            'backup_enabled': self.backup_enabled,
            'logging_config': self.logging_config,
            'database_config': self.database_config,
            'cache_config': self.cache_config
        }