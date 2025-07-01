"""Alert manager for comprehensive alerting system."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .enums import AlertSeverity, AlertState
from .models import (
    AlertRule, AlertCondition, AlertResult, EvaluationCycleResult
)
from .exceptions import AlertingError


class AlertManager:
    """Manager for alert rule evaluation and management."""
    
    def __init__(self):
        """Initialize alert manager."""
        self._alert_rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, AlertResult] = {}
        self._alert_history: List[AlertResult] = []
        self._suppressed_rules: Dict[str, datetime] = {}
        self._rule_cooldowns: Dict[str, datetime] = {}
    
    async def register_alert_rule(self, rule: AlertRule) -> AlertResult:
        """Register a new alert rule.
        
        Args:
            rule: Alert rule configuration
            
        Returns:
            Alert registration result
        """
        try:
            # Validate rule
            errors = rule.validate()
            if errors:
                return AlertResult(
                    success=False,
                    message=f"Rule validation failed: {', '.join(errors)}"
                )
            
            # Generate rule ID
            rule_id = str(uuid.uuid4())
            
            # Store rule
            self._alert_rules[rule.name] = rule
            
            return AlertResult(
                success=True,
                rule_id=rule_id,
                rule_name=rule.name,
                enabled=rule.enabled,
                message=f"Alert rule '{rule.name}' registered successfully"
            )
            
        except Exception as e:
            return AlertResult(
                success=False,
                message=f"Failed to register alert rule: {str(e)}"
            )
    
    async def evaluate_alert_condition(
        self, 
        condition: AlertCondition, 
        metric_data: Dict[str, List[Dict[str, Any]]]
    ) -> AlertResult:
        """Evaluate alert condition against metric data.
        
        Args:
            condition: Alert condition to evaluate
            metric_data: Metric data for evaluation
            
        Returns:
            Evaluation result
        """
        try:
            # Get metric values for the condition
            if condition.metric_name not in metric_data:
                return AlertResult(
                    success=False,
                    condition_met=False,
                    message=f"Metric '{condition.metric_name}' not found in data"
                )
            
            values = metric_data[condition.metric_name]
            if not values:
                return AlertResult(
                    success=False,
                    condition_met=False,
                    message=f"No data points for metric '{condition.metric_name}'"
                )
            
            # Apply aggregation function
            numeric_values = [point["value"] for point in values if "value" in point]
            if not numeric_values:
                return AlertResult(
                    success=False,
                    condition_met=False,
                    message="No numeric values found in metric data"
                )
            
            if condition.aggregation_function == "avg":
                current_value = sum(numeric_values) / len(numeric_values)
            elif condition.aggregation_function == "min":
                current_value = min(numeric_values)
            elif condition.aggregation_function == "max":
                current_value = max(numeric_values)
            elif condition.aggregation_function == "sum":
                current_value = sum(numeric_values)
            elif condition.aggregation_function == "count":
                current_value = len(numeric_values)
            else:
                current_value = sum(numeric_values) / len(numeric_values)  # Default to avg
            
            # Evaluate condition
            condition_met = self._evaluate_operator(
                current_value, 
                condition.operator, 
                condition.threshold_value
            )
            
            # Check duration requirement
            duration_exceeded = True  # Simplified for now
            
            return AlertResult(
                success=True,
                condition_met=condition_met,
                current_value=current_value,
                threshold_value=condition.threshold_value,
                duration_exceeded=duration_exceeded,
                message=f"Condition evaluated: {current_value} {condition.operator} {condition.threshold_value} = {condition_met}"
            )
            
        except Exception as e:
            return AlertResult(
                success=False,
                condition_met=False,
                message=f"Failed to evaluate condition: {str(e)}"
            )
    
    def _evaluate_operator(self, current_value: float, operator: str, threshold: float) -> bool:
        """Evaluate operator condition.
        
        Args:
            current_value: Current metric value
            operator: Comparison operator
            threshold: Threshold value
            
        Returns:
            True if condition is met
        """
        if operator == "greater_than":
            return current_value > threshold
        elif operator == "less_than":
            return current_value < threshold
        elif operator == "equal_to":
            return current_value == threshold
        elif operator == "not_equal_to":
            return current_value != threshold
        elif operator == "greater_than_or_equal":
            return current_value >= threshold
        elif operator == "less_than_or_equal":
            return current_value <= threshold
        else:
            return False
    
    async def trigger_alert(self, rule: AlertRule, evaluation_result: AlertResult) -> AlertResult:
        """Trigger an alert based on rule and evaluation.
        
        Args:
            rule: Alert rule
            evaluation_result: Condition evaluation result
            
        Returns:
            Alert trigger result
        """
        try:
            # Check if rule is suppressed
            if rule.name in self._suppressed_rules:
                suppress_until = self._suppressed_rules[rule.name]
                if datetime.utcnow() < suppress_until:
                    return AlertResult(
                        success=False,
                        rule_name=rule.name,
                        state=AlertState.SUPPRESSED,
                        message=f"Alert rule '{rule.name}' is suppressed until {suppress_until}"
                    )
                else:
                    # Remove expired suppression
                    del self._suppressed_rules[rule.name]
            
            # Check cooldown period
            if rule.name in self._rule_cooldowns:
                cooldown_until = self._rule_cooldowns[rule.name]
                if datetime.utcnow() < cooldown_until:
                    return AlertResult(
                        success=False,
                        rule_name=rule.name,
                        message=f"Alert rule '{rule.name}' is in cooldown until {cooldown_until}"
                    )
            
            # Create alert
            alert_id = str(uuid.uuid4())
            triggered_at = datetime.utcnow()
            
            alert = AlertResult(
                success=True,
                alert_id=alert_id,
                rule_name=rule.name,
                severity=rule.severity,
                state=AlertState.FIRING,
                triggered_at=triggered_at,
                current_value=evaluation_result.current_value,
                threshold_value=evaluation_result.threshold_value,
                message=f"Alert '{rule.name}' triggered: {rule.description}"
            )
            
            # Store active alert
            self._active_alerts[alert_id] = alert
            
            # Set cooldown
            cooldown_until = triggered_at + timedelta(minutes=rule.cooldown_minutes)
            self._rule_cooldowns[rule.name] = cooldown_until
            
            # Send notifications (mock)
            await self._send_notifications(rule, alert)
            
            # Add to history
            self._alert_history.append(alert)
            
            return alert
            
        except Exception as e:
            return AlertResult(
                success=False,
                rule_name=rule.name,
                message=f"Failed to trigger alert: {str(e)}"
            )
    
    async def resolve_alert(self, alert_id: str, resolution_reason: str = "") -> AlertResult:
        """Resolve an active alert.
        
        Args:
            alert_id: Alert ID to resolve
            resolution_reason: Reason for resolution
            
        Returns:
            Alert resolution result
        """
        try:
            if alert_id not in self._active_alerts:
                return AlertResult(
                    success=False,
                    alert_id=alert_id,
                    message=f"Alert '{alert_id}' not found in active alerts"
                )
            
            alert = self._active_alerts[alert_id]
            resolved_at = datetime.utcnow()
            
            # Update alert state
            alert.state = AlertState.RESOLVED
            alert.resolved_at = resolved_at
            alert.resolution_reason = resolution_reason
            alert.message = f"Alert '{alert.rule_name}' resolved: {resolution_reason}"
            
            # Remove from active alerts
            del self._active_alerts[alert_id]
            
            return alert
            
        except Exception as e:
            return AlertResult(
                success=False,
                alert_id=alert_id,
                message=f"Failed to resolve alert: {str(e)}"
            )
    
    async def suppress_alert(
        self, 
        rule_name: str, 
        suppress_duration_minutes: int,
        suppress_reason: str = ""
    ) -> AlertResult:
        """Suppress an alert rule for a specified duration.
        
        Args:
            rule_name: Name of rule to suppress
            suppress_duration_minutes: Duration to suppress in minutes
            suppress_reason: Reason for suppression
            
        Returns:
            Suppression result
        """
        try:
            if rule_name not in self._alert_rules:
                return AlertResult(
                    success=False,
                    rule_name=rule_name,
                    message=f"Alert rule '{rule_name}' not found"
                )
            
            suppress_until = datetime.utcnow() + timedelta(minutes=suppress_duration_minutes)
            self._suppressed_rules[rule_name] = suppress_until
            
            return AlertResult(
                success=True,
                rule_name=rule_name,
                state=AlertState.SUPPRESSED,
                suppressed_until=suppress_until,
                suppress_reason=suppress_reason,
                message=f"Alert rule '{rule_name}' suppressed until {suppress_until}"
            )
            
        except Exception as e:
            return AlertResult(
                success=False,
                rule_name=rule_name,
                message=f"Failed to suppress alert: {str(e)}"
            )
    
    async def get_active_alerts(self) -> List[AlertResult]:
        """Get all active alerts.
        
        Returns:
            List of active alerts
        """
        return list(self._active_alerts.values())
    
    async def _get_alerts_by_state(self, state: AlertState) -> List[AlertResult]:
        """Get alerts by state.
        
        Args:
            state: Alert state to filter by
            
        Returns:
            List of alerts with specified state
        """
        return [alert for alert in self._active_alerts.values() if alert.state == state]
    
    async def run_evaluation_cycle(self) -> EvaluationCycleResult:
        """Run complete alert evaluation cycle.
        
        Returns:
            Evaluation cycle result
        """
        start_time = time.time()
        rules_evaluated = 0
        alerts_triggered = 0
        alerts_resolved = 0
        errors = []
        
        try:
            # Mock metrics data retrieval
            metric_data = await self._get_metrics_data()
            
            # Evaluate each enabled rule
            for rule_name, rule in self._alert_rules.items():
                if not rule.enabled:
                    continue
                
                try:
                    rules_evaluated += 1
                    
                    # Evaluate condition
                    evaluation_result = await self.evaluate_alert_condition(
                        rule.condition, 
                        metric_data
                    )
                    
                    if evaluation_result.success and evaluation_result.condition_met:
                        # Trigger alert
                        alert_result = await self.trigger_alert(rule, evaluation_result)
                        if alert_result.success:
                            alerts_triggered += 1
                    
                except Exception as e:
                    errors.append(f"Failed to evaluate rule '{rule_name}': {str(e)}")
            
            evaluation_duration = (time.time() - start_time) * 1000
            
            return EvaluationCycleResult(
                success=True,
                rules_evaluated=rules_evaluated,
                alerts_triggered=alerts_triggered,
                alerts_resolved=alerts_resolved,
                evaluation_duration_ms=evaluation_duration,
                errors=errors
            )
            
        except Exception as e:
            evaluation_duration = (time.time() - start_time) * 1000
            return EvaluationCycleResult(
                success=False,
                evaluation_duration_ms=evaluation_duration,
                errors=[f"Evaluation cycle failed: {str(e)}"]
            )
    
    async def _get_metrics_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics data for evaluation.
        
        Returns:
            Mock metrics data
        """
        # Mock metrics data
        return {
            "cpu_usage_percent": [
                {"timestamp": datetime.utcnow(), "value": 85.5},
                {"timestamp": datetime.utcnow() - timedelta(minutes=1), "value": 87.2}
            ],
            "memory_usage_percent": [
                {"timestamp": datetime.utcnow(), "value": 78.3},
                {"timestamp": datetime.utcnow() - timedelta(minutes=1), "value": 79.1}
            ]
        }
    
    async def _send_notifications(self, rule: AlertRule, alert: AlertResult) -> bool:
        """Send notifications for alert.
        
        Args:
            rule: Alert rule
            alert: Alert result
            
        Returns:
            True if notifications sent successfully
        """
        # Mock notification sending
        return True