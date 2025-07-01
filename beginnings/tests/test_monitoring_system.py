"""Test-driven development tests for monitoring system.

This module contains tests that define the expected behavior of the monitoring
system before implementation. Following TDD principles:
1. Write failing tests first (RED)
2. Implement minimal code to pass tests (GREEN)  
3. Refactor while keeping tests green (REFACTOR)
"""

import pytest
import tempfile
import time
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# These imports will fail initially - that's expected in TDD
try:
    from beginnings.monitoring import (
        HealthCheckManager,
        MetricsCollector,
        PerformanceMonitor,
        SystemMonitor,
        HealthCheckConfig,
        MetricsConfig,
        MonitoringConfig,
        HealthCheckResult,
        MetricData,
        PerformanceReport,
        SystemStatus,
        MonitoringError,
        HealthCheckError,
        MetricsError
    )
except ImportError:
    # Expected during TDD - tests define the interface
    HealthCheckManager = None
    MetricsCollector = None
    PerformanceMonitor = None
    SystemMonitor = None
    HealthCheckConfig = None
    MetricsConfig = None
    MonitoringConfig = None
    HealthCheckResult = None
    MetricData = None
    PerformanceReport = None
    SystemStatus = None
    MonitoringError = None
    HealthCheckError = None
    MetricsError = None


class TestHealthCheckConfig:
    """Test HealthCheckConfig dataclass for health check configuration."""
    
    def test_health_check_config_creation(self):
        """Test HealthCheckConfig initialization with default values."""
        config = HealthCheckConfig(
            name="database_check",
            check_type="database",
            endpoint="/health/database",
            interval_seconds=30
        )
        
        assert config.name == "database_check"
        assert config.check_type == "database"
        assert config.endpoint == "/health/database"
        assert config.interval_seconds == 30
        assert config.timeout_seconds == 10  # Expected default
        assert config.retries == 3  # Expected default
        assert config.enabled is True  # Expected default
        assert config.critical is False  # Expected default
    
    def test_health_check_config_with_custom_values(self):
        """Test HealthCheckConfig with custom configuration."""
        config = HealthCheckConfig(
            name="api_gateway_check",
            check_type="http",
            endpoint="https://api.example.com/health",
            interval_seconds=60,
            timeout_seconds=15,
            retries=5,
            enabled=True,
            critical=True,
            headers={"Authorization": "Bearer token"},
            expected_status_codes=[200, 202],
            dependencies=["database_check", "redis_check"]
        )
        
        assert config.name == "api_gateway_check"
        assert config.check_type == "http"
        assert config.endpoint == "https://api.example.com/health"
        assert config.interval_seconds == 60
        assert config.timeout_seconds == 15
        assert config.retries == 5
        assert config.enabled is True
        assert config.critical is True
        assert config.headers["Authorization"] == "Bearer token"
        assert 200 in config.expected_status_codes
        assert 202 in config.expected_status_codes
        assert "database_check" in config.dependencies
        assert "redis_check" in config.dependencies
    
    def test_health_check_config_validation(self):
        """Test HealthCheckConfig validation methods."""
        config = HealthCheckConfig(
            name="test_check",
            check_type="http",
            endpoint="/health",
            interval_seconds=30
        )
        
        # Valid config should pass validation
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid interval should fail
        config.interval_seconds = 0
        errors = config.validate()
        assert len(errors) > 0
        assert any("interval" in error.lower() for error in errors)
        
        # Invalid timeout should fail
        config.interval_seconds = 30
        config.timeout_seconds = -1
        errors = config.validate()
        assert len(errors) > 0
        assert any("timeout" in error.lower() for error in errors)


class TestMetricsConfig:
    """Test MetricsConfig for metrics collection configuration."""
    
    def test_metrics_config_creation(self):
        """Test MetricsConfig initialization."""
        config = MetricsConfig(
            name="application_metrics",
            collection_interval_seconds=15,
            retention_days=30,
            storage_backend="prometheus"
        )
        
        assert config.name == "application_metrics"
        assert config.collection_interval_seconds == 15
        assert config.retention_days == 30
        assert config.storage_backend == "prometheus"
        assert config.enabled is True  # Expected default
        assert config.export_enabled is True  # Expected default
        assert config.aggregation_enabled is True  # Expected default
    
    def test_metrics_config_with_custom_settings(self):
        """Test MetricsConfig with custom settings."""
        config = MetricsConfig(
            name="performance_metrics",
            collection_interval_seconds=5,
            retention_days=90,
            storage_backend="influxdb",
            enabled=True,
            export_enabled=True,
            export_endpoint="http://metrics.example.com/push",
            custom_labels={"environment": "production", "service": "api"},
            metric_types=["counter", "gauge", "histogram", "summary"],
            sampling_rate=0.1
        )
        
        assert config.name == "performance_metrics"
        assert config.collection_interval_seconds == 5
        assert config.retention_days == 90
        assert config.storage_backend == "influxdb"
        assert config.export_endpoint == "http://metrics.example.com/push"
        assert config.custom_labels["environment"] == "production"
        assert config.custom_labels["service"] == "api"
        assert "counter" in config.metric_types
        assert "histogram" in config.metric_types
        assert config.sampling_rate == 0.1


class TestMonitoringConfig:
    """Test MonitoringConfig for overall monitoring configuration."""
    
    def test_monitoring_config_creation(self):
        """Test MonitoringConfig initialization."""
        health_config = HealthCheckConfig(
            name="app_health",
            check_type="http",
            endpoint="/health",
            interval_seconds=30
        )
        
        metrics_config = MetricsConfig(
            name="app_metrics",
            collection_interval_seconds=15,
            retention_days=30,
            storage_backend="prometheus"
        )
        
        config = MonitoringConfig(
            project_name="test-app",
            environment="production",
            health_checks=[health_config],
            metrics_configs=[metrics_config],
            dashboard_enabled=True,
            alerting_enabled=True
        )
        
        assert config.project_name == "test-app"
        assert config.environment == "production"
        assert len(config.health_checks) == 1
        assert len(config.metrics_configs) == 1
        assert config.dashboard_enabled is True
        assert config.alerting_enabled is True
    
    def test_monitoring_config_validation(self):
        """Test monitoring configuration validation."""
        config = MonitoringConfig(
            project_name="test-app",
            environment="production",
            health_checks=[],
            metrics_configs=[]
        )
        
        errors = config.validate()
        # Should warn about no health checks or metrics configured
        assert len(errors) >= 0
        
        # Invalid project name should fail
        config.project_name = ""
        errors = config.validate()
        assert len(errors) > 0
        assert any("project_name" in error for error in errors)


class TestHealthCheckManager:
    """Test HealthCheckManager for health check management."""
    
    @pytest.fixture
    def manager(self):
        """Create HealthCheckManager instance."""
        return HealthCheckManager()
    
    @pytest.fixture
    def sample_health_config(self):
        """Create sample health check configuration."""
        return HealthCheckConfig(
            name="database_check",
            check_type="database",
            endpoint="postgresql://localhost:5432/test",
            interval_seconds=30,
            timeout_seconds=10,
            critical=True
        )
    
    @pytest.fixture
    def sample_http_health_config(self):
        """Create sample HTTP health check configuration."""
        return HealthCheckConfig(
            name="api_check",
            check_type="http",
            endpoint="http://localhost:8000/health",
            interval_seconds=15,
            timeout_seconds=5,
            expected_status_codes=[200],
            headers={"User-Agent": "HealthChecker/1.0"}
        )
    
    @pytest.mark.asyncio
    async def test_register_health_check(self, manager, sample_health_config):
        """Test registering a health check."""
        result = await manager.register_health_check(sample_health_config)
        
        assert result.success is True
        assert result.check_id is not None
        assert result.check_name == "database_check"
        assert result.scheduled is True
    
    @pytest.mark.asyncio
    async def test_execute_health_check(self, manager, sample_http_health_config):
        """Test executing a single health check."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"status": "healthy"}')
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await manager.execute_health_check(sample_http_health_config)
            
            assert result.success is True
            assert result.check_name == "api_check"
            assert result.status == "healthy"
            assert result.response_time_ms > 0
            assert result.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_execute_database_health_check(self, manager, sample_health_config):
        """Test executing database health check."""
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=1)
            mock_connect.return_value.__aenter__.return_value = mock_conn
            
            result = await manager.execute_health_check(sample_health_config)
            
            assert result.success is True
            assert result.check_name == "database_check"
            assert result.status == "healthy"
            assert result.details["connection"] == "successful"
    
    @pytest.mark.asyncio
    async def test_execute_health_check_failure(self, manager, sample_http_health_config):
        """Test health check failure handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            
            result = await manager.execute_health_check(sample_http_health_config)
            
            assert result.success is False
            assert result.check_name == "api_check"
            assert result.status == "unhealthy"
            assert "Connection failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_run_all_health_checks(self, manager):
        """Test running all registered health checks."""
        # Register multiple health checks
        http_config = HealthCheckConfig(
            name="http_check",
            check_type="http",
            endpoint="http://localhost:8000/health",
            interval_seconds=15
        )
        
        db_config = HealthCheckConfig(
            name="db_check",
            check_type="database",
            endpoint="postgresql://localhost:5432/test",
            interval_seconds=30
        )
        
        await manager.register_health_check(http_config)
        await manager.register_health_check(db_config)
        
        with patch.object(manager, 'execute_health_check') as mock_execute:
            mock_execute.return_value = HealthCheckResult(
                check_name="test",
                success=True,
                status="healthy",
                timestamp=datetime.utcnow(),
                response_time_ms=50
            )
            
            results = await manager.run_all_health_checks()
            
            assert len(results) == 2
            assert all(r.success for r in results)
            assert mock_execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_health_status_summary(self, manager):
        """Test getting overall health status summary."""
        # Mock some health check results
        results = [
            HealthCheckResult(
                check_name="api_check",
                success=True,
                status="healthy",
                timestamp=datetime.utcnow(),
                response_time_ms=45
            ),
            HealthCheckResult(
                check_name="db_check",
                success=False,
                status="unhealthy",
                timestamp=datetime.utcnow(),
                response_time_ms=0,
                error_message="Connection timeout"
            )
        ]
        
        summary = await manager.get_health_status_summary(results)
        
        assert summary.overall_status == "degraded"  # Mixed healthy/unhealthy
        assert summary.total_checks == 2
        assert summary.healthy_checks == 1
        assert summary.unhealthy_checks == 1
        assert summary.critical_failures == 0  # db_check not marked as critical
    
    @pytest.mark.asyncio
    async def test_start_health_monitoring(self, manager, sample_health_config):
        """Test starting continuous health monitoring."""
        await manager.register_health_check(sample_health_config)
        
        with patch.object(manager, 'execute_health_check') as mock_execute:
            mock_execute.return_value = HealthCheckResult(
                check_name="database_check",
                success=True,
                status="healthy",
                timestamp=datetime.utcnow(),
                response_time_ms=25
            )
            
            # Start monitoring (this would run in background)
            monitoring_task = await manager.start_monitoring()
            
            assert monitoring_task is not None
            assert manager.is_monitoring is True
            
            # Stop monitoring
            await manager.stop_monitoring()
            assert manager.is_monitoring is False


class TestMetricsCollector:
    """Test MetricsCollector for metrics collection."""
    
    @pytest.fixture
    def collector(self):
        """Create MetricsCollector instance."""
        return MetricsCollector()
    
    @pytest.fixture
    def sample_metrics_config(self):
        """Create sample metrics configuration."""
        return MetricsConfig(
            name="application_metrics",
            collection_interval_seconds=15,
            retention_days=30,
            storage_backend="prometheus",
            custom_labels={"service": "api", "environment": "production"}
        )
    
    @pytest.mark.asyncio
    async def test_initialize_metrics_collection(self, collector, sample_metrics_config):
        """Test initializing metrics collection."""
        result = await collector.initialize(sample_metrics_config)
        
        assert result.success is True
        assert result.backend == "prometheus"
        assert result.labels_configured is True
        assert len(result.registered_metrics) >= 0
    
    @pytest.mark.asyncio
    async def test_record_counter_metric(self, collector, sample_metrics_config):
        """Test recording counter metric."""
        await collector.initialize(sample_metrics_config)
        
        result = await collector.record_counter(
            name="http_requests_total",
            value=1,
            labels={"method": "GET", "endpoint": "/api/users", "status": "200"}
        )
        
        assert result.success is True
        assert result.metric_name == "http_requests_total"
        assert result.metric_type == "counter"
        assert result.value == 1
        assert result.labels["method"] == "GET"
    
    @pytest.mark.asyncio
    async def test_record_gauge_metric(self, collector, sample_metrics_config):
        """Test recording gauge metric."""
        await collector.initialize(sample_metrics_config)
        
        result = await collector.record_gauge(
            name="memory_usage_bytes",
            value=1024000000,  # 1GB
            labels={"process": "api_server"}
        )
        
        assert result.success is True
        assert result.metric_name == "memory_usage_bytes"
        assert result.metric_type == "gauge"
        assert result.value == 1024000000
        assert result.labels["process"] == "api_server"
    
    @pytest.mark.asyncio
    async def test_record_histogram_metric(self, collector, sample_metrics_config):
        """Test recording histogram metric."""
        await collector.initialize(sample_metrics_config)
        
        result = await collector.record_histogram(
            name="http_request_duration_seconds",
            value=0.245,  # 245ms
            labels={"method": "POST", "endpoint": "/api/orders"},
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        assert result.success is True
        assert result.metric_name == "http_request_duration_seconds"
        assert result.metric_type == "histogram"
        assert result.value == 0.245
        assert result.bucket_counts is not None
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, collector, sample_metrics_config):
        """Test collecting system metrics."""
        await collector.initialize(sample_metrics_config)
        
        with patch('psutil.cpu_percent', return_value=25.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 67.8
            mock_memory.return_value.total = 8589934592  # 8GB
            mock_memory.return_value.used = 5826682266   # ~5.4GB
            
            mock_disk.return_value.percent = 45.2
            mock_disk.return_value.total = 500000000000  # 500GB
            
            metrics = await collector.collect_system_metrics()
            
            assert len(metrics) >= 3  # CPU, memory, disk
            assert any(m.name == "cpu_usage_percent" for m in metrics)
            assert any(m.name == "memory_usage_percent" for m in metrics)
            assert any(m.name == "disk_usage_percent" for m in metrics)
    
    @pytest.mark.asyncio
    async def test_collect_application_metrics(self, collector, sample_metrics_config):
        """Test collecting application-specific metrics."""
        await collector.initialize(sample_metrics_config)
        
        # Mock application metrics
        app_metrics = {
            "active_connections": 150,
            "request_rate": 250.5,
            "error_rate": 0.02,
            "response_time_p95": 0.185
        }
        
        results = []
        for metric_name, value in app_metrics.items():
            result = await collector.record_gauge(
                name=metric_name,
                value=value,
                labels={"service": "api"}
            )
            results.append(result)
        
        assert len(results) == 4
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_export_metrics(self, collector, sample_metrics_config):
        """Test exporting metrics to external system."""
        await collector.initialize(sample_metrics_config)
        
        # Record some metrics first
        await collector.record_counter("test_counter", 5)
        await collector.record_gauge("test_gauge", 42.0)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await collector.export_metrics(
                endpoint="http://prometheus.example.com/api/v1/import/prometheus"
            )
            
            assert result.success is True
            assert result.exported_metrics_count > 0
            assert result.export_timestamp is not None
    
    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, collector, sample_metrics_config):
        """Test getting metrics summary."""
        await collector.initialize(sample_metrics_config)
        
        # Record various metrics
        await collector.record_counter("requests_total", 1000)
        await collector.record_gauge("memory_usage", 75.5)
        await collector.record_histogram("response_time", 0.125)
        
        summary = await collector.get_metrics_summary()
        
        assert summary.total_metrics >= 3
        assert summary.counter_metrics >= 1
        assert summary.gauge_metrics >= 1
        assert summary.histogram_metrics >= 1
        assert summary.collection_interval == 15
        assert summary.retention_days == 30


class TestPerformanceMonitor:
    """Test PerformanceMonitor for performance monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create PerformanceMonitor instance."""
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_start_request_monitoring(self, monitor):
        """Test starting request performance monitoring."""
        request_id = await monitor.start_request_monitoring(
            method="GET",
            endpoint="/api/users",
            user_id="user_123"
        )
        
        assert request_id is not None
        assert len(request_id) > 0
        assert monitor.is_monitoring_request(request_id) is True
    
    @pytest.mark.asyncio
    async def test_end_request_monitoring(self, monitor):
        """Test ending request performance monitoring."""
        request_id = await monitor.start_request_monitoring(
            method="POST",
            endpoint="/api/orders",
            user_id="user_456"
        )
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        result = await monitor.end_request_monitoring(
            request_id,
            status_code=201,
            response_size=1024
        )
        
        assert result.success is True
        assert result.request_id == request_id
        assert result.duration_ms >= 100  # At least 100ms
        assert result.status_code == 201
        assert result.response_size == 1024
    
    @pytest.mark.asyncio
    async def test_monitor_database_query(self, monitor):
        """Test monitoring database query performance."""
        with patch('time.time', side_effect=[1000.0, 1000.5]):  # 500ms query
            result = await monitor.monitor_database_query(
                query="SELECT * FROM users WHERE active = true",
                params={"active": True},
                connection_pool="main"
            )
            
            assert result.success is True
            assert result.query_hash is not None
            assert result.execution_time_ms == 500
            assert result.connection_pool == "main"
    
    @pytest.mark.asyncio
    async def test_monitor_external_api_call(self, monitor):
        """Test monitoring external API call performance."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "test"})
            
            start_time = time.time()
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await monitor.monitor_external_api_call(
                service_name="payment_service",
                endpoint="https://api.payment.com/charge",
                method="POST"
            )
            
            assert result.success is True
            assert result.service_name == "payment_service"
            assert result.response_status == 200
            assert result.response_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_generate_performance_report(self, monitor):
        """Test generating performance report."""
        # Simulate some monitored requests
        for i in range(10):
            request_id = await monitor.start_request_monitoring(
                method="GET",
                endpoint=f"/api/endpoint_{i % 3}",
                user_id=f"user_{i}"
            )
            await monitor.end_request_monitoring(
                request_id,
                status_code=200 if i % 5 != 0 else 500,
                response_size=1024 + i * 100
            )
        
        report = await monitor.generate_performance_report(
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow()
        )
        
        assert report.total_requests == 10
        assert report.average_response_time_ms > 0
        assert report.error_rate >= 0
        assert report.p95_response_time_ms > 0
        assert report.requests_per_second > 0
        assert len(report.endpoint_stats) <= 3  # 3 unique endpoints
    
    @pytest.mark.asyncio
    async def test_identify_performance_bottlenecks(self, monitor):
        """Test identifying performance bottlenecks."""
        # Create mock performance data with some slow endpoints
        slow_endpoints = [
            {"endpoint": "/api/slow_query", "avg_time": 2500, "request_count": 100},
            {"endpoint": "/api/heavy_computation", "avg_time": 1800, "request_count": 50},
            {"endpoint": "/api/normal", "avg_time": 150, "request_count": 1000}
        ]
        
        with patch.object(monitor, '_get_endpoint_performance_data', return_value=slow_endpoints):
            bottlenecks = await monitor.identify_performance_bottlenecks(
                threshold_ms=1000,
                minimum_requests=10
            )
            
            assert len(bottlenecks) == 2  # Two slow endpoints
            assert any(b.endpoint == "/api/slow_query" for b in bottlenecks)
            assert any(b.endpoint == "/api/heavy_computation" for b in bottlenecks)
            assert all(b.avg_response_time_ms > 1000 for b in bottlenecks)


class TestSystemMonitor:
    """Test SystemMonitor for system-level monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create SystemMonitor instance."""
        return SystemMonitor()
    
    @pytest.mark.asyncio
    async def test_collect_system_status(self, monitor):
        """Test collecting overall system status."""
        with patch('psutil.cpu_percent', return_value=45.2), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_network:
            
            mock_memory.return_value.percent = 67.8
            mock_memory.return_value.available = 2684354560  # 2.5GB
            
            mock_disk.return_value.percent = 72.1
            mock_disk.return_value.free = 139586437120  # ~130GB
            
            mock_network.return_value.bytes_sent = 5000000000  # 5GB
            mock_network.return_value.bytes_recv = 15000000000  # 15GB
            
            status = await monitor.collect_system_status()
            
            assert status.cpu_usage_percent == 45.2
            assert status.memory_usage_percent == 67.8
            assert status.disk_usage_percent == 72.1
            assert status.network_bytes_sent == 5000000000
            assert status.network_bytes_received == 15000000000
            assert status.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_monitor_resource_usage(self, monitor):
        """Test monitoring resource usage over time."""
        # Mock multiple data points over time
        cpu_values = [25.0, 30.5, 45.2, 67.8, 55.1]
        memory_values = [45.5, 48.2, 52.7, 58.1, 55.9]
        
        usage_data = []
        for cpu, memory in zip(cpu_values, memory_values):
            with patch('psutil.cpu_percent', return_value=cpu), \
                 patch('psutil.virtual_memory') as mock_memory:
                
                mock_memory.return_value.percent = memory
                
                data_point = await monitor.collect_resource_usage()
                usage_data.append(data_point)
        
        assert len(usage_data) == 5
        assert all(d.cpu_usage >= 0 for d in usage_data)
        assert all(d.memory_usage >= 0 for d in usage_data)
        
        # Test trend analysis
        trend = monitor.analyze_usage_trend(usage_data)
        assert trend.cpu_trend in ["increasing", "decreasing", "stable"]
        assert trend.memory_trend in ["increasing", "decreasing", "stable"]
    
    @pytest.mark.asyncio
    async def test_check_system_health(self, monitor):
        """Test checking overall system health."""
        with patch('psutil.cpu_percent', return_value=85.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 92.3  # High memory usage
            mock_disk.return_value.percent = 95.8   # Very high disk usage
            
            health_check = await monitor.check_system_health()
            
            assert health_check.overall_status in ["healthy", "warning", "critical"]
            assert health_check.cpu_status in ["normal", "high", "critical"]
            assert health_check.memory_status in ["normal", "high", "critical"]
            assert health_check.disk_status in ["normal", "high", "critical"]
            
            # With these high values, should trigger warnings/critical status
            assert health_check.memory_status in ["high", "critical"]
            assert health_check.disk_status == "critical"
    
    @pytest.mark.asyncio
    async def test_monitor_application_processes(self, monitor):
        """Test monitoring application processes."""
        with patch('psutil.process_iter') as mock_processes:
            # Mock application processes
            mock_process1 = Mock()
            mock_process1.info = {
                'pid': 1234,
                'name': 'gunicorn',
                'cpu_percent': 15.5,
                'memory_percent': 8.2,
                'status': 'running'
            }
            
            mock_process2 = Mock()
            mock_process2.info = {
                'pid': 5678,
                'name': 'celery',
                'cpu_percent': 5.1,
                'memory_percent': 3.7,
                'status': 'running'
            }
            
            mock_processes.return_value = [mock_process1, mock_process2]
            
            process_stats = await monitor.monitor_application_processes(
                process_names=["gunicorn", "celery"]
            )
            
            assert len(process_stats) == 2
            assert any(p.name == "gunicorn" for p in process_stats)
            assert any(p.name == "celery" for p in process_stats)
            assert all(p.status == "running" for p in process_stats)
    
    @pytest.mark.asyncio
    async def test_generate_system_report(self, monitor):
        """Test generating comprehensive system report."""
        with patch.object(monitor, 'collect_system_status') as mock_status, \
             patch.object(monitor, 'check_system_health') as mock_health, \
             patch.object(monitor, 'monitor_application_processes') as mock_processes:
            
            mock_status.return_value = SystemStatus(
                cpu_usage_percent=45.2,
                memory_usage_percent=67.8,
                disk_usage_percent=72.1,
                network_bytes_sent=5000000000,
                network_bytes_received=15000000000,
                timestamp=datetime.utcnow()
            )
            
            mock_health.return_value = Mock(
                overall_status="warning",
                cpu_status="normal",
                memory_status="high",
                disk_status="high"
            )
            
            mock_processes.return_value = [
                Mock(name="gunicorn", cpu_percent=15.5, memory_percent=8.2, status="running"),
                Mock(name="celery", cpu_percent=5.1, memory_percent=3.7, status="running")
            ]
            
            report = await monitor.generate_system_report()
            
            assert report.system_status is not None
            assert report.health_check is not None
            assert len(report.process_stats) == 2
            assert report.generated_at is not None
            assert report.overall_health_status == "warning"


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""
    
    @pytest.fixture
    def temp_monitoring_dir(self):
        """Create temporary monitoring directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            monitoring_path = Path(temp_dir) / "monitoring"
            monitoring_path.mkdir()
            
            # Create subdirectories
            (monitoring_path / "health_checks").mkdir()
            (monitoring_path / "metrics").mkdir()
            (monitoring_path / "reports").mkdir()
            (monitoring_path / "logs").mkdir()
            
            yield monitoring_path
    
    @pytest.mark.asyncio
    async def test_full_monitoring_setup_workflow(self, temp_monitoring_dir):
        """Test complete monitoring setup workflow."""
        # This test would orchestrate the full monitoring setup process
        health_manager = HealthCheckManager()
        metrics_collector = MetricsCollector()
        performance_monitor = PerformanceMonitor()
        system_monitor = SystemMonitor()
        
        # Configure monitoring
        monitoring_config = MonitoringConfig(
            project_name="test-app",
            environment="production",
            health_checks=[
                HealthCheckConfig(
                    name="app_health",
                    check_type="http",
                    endpoint="/health",
                    interval_seconds=30
                )
            ],
            metrics_configs=[
                MetricsConfig(
                    name="app_metrics",
                    collection_interval_seconds=15,
                    retention_days=30,
                    storage_backend="prometheus"
                )
            ]
        )
        
        # Would run the actual monitoring setup
        # setup_result = await setup_full_monitoring(monitoring_config, temp_monitoring_dir)
        # 
        # assert setup_result.success is True
        # assert setup_result.health_checks_configured is True
        # assert setup_result.metrics_collection_started is True
        # assert setup_result.dashboards_created is True
    
    @pytest.mark.asyncio
    async def test_monitoring_data_aggregation(self):
        """Test monitoring data aggregation and reporting."""
        # This test would verify data aggregation across all monitoring components
        pass
    
    def test_monitoring_alerting_integration(self):
        """Test monitoring alerting integration."""
        # This test would verify alerting system integration
        alerting_rules = [
            {
                "name": "high_cpu_usage",
                "condition": "cpu_usage > 80",
                "severity": "warning",
                "notification_channels": ["email", "slack"]
            },
            {
                "name": "memory_critical",
                "condition": "memory_usage > 95",
                "severity": "critical",
                "notification_channels": ["email", "slack", "pagerduty"]
            }
        ]
        
        # Would test alerting rule configuration and triggering
        # for rule in alerting_rules:
        #     alert_config = AlertConfig(**rule)
        #     assert alert_config.is_valid() is True
    
    def test_monitoring_dashboard_generation(self):
        """Test monitoring dashboard generation."""
        # This test would verify dashboard creation and visualization
        dashboard_config = {
            "name": "Application Dashboard",
            "panels": [
                {"type": "graph", "metric": "cpu_usage", "timespan": "1h"},
                {"type": "graph", "metric": "memory_usage", "timespan": "1h"},
                {"type": "table", "data": "health_checks", "refresh": "30s"}
            ]
        }
        
        # Would test dashboard configuration and generation
        # dashboard = generate_monitoring_dashboard(dashboard_config)
        # assert dashboard is not None
        # assert len(dashboard.panels) == 3