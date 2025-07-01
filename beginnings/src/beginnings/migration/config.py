"""Configuration migration implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime
import copy

try:
    import yaml
except ImportError:
    yaml = None

try:
    import toml
except ImportError:
    toml = None

from .base import BaseMigration, MigrationError, MigrationExecutionError, MigrationRollbackError


class ConfigMigration(BaseMigration):
    """Configuration migration for updating config files and formats."""
    
    def __init__(
        self,
        migration_id: str,
        description: str,
        version: str,
        config_files: List[str],
        transformations: List[Dict[str, Any]],
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        backup_enabled: bool = True,
        validate_schema: bool = True
    ):
        """Initialize config migration.
        
        Args:
            migration_id: Unique migration identifier
            description: Migration description
            version: Migration version
            config_files: Configuration files to modify
            transformations: List of transformation rules
            dependencies: Migration dependencies
            tags: Migration tags
            backup_enabled: Whether to create backups
            validate_schema: Whether to validate config schema
        """
        super().__init__(migration_id, description, version, dependencies, tags)
        self.config_files = config_files
        self.transformations = transformations
        self.backup_enabled = backup_enabled
        self.validate_schema = validate_schema
        self.backup_paths: Dict[str, str] = {}
    
    def validate(self) -> List[str]:
        """Validate config migration."""
        errors = []
        
        # Check if config files exist
        for config_file in self.config_files:
            path = Path(config_file)
            if not path.exists():
                errors.append(f"Config file does not exist: {config_file}")
            elif not path.is_file():
                errors.append(f"Config path is not a file: {config_file}")
        
        # Validate transformation rules
        for i, transformation in enumerate(self.transformations):
            if not isinstance(transformation, dict):
                errors.append(f"Transformation {i} must be a dictionary")
                continue
            
            transform_type = transformation.get('type')
            if not transform_type:
                errors.append(f"Transformation {i} missing 'type' field")
            elif transform_type not in [
                'add_key', 'remove_key', 'update_key', 'rename_key', 
                'restructure', 'format_change', 'schema_update'
            ]:
                errors.append(f"Unknown transformation type: {transform_type}")
            
            # Validate specific transformation requirements
            if transform_type in ['add_key', 'update_key'] and 'value' not in transformation:
                errors.append(f"Transformation {i} missing 'value' field")
            
            if transform_type in ['remove_key', 'update_key', 'rename_key'] and 'key' not in transformation:
                errors.append(f"Transformation {i} missing 'key' field")
            
            if transform_type == 'rename_key' and 'new_key' not in transformation:
                errors.append(f"Transformation {i} missing 'new_key' field")
        
        return errors
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute config migration."""
        dry_run = context.get('dry_run', False)
        project_root = context.get('project_root', '.')
        
        if dry_run:
            return await self._dry_run_preview(context)
        
        start_time = datetime.utcnow()
        results = {
            "files_modified": [],
            "backups_created": [],
            "transformations_applied": 0,
            "errors": [],
            "schema_changes": []
        }
        
        try:
            # Create backups if enabled
            if self.backup_enabled:
                await self._create_backups(project_root, results)
            
            # Apply transformations to each config file
            for config_file in self.config_files:
                full_path = Path(project_root) / config_file
                try:
                    modified = await self._apply_config_transformations(full_path, results)
                    if modified:
                        results["files_modified"].append(str(config_file))
                        
                        # Validate config after changes if enabled
                        if self.validate_schema:
                            await self._validate_config_schema(full_path)
                        
                except Exception as e:
                    error_msg = f"Failed to transform {config_file}: {e}"
                    results["errors"].append(error_msg)
                    # Restore backup if error occurred
                    if self.backup_enabled and str(config_file) in self.backup_paths:
                        await self._restore_backup(config_file)
            
            results["transformations_applied"] = len(self.transformations) * len(results["files_modified"])
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.execution_time_ms = execution_time
            
            return results
            
        except Exception as e:
            # Restore all backups if major error
            if self.backup_enabled:
                await self._restore_all_backups()
            raise MigrationExecutionError(f"Config migration failed: {e}")
    
    async def rollback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback config migration."""
        if not self.can_rollback():
            raise MigrationRollbackError(f"Migration {self.migration_id} cannot be rolled back")
        
        dry_run = context.get('dry_run', False)
        
        if dry_run:
            return {
                "dry_run": True,
                "preview": f"Rollback {self.migration_id}: Restore config files from backups",
                "files_to_restore": list(self.backup_paths.keys())
            }
        
        results = {
            "files_restored": [],
            "errors": []
        }
        
        try:
            for file_path, backup_path in self.backup_paths.items():
                try:
                    await self._restore_backup(file_path, backup_path)
                    results["files_restored"].append(file_path)
                except Exception as e:
                    results["errors"].append(f"Failed to restore {file_path}: {e}")
            
            return results
            
        except Exception as e:
            raise MigrationRollbackError(f"Failed to rollback config migration: {e}")
    
    def can_rollback(self) -> bool:
        """Check if migration can be rolled back."""
        return self.backup_enabled and bool(self.backup_paths)
    
    def get_dry_run_preview(self, context: Dict[str, Any]) -> str:
        """Get preview of config changes."""
        preview = f"Config Migration {self.migration_id}: {self.description}\n"
        preview += f"Config files to modify: {', '.join(self.config_files)}\n"
        preview += f"Transformations:\n"
        
        for i, transform in enumerate(self.transformations):
            transform_type = transform.get('type', 'unknown')
            preview += f"  {i+1}. {transform_type}"
            
            if transform_type == 'add_key':
                preview += f": Add {transform.get('key', '')} = {transform.get('value', '')}"
            elif transform_type == 'remove_key':
                preview += f": Remove {transform.get('key', '')}"
            elif transform_type == 'update_key':
                preview += f": Update {transform.get('key', '')} = {transform.get('value', '')}"
            elif transform_type == 'rename_key':
                preview += f": Rename {transform.get('key', '')} -> {transform.get('new_key', '')}"
            elif transform_type == 'format_change':
                preview += f": Change format from {transform.get('from_format', '')} to {transform.get('to_format', '')}"
            
            preview += "\n"
        
        return preview
    
    def get_estimated_duration(self) -> Optional[float]:
        """Estimate migration duration."""
        # Rough estimation: 0.2 seconds per file per transformation
        return len(self.config_files) * len(self.transformations) * 0.2
    
    def requires_downtime(self) -> bool:
        """Check if migration requires downtime."""
        # Config migrations typically require restart but not immediate downtime
        return False
    
    def get_affected_components(self) -> List[str]:
        """Get affected configuration components."""
        components = []
        
        for config_file in self.config_files:
            # Extract component names from config file paths
            file_name = Path(config_file).stem
            components.append(f"config:{file_name}")
        
        # Add components affected by specific transformations
        for transform in self.transformations:
            if 'component' in transform:
                components.append(transform['component'])
        
        return list(set(components))
    
    async def _dry_run_preview(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dry run preview."""
        project_root = context.get('project_root', '.')
        preview_results = {
            "dry_run": True,
            "preview": self.get_dry_run_preview(context),
            "files_to_modify": self.config_files,
            "transformations": self.transformations,
            "changes_preview": []
        }
        
        # Generate preview of actual changes
        for config_file in self.config_files:
            full_path = Path(project_root) / config_file
            if full_path.exists():
                try:
                    original_config = await self._load_config(full_path)
                    modified_config = await self._apply_transformations_to_config(original_config, full_path)
                    
                    if original_config != modified_config:
                        changes = self._generate_config_diff(original_config, modified_config)
                        preview_results["changes_preview"].append({
                            "file": str(config_file),
                            "changes": changes
                        })
                except Exception as e:
                    preview_results["changes_preview"].append({
                        "file": str(config_file),
                        "error": str(e)
                    })
        
        return preview_results
    
    async def _create_backups(self, project_root: str, results: Dict[str, Any]):
        """Create backup files."""
        backup_dir = Path(project_root) / '.beginnings_migration_backups' / self.migration_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for config_file in self.config_files:
            source_path = Path(project_root) / config_file
            if source_path.exists():
                backup_path = backup_dir / f"{Path(config_file).name}.backup"
                backup_path.write_bytes(source_path.read_bytes())
                
                self.backup_paths[str(config_file)] = str(backup_path)
                results["backups_created"].append(str(backup_path))
    
    async def _apply_config_transformations(self, config_path: Path, results: Dict[str, Any]) -> bool:
        """Apply transformations to a config file."""
        if not config_path.exists():
            return False
        
        original_config = await self._load_config(config_path)
        modified_config = await self._apply_transformations_to_config(original_config, config_path)
        
        if original_config != modified_config:
            await self._save_config(config_path, modified_config)
            return True
        
        return False
    
    async def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        suffix = config_path.suffix.lower()
        content = config_path.read_text(encoding='utf-8')
        
        if suffix == '.json':
            return json.loads(content)
        elif suffix in ['.yml', '.yaml']:
            if yaml:
                return yaml.safe_load(content) or {}
            else:
                raise MigrationExecutionError(f"YAML support not available (install PyYAML): {config_path}")
        elif suffix == '.toml':
            if toml:
                return toml.loads(content)
            else:
                raise MigrationExecutionError(f"TOML support not available (install toml): {config_path}")
        elif suffix in ['.ini', '.cfg']:
            # Simple INI-style parsing
            return self._parse_ini(content)
        else:
            # Try to detect format from content
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if yaml:
                    try:
                        return yaml.safe_load(content) or {}
                    except yaml.YAMLError:
                        raise MigrationExecutionError(f"Unknown config format: {config_path}")
                else:
                    raise MigrationExecutionError(f"Unknown config format: {config_path}")
    
    async def _save_config(self, config_path: Path, config_data: Dict[str, Any]):
        """Save configuration to file."""
        suffix = config_path.suffix.lower()
        
        if suffix == '.json':
            content = json.dumps(config_data, indent=2, sort_keys=True)
        elif suffix in ['.yml', '.yaml']:
            if yaml:
                content = yaml.dump(config_data, default_flow_style=False, sort_keys=True)
            else:
                raise MigrationExecutionError(f"YAML support not available (install PyYAML): {config_path}")
        elif suffix == '.toml':
            if toml:
                content = toml.dumps(config_data)
            else:
                raise MigrationExecutionError(f"TOML support not available (install toml): {config_path}")
        elif suffix in ['.ini', '.cfg']:
            content = self._format_ini(config_data)
        else:
            # Default to JSON
            content = json.dumps(config_data, indent=2, sort_keys=True)
        
        config_path.write_text(content, encoding='utf-8')
    
    async def _apply_transformations_to_config(
        self, 
        config: Dict[str, Any], 
        config_path: Path
    ) -> Dict[str, Any]:
        """Apply transformations to config data."""
        modified_config = copy.deepcopy(config)
        
        for transformation in self.transformations:
            transform_type = transformation['type']
            
            if transform_type == 'add_key':
                key = transformation['key']
                value = transformation['value']
                self._set_nested_key(modified_config, key, value)
            
            elif transform_type == 'remove_key':
                key = transformation['key']
                self._remove_nested_key(modified_config, key)
            
            elif transform_type == 'update_key':
                key = transformation['key']
                value = transformation['value']
                if self._has_nested_key(modified_config, key):
                    self._set_nested_key(modified_config, key, value)
            
            elif transform_type == 'rename_key':
                old_key = transformation['key']
                new_key = transformation['new_key']
                if self._has_nested_key(modified_config, old_key):
                    value = self._get_nested_key(modified_config, old_key)
                    self._remove_nested_key(modified_config, old_key)
                    self._set_nested_key(modified_config, new_key, value)
            
            elif transform_type == 'restructure':
                mappings = transformation.get('mappings', {})
                modified_config = self._restructure_config(modified_config, mappings)
            
            elif transform_type == 'format_change':
                # Format changes are handled in save/load methods
                pass
            
            elif transform_type == 'schema_update':
                schema_changes = transformation.get('schema_changes', {})
                modified_config = self._apply_schema_changes(modified_config, schema_changes)
        
        return modified_config
    
    def _set_nested_key(self, config: Dict[str, Any], key: str, value: Any):
        """Set a nested key in config."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _get_nested_key(self, config: Dict[str, Any], key: str) -> Any:
        """Get a nested key from config."""
        keys = key.split('.')
        current = config
        
        for k in keys:
            current = current[k]
        
        return current
    
    def _has_nested_key(self, config: Dict[str, Any], key: str) -> bool:
        """Check if nested key exists in config."""
        try:
            self._get_nested_key(config, key)
            return True
        except (KeyError, TypeError):
            return False
    
    def _remove_nested_key(self, config: Dict[str, Any], key: str):
        """Remove a nested key from config."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            current = current[k]
        
        if keys[-1] in current:
            del current[keys[-1]]
    
    def _restructure_config(
        self, 
        config: Dict[str, Any], 
        mappings: Dict[str, str]
    ) -> Dict[str, Any]:
        """Restructure config based on key mappings."""
        new_config = {}
        
        for old_key, new_key in mappings.items():
            if self._has_nested_key(config, old_key):
                value = self._get_nested_key(config, old_key)
                self._set_nested_key(new_config, new_key, value)
        
        # Add unmapped keys
        for key, value in config.items():
            if key not in mappings:
                new_config[key] = value
        
        return new_config
    
    def _apply_schema_changes(
        self, 
        config: Dict[str, Any], 
        schema_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply schema changes to config."""
        # This would implement more complex schema transformations
        # For now, just return the config unchanged
        return config
    
    def _parse_ini(self, content: str) -> Dict[str, Any]:
        """Simple INI parser."""
        config = {}
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                config[current_section] = {}
            elif '=' in line and current_section:
                key, value = line.split('=', 1)
                config[current_section][key.strip()] = value.strip()
        
        return config
    
    def _format_ini(self, config: Dict[str, Any]) -> str:
        """Format config as INI."""
        lines = []
        
        for section, values in config.items():
            lines.append(f"[{section}]")
            for key, value in values.items():
                lines.append(f"{key} = {value}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_config_diff(
        self, 
        original: Dict[str, Any], 
        modified: Dict[str, Any]
    ) -> List[str]:
        """Generate a diff between config states."""
        diff = []
        
        # Find added/modified keys
        for key, value in modified.items():
            if key not in original:
                diff.append(f"+ {key}: {value}")
            elif original[key] != value:
                diff.append(f"~ {key}: {original[key]} -> {value}")
        
        # Find removed keys
        for key in original:
            if key not in modified:
                diff.append(f"- {key}: {original[key]}")
        
        return diff[:20]  # Limit to 20 changes
    
    async def _validate_config_schema(self, config_path: Path):
        """Validate config schema after changes."""
        # This would implement schema validation
        # For now, just check if the file can be loaded
        try:
            await self._load_config(config_path)
        except Exception as e:
            raise MigrationExecutionError(f"Config validation failed for {config_path}: {e}")
    
    async def _restore_backup(self, file_path: str, backup_path: Optional[str] = None):
        """Restore file from backup."""
        if backup_path is None:
            backup_path = self.backup_paths.get(file_path)
        
        if backup_path and Path(backup_path).exists():
            source_path = Path(file_path)
            source_path.write_bytes(Path(backup_path).read_bytes())
    
    async def _restore_all_backups(self):
        """Restore all backed up files."""
        for file_path, backup_path in self.backup_paths.items():
            await self._restore_backup(file_path, backup_path)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConfigMigration:
        """Create migration from dictionary."""
        return cls(
            migration_id=data["migration_id"],
            description=data["description"],
            version=data["version"],
            config_files=data["config_files"],
            transformations=data["transformations"],
            dependencies=data.get("dependencies"),
            tags=data.get("tags"),
            backup_enabled=data.get("backup_enabled", True),
            validate_schema=data.get("validate_schema", True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data.update({
            "type": "config",
            "config_files": self.config_files,
            "transformations": self.transformations,
            "backup_enabled": self.backup_enabled,
            "validate_schema": self.validate_schema,
            "backup_paths": self.backup_paths
        })
        return data


class ConfigMigrationRunner:
    """Runner for config migrations."""
    
    def __init__(self, project_root: str = "."):
        """Initialize runner.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
    
    async def run_migration(
        self, 
        migration: ConfigMigration, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Run a config migration.
        
        Args:
            migration: Migration to run
            dry_run: Whether to perform dry run
            
        Returns:
            Migration result
        """
        context = {
            "project_root": self.project_root,
            "dry_run": dry_run
        }
        
        return await migration.execute(context)
    
    async def rollback_migration(
        self, 
        migration: ConfigMigration, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Rollback a config migration.
        
        Args:
            migration: Migration to rollback
            dry_run: Whether to perform dry run
            
        Returns:
            Rollback result
        """
        context = {
            "project_root": self.project_root,
            "dry_run": dry_run
        }
        
        return await migration.rollback(context)