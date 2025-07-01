"""Migration system for Beginnings framework.

This module provides comprehensive migration tools for:
- Database schema migrations
- Code migrations and refactoring
- Configuration migrations
- Extension migrations

The migration system supports:
- Forward and backward migrations
- Migration versioning and tracking
- Dry-run capabilities
- Rollback functionality
- Dependency resolution
"""

from .base import BaseMigration, MigrationError
from .database import DatabaseMigration, DatabaseMigrationRunner
from .code import CodeMigration, CodeMigrationRunner
from .config import ConfigMigration, ConfigMigrationRunner
from .runner import MigrationRunner, MigrationResult
from .registry import MigrationRegistry
from .utils import MigrationUtils

__all__ = [
    # Base classes
    'BaseMigration',
    'MigrationError',
    
    # Migration types
    'DatabaseMigration',
    'CodeMigration', 
    'ConfigMigration',
    
    # Runners
    'DatabaseMigrationRunner',
    'CodeMigrationRunner',
    'ConfigMigrationRunner',
    'MigrationRunner',
    
    # Supporting classes
    'MigrationResult',
    'MigrationRegistry',
    'MigrationUtils',
]