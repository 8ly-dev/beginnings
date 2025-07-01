"""Code migration implementation for refactoring and updates."""

from __future__ import annotations

import ast
import re
import os
from typing import Any, Dict, List, Optional, Callable, Tuple
from pathlib import Path
import subprocess
from datetime import datetime

from .base import BaseMigration, MigrationError, MigrationExecutionError, MigrationRollbackError


class CodeMigration(BaseMigration):
    """Code migration for refactoring and code updates."""
    
    def __init__(
        self,
        migration_id: str,
        description: str,
        version: str,
        target_files: List[str],
        transformations: List[Dict[str, Any]],
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        backup_enabled: bool = True,
        syntax_check: bool = True
    ):
        """Initialize code migration.
        
        Args:
            migration_id: Unique migration identifier
            description: Migration description
            version: Migration version
            target_files: Files to be modified
            transformations: List of transformation rules
            dependencies: Migration dependencies
            tags: Migration tags
            backup_enabled: Whether to create backups
            syntax_check: Whether to validate syntax after changes
        """
        super().__init__(migration_id, description, version, dependencies, tags)
        self.target_files = target_files
        self.transformations = transformations
        self.backup_enabled = backup_enabled
        self.syntax_check = syntax_check
        self.backup_paths: Dict[str, str] = {}
    
    def validate(self) -> List[str]:
        """Validate code migration."""
        errors = []
        
        # Check if target files exist
        for file_path in self.target_files:
            path = Path(file_path)
            if not path.exists():
                errors.append(f"Target file does not exist: {file_path}")
            elif not path.is_file():
                errors.append(f"Target path is not a file: {file_path}")
            elif not os.access(path, os.R_OK | os.W_OK):
                errors.append(f"Insufficient permissions for file: {file_path}")
        
        # Validate transformation rules
        for i, transformation in enumerate(self.transformations):
            if not isinstance(transformation, dict):
                errors.append(f"Transformation {i} must be a dictionary")
                continue
            
            transform_type = transformation.get('type')
            if not transform_type:
                errors.append(f"Transformation {i} missing 'type' field")
            elif transform_type not in ['regex_replace', 'ast_transform', 'line_replace', 'import_update']:
                errors.append(f"Unknown transformation type: {transform_type}")
            
            # Validate specific transformation types
            if transform_type == 'regex_replace':
                if not transformation.get('pattern'):
                    errors.append(f"Regex transformation {i} missing 'pattern'")
                if 'replacement' not in transformation:
                    errors.append(f"Regex transformation {i} missing 'replacement'")
                
                # Test regex pattern
                try:
                    re.compile(transformation['pattern'])
                except re.error as e:
                    errors.append(f"Invalid regex pattern in transformation {i}: {e}")
        
        return errors
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code migration."""
        dry_run = context.get('dry_run', False)
        project_root = context.get('project_root', '.')
        
        if dry_run:
            return await self._dry_run_preview(context)
        
        start_time = datetime.utcnow()
        results = {
            "files_modified": [],
            "backups_created": [],
            "transformations_applied": 0,
            "errors": []
        }
        
        try:
            # Create backups if enabled
            if self.backup_enabled:
                await self._create_backups(project_root, results)
            
            # Apply transformations
            for file_path in self.target_files:
                full_path = Path(project_root) / file_path
                try:
                    modified = await self._apply_transformations(full_path)
                    if modified:
                        results["files_modified"].append(str(file_path))
                        
                        # Syntax check if enabled
                        if self.syntax_check and file_path.endswith('.py'):
                            await self._validate_python_syntax(full_path)
                        
                except Exception as e:
                    error_msg = f"Failed to transform {file_path}: {e}"
                    results["errors"].append(error_msg)
                    # Restore backup if error occurred
                    if self.backup_enabled and str(file_path) in self.backup_paths:
                        await self._restore_backup(file_path)
            
            results["transformations_applied"] = len(self.transformations) * len(results["files_modified"])
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.execution_time_ms = execution_time
            
            return results
            
        except Exception as e:
            # Restore all backups if major error
            if self.backup_enabled:
                await self._restore_all_backups()
            raise MigrationExecutionError(f"Code migration failed: {e}")
    
    async def rollback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback code migration."""
        if not self.can_rollback():
            raise MigrationRollbackError(f"Migration {self.migration_id} cannot be rolled back")
        
        dry_run = context.get('dry_run', False)
        
        if dry_run:
            return {
                "dry_run": True,
                "preview": f"Rollback {self.migration_id}: Restore from backups",
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
            raise MigrationRollbackError(f"Failed to rollback code migration: {e}")
    
    def can_rollback(self) -> bool:
        """Check if migration can be rolled back."""
        return self.backup_enabled and bool(self.backup_paths)
    
    def get_dry_run_preview(self, context: Dict[str, Any]) -> str:
        """Get preview of code changes."""
        preview = f"Code Migration {self.migration_id}: {self.description}\n"
        preview += f"Files to modify: {', '.join(self.target_files)}\n"
        preview += f"Transformations:\n"
        
        for i, transform in enumerate(self.transformations):
            transform_type = transform.get('type', 'unknown')
            preview += f"  {i+1}. {transform_type}"
            
            if transform_type == 'regex_replace':
                preview += f": s/{transform.get('pattern', '')}/"
                preview += f"{transform.get('replacement', '')}/g"
            elif transform_type == 'import_update':
                preview += f": {transform.get('old_import', '')} -> "
                preview += f"{transform.get('new_import', '')}"
            
            preview += "\n"
        
        return preview
    
    def get_estimated_duration(self) -> Optional[float]:
        """Estimate migration duration."""
        # Rough estimation: 0.5 seconds per file per transformation
        return len(self.target_files) * len(self.transformations) * 0.5
    
    def requires_downtime(self) -> bool:
        """Check if migration requires downtime."""
        # Code migrations typically don't require downtime
        return False
    
    def get_affected_components(self) -> List[str]:
        """Get affected code components."""
        components = []
        
        for file_path in self.target_files:
            # Extract module/package names from file paths
            if file_path.endswith('.py'):
                module_path = file_path.replace('/', '.').replace('.py', '')
                components.append(module_path)
            else:
                components.append(file_path)
        
        return components
    
    async def _dry_run_preview(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dry run preview."""
        project_root = context.get('project_root', '.')
        preview_results = {
            "dry_run": True,
            "preview": self.get_dry_run_preview(context),
            "files_to_modify": self.target_files,
            "transformations": [],
            "changes_preview": []
        }
        
        # Generate preview of actual changes
        for file_path in self.target_files:
            full_path = Path(project_root) / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    modified_content = await self._apply_transformations_to_content(content)
                    
                    if content != modified_content:
                        # Generate diff-like preview
                        changes = self._generate_diff_preview(content, modified_content)
                        preview_results["changes_preview"].append({
                            "file": str(file_path),
                            "changes": changes
                        })
                except Exception as e:
                    preview_results["changes_preview"].append({
                        "file": str(file_path),
                        "error": str(e)
                    })
        
        return preview_results
    
    async def _create_backups(self, project_root: str, results: Dict[str, Any]):
        """Create backup files."""
        backup_dir = Path(project_root) / '.beginnings_migration_backups' / self.migration_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in self.target_files:
            source_path = Path(project_root) / file_path
            if source_path.exists():
                backup_path = backup_dir / f"{Path(file_path).name}.backup"
                backup_path.write_bytes(source_path.read_bytes())
                
                self.backup_paths[str(file_path)] = str(backup_path)
                results["backups_created"].append(str(backup_path))
    
    async def _apply_transformations(self, file_path: Path) -> bool:
        """Apply transformations to a file."""
        if not file_path.exists():
            return False
        
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        content = await self._apply_transformations_to_content(content)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
        
        return False
    
    async def _apply_transformations_to_content(self, content: str) -> str:
        """Apply transformations to content string."""
        for transformation in self.transformations:
            transform_type = transformation['type']
            
            if transform_type == 'regex_replace':
                pattern = transformation['pattern']
                replacement = transformation['replacement']
                flags = transformation.get('flags', 0)
                content = re.sub(pattern, replacement, content, flags=flags)
            
            elif transform_type == 'line_replace':
                old_line = transformation['old_line']
                new_line = transformation['new_line']
                content = content.replace(old_line, new_line)
            
            elif transform_type == 'import_update':
                old_import = transformation['old_import']
                new_import = transformation['new_import']
                content = self._update_imports(content, old_import, new_import)
            
            elif transform_type == 'ast_transform':
                content = await self._apply_ast_transformation(content, transformation)
        
        return content
    
    def _update_imports(self, content: str, old_import: str, new_import: str) -> str:
        """Update import statements."""
        # Handle various import formats
        patterns = [
            (f"^import {re.escape(old_import)}$", f"import {new_import}"),
            (f"^from {re.escape(old_import)} import", f"from {new_import} import"),
            (f"import {re.escape(old_import)} as", f"import {new_import} as")
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        return content
    
    async def _apply_ast_transformation(self, content: str, transformation: Dict[str, Any]) -> str:
        """Apply AST-based transformation."""
        try:
            tree = ast.parse(content)
            # This would require implementing specific AST transformers
            # For now, return content unchanged
            return content
        except SyntaxError:
            # If content has syntax errors, skip AST transformation
            return content
    
    async def _validate_python_syntax(self, file_path: Path):
        """Validate Python syntax."""
        try:
            content = file_path.read_text(encoding='utf-8')
            ast.parse(content)
        except SyntaxError as e:
            raise MigrationExecutionError(f"Syntax error in {file_path}: {e}")
    
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
    
    def _generate_diff_preview(self, original: str, modified: str) -> List[str]:
        """Generate a simple diff preview."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        diff = []
        max_lines = max(len(original_lines), len(modified_lines))
        
        for i in range(max_lines):
            orig_line = original_lines[i] if i < len(original_lines) else ""
            mod_line = modified_lines[i] if i < len(modified_lines) else ""
            
            if orig_line != mod_line:
                if orig_line:
                    diff.append(f"- {orig_line}")
                if mod_line:
                    diff.append(f"+ {mod_line}")
        
        return diff[:20]  # Limit preview to 20 lines
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CodeMigration:
        """Create migration from dictionary."""
        return cls(
            migration_id=data["migration_id"],
            description=data["description"],
            version=data["version"],
            target_files=data["target_files"],
            transformations=data["transformations"],
            dependencies=data.get("dependencies"),
            tags=data.get("tags"),
            backup_enabled=data.get("backup_enabled", True),
            syntax_check=data.get("syntax_check", True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data.update({
            "type": "code",
            "target_files": self.target_files,
            "transformations": self.transformations,
            "backup_enabled": self.backup_enabled,
            "syntax_check": self.syntax_check,
            "backup_paths": self.backup_paths
        })
        return data


class CodeMigrationRunner:
    """Runner for code migrations."""
    
    def __init__(self, project_root: str = "."):
        """Initialize runner.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
    
    async def run_migration(
        self, 
        migration: CodeMigration, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Run a code migration.
        
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
        migration: CodeMigration, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Rollback a code migration.
        
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