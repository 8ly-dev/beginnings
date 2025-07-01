"""Migration registry for discovering and managing migrations."""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Type, Union
from pathlib import Path
import importlib.util
import inspect
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

from .base import BaseMigration, MigrationError
from .database import DatabaseMigration
from .code import CodeMigration
from .config import ConfigMigration


class MigrationRegistry:
    """Registry for discovering and managing migrations."""
    
    def __init__(self, migration_paths: Optional[List[str]] = None):
        """Initialize migration registry.
        
        Args:
            migration_paths: Directories to search for migrations
        """
        self.migration_paths = migration_paths or ["migrations"]
        self.migrations: Dict[str, BaseMigration] = {}
        self.migration_files: Dict[str, str] = {}
        
    def register_migration(self, migration: BaseMigration, file_path: Optional[str] = None):
        """Register a migration.
        
        Args:
            migration: Migration to register
            file_path: Source file path (optional)
        """
        if migration.migration_id in self.migrations:
            raise MigrationError(f"Migration {migration.migration_id} already registered")
        
        self.migrations[migration.migration_id] = migration
        if file_path:
            self.migration_files[migration.migration_id] = file_path
    
    def get_migration(self, migration_id: str) -> BaseMigration:
        """Get migration by ID.
        
        Args:
            migration_id: Migration identifier
            
        Returns:
            Migration instance
            
        Raises:
            MigrationError: If migration not found
        """
        if migration_id not in self.migrations:
            raise MigrationError(f"Migration not found: {migration_id}")
        
        return self.migrations[migration_id]
    
    def get_all_migrations(self) -> List[BaseMigration]:
        """Get all registered migrations.
        
        Returns:
            List of all migrations
        """
        return list(self.migrations.values())
    
    def get_migrations_by_type(self, migration_type: Type[BaseMigration]) -> List[BaseMigration]:
        """Get migrations of specific type.
        
        Args:
            migration_type: Migration class type
            
        Returns:
            List of migrations of the specified type
        """
        return [m for m in self.migrations.values() if isinstance(m, migration_type)]
    
    def get_migrations_by_tag(self, tag: str) -> List[BaseMigration]:
        """Get migrations with specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of migrations with the tag
        """
        return [m for m in self.migrations.values() if tag in m.tags]
    
    def get_migrations_by_version_range(
        self, 
        min_version: Optional[str] = None, 
        max_version: Optional[str] = None
    ) -> List[BaseMigration]:
        """Get migrations within version range.
        
        Args:
            min_version: Minimum version (inclusive)
            max_version: Maximum version (inclusive)
            
        Returns:
            List of migrations in the version range
        """
        migrations = []
        
        for migration in self.migrations.values():
            if min_version and migration.version < min_version:
                continue
            if max_version and migration.version > max_version:
                continue
            migrations.append(migration)
        
        return migrations
    
    async def discover_migrations(self, auto_register: bool = True) -> List[BaseMigration]:
        """Discover migrations from configured paths.
        
        Args:
            auto_register: Whether to automatically register discovered migrations
            
        Returns:
            List of discovered migrations
        """
        discovered_migrations = []
        
        for migration_path in self.migration_paths:
            path = Path(migration_path)
            if not path.exists():
                continue
            
            # Discover different types of migration files
            discovered_migrations.extend(await self._discover_python_migrations(path, auto_register))
            discovered_migrations.extend(await self._discover_sql_migrations(path, auto_register))
            discovered_migrations.extend(await self._discover_yaml_migrations(path, auto_register))
            discovered_migrations.extend(await self._discover_json_migrations(path, auto_register))
        
        return discovered_migrations
    
    async def _discover_python_migrations(self, path: Path, auto_register: bool) -> List[BaseMigration]:
        """Discover Python migration files."""
        migrations = []
        
        for py_file in path.glob("**/*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                # Load the Python module
                spec = importlib.util.spec_from_file_location("migration", py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for migration classes
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, BaseMigration) and 
                            obj != BaseMigration and 
                            not inspect.isabstract(obj)):
                            
                            # Try to instantiate the migration
                            try:
                                # Look for a create_migration function or use default constructor
                                if hasattr(module, 'create_migration'):
                                    migration = module.create_migration()
                                else:
                                    # Try to create with minimal parameters
                                    migration = obj(
                                        migration_id=py_file.stem,
                                        description=f"Migration from {py_file.name}",
                                        version="1.0.0"
                                    )
                                
                                migrations.append(migration)
                                
                                if auto_register:
                                    self.register_migration(migration, str(py_file))
                                    
                            except Exception as e:
                                # Skip migrations that can't be instantiated
                                continue
                        
            except Exception as e:
                # Skip files that can't be loaded
                continue
        
        return migrations
    
    async def _discover_sql_migrations(self, path: Path, auto_register: bool) -> List[BaseMigration]:
        """Discover SQL migration files."""
        migrations = []
        
        for sql_file in path.glob("**/*.sql"):
            try:
                migration = await self._create_sql_migration(sql_file)
                if migration:
                    migrations.append(migration)
                    
                    if auto_register:
                        self.register_migration(migration, str(sql_file))
                        
            except Exception as e:
                # Skip invalid SQL files
                continue
        
        return migrations
    
    async def _discover_yaml_migrations(self, path: Path, auto_register: bool) -> List[BaseMigration]:
        """Discover YAML migration files."""
        migrations = []
        
        for yaml_file in path.glob("**/*.yml") + path.glob("**/*.yaml"):
            try:
                migration = await self._create_yaml_migration(yaml_file)
                if migration:
                    migrations.append(migration)
                    
                    if auto_register:
                        self.register_migration(migration, str(yaml_file))
                        
            except Exception as e:
                # Skip invalid YAML files
                continue
        
        return migrations
    
    async def _discover_json_migrations(self, path: Path, auto_register: bool) -> List[BaseMigration]:
        """Discover JSON migration files."""
        migrations = []
        
        for json_file in path.glob("**/*.json"):
            try:
                migration = await self._create_json_migration(json_file)
                if migration:
                    migrations.append(migration)
                    
                    if auto_register:
                        self.register_migration(migration, str(json_file))
                        
            except Exception as e:
                # Skip invalid JSON files
                continue
        
        return migrations
    
    async def _create_sql_migration(self, sql_file: Path) -> Optional[DatabaseMigration]:
        """Create database migration from SQL file."""
        content = sql_file.read_text(encoding='utf-8')
        
        # Look for migration metadata in comments
        metadata = self._parse_sql_metadata(content)
        
        # Look for UP/DOWN sections
        up_sql, down_sql = self._parse_sql_sections(content)
        
        if not up_sql:
            up_sql = content
        
        migration_id = metadata.get('id', sql_file.stem)
        description = metadata.get('description', f"Database migration from {sql_file.name}")
        version = metadata.get('version', '1.0.0')
        
        return DatabaseMigration(
            migration_id=migration_id,
            description=description,
            version=version,
            up_sql=up_sql,
            down_sql=down_sql,
            dependencies=metadata.get('dependencies', []),
            tags=metadata.get('tags', [])
        )
    
    async def _create_yaml_migration(self, yaml_file: Path) -> Optional[BaseMigration]:
        """Create migration from YAML file."""
        if not yaml:
            return None
        
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)
        
        if not isinstance(data, dict):
            return None
        
        migration_type = data.get('type', 'database')
        
        if migration_type == 'database':
            return DatabaseMigration.from_dict(data)
        elif migration_type == 'code':
            return CodeMigration.from_dict(data)
        elif migration_type == 'config':
            return ConfigMigration.from_dict(data)
        
        return None
    
    async def _create_json_migration(self, json_file: Path) -> Optional[BaseMigration]:
        """Create migration from JSON file."""
        content = json_file.read_text(encoding='utf-8')
        data = json.loads(content)
        
        if not isinstance(data, dict):
            return None
        
        migration_type = data.get('type', 'database')
        
        if migration_type == 'database':
            return DatabaseMigration.from_dict(data)
        elif migration_type == 'code':
            return CodeMigration.from_dict(data)
        elif migration_type == 'config':
            return ConfigMigration.from_dict(data)
        
        return None
    
    def _parse_sql_metadata(self, content: str) -> Dict[str, Any]:
        """Parse metadata from SQL comments."""
        metadata = {}
        
        # Look for metadata in header comments
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('-- @'):
                # Parse metadata line: -- @key: value
                if ':' in line:
                    key_part, value_part = line[4:].split(':', 1)
                    key = key_part.strip()
                    value = value_part.strip()
                    
                    # Handle special cases
                    if key in ['dependencies', 'tags'] and ',' in value:
                        metadata[key] = [v.strip() for v in value.split(',')]
                    else:
                        metadata[key] = value
            elif line and not line.startswith('--'):
                # Stop parsing metadata at first non-comment line
                break
        
        return metadata
    
    def _parse_sql_sections(self, content: str) -> tuple[str, Optional[str]]:
        """Parse UP and DOWN sections from SQL content."""
        # Look for section markers
        up_start = content.find('-- UP')
        down_start = content.find('-- DOWN')
        
        if up_start == -1 and down_start == -1:
            # No sections found, entire content is UP
            return content, None
        
        up_sql = ""
        down_sql = None
        
        if up_start != -1:
            if down_start != -1:
                up_sql = content[up_start:down_start].replace('-- UP', '').strip()
                down_sql = content[down_start:].replace('-- DOWN', '').strip()
            else:
                up_sql = content[up_start:].replace('-- UP', '').strip()
        elif down_start != -1:
            up_sql = content[:down_start].strip()
            down_sql = content[down_start:].replace('-- DOWN', '').strip()
        
        return up_sql, down_sql if down_sql else None
    
    def list_migrations(self, verbose: bool = False) -> str:
        """List all registered migrations.
        
        Args:
            verbose: Whether to include detailed information
            
        Returns:
            Formatted string of migrations
        """
        if not self.migrations:
            return "No migrations registered"
        
        lines = []
        migrations = sorted(self.migrations.values(), key=lambda m: m.version)
        
        if verbose:
            lines.append("Registered Migrations:")
            lines.append("=" * 50)
            
            for migration in migrations:
                lines.append(f"ID: {migration.migration_id}")
                lines.append(f"  Description: {migration.description}")
                lines.append(f"  Version: {migration.version}")
                lines.append(f"  Type: {type(migration).__name__}")
                lines.append(f"  Status: {migration.status.value}")
                lines.append(f"  Dependencies: {', '.join(migration.dependencies) if migration.dependencies else 'None'}")
                lines.append(f"  Tags: {', '.join(migration.tags) if migration.tags else 'None'}")
                lines.append(f"  Can rollback: {migration.can_rollback()}")
                lines.append(f"  Requires downtime: {migration.requires_downtime()}")
                
                if migration.migration_id in self.migration_files:
                    lines.append(f"  Source: {self.migration_files[migration.migration_id]}")
                
                lines.append("")
        else:
            lines.append(f"{'ID':<30} {'Version':<10} {'Type':<15} {'Status':<10} {'Description'}")
            lines.append("-" * 90)
            
            for migration in migrations:
                migration_type = type(migration).__name__.replace('Migration', '')
                lines.append(
                    f"{migration.migration_id:<30} "
                    f"{migration.version:<10} "
                    f"{migration_type:<15} "
                    f"{migration.status.value:<10} "
                    f"{migration.description}"
                )
        
        return '\n'.join(lines)
    
    def export_migrations(self, format: str = 'json') -> str:
        """Export migrations to specified format.
        
        Args:
            format: Export format ('json' or 'yaml')
            
        Returns:
            Serialized migrations
        """
        migrations_data = [m.to_dict() for m in self.migrations.values()]
        
        if format.lower() == 'json':
            return json.dumps(migrations_data, indent=2)
        elif format.lower() == 'yaml':
            if yaml:
                return yaml.dump(migrations_data, default_flow_style=False)
            else:
                raise MigrationError("YAML support not available (install PyYAML)")
        else:
            raise MigrationError(f"Unsupported export format: {format}")
    
    def import_migrations(self, data: str, format: str = 'json'):
        """Import migrations from serialized data.
        
        Args:
            data: Serialized migration data
            format: Data format ('json' or 'yaml')
        """
        if format.lower() == 'json':
            migrations_data = json.loads(data)
        elif format.lower() == 'yaml':
            if yaml:
                migrations_data = yaml.safe_load(data)
            else:
                raise MigrationError("YAML support not available (install PyYAML)")
        else:
            raise MigrationError(f"Unsupported import format: {format}")
        
        for migration_data in migrations_data:
            migration_type = migration_data.get('type', 'database')
            
            if migration_type == 'database':
                migration = DatabaseMigration.from_dict(migration_data)
            elif migration_type == 'code':
                migration = CodeMigration.from_dict(migration_data)
            elif migration_type == 'config':
                migration = ConfigMigration.from_dict(migration_data)
            else:
                continue  # Skip unknown types
            
            self.register_migration(migration)
    
    def clear(self):
        """Clear all registered migrations."""
        self.migrations.clear()
        self.migration_files.clear()
    
    def remove_migration(self, migration_id: str):
        """Remove a migration from registry.
        
        Args:
            migration_id: Migration ID to remove
        """
        if migration_id in self.migrations:
            del self.migrations[migration_id]
        
        if migration_id in self.migration_files:
            del self.migration_files[migration_id]