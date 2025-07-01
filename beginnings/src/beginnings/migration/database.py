"""Database migration implementation."""

from __future__ import annotations

import re
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from datetime import datetime

try:
    import sqlparse
except ImportError:
    sqlparse = None

from .base import BaseMigration, MigrationError, MigrationExecutionError, MigrationRollbackError


class DatabaseMigration(BaseMigration):
    """Database schema migration."""
    
    def __init__(
        self,
        migration_id: str,
        description: str,
        version: str,
        up_sql: str,
        down_sql: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        table_dependencies: Optional[List[str]] = None,
        estimated_rows_affected: Optional[int] = None
    ):
        """Initialize database migration.
        
        Args:
            migration_id: Unique migration identifier
            description: Migration description
            version: Migration version
            up_sql: SQL for forward migration
            down_sql: SQL for rollback (optional)
            dependencies: Migration dependencies
            tags: Migration tags
            table_dependencies: Tables this migration depends on
            estimated_rows_affected: Estimated number of rows affected
        """
        super().__init__(migration_id, description, version, dependencies, tags)
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.table_dependencies = table_dependencies or []
        self.estimated_rows_affected = estimated_rows_affected
    
    def validate(self) -> List[str]:
        """Validate database migration."""
        errors = []
        
        # Validate SQL syntax if sqlparse is available
        if sqlparse:
            try:
                parsed = sqlparse.parse(self.up_sql)
                if not parsed:
                    errors.append("Invalid SQL syntax in up_sql")
            except Exception as e:
                errors.append(f"SQL parsing error in up_sql: {e}")
            
            if self.down_sql:
                try:
                    parsed = sqlparse.parse(self.down_sql)
                    if not parsed:
                        errors.append("Invalid SQL syntax in down_sql")
                except Exception as e:
                    errors.append(f"SQL parsing error in down_sql: {e}")
        else:
            # Basic validation without sqlparse
            if not self.up_sql.strip():
                errors.append("up_sql cannot be empty")
        
        # Check for dangerous operations
        dangerous_patterns = [
            (r'\bDROP\s+TABLE\b', "DROP TABLE operations require careful review"),
            (r'\bTRUNCATE\b', "TRUNCATE operations are irreversible"),
            (r'\bDELETE\s+FROM\s+\w+\s*;', "DELETE without WHERE clause detected"),
            (r'\bUPDATE\s+\w+\s+SET\s+.*\s*;', "UPDATE without WHERE clause detected")
        ]
        
        for pattern, warning in dangerous_patterns:
            if re.search(pattern, self.up_sql, re.IGNORECASE):
                errors.append(warning)
        
        return errors
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database migration."""
        db_connection = context.get('db_connection')
        if not db_connection:
            raise MigrationExecutionError("Database connection not provided in context")
        
        dry_run = context.get('dry_run', False)
        
        if dry_run:
            return {
                "dry_run": True,
                "preview": self.get_dry_run_preview(context),
                "sql": self.up_sql
            }
        
        start_time = datetime.utcnow()
        
        try:
            # Execute migration SQL
            result = await self._execute_sql(db_connection, self.up_sql)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.execution_time_ms = execution_time
            
            return {
                "executed": True,
                "execution_time_ms": execution_time,
                "rows_affected": result.get('rows_affected', 0),
                "result": result
            }
            
        except Exception as e:
            raise MigrationExecutionError(f"Failed to execute migration {self.migration_id}: {e}")
    
    async def rollback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback database migration."""
        if not self.can_rollback():
            raise MigrationRollbackError(f"Migration {self.migration_id} cannot be rolled back")
        
        db_connection = context.get('db_connection')
        if not db_connection:
            raise MigrationRollbackError("Database connection not provided in context")
        
        dry_run = context.get('dry_run', False)
        
        if dry_run:
            return {
                "dry_run": True,
                "preview": f"Rollback {self.migration_id}: {self.description}",
                "sql": self.down_sql
            }
        
        start_time = datetime.utcnow()
        
        try:
            result = await self._execute_sql(db_connection, self.down_sql)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "rolled_back": True,
                "execution_time_ms": execution_time,
                "rows_affected": result.get('rows_affected', 0),
                "result": result
            }
            
        except Exception as e:
            raise MigrationRollbackError(f"Failed to rollback migration {self.migration_id}: {e}")
    
    def can_rollback(self) -> bool:
        """Check if migration can be rolled back."""
        return self.down_sql is not None and self.down_sql.strip() != ""
    
    def get_dry_run_preview(self, context: Dict[str, Any]) -> str:
        """Get preview of migration SQL."""
        preview = f"Database Migration {self.migration_id}: {self.description}\n"
        preview += f"SQL to execute:\n{self.up_sql}"
        
        if self.estimated_rows_affected:
            preview += f"\nEstimated rows affected: {self.estimated_rows_affected}"
        
        return preview
    
    def get_estimated_duration(self) -> Optional[float]:
        """Estimate migration duration based on operations."""
        if self.estimated_rows_affected:
            # Rough estimation: 1000 rows per second
            return self.estimated_rows_affected / 1000.0
        
        # Simple estimation based on SQL complexity
        sql_lines = len(self.up_sql.split('\n'))
        return sql_lines * 0.1  # 100ms per line
    
    def requires_downtime(self) -> bool:
        """Check if migration requires downtime."""
        downtime_patterns = [
            r'\bALTER\s+TABLE\s+.*\s+DROP\s+COLUMN\b',
            r'\bALTER\s+TABLE\s+.*\s+MODIFY\s+COLUMN\b',
            r'\bDROP\s+TABLE\b',
            r'\bRENAME\s+TABLE\b'
        ]
        
        for pattern in downtime_patterns:
            if re.search(pattern, self.up_sql, re.IGNORECASE):
                return True
        
        return False
    
    def get_affected_components(self) -> List[str]:
        """Get tables and components affected by migration."""
        components = []
        
        # Extract table names from SQL
        table_patterns = [
            r'\bCREATE\s+TABLE\s+(\w+)',
            r'\bALTER\s+TABLE\s+(\w+)',
            r'\bDROP\s+TABLE\s+(\w+)',
            r'\bINSERT\s+INTO\s+(\w+)',
            r'\bUPDATE\s+(\w+)',
            r'\bDELETE\s+FROM\s+(\w+)'
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, self.up_sql, re.IGNORECASE)
            components.extend(matches)
        
        return list(set(components))
    
    async def _execute_sql(self, connection, sql: str) -> Dict[str, Any]:
        """Execute SQL and return result."""
        # This is a placeholder - actual implementation would depend on database driver
        # For now, simulate execution
        if sqlparse:
            statements = sqlparse.split(sql)
        else:
            # Simple statement splitting without sqlparse
            statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
        
        results = []
        
        for statement in statements:
            if statement.strip():
                # Simulate SQL execution
                result = {
                    "statement": statement,
                    "rows_affected": 0
                }
                results.append(result)
        
        return {
            "statements_executed": len(results),
            "results": results,
            "rows_affected": sum(r["rows_affected"] for r in results)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DatabaseMigration:
        """Create migration from dictionary."""
        return cls(
            migration_id=data["migration_id"],
            description=data["description"],
            version=data["version"],
            up_sql=data["up_sql"],
            down_sql=data.get("down_sql"),
            dependencies=data.get("dependencies"),
            tags=data.get("tags"),
            table_dependencies=data.get("table_dependencies"),
            estimated_rows_affected=data.get("estimated_rows_affected")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data.update({
            "type": "database",
            "up_sql": self.up_sql,
            "down_sql": self.down_sql,
            "table_dependencies": self.table_dependencies,
            "estimated_rows_affected": self.estimated_rows_affected
        })
        return data


class DatabaseMigrationRunner:
    """Runner for database migrations."""
    
    def __init__(self, connection_factory: Callable[[], Any]):
        """Initialize runner.
        
        Args:
            connection_factory: Function that creates database connections
        """
        self.connection_factory = connection_factory
        self.migration_table = "beginnings_migrations"
    
    async def run_migration(
        self, 
        migration: DatabaseMigration, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Run a single database migration.
        
        Args:
            migration: Migration to run
            dry_run: Whether to perform dry run
            
        Returns:
            Migration result
        """
        connection = self.connection_factory()
        
        try:
            # Ensure migration table exists
            await self._ensure_migration_table(connection)
            
            # Check if migration already applied
            if not dry_run and await self._is_migration_applied(connection, migration.migration_id):
                return {
                    "skipped": True,
                    "reason": "Migration already applied"
                }
            
            # Execute migration
            context = {
                "db_connection": connection,
                "dry_run": dry_run
            }
            
            result = await migration.execute(context)
            
            # Record migration if not dry run
            if not dry_run:
                await self._record_migration(connection, migration)
            
            return result
            
        finally:
            if hasattr(connection, 'close'):
                await connection.close()
    
    async def rollback_migration(
        self, 
        migration: DatabaseMigration, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Rollback a database migration.
        
        Args:
            migration: Migration to rollback
            dry_run: Whether to perform dry run
            
        Returns:
            Rollback result
        """
        connection = self.connection_factory()
        
        try:
            # Check if migration was applied
            if not dry_run and not await self._is_migration_applied(connection, migration.migration_id):
                return {
                    "skipped": True,
                    "reason": "Migration not applied"
                }
            
            # Rollback migration
            context = {
                "db_connection": connection,
                "dry_run": dry_run
            }
            
            result = await migration.rollback(context)
            
            # Remove migration record if not dry run
            if not dry_run:
                await self._remove_migration_record(connection, migration.migration_id)
            
            return result
            
        finally:
            if hasattr(connection, 'close'):
                await connection.close()
    
    async def _ensure_migration_table(self, connection):
        """Ensure migration tracking table exists."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.migration_table} (
            id VARCHAR(255) PRIMARY KEY,
            version VARCHAR(50) NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INTEGER,
            checksum VARCHAR(64)
        )
        """
        # Execute table creation (implementation depends on database driver)
        pass
    
    async def _is_migration_applied(self, connection, migration_id: str) -> bool:
        """Check if migration has been applied."""
        # Implementation depends on database driver
        return False
    
    async def _record_migration(self, connection, migration: DatabaseMigration):
        """Record migration as applied."""
        # Implementation depends on database driver
        pass
    
    async def _remove_migration_record(self, connection, migration_id: str):
        """Remove migration record."""
        # Implementation depends on database driver
        pass