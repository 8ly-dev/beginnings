"""Base migration classes and interfaces."""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum


class MigrationStatus(Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationError(Exception):
    """Base exception for migration errors."""
    
    def __init__(self, message: str, migration_id: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.migration_id = migration_id
        self.cause = cause


class MigrationValidationError(MigrationError):
    """Exception raised when migration validation fails."""
    pass


class MigrationExecutionError(MigrationError):
    """Exception raised when migration execution fails."""
    pass


class MigrationRollbackError(MigrationError):
    """Exception raised when migration rollback fails."""
    pass


class BaseMigration(abc.ABC):
    """Base class for all migrations."""
    
    def __init__(
        self,
        migration_id: str,
        description: str,
        version: str,
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ):
        """Initialize migration.
        
        Args:
            migration_id: Unique identifier for the migration
            description: Human-readable description
            version: Migration version
            dependencies: List of migration IDs this depends on
            tags: Optional tags for categorization
        """
        self.migration_id = migration_id
        self.description = description
        self.version = version
        self.dependencies = dependencies or []
        self.tags = tags or []
        self.created_at = datetime.now(timezone.utc)
        self.status = MigrationStatus.PENDING
        self.executed_at: Optional[datetime] = None
        self.execution_time_ms: Optional[float] = None
        self.error_message: Optional[str] = None
    
    @abc.abstractmethod
    def validate(self) -> List[str]:
        """Validate migration can be executed.
        
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    @abc.abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the migration.
        
        Args:
            context: Migration execution context
            
        Returns:
            Migration result data
            
        Raises:
            MigrationExecutionError: If execution fails
        """
        pass
    
    @abc.abstractmethod
    def rollback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback the migration.
        
        Args:
            context: Migration execution context
            
        Returns:
            Rollback result data
            
        Raises:
            MigrationRollbackError: If rollback fails
        """
        pass
    
    @abc.abstractmethod
    def can_rollback(self) -> bool:
        """Check if migration can be rolled back.
        
        Returns:
            True if migration supports rollback
        """
        pass
    
    def get_dry_run_preview(self, context: Dict[str, Any]) -> str:
        """Get preview of what migration would do.
        
        Args:
            context: Migration execution context
            
        Returns:
            Human-readable preview of migration actions
        """
        return f"Migration {self.migration_id}: {self.description}"
    
    def get_estimated_duration(self) -> Optional[float]:
        """Get estimated execution duration in seconds.
        
        Returns:
            Estimated duration or None if unknown
        """
        return None
    
    def requires_downtime(self) -> bool:
        """Check if migration requires application downtime.
        
        Returns:
            True if downtime is required
        """
        return False
    
    def is_reversible(self) -> bool:
        """Check if migration is reversible.
        
        Returns:
            True if migration can be reversed
        """
        return self.can_rollback()
    
    def get_affected_components(self) -> List[str]:
        """Get list of components affected by this migration.
        
        Returns:
            List of component names
        """
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert migration to dictionary representation.
        
        Returns:
            Dictionary representation of migration
        """
        return {
            "migration_id": self.migration_id,
            "description": self.description,
            "version": self.version,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "can_rollback": self.can_rollback(),
            "requires_downtime": self.requires_downtime(),
            "estimated_duration": self.get_estimated_duration(),
            "affected_components": self.get_affected_components()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseMigration:
        """Create migration from dictionary representation.
        
        Args:
            data: Dictionary data
            
        Returns:
            Migration instance
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement from_dict")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.migration_id}, version={self.version}, status={self.status.value})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, BaseMigration):
            return False
        return self.migration_id == other.migration_id
    
    def __hash__(self) -> int:
        return hash(self.migration_id)


class BaseMigrator(abc.ABC):
    """Base class for framework migrators."""
    
    def __init__(self, source_dir: str, output_dir: str, verbose: bool = False):
        """Initialize migrator.
        
        Args:
            source_dir: Source framework project directory
            output_dir: Output directory for Beginnings project
            verbose: Enable verbose output
        """
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.verbose = verbose
    
    @abc.abstractmethod
    async def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """Perform migration from source framework to Beginnings.
        
        Args:
            dry_run: If True, only analyze without creating files
            
        Returns:
            Migration results dictionary
        """
        pass
    
    def generate_report(self, result: Dict[str, Any], report_path) -> None:
        """Generate migration report.
        
        Args:
            result: Migration results
            report_path: Path to save report
        """
        pass