"""
Health check functionality for Beginnings framework.

Provides health checks for extensions and system components.
"""

import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details or {}
        }


class HealthCheck:
    """Health check manager for monitoring system health."""
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
    
    def register_check(self, name: str, check_func: Callable[[], HealthCheckResult]):
        """Register a health check function."""
        self._checks[name] = check_func
    
    def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check."""
        if name not in self._checks:
            return None
        
        try:
            result = self._checks[name]()
            self._last_results[name] = result
            return result
        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e), "error_type": type(e).__name__}
            )
            self._last_results[name] = result
            return result
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        for name in self._checks:
            results[name] = self.run_check(name)
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self._last_results:
            return HealthStatus.HEALTHY
        
        statuses = [result.status for result in self._last_results.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def get_health_summary(self) -> dict:
        """Get health summary for all components."""
        return {
            "overall_status": self.get_overall_status().value,
            "timestamp": time.time(),
            "checks": {name: result.to_dict() for name, result in self._last_results.items()}
        }
    
    def register_extension_check(self, extension_name: str, extension_instance: Any):
        """Register health check for an extension."""
        def extension_health_check() -> HealthCheckResult:
            try:
                # Basic health check - extension is loaded and configured
                if hasattr(extension_instance, 'validate_config'):
                    errors = extension_instance.validate_config()
                    if errors:
                        return HealthCheckResult(
                            name=f"extension_{extension_name}",
                            status=HealthStatus.DEGRADED,
                            message=f"Configuration issues: {', '.join(errors)}",
                            timestamp=time.time(),
                            details={"config_errors": errors}
                        )
                
                # Check if extension has custom health check
                if hasattr(extension_instance, 'health_check'):
                    return extension_instance.health_check()
                
                # Default healthy status
                return HealthCheckResult(
                    name=f"extension_{extension_name}",
                    status=HealthStatus.HEALTHY,
                    message="Extension is operational",
                    timestamp=time.time()
                )
                
            except Exception as e:
                return HealthCheckResult(
                    name=f"extension_{extension_name}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Extension health check failed: {str(e)}",
                    timestamp=time.time(),
                    details={"error": str(e)}
                )
        
        self.register_check(f"extension_{extension_name}", extension_health_check)
    
    def register_storage_check(self, storage_name: str, storage_instance: Any):
        """Register health check for storage backend."""
        def storage_health_check() -> HealthCheckResult:
            try:
                # Test basic storage operations
                if hasattr(storage_instance, 'health_check'):
                    return storage_instance.health_check()
                
                # Basic connectivity test
                if hasattr(storage_instance, '_get_redis'):
                    # Redis/Valkey storage check
                    import asyncio
                    async def test_redis():
                        redis = await storage_instance._get_redis()
                        await redis.ping()
                    
                    # Run in event loop if available
                    try:
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(test_redis())
                    except RuntimeError:
                        # No event loop, create new one
                        asyncio.run(test_redis())
                
                return HealthCheckResult(
                    name=f"storage_{storage_name}",
                    status=HealthStatus.HEALTHY,
                    message="Storage is accessible",
                    timestamp=time.time()
                )
                
            except Exception as e:
                return HealthCheckResult(
                    name=f"storage_{storage_name}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Storage health check failed: {str(e)}",
                    timestamp=time.time(),
                    details={"error": str(e)}
                )
        
        self.register_check(f"storage_{storage_name}", storage_health_check)


# Global health check instance
_health_check: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    """Get the global health check instance."""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check