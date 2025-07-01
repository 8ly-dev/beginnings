"""Main migration runner and orchestration."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from enum import Enum
import logging

from .base import BaseMigration, MigrationStatus, MigrationError, MigrationExecutionError
from .database import DatabaseMigration, DatabaseMigrationRunner
from .code import CodeMigration, CodeMigrationRunner
from .config import ConfigMigration, ConfigMigrationRunner
from .registry import MigrationRegistry


class MigrationDirection(Enum):
    """Migration direction enumeration."""
    UP = "up"
    DOWN = "down"


class MigrationResult:
    """Result of migration execution."""
    
    def __init__(
        self,
        migration_id: str,
        status: MigrationStatus,
        execution_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """Initialize migration result.
        
        Args:
            migration_id: Migration identifier
            status: Final status
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if failed
            result_data: Additional result data
        """
        self.migration_id = migration_id
        self.status = status
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message
        self.result_data = result_data or {}
        self.timestamp = datetime.utcnow()
    
    def is_success(self) -> bool:
        """Check if migration was successful."""
        return self.status == MigrationStatus.COMPLETED
    
    def is_failure(self) -> bool:
        """Check if migration failed."""
        return self.status == MigrationStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "migration_id": self.migration_id,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "result_data": self.result_data,
            "timestamp": self.timestamp.isoformat()
        }


class MigrationPlan:
    """Migration execution plan."""
    
    def __init__(self, migrations: List[BaseMigration], direction: MigrationDirection):
        """Initialize migration plan.
        
        Args:
            migrations: List of migrations in execution order
            direction: Migration direction
        """
        self.migrations = migrations
        self.direction = direction
        self.created_at = datetime.utcnow()
    
    def get_execution_order(self) -> List[BaseMigration]:
        """Get migrations in execution order."""
        if self.direction == MigrationDirection.DOWN:
            return list(reversed(self.migrations))
        return self.migrations
    
    def get_estimated_duration(self) -> float:
        """Get estimated total execution time."""
        total = 0.0
        for migration in self.migrations:
            duration = migration.get_estimated_duration()
            if duration:
                total += duration
        return total
    
    def requires_downtime(self) -> bool:
        """Check if any migration requires downtime."""
        return any(m.requires_downtime() for m in self.migrations)
    
    def get_affected_components(self) -> Set[str]:
        """Get all affected components."""
        components = set()
        for migration in self.migrations:
            components.update(migration.get_affected_components())
        return components


class MigrationRunner:
    """Main migration runner and orchestrator."""
    
    def __init__(
        self,
        registry: MigrationRegistry,
        database_runner: Optional[DatabaseMigrationRunner] = None,
        code_runner: Optional[CodeMigrationRunner] = None,
        config_runner: Optional[ConfigMigrationRunner] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize migration runner.
        
        Args:
            registry: Migration registry
            database_runner: Database migration runner
            code_runner: Code migration runner
            config_runner: Config migration runner
            logger: Optional logger
        """
        self.registry = registry
        self.database_runner = database_runner
        self.code_runner = code_runner
        self.config_runner = config_runner
        self.logger = logger or logging.getLogger(__name__)
        
        # Track migration state
        self.applied_migrations: Set[str] = set()
        self.execution_history: List[MigrationResult] = []
    
    async def run_migrations(
        self,
        target_version: Optional[str] = None,
        migration_ids: Optional[List[str]] = None,
        dry_run: bool = False,
        force: bool = False,
        parallel: bool = False
    ) -> List[MigrationResult]:
        """Run migrations.
        
        Args:
            target_version: Target version to migrate to
            migration_ids: Specific migrations to run
            dry_run: Whether to perform dry run
            force: Force execution even with warnings
            parallel: Whether to run independent migrations in parallel
            
        Returns:
            List of migration results
        """
        try:
            # Load current state
            await self._load_migration_state()
            
            # Determine migrations to run
            if migration_ids:
                migrations = [self.registry.get_migration(mid) for mid in migration_ids]
            else:
                migrations = await self._get_pending_migrations(target_version)
            
            if not migrations:
                self.logger.info("No migrations to run")
                return []
            
            # Create execution plan
            plan = await self._create_migration_plan(migrations, MigrationDirection.UP)
            
            # Validate plan
            validation_errors = await self._validate_migration_plan(plan, force)
            if validation_errors and not force:
                raise MigrationError(f"Migration validation failed: {'; '.join(validation_errors)}")
            
            # Log plan information
            self._log_migration_plan(plan, dry_run)
            
            # Execute plan
            if parallel and not dry_run:
                return await self._execute_plan_parallel(plan, dry_run)
            else:
                return await self._execute_plan_sequential(plan, dry_run)
                
        except Exception as e:
            self.logger.error(f"Migration execution failed: {e}")
            raise
    
    async def rollback_migrations(
        self,
        target_version: Optional[str] = None,
        count: Optional[int] = None,
        migration_ids: Optional[List[str]] = None,
        dry_run: bool = False,
        force: bool = False
    ) -> List[MigrationResult]:
        """Rollback migrations.
        
        Args:
            target_version: Target version to rollback to
            count: Number of migrations to rollback
            migration_ids: Specific migrations to rollback
            dry_run: Whether to perform dry run
            force: Force rollback even with warnings
            
        Returns:
            List of rollback results
        """
        try:
            # Load current state
            await self._load_migration_state()
            
            # Determine migrations to rollback
            if migration_ids:
                migrations = [self.registry.get_migration(mid) for mid in migration_ids]
            else:
                migrations = await self._get_rollback_migrations(target_version, count)
            
            if not migrations:
                self.logger.info("No migrations to rollback")
                return []
            
            # Check if migrations can be rolled back
            non_reversible = [m for m in migrations if not m.can_rollback()]
            if non_reversible and not force:
                raise MigrationError(f"Non-reversible migrations found: {[m.migration_id for m in non_reversible]}")
            
            # Create rollback plan
            plan = await self._create_migration_plan(migrations, MigrationDirection.DOWN)
            
            # Log plan information
            self._log_migration_plan(plan, dry_run, rollback=True)
            
            # Execute rollback plan
            return await self._execute_rollback_plan(plan, dry_run)
                
        except Exception as e:
            self.logger.error(f"Migration rollback failed: {e}")
            raise
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status.
        
        Returns:
            Migration status information
        """
        await self._load_migration_state()
        
        all_migrations = self.registry.get_all_migrations()
        pending_migrations = [m for m in all_migrations if m.migration_id not in self.applied_migrations]
        
        return {
            "total_migrations": len(all_migrations),
            "applied_migrations": len(self.applied_migrations),
            "pending_migrations": len(pending_migrations),
            "applied_migration_ids": list(self.applied_migrations),
            "pending_migration_ids": [m.migration_id for m in pending_migrations],
            "execution_history": [r.to_dict() for r in self.execution_history[-10:]],  # Last 10
            "last_execution": self.execution_history[-1].to_dict() if self.execution_history else None
        }
    
    async def validate_migrations(self, migration_ids: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Validate migrations.
        
        Args:
            migration_ids: Specific migrations to validate (all if None)
            
        Returns:
            Dictionary mapping migration IDs to validation errors
        """
        if migration_ids:
            migrations = [self.registry.get_migration(mid) for mid in migration_ids]
        else:
            migrations = self.registry.get_all_migrations()
        
        validation_results = {}
        
        for migration in migrations:
            try:
                errors = migration.validate()
                validation_results[migration.migration_id] = errors
            except Exception as e:
                validation_results[migration.migration_id] = [f"Validation error: {e}"]
        
        return validation_results
    
    async def _load_migration_state(self):
        """Load current migration state."""
        # This would typically load from a migration tracking table/file
        # For now, simulate with empty state
        self.applied_migrations = set()
        self.execution_history = []
    
    async def _get_pending_migrations(self, target_version: Optional[str] = None) -> List[BaseMigration]:
        """Get pending migrations up to target version."""
        all_migrations = self.registry.get_all_migrations()
        pending = []
        
        for migration in all_migrations:
            if migration.migration_id not in self.applied_migrations:
                if target_version is None or migration.version <= target_version:
                    pending.append(migration)
        
        # Sort by version
        pending.sort(key=lambda m: m.version)
        return pending
    
    async def _get_rollback_migrations(
        self, 
        target_version: Optional[str] = None, 
        count: Optional[int] = None
    ) -> List[BaseMigration]:
        """Get migrations to rollback."""
        all_migrations = self.registry.get_all_migrations()
        applied = [m for m in all_migrations if m.migration_id in self.applied_migrations]
        
        # Sort by version descending (most recent first)
        applied.sort(key=lambda m: m.version, reverse=True)
        
        rollback_migrations = []
        
        if count is not None:
            rollback_migrations = applied[:count]
        elif target_version is not None:
            for migration in applied:
                if migration.version > target_version:
                    rollback_migrations.append(migration)
                else:
                    break
        else:
            # Rollback last migration
            if applied:
                rollback_migrations = [applied[0]]
        
        return rollback_migrations
    
    async def _create_migration_plan(
        self, 
        migrations: List[BaseMigration], 
        direction: MigrationDirection
    ) -> MigrationPlan:
        """Create migration execution plan with dependency resolution."""
        if direction == MigrationDirection.UP:
            ordered_migrations = await self._resolve_dependencies(migrations)
        else:
            # For rollback, reverse the dependency order
            ordered_migrations = await self._resolve_dependencies(migrations)
            ordered_migrations.reverse()
        
        return MigrationPlan(ordered_migrations, direction)
    
    async def _resolve_dependencies(self, migrations: List[BaseMigration]) -> List[BaseMigration]:
        """Resolve migration dependencies using topological sort."""
        migration_map = {m.migration_id: m for m in migrations}
        resolved = []
        temp_mark = set()
        perm_mark = set()
        
        def visit(migration_id: str):
            if migration_id in perm_mark:
                return
            if migration_id in temp_mark:
                raise MigrationError(f"Circular dependency detected involving {migration_id}")
            
            temp_mark.add(migration_id)
            
            migration = migration_map.get(migration_id)
            if migration:
                for dep_id in migration.dependencies:
                    if dep_id in migration_map:
                        visit(dep_id)
                
                perm_mark.add(migration_id)
                resolved.append(migration)
            
            temp_mark.remove(migration_id)
        
        for migration in migrations:
            if migration.migration_id not in perm_mark:
                visit(migration.migration_id)
        
        return resolved
    
    async def _validate_migration_plan(self, plan: MigrationPlan, force: bool = False) -> List[str]:
        """Validate migration plan."""
        errors = []
        
        # Validate individual migrations
        for migration in plan.migrations:
            migration_errors = migration.validate()
            if migration_errors:
                errors.extend([f"{migration.migration_id}: {err}" for err in migration_errors])
        
        # Check for potential conflicts
        affected_components = plan.get_affected_components()
        if len(affected_components) > 1 and not force:
            # Could add more sophisticated conflict detection
            pass
        
        # Check downtime requirements
        if plan.requires_downtime() and not force:
            errors.append("Migration plan requires downtime. Use --force to proceed.")
        
        return errors
    
    def _log_migration_plan(self, plan: MigrationPlan, dry_run: bool, rollback: bool = False):
        """Log migration plan information."""
        action = "Rollback" if rollback else "Migration"
        mode = " (DRY RUN)" if dry_run else ""
        
        self.logger.info(f"{action} Plan{mode}:")
        self.logger.info(f"  Direction: {plan.direction.value}")
        self.logger.info(f"  Migrations: {len(plan.migrations)}")
        self.logger.info(f"  Estimated duration: {plan.get_estimated_duration():.2f}s")
        self.logger.info(f"  Requires downtime: {plan.requires_downtime()}")
        self.logger.info(f"  Affected components: {', '.join(plan.get_affected_components())}")
        
        for i, migration in enumerate(plan.get_execution_order(), 1):
            self.logger.info(f"    {i}. {migration.migration_id}: {migration.description}")
    
    async def _execute_plan_sequential(self, plan: MigrationPlan, dry_run: bool) -> List[MigrationResult]:
        """Execute migration plan sequentially."""
        results = []
        
        for migration in plan.get_execution_order():
            try:
                self.logger.info(f"Executing migration: {migration.migration_id}")
                
                result = await self._execute_single_migration(migration, dry_run)
                results.append(result)
                
                if result.is_failure() and not dry_run:
                    self.logger.error(f"Migration {migration.migration_id} failed, stopping execution")
                    break
                    
            except Exception as e:
                error_result = MigrationResult(
                    migration.migration_id,
                    MigrationStatus.FAILED,
                    error_message=str(e)
                )
                results.append(error_result)
                self.logger.error(f"Migration {migration.migration_id} failed: {e}")
                break
        
        return results
    
    async def _execute_plan_parallel(self, plan: MigrationPlan, dry_run: bool) -> List[MigrationResult]:
        """Execute migration plan in parallel where possible."""
        # Group migrations by their dependencies
        dependency_groups = await self._group_by_dependencies(plan.migrations)
        results = []
        
        for group in dependency_groups:
            # Execute each group in parallel
            group_tasks = []
            for migration in group:
                task = asyncio.create_task(self._execute_single_migration(migration, dry_run))
                group_tasks.append(task)
            
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
            
            for i, result in enumerate(group_results):
                if isinstance(result, Exception):
                    error_result = MigrationResult(
                        group[i].migration_id,
                        MigrationStatus.FAILED,
                        error_message=str(result)
                    )
                    results.append(error_result)
                else:
                    results.append(result)
                    
                    # Stop if any migration in the group failed
                    if result.is_failure() and not dry_run:
                        self.logger.error(f"Migration {group[i].migration_id} failed, stopping execution")
                        return results
        
        return results
    
    async def _execute_rollback_plan(self, plan: MigrationPlan, dry_run: bool) -> List[MigrationResult]:
        """Execute rollback plan."""
        results = []
        
        for migration in plan.get_execution_order():
            try:
                self.logger.info(f"Rolling back migration: {migration.migration_id}")
                
                result = await self._rollback_single_migration(migration, dry_run)
                results.append(result)
                
                if result.is_failure() and not dry_run:
                    self.logger.error(f"Rollback of {migration.migration_id} failed, stopping")
                    break
                    
            except Exception as e:
                error_result = MigrationResult(
                    migration.migration_id,
                    MigrationStatus.FAILED,
                    error_message=str(e)
                )
                results.append(error_result)
                self.logger.error(f"Rollback of {migration.migration_id} failed: {e}")
                break
        
        return results
    
    async def _execute_single_migration(self, migration: BaseMigration, dry_run: bool) -> MigrationResult:
        """Execute a single migration."""
        start_time = datetime.utcnow()
        
        try:
            # Update migration status
            migration.status = MigrationStatus.RUNNING
            migration.executed_at = start_time
            
            # Execute based on migration type
            if isinstance(migration, DatabaseMigration):
                if not self.database_runner:
                    raise MigrationError("Database runner not configured")
                result_data = await self.database_runner.run_migration(migration, dry_run)
            
            elif isinstance(migration, CodeMigration):
                if not self.code_runner:
                    raise MigrationError("Code runner not configured")
                result_data = await self.code_runner.run_migration(migration, dry_run)
            
            elif isinstance(migration, ConfigMigration):
                if not self.config_runner:
                    raise MigrationError("Config runner not configured")
                result_data = await self.config_runner.run_migration(migration, dry_run)
            
            else:
                # Generic migration execution
                context = {"dry_run": dry_run}
                result_data = await migration.execute(context)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            migration.execution_time_ms = execution_time
            migration.status = MigrationStatus.COMPLETED
            
            # Track applied migration
            if not dry_run:
                self.applied_migrations.add(migration.migration_id)
            
            result = MigrationResult(
                migration.migration_id,
                MigrationStatus.COMPLETED,
                execution_time,
                result_data=result_data
            )
            
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            migration.status = MigrationStatus.FAILED
            migration.error_message = str(e)
            
            result = MigrationResult(
                migration.migration_id,
                MigrationStatus.FAILED,
                execution_time,
                error_message=str(e)
            )
            
            self.execution_history.append(result)
            return result
    
    async def _rollback_single_migration(self, migration: BaseMigration, dry_run: bool) -> MigrationResult:
        """Rollback a single migration."""
        start_time = datetime.utcnow()
        
        try:
            # Execute rollback based on migration type
            if isinstance(migration, DatabaseMigration):
                if not self.database_runner:
                    raise MigrationError("Database runner not configured")
                result_data = await self.database_runner.rollback_migration(migration, dry_run)
            
            elif isinstance(migration, CodeMigration):
                if not self.code_runner:
                    raise MigrationError("Code runner not configured")
                result_data = await self.code_runner.rollback_migration(migration, dry_run)
            
            elif isinstance(migration, ConfigMigration):
                if not self.config_runner:
                    raise MigrationError("Config runner not configured")
                result_data = await self.config_runner.rollback_migration(migration, dry_run)
            
            else:
                # Generic migration rollback
                context = {"dry_run": dry_run}
                result_data = await migration.rollback(context)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            migration.status = MigrationStatus.ROLLED_BACK
            
            # Remove from applied migrations
            if not dry_run:
                self.applied_migrations.discard(migration.migration_id)
            
            result = MigrationResult(
                migration.migration_id,
                MigrationStatus.ROLLED_BACK,
                execution_time,
                result_data=result_data
            )
            
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = MigrationResult(
                migration.migration_id,
                MigrationStatus.FAILED,
                execution_time,
                error_message=str(e)
            )
            
            self.execution_history.append(result)
            return result
    
    async def _group_by_dependencies(self, migrations: List[BaseMigration]) -> List[List[BaseMigration]]:
        """Group migrations by dependency levels for parallel execution."""
        # Simple implementation - in practice would be more sophisticated
        groups = []
        remaining = migrations.copy()
        
        while remaining:
            # Find migrations with no unresolved dependencies
            current_group = []
            resolved_ids = {m.migration_id for group in groups for m in group}
            
            for migration in remaining[:]:
                if all(dep in resolved_ids for dep in migration.dependencies):
                    current_group.append(migration)
                    remaining.remove(migration)
            
            if not current_group:
                # Circular dependency or missing dependency
                raise MigrationError("Unable to resolve migration dependencies")
            
            groups.append(current_group)
        
        return groups