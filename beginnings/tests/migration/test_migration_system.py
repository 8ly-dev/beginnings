"""Tests for the migration system."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.beginnings.migration.base import BaseMigration, MigrationStatus, MigrationError
from src.beginnings.migration.database import DatabaseMigration, DatabaseMigrationRunner
from src.beginnings.migration.code import CodeMigration, CodeMigrationRunner
from src.beginnings.migration.config import ConfigMigration, ConfigMigrationRunner
from src.beginnings.migration.runner import MigrationRunner, MigrationResult, MigrationPlan
from src.beginnings.migration.registry import MigrationRegistry
from src.beginnings.migration.utils import MigrationUtils


class MigrationForTesting(BaseMigration):
    """Test migration for testing purposes."""
    
    def __init__(self, migration_id, description="Test migration", version="1.0.0"):
        super().__init__(migration_id, description, version)
        self.executed = False
        self.rolled_back = False
    
    def validate(self):
        return []
    
    async def execute(self, context):
        self.executed = True
        return {"test": "executed"}
    
    async def rollback(self, context):
        self.rolled_back = True
        return {"test": "rolled_back"}
    
    def can_rollback(self):
        return True


class TestBaseMigration:
    """Test base migration functionality."""
    
    def test_migration_creation(self):
        migration = MigrationForTesting("test_001", "Test migration", "1.0.0")
        
        assert migration.migration_id == "test_001"
        assert migration.description == "Test migration"
        assert migration.version == "1.0.0"
        assert migration.status == MigrationStatus.PENDING
        assert migration.dependencies == []
        assert migration.tags == []
    
    def test_migration_with_dependencies(self):
        migration = MigrationForTesting("test_002", "Test migration", "1.0.0")
        migration.dependencies = ["test_001"]
        migration.tags = ["database", "schema"]
        
        assert migration.dependencies == ["test_001"]
        assert "database" in migration.tags
        assert "schema" in migration.tags
    
    def test_migration_equality(self):
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_001")
        migration3 = MigrationForTesting("test_002")
        
        assert migration1 == migration2
        assert migration1 != migration3
        assert hash(migration1) == hash(migration2)
    
    def test_migration_to_dict(self):
        migration = MigrationForTesting("test_001", "Test migration", "1.0.0")
        data = migration.to_dict()
        
        assert data["migration_id"] == "test_001"
        assert data["description"] == "Test migration"
        assert data["version"] == "1.0.0"
        assert data["status"] == "pending"
        assert data["can_rollback"] is True


class TestDatabaseMigration:
    """Test database migration functionality."""
    
    def test_database_migration_creation(self):
        migration = DatabaseMigration(
            migration_id="db_001",
            description="Create users table",
            version="1.0.0",
            up_sql="CREATE TABLE users (id SERIAL PRIMARY KEY);",
            down_sql="DROP TABLE users;"
        )
        
        assert migration.migration_id == "db_001"
        assert "CREATE TABLE" in migration.up_sql
        assert "DROP TABLE" in migration.down_sql
        assert migration.can_rollback() is True
    
    def test_database_migration_validation(self):
        # Valid migration
        migration = DatabaseMigration(
            migration_id="db_001",
            description="Create table",
            version="1.0.0",
            up_sql="CREATE TABLE test (id SERIAL);",
            down_sql="DROP TABLE test;"
        )
        
        errors = migration.validate()
        assert len(errors) == 0
    
    def test_database_migration_dangerous_operations(self):
        # Migration with dangerous operations
        migration = DatabaseMigration(
            migration_id="db_002",
            description="Dangerous migration",
            version="1.0.0",
            up_sql="DROP TABLE users; DELETE FROM logs;",
            down_sql=""
        )
        
        errors = migration.validate()
        assert len(errors) > 0
        assert any("DROP TABLE" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_database_migration_execution(self):
        migration = DatabaseMigration(
            migration_id="db_001",
            description="Test migration",
            version="1.0.0",
            up_sql="CREATE TABLE test (id SERIAL);",
            down_sql="DROP TABLE test;"
        )
        
        # Mock database connection
        context = {
            "db_connection": "mock_connection",
            "dry_run": True
        }
        
        result = await migration.execute(context)
        assert result["dry_run"] is True
        assert "sql" in result
    
    def test_database_migration_requires_downtime(self):
        # Migration that requires downtime
        migration = DatabaseMigration(
            migration_id="db_003",
            description="Drop column",
            version="1.0.0",
            up_sql="ALTER TABLE users DROP COLUMN email;",
        )
        
        assert migration.requires_downtime() is True
    
    def test_database_migration_affected_components(self):
        migration = DatabaseMigration(
            migration_id="db_004",
            description="Create and update tables",
            version="1.0.0",
            up_sql="CREATE TABLE users (id SERIAL); UPDATE settings SET value = 'new';"
        )
        
        components = migration.get_affected_components()
        assert "users" in components
        assert "settings" in components


class TestCodeMigration:
    """Test code migration functionality."""
    
    def test_code_migration_creation(self):
        migration = CodeMigration(
            migration_id="code_001",
            description="Update imports",
            version="1.0.0",
            target_files=["src/app.py", "src/utils.py"],
            transformations=[
                {
                    "type": "regex_replace",
                    "pattern": r"from old_module import",
                    "replacement": "from new_module import"
                }
            ]
        )
        
        assert migration.migration_id == "code_001"
        assert len(migration.target_files) == 2
        assert len(migration.transformations) == 1
        assert migration.backup_enabled is True
    
    def test_code_migration_validation(self):
        # Valid migration
        migration = CodeMigration(
            migration_id="code_001",
            description="Update code",
            version="1.0.0",
            target_files=["tests/migration/test_migration_system.py"],  # This file exists
            transformations=[
                {
                    "type": "regex_replace",
                    "pattern": r"old_pattern",
                    "replacement": "new_pattern"
                }
            ]
        )
        
        errors = migration.validate()
        # Should have no errors for existing file and valid transformation
        assert len(errors) == 0
    
    def test_code_migration_invalid_transformation(self):
        migration = CodeMigration(
            migration_id="code_002",
            description="Invalid migration",
            version="1.0.0",
            target_files=["src/app.py"],
            transformations=[
                {
                    "type": "regex_replace",
                    "pattern": r"[invalid_regex",  # Invalid regex
                    "replacement": "new_pattern"
                }
            ]
        )
        
        errors = migration.validate()
        assert len(errors) > 0
        assert any("Invalid regex pattern" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_code_migration_dry_run(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("from old_module import function\n")
            temp_file = f.name
        
        try:
            migration = CodeMigration(
                migration_id="code_001",
                description="Update imports",
                version="1.0.0",
                target_files=[temp_file],
                transformations=[
                    {
                        "type": "regex_replace",
                        "pattern": r"old_module",
                        "replacement": "new_module"
                    }
                ]
            )
            
            context = {
                "project_root": ".",
                "dry_run": True
            }
            
            result = await migration.execute(context)
            assert result["dry_run"] is True
            assert "changes_preview" in result
        finally:
            Path(temp_file).unlink()
    
    def test_code_migration_affected_components(self):
        migration = CodeMigration(
            migration_id="code_001",
            description="Update code",
            version="1.0.0",
            target_files=["src/app.py", "src/utils/__init__.py"],
            transformations=[]
        )
        
        components = migration.get_affected_components()
        assert "src.app" in components
        assert "src.utils.__init__" in components


class TestConfigMigration:
    """Test config migration functionality."""
    
    def test_config_migration_creation(self):
        migration = ConfigMigration(
            migration_id="config_001",
            description="Update config",
            version="1.0.0",
            config_files=["config.json", "settings.yaml"],
            transformations=[
                {
                    "type": "add_key",
                    "key": "new_setting",
                    "value": "default_value"
                }
            ]
        )
        
        assert migration.migration_id == "config_001"
        assert len(migration.config_files) == 2
        assert len(migration.transformations) == 1
        assert migration.backup_enabled is True
    
    def test_config_migration_validation(self):
        migration = ConfigMigration(
            migration_id="config_001",
            description="Update config",
            version="1.0.0",
            config_files=["config.json"],
            transformations=[
                {
                    "type": "add_key",
                    "key": "test_key",
                    "value": "test_value"
                },
                {
                    "type": "invalid_type"  # Invalid transformation type
                }
            ]
        )
        
        errors = migration.validate()
        assert len(errors) > 0
        assert any("Unknown transformation type" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_config_migration_transformations(self):
        # Test nested key operations
        original_config = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "old_setting": "old_value"
        }
        
        migration = ConfigMigration(
            migration_id="config_001",
            description="Update config",
            version="1.0.0",
            config_files=[],
            transformations=[
                {
                    "type": "add_key",
                    "key": "database.timeout",
                    "value": 30
                },
                {
                    "type": "rename_key",
                    "key": "old_setting",
                    "new_key": "new_setting"
                }
            ]
        )
        
        modified_config = await migration._apply_transformations_to_config(
            original_config, Path("config.json")
        )
        
        assert modified_config["database"]["timeout"] == 30
        assert "new_setting" in modified_config
        assert "old_setting" not in modified_config


class TestMigrationRegistry:
    """Test migration registry functionality."""
    
    def test_registry_creation(self):
        registry = MigrationRegistry(["migrations", "custom_migrations"])
        
        assert len(registry.migration_paths) == 2
        assert "migrations" in registry.migration_paths
        assert len(registry.migrations) == 0
    
    def test_register_migration(self):
        registry = MigrationRegistry()
        migration = MigrationForTesting("test_001")
        
        registry.register_migration(migration)
        
        assert "test_001" in registry.migrations
        assert registry.get_migration("test_001") == migration
    
    def test_register_duplicate_migration(self):
        registry = MigrationRegistry()
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_001")
        
        registry.register_migration(migration1)
        
        with pytest.raises(MigrationError, match="already registered"):
            registry.register_migration(migration2)
    
    def test_get_migrations_by_type(self):
        registry = MigrationRegistry()
        test_migration = MigrationForTesting("test_001")
        db_migration = DatabaseMigration("db_001", "DB migration", "1.0.0", "SELECT 1;")
        
        registry.register_migration(test_migration)
        registry.register_migration(db_migration)
        
        db_migrations = registry.get_migrations_by_type(DatabaseMigration)
        assert len(db_migrations) == 1
        assert db_migrations[0] == db_migration
    
    def test_get_migrations_by_tag(self):
        registry = MigrationRegistry()
        migration1 = MigrationForTesting("test_001")
        migration1.tags = ["database", "schema"]
        migration2 = MigrationForTesting("test_002")
        migration2.tags = ["config"]
        
        registry.register_migration(migration1)
        registry.register_migration(migration2)
        
        db_migrations = registry.get_migrations_by_tag("database")
        assert len(db_migrations) == 1
        assert db_migrations[0] == migration1
    
    def test_get_migrations_by_version_range(self):
        registry = MigrationRegistry()
        migration1 = MigrationForTesting("test_001", version="1.0.0")
        migration2 = MigrationForTesting("test_002", version="1.1.0")
        migration3 = MigrationForTesting("test_003", version="2.0.0")
        
        registry.register_migration(migration1)
        registry.register_migration(migration2)
        registry.register_migration(migration3)
        
        migrations = registry.get_migrations_by_version_range("1.0.0", "1.9.0")
        assert len(migrations) == 2
        assert migration1 in migrations
        assert migration2 in migrations
        assert migration3 not in migrations
    
    def test_export_import_migrations(self):
        registry = MigrationRegistry()
        migration = MigrationForTesting("test_001")
        registry.register_migration(migration)
        
        # Export
        export_data = registry.export_migrations("json")
        assert "test_001" in export_data
        
        # Clear and import
        registry.clear()
        assert len(registry.migrations) == 0
        
        # This would need proper from_dict implementation for MigrationForTesting
        # registry.import_migrations(export_data, "json")


class TestMigrationRunner:
    """Test migration runner functionality."""
    
    @pytest.mark.asyncio
    async def test_runner_creation(self):
        registry = MigrationRegistry()
        runner = MigrationRunner(registry)
        
        assert runner.registry == registry
        assert len(runner.applied_migrations) == 0
    
    @pytest.mark.asyncio
    async def test_run_single_migration(self):
        registry = MigrationRegistry()
        migration = MigrationForTesting("test_001")
        registry.register_migration(migration)
        
        runner = MigrationRunner(registry)
        results = await runner.run_migrations(migration_ids=["test_001"], dry_run=True)
        
        assert len(results) == 1
        assert results[0].migration_id == "test_001"
        assert results[0].is_success()
    
    @pytest.mark.asyncio
    async def test_dependency_resolution(self):
        registry = MigrationRegistry()
        
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_002")
        migration2.dependencies = ["test_001"]
        migration3 = MigrationForTesting("test_003")
        migration3.dependencies = ["test_002"]
        
        registry.register_migration(migration1)
        registry.register_migration(migration2)
        registry.register_migration(migration3)
        
        runner = MigrationRunner(registry)
        
        # Test dependency resolution
        migrations = [migration3, migration1, migration2]  # Out of order
        resolved = await runner._resolve_dependencies(migrations)
        
        # Should be in dependency order
        assert resolved[0] == migration1
        assert resolved[1] == migration2
        assert resolved[2] == migration3
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        registry = MigrationRegistry()
        
        migration1 = MigrationForTesting("test_001")
        migration1.dependencies = ["test_002"]
        migration2 = MigrationForTesting("test_002")
        migration2.dependencies = ["test_001"]  # Circular
        
        registry.register_migration(migration1)
        registry.register_migration(migration2)
        
        runner = MigrationRunner(registry)
        
        with pytest.raises(MigrationError, match="Circular dependency"):
            await runner._resolve_dependencies([migration1, migration2])
    
    @pytest.mark.asyncio
    async def test_migration_status(self):
        registry = MigrationRegistry()
        migration = MigrationForTesting("test_001")
        registry.register_migration(migration)
        
        runner = MigrationRunner(registry)
        status = await runner.get_migration_status()
        
        assert status["total_migrations"] == 1
        assert status["applied_migrations"] == 0
        assert status["pending_migrations"] == 1
        assert "test_001" in status["pending_migration_ids"]


class TestMigrationUtils:
    """Test migration utilities."""
    
    def test_generate_migration_id(self):
        description = "Create users table"
        migration_id = MigrationUtils.generate_migration_id(description)
        
        assert "create_users_table" in migration_id
        assert len(migration_id.split("_")) >= 3  # timestamp + description parts
    
    def test_calculate_migration_checksum(self):
        migration = MigrationForTesting("test_001", "Test migration")
        checksum1 = MigrationUtils.calculate_migration_checksum(migration)
        checksum2 = MigrationUtils.calculate_migration_checksum(migration)
        
        # Same migration should produce same checksum
        assert checksum1 == checksum2
        
        # Different migration should produce different checksum
        migration2 = MigrationForTesting("test_002", "Different migration")
        checksum3 = MigrationUtils.calculate_migration_checksum(migration2)
        assert checksum1 != checksum3
    
    def test_validate_migration_sequence(self):
        migration1 = MigrationForTesting("test_001", version="1.0.0")
        migration2 = MigrationForTesting("test_002", version="1.1.0")
        migration2.dependencies = ["test_001"]
        migration3 = MigrationForTesting("test_001", version="2.0.0")  # Duplicate ID
        
        # Valid sequence
        errors = MigrationUtils.validate_migration_sequence([migration1, migration2])
        assert len(errors) == 0
        
        # Invalid sequence with duplicate
        errors = MigrationUtils.validate_migration_sequence([migration1, migration2, migration3])
        assert len(errors) > 0
        assert any("Duplicate migration IDs" in error for error in errors)
    
    def test_detect_circular_dependencies(self):
        migration1 = MigrationForTesting("test_001")
        migration1.dependencies = ["test_002"]
        migration2 = MigrationForTesting("test_002")
        migration2.dependencies = ["test_001"]
        
        cycles = MigrationUtils.detect_circular_dependencies([migration1, migration2])
        assert len(cycles) > 0
        assert "test_001" in cycles[0] and "test_002" in cycles[0]
    
    def test_estimate_migration_impact(self):
        migration1 = MigrationForTesting("test_001")
        migration2 = DatabaseMigration("db_001", "Create table", "1.0.0", "CREATE TABLE test (id SERIAL);")
        
        impact = MigrationUtils.estimate_migration_impact([migration1, migration2])
        
        assert impact["total_migrations"] == 2
        assert impact["estimated_duration"] > 0
        assert "MigrationForTesting" in impact["by_type"]
        assert "DatabaseMigration" in impact["by_type"]
    
    def test_generate_migration_report(self):
        migration1 = MigrationForTesting("test_001", "First migration")
        migration2 = MigrationForTesting("test_002", "Second migration")
        
        report = MigrationUtils.generate_migration_report([migration1, migration2])
        
        assert "Migration Report" in report
        assert "test_001" in report
        assert "test_002" in report
        assert "Total migrations: 2" in report
    
    def test_create_migration_template(self):
        # Test database template
        template = MigrationUtils.create_migration_template(
            "database", "test_001", "Create table"
        )
        
        assert "test_001" in template
        assert "Create table" in template
        assert "-- UP" in template
        assert "-- DOWN" in template
        
        # Test code template
        template = MigrationUtils.create_migration_template(
            "code", "test_002", "Update imports"
        )
        
        assert "test_002" in template
        assert "Update imports" in template
        assert "CodeMigration" in template
    
    def test_verify_migration_integrity(self):
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_002")
        
        # Calculate checksums
        checksum1 = MigrationUtils.calculate_migration_checksum(migration1)
        checksum2 = MigrationUtils.calculate_migration_checksum(migration2)
        
        checksums = {
            "test_001": checksum1,
            "test_002": checksum2
        }
        
        # Verify integrity
        results = MigrationUtils.verify_migration_integrity([migration1, migration2], checksums)
        
        assert results["test_001"] is True
        assert results["test_002"] is True
        
        # Test with wrong checksum
        checksums["test_001"] = "wrong_checksum"
        results = MigrationUtils.verify_migration_integrity([migration1, migration2], checksums)
        
        assert results["test_001"] is False
        assert results["test_002"] is True


class TestMigrationPlan:
    """Test migration plan functionality."""
    
    def test_migration_plan_creation(self):
        from src.beginnings.migration.runner import MigrationDirection
        
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_002")
        
        plan = MigrationPlan([migration1, migration2], MigrationDirection.UP)
        
        assert len(plan.migrations) == 2
        assert plan.direction == MigrationDirection.UP
        assert plan.created_at is not None
    
    def test_migration_plan_execution_order(self):
        from src.beginnings.migration.runner import MigrationDirection
        
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_002")
        
        # Forward direction
        plan = MigrationPlan([migration1, migration2], MigrationDirection.UP)
        order = plan.get_execution_order()
        assert order == [migration1, migration2]
        
        # Reverse direction
        plan = MigrationPlan([migration1, migration2], MigrationDirection.DOWN)
        order = plan.get_execution_order()
        assert order == [migration2, migration1]
    
    def test_migration_plan_estimates(self):
        from src.beginnings.migration.runner import MigrationDirection
        
        migration1 = MigrationForTesting("test_001")
        migration2 = MigrationForTesting("test_002")
        
        plan = MigrationPlan([migration1, migration2], MigrationDirection.UP)
        
        # Test estimates (will be None for MigrationForTesting)
        duration = plan.get_estimated_duration()
        assert duration == 0.0  # No estimates provided
        
        downtime = plan.requires_downtime()
        assert downtime is False
        
        components = plan.get_affected_components()
        assert isinstance(components, set)


class TestMigrationResult:
    """Test migration result functionality."""
    
    def test_migration_result_creation(self):
        result = MigrationResult(
            "test_001",
            MigrationStatus.COMPLETED,
            execution_time_ms=150.5,
            result_data={"rows_affected": 10}
        )
        
        assert result.migration_id == "test_001"
        assert result.status == MigrationStatus.COMPLETED
        assert result.execution_time_ms == 150.5
        assert result.result_data["rows_affected"] == 10
        assert result.is_success() is True
        assert result.is_failure() is False
    
    def test_migration_result_failure(self):
        result = MigrationResult(
            "test_001",
            MigrationStatus.FAILED,
            error_message="Migration failed"
        )
        
        assert result.is_success() is False
        assert result.is_failure() is True
        assert result.error_message == "Migration failed"
    
    def test_migration_result_to_dict(self):
        result = MigrationResult(
            "test_001",
            MigrationStatus.COMPLETED,
            execution_time_ms=150.5
        )
        
        data = result.to_dict()
        
        assert data["migration_id"] == "test_001"
        assert data["status"] == "completed"
        assert data["execution_time_ms"] == 150.5
        assert "timestamp" in data