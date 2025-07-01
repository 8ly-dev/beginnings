"""Test-driven development tests for alerting and logging systems.

This module contains tests that define the expected behavior of the alerting
and logging systems before implementation. Following TDD principles:
1. Write failing tests first (RED)
2. Implement minimal code to pass tests (GREEN)  
3. Refactor while keeping tests green (REFACTOR)
"""

import pytest
import tempfile
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

# These imports will fail initially - that's expected in TDD
try:
    from beginnings.alerting import (
        AlertManager,
        NotificationManager,
        AlertRule,
        AlertConfig,
        NotificationConfig,
        AlertCondition,
        AlertSeverity,
        AlertState,
        AlertResult,
        NotificationResult,
        AlertingError,
        NotificationError
    )
    from beginnings.logging import (
        LogManager,
        LogProcessor,
        LogAnalyzer,
        LogConfig,
        LogEntry,
        LogLevel,
        LogFormat,
        LogFilter,
        LogAggregator,
        LogResult,
        LoggingError,
        LogAnalysisResult
    )
except ImportError:
    # Expected during TDD - tests define the interface
    AlertManager = None
    NotificationManager = None
    AlertRule = None
    AlertConfig = None
    NotificationConfig = None
    AlertCondition = None
    AlertSeverity = None
    AlertState = None
    AlertResult = None
    NotificationResult = None
    AlertingError = None
    NotificationError = None
    LogManager = None
    LogProcessor = None
    LogAnalyzer = None
    LogConfig = None
    LogEntry = None
    LogLevel = None
    LogFormat = None
    LogFilter = None
    LogAggregator = None
    LogResult = None
    LoggingError = None
    LogAnalysisResult = None


class TestAlertSeverity:
    """Test AlertSeverity enum for alert severity levels."""
    
    def test_alert_severity_values(self):
        """Test AlertSeverity enum values."""
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_alert_severity_ordering(self):
        """Test AlertSeverity ordering for priority."""
        # Should be orderable for priority handling
        assert AlertSeverity.CRITICAL > AlertSeverity.HIGH
        assert AlertSeverity.HIGH > AlertSeverity.MEDIUM
        assert AlertSeverity.MEDIUM > AlertSeverity.LOW


class TestAlertCondition:
    """Test AlertCondition dataclass for alert conditions."""
    
    def test_alert_condition_creation(self):
        """Test AlertCondition initialization."""
        condition = AlertCondition(
            metric_name="cpu_usage_percent",
            operator="greater_than",
            threshold_value=80.0,
            duration_minutes=5
        )
        
        assert condition.metric_name == "cpu_usage_percent"
        assert condition.operator == "greater_than"
        assert condition.threshold_value == 80.0
        assert condition.duration_minutes == 5
        assert condition.aggregation_function == "avg"  # Expected default
        assert condition.evaluation_window_minutes == 1  # Expected default
    
    def test_alert_condition_with_complex_logic(self):
        """Test AlertCondition with complex logic."""
        condition = AlertCondition(
            metric_name="error_rate",
            operator="greater_than",
            threshold_value=0.05,  # 5% error rate
            duration_minutes=2,
            aggregation_function="max",
            evaluation_window_minutes=5,
            labels_filter={"service": "api", "environment": "production"},
            custom_query="rate(http_requests_total{status=~'5..'}[5m])"
        )
        
        assert condition.metric_name == "error_rate"
        assert condition.operator == "greater_than"
        assert condition.threshold_value == 0.05
        assert condition.aggregation_function == "max"
        assert condition.evaluation_window_minutes == 5
        assert condition.labels_filter["service"] == "api"
        assert condition.custom_query is not None
    
    def test_alert_condition_validation(self):
        """Test AlertCondition validation."""
        condition = AlertCondition(
            metric_name="memory_usage",
            operator="greater_than",
            threshold_value=85.0,
            duration_minutes=3
        )
        
        # Valid condition should pass
        errors = condition.validate()
        assert len(errors) == 0
        
        # Invalid operator should fail
        condition.operator = "invalid_operator"
        errors = condition.validate()
        assert len(errors) > 0
        assert any("operator" in error.lower() for error in errors)
        
        # Invalid duration should fail
        condition.operator = "greater_than"
        condition.duration_minutes = 0
        errors = condition.validate()
        assert len(errors) > 0
        assert any("duration" in error.lower() for error in errors)


class TestAlertRule:
    """Test AlertRule dataclass for alert rule configuration."""
    
    def test_alert_rule_creation(self):
        """Test AlertRule initialization."""
        condition = AlertCondition(
            metric_name="cpu_usage_percent",
            operator="greater_than",
            threshold_value=80.0,
            duration_minutes=5
        )
        
        rule = AlertRule(
            name="high_cpu_usage",
            description="Alert when CPU usage is high",
            condition=condition,
            severity=AlertSeverity.HIGH,
            enabled=True
        )
        
        assert rule.name == "high_cpu_usage"
        assert rule.description == "Alert when CPU usage is high"
        assert rule.condition == condition
        assert rule.severity == AlertSeverity.HIGH
        assert rule.enabled is True
        assert rule.notification_channels == []  # Expected default
        assert rule.cooldown_minutes == 60  # Expected default
    
    def test_alert_rule_with_notifications(self):
        """Test AlertRule with notification configuration."""
        condition = AlertCondition(
            metric_name="disk_usage_percent",
            operator="greater_than",
            threshold_value=90.0,
            duration_minutes=1
        )
        
        rule = AlertRule(
            name="disk_space_critical",
            description="Critical disk space alert",
            condition=condition,
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            notification_channels=["email", "slack", "pagerduty"],
            cooldown_minutes=30,
            tags=["infrastructure", "storage"],
            runbook_url="https://wiki.example.com/runbooks/disk-space"
        )
        
        assert rule.name == "disk_space_critical"
        assert rule.severity == AlertSeverity.CRITICAL
        assert "email" in rule.notification_channels
        assert "slack" in rule.notification_channels
        assert "pagerduty" in rule.notification_channels
        assert rule.cooldown_minutes == 30
        assert "infrastructure" in rule.tags
        assert rule.runbook_url is not None
    
    def test_alert_rule_validation(self):
        """Test AlertRule validation."""
        condition = AlertCondition(
            metric_name="memory_usage",
            operator="greater_than",
            threshold_value=85.0,
            duration_minutes=3
        )
        
        rule = AlertRule(
            name="memory_alert",
            description="Memory usage alert",
            condition=condition,
            severity=AlertSeverity.MEDIUM,
            enabled=True
        )
        
        # Valid rule should pass
        errors = rule.validate()
        assert len(errors) == 0
        
        # Empty name should fail
        rule.name = ""
        errors = rule.validate()
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)


class TestNotificationConfig:
    """Test NotificationConfig for notification channel configuration."""
    
    def test_email_notification_config(self):
        """Test email notification configuration."""
        config = NotificationConfig(
            channel_type="email",
            channel_name="production_alerts",
            enabled=True,
            settings={
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "alerts@example.com",
                "recipients": ["admin@example.com", "oncall@example.com"],
                "subject_template": "[ALERT] {severity}: {rule_name}",
                "use_tls": True
            }
        )
        
        assert config.channel_type == "email"
        assert config.channel_name == "production_alerts"
        assert config.enabled is True
        assert config.settings["smtp_server"] == "smtp.example.com"
        assert "admin@example.com" in config.settings["recipients"]
    
    def test_slack_notification_config(self):
        """Test Slack notification configuration."""
        config = NotificationConfig(
            channel_type="slack",
            channel_name="alerts_channel",
            enabled=True,
            settings={
                "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
                "channel": "#alerts",
                "username": "AlertBot",
                "icon_emoji": ":warning:",
                "mention_users": ["@oncall", "@admin"],
                "thread_alerts": True
            }
        )
        
        assert config.channel_type == "slack"
        assert config.channel_name == "alerts_channel"
        assert config.settings["channel"] == "#alerts"
        assert config.settings["username"] == "AlertBot"
        assert "@oncall" in config.settings["mention_users"]
    
    def test_pagerduty_notification_config(self):
        """Test PagerDuty notification configuration."""
        config = NotificationConfig(
            channel_type="pagerduty",
            channel_name="critical_alerts",
            enabled=True,
            settings={
                "integration_key": "abcdef1234567890abcdef1234567890",
                "service_id": "PXXXXXX",
                "escalation_policy": "P123456",
                "severity_mapping": {
                    "critical": "critical",
                    "high": "error",
                    "medium": "warning",
                    "low": "info"
                }
            }
        )
        
        assert config.channel_type == "pagerduty"
        assert config.settings["integration_key"] is not None
        assert config.settings["service_id"] == "PXXXXXX"
        assert config.settings["severity_mapping"]["critical"] == "critical"


class TestAlertManager:
    """Test AlertManager for alert management."""
    
    @pytest.fixture
    def manager(self):
        """Create AlertManager instance."""
        return AlertManager()
    
    @pytest.fixture
    def sample_alert_rule(self):
        """Create sample alert rule."""
        condition = AlertCondition(
            metric_name="cpu_usage_percent",
            operator="greater_than",
            threshold_value=80.0,
            duration_minutes=5
        )
        
        return AlertRule(
            name="high_cpu_usage",
            description="Alert when CPU usage exceeds 80%",
            condition=condition,
            severity=AlertSeverity.HIGH,
            enabled=True,
            notification_channels=["email", "slack"]
        )
    
    @pytest.mark.asyncio
    async def test_register_alert_rule(self, manager, sample_alert_rule):
        """Test registering an alert rule."""
        result = await manager.register_alert_rule(sample_alert_rule)
        
        assert result.success is True
        assert result.rule_id is not None
        assert result.rule_name == "high_cpu_usage"
        assert result.enabled is True
    
    @pytest.mark.asyncio
    async def test_evaluate_alert_condition(self, manager, sample_alert_rule):
        """Test evaluating alert condition against metrics."""
        # Mock metrics data
        metric_data = {
            "cpu_usage_percent": [
                {"timestamp": datetime.utcnow(), "value": 85.5},
                {"timestamp": datetime.utcnow() - timedelta(minutes=1), "value": 87.2},
                {"timestamp": datetime.utcnow() - timedelta(minutes=2), "value": 82.1}
            ]
        }
        
        result = await manager.evaluate_alert_condition(
            sample_alert_rule.condition, 
            metric_data
        )
        
        assert result.condition_met is True
        assert result.current_value >= 80.0
        assert result.threshold_value == 80.0
        assert result.duration_exceeded is True
    
    @pytest.mark.asyncio
    async def test_trigger_alert(self, manager, sample_alert_rule):
        """Test triggering an alert."""
        await manager.register_alert_rule(sample_alert_rule)
        
        # Mock alert evaluation result
        evaluation_result = Mock()
        evaluation_result.condition_met = True
        evaluation_result.current_value = 85.5
        evaluation_result.threshold_value = 80.0
        evaluation_result.duration_exceeded = True
        
        with patch.object(manager, '_send_notifications') as mock_send:
            mock_send.return_value = True
            
            alert_result = await manager.trigger_alert(
                sample_alert_rule, 
                evaluation_result
            )
            
            assert alert_result.success is True
            assert alert_result.alert_id is not None
            assert alert_result.rule_name == "high_cpu_usage"
            assert alert_result.severity == AlertSeverity.HIGH
            assert alert_result.state == AlertState.FIRING
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, manager, sample_alert_rule):
        """Test resolving an alert."""
        # First trigger an alert
        await manager.register_alert_rule(sample_alert_rule)
        
        evaluation_result = Mock()
        evaluation_result.condition_met = True
        evaluation_result.current_value = 85.5
        
        with patch.object(manager, '_send_notifications'):
            alert_result = await manager.trigger_alert(sample_alert_rule, evaluation_result)
            alert_id = alert_result.alert_id
            
            # Now resolve it
            resolve_result = await manager.resolve_alert(
                alert_id,
                resolution_reason="CPU usage returned to normal"
            )
            
            assert resolve_result.success is True
            assert resolve_result.alert_id == alert_id
            assert resolve_result.state == AlertState.RESOLVED
            assert resolve_result.resolution_reason is not None
    
    @pytest.mark.asyncio
    async def test_suppress_alert(self, manager, sample_alert_rule):
        """Test suppressing an alert."""
        await manager.register_alert_rule(sample_alert_rule)
        
        suppress_result = await manager.suppress_alert(
            rule_name="high_cpu_usage",
            suppress_duration_minutes=60,
            suppress_reason="Planned maintenance"
        )
        
        assert suppress_result.success is True
        assert suppress_result.rule_name == "high_cpu_usage"
        assert suppress_result.suppressed_until is not None
        assert suppress_result.suppress_reason == "Planned maintenance"
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, manager):
        """Test getting active alerts."""
        # Mock some active alerts
        mock_alerts = [
            Mock(
                alert_id="alert_001",
                rule_name="high_cpu_usage",
                severity=AlertSeverity.HIGH,
                state=AlertState.FIRING,
                triggered_at=datetime.utcnow()
            ),
            Mock(
                alert_id="alert_002", 
                rule_name="memory_warning",
                severity=AlertSeverity.MEDIUM,
                state=AlertState.FIRING,
                triggered_at=datetime.utcnow() - timedelta(minutes=30)
            )
        ]
        
        with patch.object(manager, '_get_alerts_by_state', return_value=mock_alerts):
            active_alerts = await manager.get_active_alerts()
            
            assert len(active_alerts) == 2
            assert all(alert.state == AlertState.FIRING for alert in active_alerts)
            assert any(alert.rule_name == "high_cpu_usage" for alert in active_alerts)
    
    @pytest.mark.asyncio
    async def test_run_alert_evaluation_cycle(self, manager, sample_alert_rule):
        """Test running complete alert evaluation cycle."""
        await manager.register_alert_rule(sample_alert_rule)
        
        # Mock metrics retrieval
        with patch.object(manager, '_get_metrics_data') as mock_metrics, \
             patch.object(manager, 'evaluate_alert_condition') as mock_evaluate:
            
            mock_metrics.return_value = {"cpu_usage_percent": [{"value": 85.0}]}
            mock_evaluate.return_value = Mock(
                condition_met=True,
                current_value=85.0,
                duration_exceeded=True
            )
            
            cycle_result = await manager.run_evaluation_cycle()
            
            assert cycle_result.success is True
            assert cycle_result.rules_evaluated >= 1
            assert cycle_result.alerts_triggered >= 0
            assert cycle_result.evaluation_duration_ms > 0


class TestNotificationManager:
    """Test NotificationManager for notification delivery."""
    
    @pytest.fixture
    def manager(self):
        """Create NotificationManager instance."""
        return NotificationManager()
    
    @pytest.fixture
    def email_config(self):
        """Create email notification configuration."""
        return NotificationConfig(
            channel_type="email",
            channel_name="production_alerts",
            enabled=True,
            settings={
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "alerts@example.com",
                "recipients": ["admin@example.com"],
                "use_tls": True
            }
        )
    
    @pytest.fixture
    def slack_config(self):
        """Create Slack notification configuration."""
        return NotificationConfig(
            channel_type="slack",
            channel_name="alerts_channel",
            enabled=True,
            settings={
                "webhook_url": "https://hooks.slack.com/test",
                "channel": "#alerts"
            }
        )
    
    @pytest.mark.asyncio
    async def test_register_notification_channel(self, manager, email_config):
        """Test registering notification channel."""
        result = await manager.register_notification_channel(email_config)
        
        assert result.success is True
        assert result.channel_id is not None
        assert result.channel_name == "production_alerts"
        assert result.channel_type == "email"
    
    @pytest.mark.asyncio
    async def test_send_email_notification(self, manager, email_config):
        """Test sending email notification."""
        await manager.register_notification_channel(email_config)
        
        alert_data = {
            "rule_name": "high_cpu_usage",
            "severity": "high",
            "current_value": 85.5,
            "threshold_value": 80.0,
            "message": "CPU usage is above threshold"
        }
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            result = await manager.send_notification(
                channel_name="production_alerts",
                alert_data=alert_data
            )
            
            assert result.success is True
            assert result.channel_name == "production_alerts"
            assert result.delivery_time_ms > 0
            assert result.message_id is not None
    
    @pytest.mark.asyncio
    async def test_send_slack_notification(self, manager, slack_config):
        """Test sending Slack notification."""
        await manager.register_notification_channel(slack_config)
        
        alert_data = {
            "rule_name": "memory_warning",
            "severity": "medium",
            "current_value": 88.2,
            "threshold_value": 85.0,
            "message": "Memory usage is elevated"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="ok")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await manager.send_notification(
                channel_name="alerts_channel",
                alert_data=alert_data
            )
            
            assert result.success is True
            assert result.channel_name == "alerts_channel"
            assert result.delivery_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_batch_send_notifications(self, manager, email_config, slack_config):
        """Test sending notifications to multiple channels."""
        await manager.register_notification_channel(email_config)
        await manager.register_notification_channel(slack_config)
        
        alert_data = {
            "rule_name": "disk_space_critical",
            "severity": "critical",
            "current_value": 95.8,
            "threshold_value": 90.0,
            "message": "Disk space critically low"
        }
        
        with patch.object(manager, 'send_notification') as mock_send:
            mock_send.return_value = Mock(success=True, delivery_time_ms=150)
            
            results = await manager.batch_send_notifications(
                channel_names=["production_alerts", "alerts_channel"],
                alert_data=alert_data
            )
            
            assert len(results) == 2
            assert all(r.success for r in results)
            assert mock_send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_notification_retry_logic(self, manager, email_config):
        """Test notification retry logic on failure."""
        await manager.register_notification_channel(email_config)
        
        alert_data = {
            "rule_name": "test_alert",
            "severity": "high",
            "message": "Test alert message"
        }
        
        with patch('aiosmtplib.send') as mock_send:
            # First two attempts fail, third succeeds
            mock_send.side_effect = [
                Exception("SMTP timeout"),
                Exception("SMTP connection failed"),
                True
            ]
            
            result = await manager.send_notification(
                channel_name="production_alerts",
                alert_data=alert_data,
                max_retries=3
            )
            
            assert result.success is True
            assert result.retry_count == 2
            assert mock_send.call_count == 3
    
    @pytest.mark.asyncio
    async def test_notification_rate_limiting(self, manager, email_config):
        """Test notification rate limiting."""
        await manager.register_notification_channel(email_config)
        
        # Configure rate limiting: max 5 notifications per minute
        await manager.configure_rate_limiting(
            channel_name="production_alerts",
            max_notifications_per_minute=5
        )
        
        alert_data = {"rule_name": "test", "message": "Test"}
        
        # Send 6 notifications rapidly
        results = []
        for i in range(6):
            result = await manager.send_notification(
                channel_name="production_alerts",
                alert_data=alert_data
            )
            results.append(result)
        
        # First 5 should succeed, 6th should be rate limited
        successful = [r for r in results if r.success]
        rate_limited = [r for r in results if not r.success and "rate limit" in r.error_message.lower()]
        
        assert len(successful) <= 5
        assert len(rate_limited) >= 1


class TestLogLevel:
    """Test LogLevel enum for log level definitions."""
    
    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"
    
    def test_log_level_ordering(self):
        """Test LogLevel ordering for filtering."""
        assert LogLevel.CRITICAL > LogLevel.ERROR
        assert LogLevel.ERROR > LogLevel.WARNING
        assert LogLevel.WARNING > LogLevel.INFO
        assert LogLevel.INFO > LogLevel.DEBUG


class TestLogEntry:
    """Test LogEntry dataclass for log entry structure."""
    
    def test_log_entry_creation(self):
        """Test LogEntry initialization."""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            message="User login successful",
            logger_name="auth.login",
            module="auth.py",
            function="authenticate_user",
            line_number=125
        )
        
        assert entry.level == LogLevel.INFO
        assert entry.message == "User login successful"
        assert entry.logger_name == "auth.login"
        assert entry.module == "auth.py"
        assert entry.function == "authenticate_user"
        assert entry.line_number == 125
        assert entry.context == {}  # Expected default
        assert entry.trace_id is None  # Expected default
    
    def test_log_entry_with_context(self):
        """Test LogEntry with context data."""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.ERROR,
            message="Database connection failed",
            logger_name="database.connection",
            context={
                "user_id": "user_123",
                "session_id": "sess_456",
                "database_host": "db.example.com",
                "error_code": "CONNECTION_TIMEOUT"
            },
            trace_id="trace_789",
            span_id="span_012",
            exception_info={
                "type": "ConnectionTimeoutError",
                "message": "Connection timed out after 30 seconds",
                "stack_trace": "Traceback (most recent call last)..."
            }
        )
        
        assert entry.level == LogLevel.ERROR
        assert entry.context["user_id"] == "user_123"
        assert entry.context["error_code"] == "CONNECTION_TIMEOUT"
        assert entry.trace_id == "trace_789"
        assert entry.span_id == "span_012"
        assert entry.exception_info["type"] == "ConnectionTimeoutError"


class TestLogConfig:
    """Test LogConfig for logging configuration."""
    
    def test_log_config_creation(self):
        """Test LogConfig initialization."""
        config = LogConfig(
            name="application_logs",
            level=LogLevel.INFO,
            format=LogFormat.JSON,
            output_file="/var/log/app.log",
            max_file_size_mb=100,
            backup_count=5
        )
        
        assert config.name == "application_logs"
        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.JSON
        assert config.output_file == "/var/log/app.log"
        assert config.max_file_size_mb == 100
        assert config.backup_count == 5
        assert config.structured_logging is True  # Expected default
        assert config.async_logging is True  # Expected default
    
    def test_log_config_with_filters(self):
        """Test LogConfig with filtering options."""
        config = LogConfig(
            name="filtered_logs",
            level=LogLevel.WARNING,
            format=LogFormat.TEXT,
            output_file="/var/log/warnings.log",
            include_modules=["auth", "payment", "security"],
            exclude_modules=["debug", "test"],
            include_loggers=["security.*", "auth.login"],
            rate_limit_per_minute=1000,
            buffer_size=10000
        )
        
        assert config.name == "filtered_logs"
        assert config.level == LogLevel.WARNING
        assert "auth" in config.include_modules
        assert "payment" in config.include_modules
        assert "debug" in config.exclude_modules
        assert "security.*" in config.include_loggers
        assert config.rate_limit_per_minute == 1000
        assert config.buffer_size == 10000


class TestLogManager:
    """Test LogManager for log management."""
    
    @pytest.fixture
    def manager(self):
        """Create LogManager instance."""
        return LogManager()
    
    @pytest.fixture
    def sample_log_config(self):
        """Create sample log configuration."""
        return LogConfig(
            name="application_logs",
            level=LogLevel.INFO,
            format=LogFormat.JSON,
            output_file="/tmp/test_app.log",
            structured_logging=True,
            async_logging=True
        )
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_initialize_logging(self, manager, sample_log_config):
        """Test initializing logging configuration."""
        result = await manager.initialize_logging(sample_log_config)
        
        assert result.success is True
        assert result.logger_name == "application_logs"
        assert result.output_file == "/tmp/test_app.log"
        assert result.level == LogLevel.INFO
    
    @pytest.mark.asyncio
    async def test_log_message(self, manager, sample_log_config, temp_log_dir):
        """Test logging a message."""
        # Update config to use temp directory
        sample_log_config.output_file = str(temp_log_dir / "test.log")
        await manager.initialize_logging(sample_log_config)
        
        result = await manager.log(
            level=LogLevel.INFO,
            message="Test log message",
            logger_name="test.logger",
            context={"user_id": "user_123", "action": "login"}
        )
        
        assert result.success is True
        assert result.log_entry is not None
        assert result.log_entry.level == LogLevel.INFO
        assert result.log_entry.message == "Test log message"
        assert result.log_entry.context["user_id"] == "user_123"
    
    @pytest.mark.asyncio
    async def test_structured_logging(self, manager, sample_log_config, temp_log_dir):
        """Test structured logging with JSON format."""
        sample_log_config.output_file = str(temp_log_dir / "structured.log")
        sample_log_config.format = LogFormat.JSON
        await manager.initialize_logging(sample_log_config)
        
        await manager.log(
            level=LogLevel.ERROR,
            message="Payment processing failed",
            logger_name="payment.processor",
            context={
                "transaction_id": "txn_456",
                "amount": 99.99,
                "currency": "USD",
                "error_code": "INSUFFICIENT_FUNDS"
            },
            trace_id="trace_789"
        )
        
        # Verify JSON format in log file
        log_file = Path(sample_log_config.output_file)
        assert log_file.exists()
        
        log_content = log_file.read_text()
        log_data = json.loads(log_content.strip())
        
        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Payment processing failed"
        assert log_data["context"]["transaction_id"] == "txn_456"
        assert log_data["trace_id"] == "trace_789"
    
    @pytest.mark.asyncio
    async def test_log_filtering(self, manager, temp_log_dir):
        """Test log filtering by level and modules."""
        config = LogConfig(
            name="filtered_logs",
            level=LogLevel.WARNING,  # Only WARNING and above
            format=LogFormat.JSON,
            output_file=str(temp_log_dir / "filtered.log"),
            include_modules=["auth", "payment"],
            exclude_modules=["debug"]
        )
        await manager.initialize_logging(config)
        
        # These should be logged (WARNING level)
        await manager.log(LogLevel.WARNING, "Auth warning", "auth.login")
        await manager.log(LogLevel.ERROR, "Payment error", "payment.processor")
        
        # These should be filtered out
        await manager.log(LogLevel.INFO, "Info message", "auth.login")  # Level too low
        await manager.log(LogLevel.ERROR, "Debug error", "debug.utils")  # Excluded module
        await manager.log(LogLevel.WARNING, "Other warning", "other.module")  # Not included
        
        # Verify only 2 entries were logged
        log_file = Path(config.output_file)
        log_lines = log_file.read_text().strip().split('\n')
        assert len(log_lines) == 2
    
    @pytest.mark.asyncio
    async def test_log_rotation(self, manager, temp_log_dir):
        """Test log file rotation."""
        config = LogConfig(
            name="rotating_logs",
            level=LogLevel.INFO,
            format=LogFormat.TEXT,
            output_file=str(temp_log_dir / "rotating.log"),
            max_file_size_mb=1,  # Very small for testing
            backup_count=3
        )
        await manager.initialize_logging(config)
        
        # Write enough data to trigger rotation
        large_message = "x" * 1000000  # 1MB message
        
        for i in range(5):
            await manager.log(
                LogLevel.INFO,
                f"Large message {i}: {large_message}",
                "test.logger"
            )
        
        # Should have created backup files
        log_files = list(temp_log_dir.glob("rotating.log*"))
        assert len(log_files) > 1  # Original + at least one backup
    
    @pytest.mark.asyncio
    async def test_async_logging_performance(self, manager, sample_log_config, temp_log_dir):
        """Test async logging performance."""
        sample_log_config.output_file = str(temp_log_dir / "async.log")
        sample_log_config.async_logging = True
        sample_log_config.buffer_size = 1000
        await manager.initialize_logging(sample_log_config)
        
        import time
        start_time = time.time()
        
        # Log many messages quickly
        tasks = []
        for i in range(100):
            task = manager.log(
                LogLevel.INFO,
                f"Test message {i}",
                "performance.test",
                context={"iteration": i}
            )
            tasks.append(task)
        
        # Wait for all logs to complete
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        assert all(r.success for r in results)
        assert (end_time - start_time) < 1.0  # Should be fast with async logging


class TestLogProcessor:
    """Test LogProcessor for log processing and analysis."""
    
    @pytest.fixture
    def processor(self):
        """Create LogProcessor instance."""
        return LogProcessor()
    
    @pytest.fixture
    def sample_log_entries(self):
        """Create sample log entries for testing."""
        base_time = datetime.utcnow()
        return [
            LogEntry(
                timestamp=base_time - timedelta(minutes=10),
                level=LogLevel.INFO,
                message="User login successful",
                logger_name="auth.login",
                context={"user_id": "user_123"}
            ),
            LogEntry(
                timestamp=base_time - timedelta(minutes=8),
                level=LogLevel.WARNING,
                message="Slow database query detected",
                logger_name="database.monitor",
                context={"query_time": 2.5, "table": "users"}
            ),
            LogEntry(
                timestamp=base_time - timedelta(minutes=5),
                level=LogLevel.ERROR,
                message="Payment processing failed",
                logger_name="payment.processor",
                context={"user_id": "user_456", "amount": 99.99, "error": "CARD_DECLINED"}
            ),
            LogEntry(
                timestamp=base_time - timedelta(minutes=2),
                level=LogLevel.ERROR,
                message="Database connection lost",
                logger_name="database.connection",
                context={"host": "db.example.com", "retry_count": 3}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_parse_log_file(self, processor, temp_log_dir):
        """Test parsing log file."""
        log_file = temp_log_dir / "test.log"
        
        # Create sample log file content
        log_content = [
            '{"timestamp": "2023-01-01T12:00:00Z", "level": "INFO", "message": "Application started"}',
            '{"timestamp": "2023-01-01T12:01:00Z", "level": "WARNING", "message": "High memory usage"}',
            '{"timestamp": "2023-01-01T12:02:00Z", "level": "ERROR", "message": "Database error"}'
        ]
        log_file.write_text('\n'.join(log_content))
        
        entries = await processor.parse_log_file(str(log_file), LogFormat.JSON)
        
        assert len(entries) == 3
        assert entries[0].level == LogLevel.INFO
        assert entries[0].message == "Application started"
        assert entries[1].level == LogLevel.WARNING
        assert entries[2].level == LogLevel.ERROR
    
    @pytest.mark.asyncio
    async def test_filter_log_entries(self, processor, sample_log_entries):
        """Test filtering log entries by criteria."""
        # Filter by level
        error_entries = await processor.filter_entries(
            sample_log_entries,
            level_filter=LogLevel.ERROR
        )
        assert len(error_entries) == 2
        assert all(entry.level == LogLevel.ERROR for entry in error_entries)
        
        # Filter by logger name
        auth_entries = await processor.filter_entries(
            sample_log_entries,
            logger_filter="auth.*"
        )
        assert len(auth_entries) == 1
        assert auth_entries[0].logger_name == "auth.login"
        
        # Filter by time range
        recent_entries = await processor.filter_entries(
            sample_log_entries,
            start_time=datetime.utcnow() - timedelta(minutes=6),
            end_time=datetime.utcnow()
        )
        assert len(recent_entries) == 2  # Last 6 minutes
    
    @pytest.mark.asyncio
    async def test_aggregate_log_data(self, processor, sample_log_entries):
        """Test aggregating log data by various dimensions."""
        aggregation = await processor.aggregate_logs(
            sample_log_entries,
            group_by="level",
            time_window_minutes=60
        )
        
        assert "INFO" in aggregation
        assert "WARNING" in aggregation
        assert "ERROR" in aggregation
        assert aggregation["INFO"]["count"] == 1
        assert aggregation["ERROR"]["count"] == 2
        
        # Aggregate by logger
        logger_aggregation = await processor.aggregate_logs(
            sample_log_entries,
            group_by="logger_name"
        )
        
        assert "auth.login" in logger_aggregation
        assert "payment.processor" in logger_aggregation
        assert "database.connection" in logger_aggregation
    
    @pytest.mark.asyncio
    async def test_detect_log_patterns(self, processor, sample_log_entries):
        """Test detecting patterns in log data."""
        patterns = await processor.detect_patterns(
            sample_log_entries,
            pattern_types=["error_bursts", "repeated_messages", "anomalies"]
        )
        
        assert "error_bursts" in patterns
        assert "repeated_messages" in patterns
        
        # Should detect error burst (2 errors close together)
        error_burst = patterns["error_bursts"]
        assert len(error_burst) > 0
    
    @pytest.mark.asyncio
    async def test_extract_metrics_from_logs(self, processor, sample_log_entries):
        """Test extracting metrics from log entries."""
        metrics = await processor.extract_metrics(sample_log_entries)
        
        assert metrics.total_entries == 4
        assert metrics.error_count == 2
        assert metrics.warning_count == 1
        assert metrics.info_count == 1
        assert metrics.error_rate == 0.5  # 2 errors out of 4 total
        assert len(metrics.top_loggers) > 0
        assert len(metrics.top_errors) > 0


class TestLogAnalyzer:
    """Test LogAnalyzer for advanced log analysis."""
    
    @pytest.fixture
    def analyzer(self):
        """Create LogAnalyzer instance."""
        return LogAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_error_trends(self, analyzer):
        """Test analyzing error trends over time."""
        # Mock historical error data
        error_data = [
            {"timestamp": datetime.utcnow() - timedelta(hours=24), "error_count": 5},
            {"timestamp": datetime.utcnow() - timedelta(hours=18), "error_count": 8},
            {"timestamp": datetime.utcnow() - timedelta(hours=12), "error_count": 12},
            {"timestamp": datetime.utcnow() - timedelta(hours=6), "error_count": 15},
            {"timestamp": datetime.utcnow() - timedelta(hours=1), "error_count": 20}
        ]
        
        trend_analysis = await analyzer.analyze_error_trends(
            error_data,
            time_window_hours=24
        )
        
        assert trend_analysis.trend_direction == "increasing"
        assert trend_analysis.trend_strength > 0.5  # Strong upward trend
        assert trend_analysis.projected_errors_next_hour > 20
        assert len(trend_analysis.anomaly_periods) >= 0
    
    @pytest.mark.asyncio
    async def test_correlate_logs_with_metrics(self, analyzer):
        """Test correlating log patterns with system metrics."""
        # Mock log events and system metrics
        log_events = [
            {"timestamp": datetime.utcnow() - timedelta(minutes=10), "level": "ERROR", "count": 5},
            {"timestamp": datetime.utcnow() - timedelta(minutes=8), "level": "ERROR", "count": 8},
            {"timestamp": datetime.utcnow() - timedelta(minutes=5), "level": "ERROR", "count": 12}
        ]
        
        system_metrics = [
            {"timestamp": datetime.utcnow() - timedelta(minutes=10), "cpu_usage": 85.5, "memory_usage": 78.2},
            {"timestamp": datetime.utcnow() - timedelta(minutes=8), "cpu_usage": 92.1, "memory_usage": 84.7},
            {"timestamp": datetime.utcnow() - timedelta(minutes=5), "cpu_usage": 95.8, "memory_usage": 91.3}
        ]
        
        correlation = await analyzer.correlate_logs_with_metrics(
            log_events,
            system_metrics,
            correlation_window_minutes=2
        )
        
        assert correlation.cpu_correlation > 0.8  # Strong positive correlation
        assert correlation.memory_correlation > 0.8  # Strong positive correlation
        assert len(correlation.significant_correlations) > 0
    
    @pytest.mark.asyncio
    async def test_generate_log_insights(self, analyzer):
        """Test generating insights from log analysis."""
        # Mock analyzed log data
        log_summary = {
            "total_entries": 10000,
            "error_rate": 0.05,  # 5% error rate
            "top_errors": [
                {"message": "Database connection failed", "count": 150},
                {"message": "Payment processing timeout", "count": 120},
                {"message": "Authentication failed", "count": 80}
            ],
            "peak_error_times": ["14:00-15:00", "20:00-21:00"],
            "affected_services": ["database", "payment", "auth"]
        }
        
        insights = await analyzer.generate_insights(log_summary)
        
        assert len(insights.critical_issues) > 0
        assert len(insights.recommendations) > 0
        assert insights.overall_health_score >= 0
        assert insights.overall_health_score <= 100
        
        # Should identify database issues as critical
        db_issues = [issue for issue in insights.critical_issues if "database" in issue.lower()]
        assert len(db_issues) > 0


class TestAlertingLoggingIntegration:
    """Integration tests for alerting and logging systems."""
    
    @pytest.fixture
    def temp_integration_dir(self):
        """Create temporary directory for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            integration_path = Path(temp_dir) / "alerting_logging"
            integration_path.mkdir()
            
            # Create subdirectories
            (integration_path / "alerts").mkdir()
            (integration_path / "logs").mkdir()
            (integration_path / "configs").mkdir()
            
            yield integration_path
    
    @pytest.mark.asyncio
    async def test_log_based_alerting_workflow(self, temp_integration_dir):
        """Test alerting based on log analysis."""
        # This test would verify log-driven alerting
        log_manager = LogManager()
        alert_manager = AlertManager()
        log_analyzer = LogAnalyzer()
        
        # Configure log-based alerting rule
        log_alert_rule = AlertRule(
            name="high_error_rate",
            description="Alert when error rate exceeds threshold",
            condition=AlertCondition(
                metric_name="log_error_rate",
                operator="greater_than",
                threshold_value=0.1,  # 10% error rate
                duration_minutes=5
            ),
            severity=AlertSeverity.HIGH
        )
        
        # Would test the integration workflow
        # 1. Analyze logs for error patterns
        # 2. Calculate error rate metrics
        # 3. Evaluate alert conditions
        # 4. Trigger alerts if thresholds exceeded
    
    def test_alert_log_correlation(self):
        """Test correlating alerts with log events."""
        # This test would verify alert-log correlation
        correlation_config = {
            "time_window_minutes": 5,
            "correlation_threshold": 0.8,
            "log_sources": ["application", "system", "security"],
            "alert_types": ["performance", "availability", "security"]
        }
        
        # Would test correlation analysis
        # correlator = AlertLogCorrelator(correlation_config)
        # correlations = correlator.analyze_correlations(alerts, log_events)
        # assert len(correlations) > 0
    
    def test_unified_monitoring_dashboard(self):
        """Test unified dashboard for alerts and logs."""
        # This test would verify dashboard integration
        dashboard_config = {
            "name": "Unified Monitoring",
            "sections": [
                {"type": "alerts", "title": "Active Alerts", "refresh": "30s"},
                {"type": "logs", "title": "Recent Errors", "filter": "level:ERROR", "limit": 50},
                {"type": "metrics", "title": "Error Rate Trends", "timespan": "4h"}
            ]
        }
        
        # Would test dashboard creation and data integration
        # dashboard = create_unified_dashboard(dashboard_config)
        # assert dashboard is not None
        # assert len(dashboard.sections) == 3