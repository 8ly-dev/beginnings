"""Migration system for Beginnings framework.

This module provides comprehensive migration tools for:
- Database schema migrations
- Code migrations and refactoring
- Configuration migrations
- Extension migrations
- Framework migrations (Flask, Django, FastAPI to Beginnings)

The migration system supports:
- Forward and backward migrations
- Migration versioning and tracking
- Dry-run capabilities
- Rollback functionality
- Dependency resolution
- Cross-framework application migration
"""

from .base import BaseMigration, MigrationError
from .database import DatabaseMigration, DatabaseMigrationRunner
from .code import CodeMigration, CodeMigrationRunner
from .config import ConfigMigration, ConfigMigrationRunner
from .runner import MigrationRunner, MigrationResult
from .registry import MigrationRegistry
from .utils import MigrationUtils

# Framework migration components
from .framework import (
    MigrationFramework,
    MigrationConfig,
    MigrationStatus,
    ValidationResult,
    FrameworkType
)
from .converters import (
    FlaskConverter,
    DjangoConverter,
    FastAPIConverter
)

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
    
    # Framework migration
    'MigrationFramework',
    'MigrationConfig',
    'MigrationStatus',
    'ValidationResult',
    'FrameworkType',
    'FlaskConverter',
    'DjangoConverter',
    'FastAPIConverter',
]