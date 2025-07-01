"""Environment management for production utilities."""

from __future__ import annotations

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from .config import EnvironmentConfig
from .exceptions import EnvironmentValidationError, ConfigurationError


@dataclass
class EnvironmentResult:
    """Result of environment operation."""
    
    success: bool
    environment_name: Optional[str] = None
    config_path: Optional[str] = None
    validation_errors: List[str] = None
    applied_variables: int = 0
    backup_path: Optional[str] = None
    message: str = ""
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


@dataclass
class ValidationResult:
    """Result of environment validation."""
    
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    security_score: int = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ComparisonResult:
    """Result of environment comparison."""
    
    differences: Dict[str, Dict[str, Any]]
    summary: str = ""


class EnvironmentManager:
    """Manager for environment configuration and deployment."""
    
    def __init__(self):
        """Initialize environment manager."""
        pass
    
    async def create_environment(self, config: EnvironmentConfig) -> EnvironmentResult:
        """Create a new environment configuration.
        
        Args:
            config: Environment configuration
            
        Returns:
            Environment creation result
        """
        try:
            # Validate configuration
            validation_errors = config.validate()
            if validation_errors:
                return EnvironmentResult(
                    success=False,
                    validation_errors=validation_errors,
                    message="Environment validation failed"
                )
            
            # Create config file path (mock implementation)
            config_path = f"/tmp/environments/{config.name}.json"
            
            return EnvironmentResult(
                success=True,
                environment_name=config.name,
                config_path=config_path,
                message=f"Environment '{config.name}' created successfully"
            )
            
        except Exception as e:
            return EnvironmentResult(
                success=False,
                message=f"Failed to create environment: {str(e)}"
            )
    
    async def load_environment(self, environment_name: str, config_dir: str) -> Optional[EnvironmentConfig]:
        """Load environment configuration from file.
        
        Args:
            environment_name: Name of environment to load
            config_dir: Directory containing environment configurations
            
        Returns:
            Loaded environment configuration or None if not found
        """
        try:
            config_file = Path(config_dir) / f"{environment_name}.json"
            
            if not config_file.exists():
                return None
            
            config_data = json.loads(config_file.read_text())
            
            # Create EnvironmentConfig from loaded data
            return EnvironmentConfig(
                name=config_data.get("name", environment_name),
                app_env=config_data.get("app_env", "production"),
                debug=config_data.get("debug", False),
                log_level=config_data.get("log_level", "INFO"),
                allowed_hosts=config_data.get("allowed_hosts", []),
                cors_origins=config_data.get("cors_origins", []),
                environment_variables=config_data.get("environment_variables", {}),
                required_env_vars=config_data.get("required_env_vars", []),
                health_check_url=config_data.get("health_check_url", "/health"),
                metrics_enabled=config_data.get("metrics_enabled", False)
            )
            
        except Exception:
            return None
    
    async def validate_environment(self, config: EnvironmentConfig) -> ValidationResult:
        """Validate environment configuration.
        
        Args:
            config: Environment configuration to validate
            
        Returns:
            Validation result
        """
        errors = config.validate()
        warnings = []
        security_score = 100
        
        # Calculate security score based on configuration
        if config.debug:
            warnings.append("Debug mode should be disabled in production")
            security_score -= 20
        
        if not config.allowed_hosts:
            warnings.append("Consider setting allowed hosts for security")
            security_score -= 10
        
        if config.log_level == "DEBUG":
            warnings.append("Debug log level may expose sensitive information")
            security_score -= 10
        
        # Check for required environment variables
        if not config.required_env_vars:
            warnings.append("No required environment variables specified")
            security_score -= 5
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            security_score=max(0, security_score)
        )
    
    async def apply_environment(self, config: EnvironmentConfig) -> EnvironmentResult:
        """Apply environment configuration to system.
        
        Args:
            config: Environment configuration to apply
            
        Returns:
            Application result
        """
        try:
            applied_count = 0
            
            # Apply environment variables
            for key, value in config.environment_variables.items():
                os.environ[key] = value
                applied_count += 1
            
            # Set standard environment variables
            os.environ["APP_ENV"] = config.app_env
            os.environ["LOG_LEVEL"] = config.log_level
            os.environ["DEBUG"] = str(config.debug).lower()
            applied_count += 3
            
            return EnvironmentResult(
                success=True,
                environment_name=config.name,
                applied_variables=applied_count,
                message=f"Applied {applied_count} environment variables"
            )
            
        except Exception as e:
            return EnvironmentResult(
                success=False,
                environment_name=config.name,
                message=f"Failed to apply environment: {str(e)}"
            )
    
    async def backup_environment(self, config: EnvironmentConfig, backup_dir: str) -> EnvironmentResult:
        """Backup environment configuration.
        
        Args:
            config: Environment configuration to backup
            backup_dir: Directory to store backup
            
        Returns:
            Backup result
        """
        try:
            # Create backup directory if it doesn't exist
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"{config.name}_backup_{timestamp}.json"
            
            # Create backup data
            backup_data = config.to_dict()
            backup_data["backup_timestamp"] = datetime.now(timezone.utc).isoformat()
            backup_data["backup_version"] = "1.0"
            
            # Write backup file
            backup_file.write_text(json.dumps(backup_data, indent=2))
            
            return EnvironmentResult(
                success=True,
                environment_name=config.name,
                backup_path=str(backup_file),
                message=f"Environment backed up to {backup_file}"
            )
            
        except Exception as e:
            return EnvironmentResult(
                success=False,
                environment_name=config.name,
                message=f"Failed to backup environment: {str(e)}"
            )
    
    async def restore_environment(self, backup_path: str) -> Optional[EnvironmentConfig]:
        """Restore environment from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Restored environment configuration or None if failed
        """
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return None
            
            backup_data = json.loads(backup_file.read_text())
            
            # Create EnvironmentConfig from backup data
            return EnvironmentConfig(
                name=backup_data.get("name", "unknown"),
                app_env=backup_data.get("app_env", "production"),
                debug=backup_data.get("debug", False),
                log_level=backup_data.get("log_level", "INFO"),
                allowed_hosts=backup_data.get("allowed_hosts", []),
                cors_origins=backup_data.get("cors_origins", []),
                environment_variables=backup_data.get("environment_variables", {}),
                required_env_vars=backup_data.get("required_env_vars", []),
                health_check_url=backup_data.get("health_check_url", "/health"),
                metrics_enabled=backup_data.get("metrics_enabled", False)
            )
            
        except Exception:
            return None
    
    async def list_environments(self, config_dir: str) -> List[Dict[str, Any]]:
        """List available environments.
        
        Args:
            config_dir: Directory containing environment configurations
            
        Returns:
            List of environment information
        """
        try:
            config_path = Path(config_dir)
            
            if not config_path.exists():
                return []
            
            environments = []
            
            for config_file in config_path.glob("*.json"):
                try:
                    config_data = json.loads(config_file.read_text())
                    environments.append({
                        "name": config_data.get("name", config_file.stem),
                        "app_env": config_data.get("app_env", "unknown"),
                        "debug": config_data.get("debug", False),
                        "file_path": str(config_file)
                    })
                except Exception:
                    # Skip invalid configuration files
                    continue
            
            return environments
            
        except Exception:
            return []
    
    async def compare_environments(self, env1: EnvironmentConfig, env2: EnvironmentConfig) -> ComparisonResult:
        """Compare two environment configurations.
        
        Args:
            env1: First environment configuration
            env2: Second environment configuration
            
        Returns:
            Comparison result
        """
        differences = {}
        
        # Compare basic fields
        fields_to_compare = [
            "name", "app_env", "debug", "log_level", 
            "allowed_hosts", "cors_origins", "health_check_url", "metrics_enabled"
        ]
        
        for field in fields_to_compare:
            value1 = getattr(env1, field)
            value2 = getattr(env2, field)
            
            if value1 != value2:
                differences[field] = {
                    "env1": value1,
                    "env2": value2
                }
        
        # Compare environment variables
        env_vars_diff = {}
        all_keys = set(env1.environment_variables.keys()) | set(env2.environment_variables.keys())
        
        for key in all_keys:
            val1 = env1.environment_variables.get(key)
            val2 = env2.environment_variables.get(key)
            
            if val1 != val2:
                env_vars_diff[key] = {
                    "env1": val1,
                    "env2": val2
                }
        
        if env_vars_diff:
            differences["environment_variables"] = env_vars_diff
        
        # Compare required environment variables
        if set(env1.required_env_vars) != set(env2.required_env_vars):
            differences["required_env_vars"] = {
                "env1": env1.required_env_vars,
                "env2": env2.required_env_vars
            }
        
        summary = f"Found {len(differences)} differences between environments"
        
        return ComparisonResult(
            differences=differences,
            summary=summary
        )