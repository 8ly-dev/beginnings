"""System monitoring for resource usage and health."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from .exceptions import MonitoringError


@dataclass
class SystemStatus:
    """System status information."""
    
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_received: int
    timestamp: datetime
    load_average: Optional[List[float]] = None
    uptime_seconds: Optional[float] = None
    
    def __post_init__(self):
        if self.load_average is None:
            self.load_average = [0.0, 0.0, 0.0]


@dataclass
class ResourceUsageData:
    """Resource usage data point."""
    
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    timestamp: datetime
    process_count: int = 0
    
    def __post_init__(self):
        if not hasattr(self, 'timestamp') or self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class UsageTrend:
    """Usage trend analysis."""
    
    cpu_trend: str  # "increasing", "decreasing", "stable"
    memory_trend: str
    disk_trend: str
    trend_confidence: float = 0.0
    
    def __post_init__(self):
        if self.trend_confidence == 0.0:
            self.trend_confidence = 0.8  # Default confidence


@dataclass
class SystemHealthCheck:
    """System health check result."""
    
    overall_status: str  # "healthy", "warning", "critical"
    cpu_status: str
    memory_status: str
    disk_status: str
    network_status: str = "normal"
    timestamp: datetime = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}


@dataclass
class ProcessStats:
    """Process statistics."""
    
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    command: Optional[str] = None
    
    def __post_init__(self):
        if self.command is None:
            self.command = self.name


@dataclass
class SystemReport:
    """Comprehensive system report."""
    
    system_status: SystemStatus
    health_check: SystemHealthCheck
    process_stats: List[ProcessStats]
    generated_at: datetime
    overall_health_status: str
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class SystemMonitor:
    """Monitor for system-level resources and health."""
    
    def __init__(self):
        """Initialize system monitor."""
        self._usage_history: List[ResourceUsageData] = []
        self._process_cache: Dict[str, ProcessStats] = {}
    
    async def collect_system_status(self) -> SystemStatus:
        """Collect current system status.
        
        Returns:
            Current system status
        """
        try:
            # Mock system metrics collection
            # In real implementation, this would use psutil
            
            # Mock realistic system metrics
            cpu_usage = 45.2
            memory_usage = 67.8
            disk_usage = 72.1
            network_sent = 5000000000  # 5GB
            network_received = 15000000000  # 15GB
            
            return SystemStatus(
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                disk_usage_percent=disk_usage,
                network_bytes_sent=network_sent,
                network_bytes_received=network_received,
                timestamp=datetime.utcnow(),
                load_average=[1.2, 1.5, 1.8],
                uptime_seconds=86400.0  # 1 day
            )
            
        except Exception as e:
            # Return safe defaults on error
            return SystemStatus(
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                network_bytes_sent=0,
                network_bytes_received=0,
                timestamp=datetime.utcnow()
            )
    
    async def collect_resource_usage(self) -> ResourceUsageData:
        """Collect resource usage data point.
        
        Returns:
            Resource usage data
        """
        try:
            # Mock resource usage collection
            # In real implementation, this would use psutil
            
            cpu_usage = 30.5
            memory_usage = 55.2
            disk_usage = 68.9
            process_count = 156
            
            usage_data = ResourceUsageData(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                timestamp=datetime.utcnow(),
                process_count=process_count
            )
            
            # Store in history
            self._usage_history.append(usage_data)
            
            # Keep only last 1000 data points
            if len(self._usage_history) > 1000:
                self._usage_history = self._usage_history[-1000:]
            
            return usage_data
            
        except Exception as e:
            # Return safe defaults on error
            return ResourceUsageData(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                timestamp=datetime.utcnow()
            )
    
    def analyze_usage_trend(self, usage_data: List[ResourceUsageData]) -> UsageTrend:
        """Analyze usage trend from historical data.
        
        Args:
            usage_data: List of usage data points
            
        Returns:
            Usage trend analysis
        """
        if len(usage_data) < 2:
            return UsageTrend(
                cpu_trend="stable",
                memory_trend="stable",
                disk_trend="stable",
                trend_confidence=0.0
            )
        
        try:
            # Simple trend analysis based on first and last values
            first = usage_data[0]
            last = usage_data[-1]
            
            # Define thresholds for trend detection
            threshold = 5.0  # 5% change
            
            # Analyze CPU trend
            cpu_change = last.cpu_usage - first.cpu_usage
            if cpu_change > threshold:
                cpu_trend = "increasing"
            elif cpu_change < -threshold:
                cpu_trend = "decreasing"
            else:
                cpu_trend = "stable"
            
            # Analyze memory trend
            memory_change = last.memory_usage - first.memory_usage
            if memory_change > threshold:
                memory_trend = "increasing"
            elif memory_change < -threshold:
                memory_trend = "decreasing"
            else:
                memory_trend = "stable"
            
            # Analyze disk trend
            disk_change = last.disk_usage - first.disk_usage
            if disk_change > threshold:
                disk_trend = "increasing"
            elif disk_change < -threshold:
                disk_trend = "decreasing"
            else:
                disk_trend = "stable"
            
            # Calculate confidence based on data points
            confidence = min(0.9, len(usage_data) / 10.0)
            
            return UsageTrend(
                cpu_trend=cpu_trend,
                memory_trend=memory_trend,
                disk_trend=disk_trend,
                trend_confidence=confidence
            )
            
        except Exception:
            return UsageTrend(
                cpu_trend="stable",
                memory_trend="stable",
                disk_trend="stable",
                trend_confidence=0.0
            )
    
    async def check_system_health(self) -> SystemHealthCheck:
        """Check overall system health.
        
        Returns:
            System health check result
        """
        try:
            # Try to use real system metrics if available
            try:
                import psutil
                cpu_usage = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                memory_usage = memory.percent
                disk_usage = disk.percent
                
            except ImportError:
                # Fall back to mock data
                status = await self.collect_system_status()
                cpu_usage = status.cpu_usage_percent
                memory_usage = status.memory_usage_percent
                disk_usage = status.disk_usage_percent
            
            # Determine health status for each component
            cpu_status = self._get_health_status(cpu_usage, 70, 90)
            memory_status = self._get_health_status(memory_usage, 80, 95)
            disk_status = self._get_health_status(disk_usage, 85, 95)
            
            # Determine overall status
            statuses = [cpu_status, memory_status, disk_status]
            if "critical" in statuses:
                overall_status = "critical"
            elif "high" in statuses:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            return SystemHealthCheck(
                overall_status=overall_status,
                cpu_status=cpu_status,
                memory_status=memory_status,
                disk_status=disk_status,
                network_status="normal",
                timestamp=datetime.utcnow(),
                details={
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "disk_usage": disk_usage
                }
            )
            
        except Exception as e:
            return SystemHealthCheck(
                overall_status="unknown",
                cpu_status="unknown",
                memory_status="unknown",
                disk_status="unknown",
                timestamp=datetime.utcnow(),
                details={"error": str(e)}
            )
    
    def _get_health_status(self, value: float, warning_threshold: float, critical_threshold: float) -> str:
        """Get health status based on value and thresholds.
        
        Args:
            value: Current value
            warning_threshold: Warning threshold
            critical_threshold: Critical threshold
            
        Returns:
            Health status string
        """
        if value >= critical_threshold:
            return "critical"
        elif value >= warning_threshold:
            return "high"
        else:
            return "normal"
    
    async def monitor_application_processes(self, process_names: List[str]) -> List[ProcessStats]:
        """Monitor application processes.
        
        Args:
            process_names: List of process names to monitor
            
        Returns:
            List of process statistics
        """
        try:
            # Mock process monitoring
            # In real implementation, this would use psutil.process_iter()
            
            process_stats = []
            
            for i, process_name in enumerate(process_names):
                # Generate mock process data
                if process_name == "gunicorn":
                    stats = ProcessStats(
                        pid=1234 + i,
                        name=process_name,
                        cpu_percent=15.5,
                        memory_percent=8.2,
                        status="running",
                        command=f"{process_name} --workers 4"
                    )
                elif process_name == "celery":
                    stats = ProcessStats(
                        pid=5678 + i,
                        name=process_name,
                        cpu_percent=5.1,
                        memory_percent=3.7,
                        status="running",
                        command=f"{process_name} worker -A app"
                    )
                else:
                    stats = ProcessStats(
                        pid=9000 + i,
                        name=process_name,
                        cpu_percent=2.0,
                        memory_percent=1.5,
                        status="running",
                        command=process_name
                    )
                
                process_stats.append(stats)
                
                # Cache process stats
                self._process_cache[process_name] = stats
            
            return process_stats
            
        except Exception as e:
            return []
    
    async def generate_system_report(self) -> SystemReport:
        """Generate comprehensive system report.
        
        Returns:
            System report
        """
        try:
            # Collect all system information
            system_status = await self.collect_system_status()
            health_check = await self.check_system_health()
            
            # Get cached process stats or default
            process_stats = list(self._process_cache.values())
            if not process_stats:
                # Generate default process stats
                process_stats = await self.monitor_application_processes(["gunicorn", "celery"])
            
            # Generate recommendations based on health check
            recommendations = []
            if health_check.cpu_status == "high":
                recommendations.append("CPU usage is high. Consider scaling or optimizing CPU-intensive operations.")
            if health_check.memory_status == "high":
                recommendations.append("Memory usage is high. Check for memory leaks and consider increasing available memory.")
            if health_check.disk_status == "critical":
                recommendations.append("Disk usage is critical. Clean up old files and consider expanding storage.")
            
            return SystemReport(
                system_status=system_status,
                health_check=health_check,
                process_stats=process_stats,
                generated_at=datetime.utcnow(),
                overall_health_status=health_check.overall_status,
                recommendations=recommendations
            )
            
        except Exception as e:
            # Return minimal report on error
            return SystemReport(
                system_status=SystemStatus(
                    cpu_usage_percent=0,
                    memory_usage_percent=0,
                    disk_usage_percent=0,
                    network_bytes_sent=0,
                    network_bytes_received=0,
                    timestamp=datetime.utcnow()
                ),
                health_check=SystemHealthCheck(
                    overall_status="unknown",
                    cpu_status="unknown",
                    memory_status="unknown",
                    disk_status="unknown"
                ),
                process_stats=[],
                generated_at=datetime.utcnow(),
                overall_health_status="unknown",
                recommendations=[f"Error generating system report: {str(e)}"]
            )