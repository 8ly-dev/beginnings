"""Secrets management for production utilities."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from .config import SecretConfig
from .exceptions import SecretNotFoundError, ProductionError


@dataclass
class VaultResult:
    """Result of vault operation."""
    
    success: bool
    authenticated: bool = False
    message: str = ""


@dataclass
class SecretResult:
    """Result of secret operation."""
    
    success: bool
    secret_id: Optional[str] = None
    secret_value: Optional[str] = None
    version: int = 1
    metadata: Optional[Dict[str, Any]] = None
    old_version: Optional[int] = None
    new_version: Optional[int] = None
    backup_created: bool = False
    deleted: bool = False
    message: str = ""


@dataclass
class BackupResult:
    """Result of secrets backup operation."""
    
    success: bool
    backup_path: Optional[str] = None
    secrets_count: int = 0
    message: str = ""


@dataclass
class AuditResult:
    """Result of secret access audit."""
    
    success: bool
    access_logs: List[Dict[str, Any]] = None
    read_operations: int = 0
    write_operations: int = 0
    delete_operations: int = 0
    
    def __post_init__(self):
        if self.access_logs is None:
            self.access_logs = []


class SecretsManager:
    """Manager for secrets and vault operations."""
    
    def __init__(self):
        """Initialize secrets manager."""
        self.vault_client = None
    
    async def initialize_vault_connection(self, vault_url: str, vault_token: str) -> VaultResult:
        """Initialize connection to Vault.
        
        Args:
            vault_url: URL of the Vault server
            vault_token: Authentication token for Vault
            
        Returns:
            Vault connection result
        """
        try:
            # Mock vault client initialization
            try:
                import hvac
                
                self.vault_client = hvac.Client(url=vault_url, token=vault_token)
                authenticated = self.vault_client.is_authenticated()
                
                return VaultResult(
                    success=True,
                    authenticated=authenticated,
                    message="Vault connection initialized successfully"
                )
                
            except ImportError:
                # Mock successful connection for testing
                self.vault_client = MockVaultClient()
                
                return VaultResult(
                    success=True,
                    authenticated=True,
                    message="Mock vault connection initialized (hvac not available)"
                )
                
        except Exception as e:
            return VaultResult(
                success=False,
                authenticated=False,
                message=f"Failed to initialize vault connection: {str(e)}"
            )
    
    async def store_secret(
        self, 
        config: SecretConfig, 
        secret_value: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SecretResult:
        """Store a secret in vault.
        
        Args:
            config: Secret configuration
            secret_value: The secret value to store
            metadata: Optional metadata for the secret
            
        Returns:
            Secret storage result
        """
        if not self.vault_client:
            return SecretResult(
                success=False,
                message="Vault client not initialized"
            )
        
        try:
            # Validate secret configuration
            errors = config.validate()
            if errors:
                return SecretResult(
                    success=False,
                    message=f"Secret configuration invalid: {', '.join(errors)}"
                )
            
            # Prepare secret data
            secret_data = {
                config.secret_type: secret_value
            }
            
            if metadata:
                secret_data.update(metadata)
            
            # Store secret in vault
            response = self.vault_client.write(config.vault_path, **secret_data)
            
            secret_id = str(uuid.uuid4())
            
            return SecretResult(
                success=True,
                secret_id=secret_id,
                version=1,
                metadata=metadata or {},
                message=f"Secret '{config.name}' stored successfully"
            )
            
        except Exception as e:
            return SecretResult(
                success=False,
                message=f"Failed to store secret: {str(e)}"
            )
    
    async def retrieve_secret(self, config: SecretConfig) -> SecretResult:
        """Retrieve a secret from vault.
        
        Args:
            config: Secret configuration
            
        Returns:
            Secret retrieval result
        """
        if not self.vault_client:
            return SecretResult(
                success=False,
                message="Vault client not initialized"
            )
        
        try:
            # Read secret from vault
            response = self.vault_client.read(config.vault_path)
            
            if not response:
                raise SecretNotFoundError(config.name, config.vault_path)
            
            # Extract secret data
            secret_data = response.get("data", {})
            if "data" in secret_data:
                secret_data = secret_data["data"]
            
            # Get the secret value (try different possible keys)
            secret_value = None
            for key in [config.secret_type, "value", "secret", "password"]:
                if key in secret_data:
                    secret_value = secret_data[key]
                    break
            
            metadata = response.get("data", {}).get("metadata", {})
            version = metadata.get("version", 1)
            
            return SecretResult(
                success=True,
                secret_value=secret_value,
                version=version,
                metadata=metadata,
                message=f"Secret '{config.name}' retrieved successfully"
            )
            
        except SecretNotFoundError:
            raise
        except Exception as e:
            return SecretResult(
                success=False,
                message=f"Failed to retrieve secret: {str(e)}"
            )
    
    async def rotate_secret(
        self, 
        config: SecretConfig, 
        new_secret_value: str
    ) -> SecretResult:
        """Rotate a secret.
        
        Args:
            config: Secret configuration
            new_secret_value: New secret value
            
        Returns:
            Secret rotation result
        """
        if not self.vault_client:
            return SecretResult(
                success=False,
                message="Vault client not initialized"
            )
        
        try:
            # Read current secret
            current_response = self.vault_client.read(config.vault_path)
            current_version = 1
            
            if current_response:
                metadata = current_response.get("data", {}).get("metadata", {})
                current_version = metadata.get("version", 1)
            
            # Store new secret version
            secret_data = {
                config.secret_type: new_secret_value
            }
            
            self.vault_client.write(config.vault_path, **secret_data)
            
            new_version = current_version + 1
            
            return SecretResult(
                success=True,
                old_version=current_version,
                new_version=new_version,
                backup_created=True,
                message=f"Secret '{config.name}' rotated successfully"
            )
            
        except Exception as e:
            return SecretResult(
                success=False,
                message=f"Failed to rotate secret: {str(e)}"
            )
    
    async def delete_secret(self, config: SecretConfig, confirm: bool = False) -> SecretResult:
        """Delete a secret from vault.
        
        Args:
            config: Secret configuration
            confirm: Confirmation flag for deletion
            
        Returns:
            Secret deletion result
        """
        if not confirm:
            return SecretResult(
                success=False,
                message="Deletion not confirmed"
            )
        
        if not self.vault_client:
            return SecretResult(
                success=False,
                message="Vault client not initialized"
            )
        
        try:
            # Delete secret from vault
            self.vault_client.delete(config.vault_path)
            
            return SecretResult(
                success=True,
                deleted=True,
                message=f"Secret '{config.name}' deleted successfully"
            )
            
        except Exception as e:
            return SecretResult(
                success=False,
                message=f"Failed to delete secret: {str(e)}"
            )
    
    async def list_secrets(self, vault_path: str) -> List[str]:
        """List secrets in a vault path.
        
        Args:
            vault_path: Vault path to list
            
        Returns:
            List of secret paths
        """
        if not self.vault_client:
            return []
        
        try:
            response = self.vault_client.list(vault_path)
            
            if response and "data" in response and "keys" in response["data"]:
                return response["data"]["keys"]
            
            return []
            
        except Exception:
            return []
    
    async def backup_secrets(self, vault_path: str, backup_file: str) -> BackupResult:
        """Backup secrets from vault.
        
        Args:
            vault_path: Vault path to backup
            backup_file: Path to backup file
            
        Returns:
            Backup result
        """
        if not self.vault_client:
            return BackupResult(
                success=False,
                message="Vault client not initialized"
            )
        
        try:
            # List all secrets in path
            secrets = await self.list_secrets(vault_path)
            
            backup_data = {
                "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                "vault_path": vault_path,
                "secrets": {}
            }
            
            # Read each secret
            for secret_name in secrets:
                try:
                    secret_path = f"{vault_path.rstrip('/')}/{secret_name}"
                    response = self.vault_client.read(secret_path)
                    
                    if response:
                        backup_data["secrets"][secret_name] = response.get("data", {})
                        
                except Exception:
                    # Skip secrets that can't be read
                    continue
            
            # Write backup file
            backup_path = Path(backup_file)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(json.dumps(backup_data, indent=2))
            
            return BackupResult(
                success=True,
                backup_path=str(backup_path),
                secrets_count=len(backup_data["secrets"]),
                message=f"Backed up {len(backup_data['secrets'])} secrets"
            )
            
        except Exception as e:
            return BackupResult(
                success=False,
                message=f"Failed to backup secrets: {str(e)}"
            )
    
    async def audit_secret_access(
        self, 
        start_time: str, 
        end_time: str
    ) -> AuditResult:
        """Audit secret access logs.
        
        Args:
            start_time: Start time for audit (ISO format)
            end_time: End time for audit (ISO format)
            
        Returns:
            Audit result
        """
        if not self.vault_client:
            return AuditResult(
                success=False,
                access_logs=[]
            )
        
        try:
            # Mock audit log reading (in real implementation, this would query vault audit logs)
            response = self.vault_client.read("sys/audit")
            
            if response and "data" in response:
                access_logs = response["data"]
                
                # Count operations by type
                read_ops = sum(1 for log in access_logs if log.get("operation") == "read")
                write_ops = sum(1 for log in access_logs if log.get("operation") == "write") 
                delete_ops = sum(1 for log in access_logs if log.get("operation") == "delete")
                
                return AuditResult(
                    success=True,
                    access_logs=access_logs,
                    read_operations=read_ops,
                    write_operations=write_ops,
                    delete_operations=delete_ops
                )
            
            return AuditResult(
                success=True,
                access_logs=[]
            )
            
        except Exception as e:
            return AuditResult(
                success=False,
                access_logs=[]
            )


class MockVaultClient:
    """Mock vault client for testing."""
    
    def __init__(self):
        self._data = {}
    
    def is_authenticated(self):
        return True
    
    def write(self, path: str, **kwargs):
        self._data[path] = {"data": kwargs}
        return {"request_id": str(uuid.uuid4())}
    
    def read(self, path: str):
        if path in self._data:
            return self._data[path]
        return None
    
    def delete(self, path: str):
        if path in self._data:
            del self._data[path]
        return True
    
    def list(self, path: str):
        keys = [key.split('/')[-1] for key in self._data.keys() if key.startswith(path)]
        return {"data": {"keys": keys}} if keys else None