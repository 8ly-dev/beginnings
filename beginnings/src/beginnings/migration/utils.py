"""Migration utilities and helper functions."""

from __future__ import annotations

import os
import shutil
import hashlib
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import zipfile
import json

from .base import BaseMigration, MigrationError


class MigrationUtils:
    """Utility functions for migration operations."""
    
    @staticmethod
    def generate_migration_id(description: str, timestamp: Optional[datetime] = None) -> str:
        """Generate a migration ID from description and timestamp.
        
        Args:
            description: Migration description
            timestamp: Optional timestamp (uses current time if None)
            
        Returns:
            Generated migration ID
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Format: YYYYMMDD_HHMMSS_description_in_snake_case
        time_part = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Convert description to snake_case
        desc_part = description.lower()
        desc_part = ''.join(c if c.isalnum() else '_' for c in desc_part)
        desc_part = '_'.join(filter(None, desc_part.split('_')))[:50]  # Limit length
        
        return f"{time_part}_{desc_part}"
    
    @staticmethod
    def calculate_migration_checksum(migration: BaseMigration) -> str:
        """Calculate checksum for migration content.
        
        Args:
            migration: Migration to calculate checksum for
            
        Returns:
            SHA256 checksum
        """
        # Create a deterministic representation of the migration
        content_parts = [
            migration.migration_id,
            migration.description,
            migration.version,
            str(sorted(migration.dependencies)),
            str(sorted(migration.tags))
        ]
        
        # Add type-specific content
        if hasattr(migration, 'up_sql'):
            content_parts.append(migration.up_sql)
            content_parts.append(migration.down_sql or '')
        elif hasattr(migration, 'transformations'):
            content_parts.append(json.dumps(migration.transformations, sort_keys=True))
        elif hasattr(migration, 'config_files'):
            content_parts.append(json.dumps(migration.config_files, sort_keys=True))
            content_parts.append(json.dumps(migration.transformations, sort_keys=True))
        
        content = '|'.join(content_parts)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def create_migration_backup(
        migrations: List[BaseMigration],
        backup_path: Optional[str] = None
    ) -> str:
        """Create a backup of migrations.
        
        Args:
            migrations: List of migrations to backup
            backup_path: Path for backup file (auto-generated if None)
            
        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = f"migrations_backup_{timestamp}.zip"
        
        backup_dir = Path(backup_path).parent
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Add migrations metadata
            migrations_data = [m.to_dict() for m in migrations]
            backup_zip.writestr(
                'migrations.json',
                json.dumps(migrations_data, indent=2)
            )
            
            # Add migration source files if available
            for migration in migrations:
                # This would add source files if we track them
                pass
        
        return backup_path
    
    @staticmethod
    def restore_migration_backup(backup_path: str) -> List[Dict[str, Any]]:
        """Restore migrations from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            List of migration dictionaries
        """
        if not Path(backup_path).exists():
            raise MigrationError(f"Backup file not found: {backup_path}")
        
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            if 'migrations.json' not in backup_zip.namelist():
                raise MigrationError("Invalid backup file: missing migrations.json")
            
            migrations_data = json.loads(backup_zip.read('migrations.json').decode('utf-8'))
            return migrations_data
    
    @staticmethod
    def validate_migration_sequence(migrations: List[BaseMigration]) -> List[str]:
        """Validate a sequence of migrations.
        
        Args:
            migrations: List of migrations to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        migration_ids = {m.migration_id for m in migrations}
        
        # Check for duplicate IDs
        ids_list = [m.migration_id for m in migrations]
        if len(ids_list) != len(set(ids_list)):
            duplicates = [mid for mid in ids_list if ids_list.count(mid) > 1]
            errors.append(f"Duplicate migration IDs found: {set(duplicates)}")
        
        # Check dependencies
        for migration in migrations:
            for dep_id in migration.dependencies:
                if dep_id not in migration_ids:
                    errors.append(f"Migration {migration.migration_id} has missing dependency: {dep_id}")
        
        # Check version ordering
        sorted_migrations = sorted(migrations, key=lambda m: m.version)
        if migrations != sorted_migrations:
            errors.append("Migrations are not in version order")
        
        return errors
    
    @staticmethod
    def detect_circular_dependencies(migrations: List[BaseMigration]) -> List[str]:
        """Detect circular dependencies in migrations.
        
        Args:
            migrations: List of migrations to check
            
        Returns:
            List of circular dependency chains
        """
        migration_map = {m.migration_id: m for m in migrations}
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(migration_id: str, path: List[str]) -> bool:
            if migration_id in rec_stack:
                # Found a cycle
                cycle_start = path.index(migration_id)
                cycle = path[cycle_start:] + [migration_id]
                cycles.append(" -> ".join(cycle))
                return True
            
            if migration_id in visited:
                return False
            
            visited.add(migration_id)
            rec_stack.add(migration_id)
            
            migration = migration_map.get(migration_id)
            if migration:
                for dep_id in migration.dependencies:
                    if dep_id in migration_map:
                        if dfs(dep_id, path + [migration_id]):
                            return True
            
            rec_stack.remove(migration_id)
            return False
        
        for migration in migrations:
            if migration.migration_id not in visited:
                dfs(migration.migration_id, [])
        
        return cycles
    
    @staticmethod
    def estimate_migration_impact(migrations: List[BaseMigration]) -> Dict[str, Any]:
        """Estimate the impact of running migrations.
        
        Args:
            migrations: List of migrations to analyze
            
        Returns:
            Impact analysis
        """
        impact = {
            "total_migrations": len(migrations),
            "estimated_duration": 0.0,
            "requires_downtime": False,
            "affected_components": set(),
            "reversible_migrations": 0,
            "breaking_changes": 0,
            "by_type": {}
        }
        
        for migration in migrations:
            # Duration
            duration = migration.get_estimated_duration()
            if duration:
                impact["estimated_duration"] += duration
            
            # Downtime
            if migration.requires_downtime():
                impact["requires_downtime"] = True
            
            # Components
            impact["affected_components"].update(migration.get_affected_components())
            
            # Reversibility
            if migration.can_rollback():
                impact["reversible_migrations"] += 1
            
            # Type breakdown
            migration_type = type(migration).__name__
            impact["by_type"][migration_type] = impact["by_type"].get(migration_type, 0) + 1
            
            # Breaking changes (heuristic)
            if ("drop" in migration.description.lower() or 
                "remove" in migration.description.lower() or
                "delete" in migration.description.lower()):
                impact["breaking_changes"] += 1
        
        impact["affected_components"] = list(impact["affected_components"])
        return impact
    
    @staticmethod
    def generate_migration_report(
        migrations: List[BaseMigration],
        results: Optional[List] = None
    ) -> str:
        """Generate a detailed migration report.
        
        Args:
            migrations: List of migrations
            results: Optional execution results
            
        Returns:
            Formatted report
        """
        report_lines = []
        
        # Header
        report_lines.append("Migration Report")
        report_lines.append("=" * 50)
        report_lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        report_lines.append("")
        
        # Summary
        impact = MigrationUtils.estimate_migration_impact(migrations)
        report_lines.append("Summary:")
        report_lines.append(f"  Total migrations: {impact['total_migrations']}")
        report_lines.append(f"  Estimated duration: {impact['estimated_duration']:.2f} seconds")
        report_lines.append(f"  Requires downtime: {impact['requires_downtime']}")
        report_lines.append(f"  Reversible migrations: {impact['reversible_migrations']}")
        report_lines.append(f"  Potential breaking changes: {impact['breaking_changes']}")
        report_lines.append("")
        
        # By type
        if impact['by_type']:
            report_lines.append("Migrations by type:")
            for migration_type, count in impact['by_type'].items():
                report_lines.append(f"  {migration_type}: {count}")
            report_lines.append("")
        
        # Affected components
        if impact['affected_components']:
            report_lines.append("Affected components:")
            for component in sorted(impact['affected_components']):
                report_lines.append(f"  - {component}")
            report_lines.append("")
        
        # Migration details
        report_lines.append("Migration Details:")
        report_lines.append("-" * 30)
        
        for i, migration in enumerate(migrations, 1):
            report_lines.append(f"{i}. {migration.migration_id}")
            report_lines.append(f"   Description: {migration.description}")
            report_lines.append(f"   Version: {migration.version}")
            report_lines.append(f"   Type: {type(migration).__name__}")
            
            if migration.dependencies:
                report_lines.append(f"   Dependencies: {', '.join(migration.dependencies)}")
            
            if migration.tags:
                report_lines.append(f"   Tags: {', '.join(migration.tags)}")
            
            report_lines.append(f"   Reversible: {migration.can_rollback()}")
            report_lines.append(f"   Requires downtime: {migration.requires_downtime()}")
            
            duration = migration.get_estimated_duration()
            if duration:
                report_lines.append(f"   Estimated duration: {duration:.2f}s")
            
            report_lines.append("")
        
        # Execution results
        if results:
            report_lines.append("Execution Results:")
            report_lines.append("-" * 30)
            
            for result in results:
                if hasattr(result, 'migration_id'):
                    report_lines.append(f"✓ {result.migration_id}: {result.status.value}")
                    if result.execution_time_ms:
                        report_lines.append(f"   Execution time: {result.execution_time_ms:.2f}ms")
                    if result.error_message:
                        report_lines.append(f"   Error: {result.error_message}")
                    report_lines.append("")
        
        return '\n'.join(report_lines)
    
    @staticmethod
    def create_migration_template(
        migration_type: str,
        migration_id: str,
        description: str,
        template_path: Optional[str] = None
    ) -> str:
        """Create a migration template file.
        
        Args:
            migration_type: Type of migration ('database', 'code', 'config')
            migration_id: Migration identifier
            description: Migration description
            template_path: Path to save template (returns content if None)
            
        Returns:
            Template content or file path
        """
        templates = {
            'database': '''-- @id: {migration_id}
-- @description: {description}
-- @version: 1.0.0
-- @dependencies: 
-- @tags: 

-- UP
CREATE TABLE example_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DOWN
DROP TABLE IF EXISTS example_table;
''',
            'code': '''"""
Code migration: {description}
"""

from beginnings.migration.code import CodeMigration

def create_migration():
    return CodeMigration(
        migration_id="{migration_id}",
        description="{description}",
        version="1.0.0",
        target_files=[
            "src/example.py"
        ],
        transformations=[
            {{
                "type": "regex_replace",
                "pattern": r"old_pattern",
                "replacement": "new_pattern"
            }}
        ]
    )
''',
            'config': '''{{
    "migration_id": "{migration_id}",
    "description": "{description}",
    "version": "1.0.0",
    "type": "config",
    "config_files": [
        "config.json"
    ],
    "transformations": [
        {{
            "type": "add_key",
            "key": "new_setting",
            "value": "default_value"
        }}
    ]
}}
'''
        }
        
        if migration_type not in templates:
            raise MigrationError(f"Unknown migration type: {migration_type}")
        
        content = templates[migration_type].format(
            migration_id=migration_id,
            description=description
        )
        
        if template_path:
            Path(template_path).write_text(content, encoding='utf-8')
            return template_path
        
        return content
    
    @staticmethod
    def cleanup_migration_backups(
        backup_dir: str,
        keep_count: int = 10,
        max_age_days: int = 30
    ):
        """Clean up old migration backups.
        
        Args:
            backup_dir: Directory containing backups
            keep_count: Number of recent backups to keep
            max_age_days: Maximum age of backups to keep
        """
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return
        
        # Find backup files
        backup_files = list(backup_path.glob("migrations_backup_*.zip"))
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Keep recent backups
        files_to_keep = backup_files[:keep_count]
        files_to_check = backup_files[keep_count:]
        
        # Remove old backups
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = datetime.utcnow().timestamp()
        
        for backup_file in files_to_check:
            file_age = current_time - backup_file.stat().st_mtime
            if file_age > max_age_seconds:
                backup_file.unlink()
    
    @staticmethod
    def verify_migration_integrity(
        migrations: List[BaseMigration],
        checksums: Optional[Dict[str, str]] = None
    ) -> Dict[str, bool]:
        """Verify migration integrity using checksums.
        
        Args:
            migrations: List of migrations to verify
            checksums: Expected checksums (calculated if None)
            
        Returns:
            Dictionary mapping migration IDs to integrity status
        """
        results = {}
        
        for migration in migrations:
            current_checksum = MigrationUtils.calculate_migration_checksum(migration)
            
            if checksums and migration.migration_id in checksums:
                expected_checksum = checksums[migration.migration_id]
                results[migration.migration_id] = current_checksum == expected_checksum
            else:
                # No checksum to compare against, assume valid
                results[migration.migration_id] = True
        
        return results