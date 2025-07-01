"""Log analyzer for advanced log analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .models import TrendAnalysis, CorrelationAnalysis, LogInsights


class LogAnalyzer:
    """Analyzer for advanced log analysis."""
    
    def __init__(self):
        """Initialize log analyzer."""
        pass
    
    async def analyze_error_trends(
        self, 
        error_data: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> TrendAnalysis:
        """Analyze error trends over time.
        
        Args:
            error_data: Historical error data points
            time_window_hours: Time window for analysis
            
        Returns:
            Trend analysis result
        """
        if len(error_data) < 2:
            return TrendAnalysis(
                trend_direction="stable",
                trend_strength=0.0,
                projected_errors_next_hour=0
            )
        
        # Sort by timestamp
        sorted_data = sorted(error_data, key=lambda x: x["timestamp"])
        
        # Calculate trend
        error_counts = [point["error_count"] for point in sorted_data]
        
        # Simple linear trend calculation
        n = len(error_counts)
        x_sum = sum(range(n))
        y_sum = sum(error_counts)
        xy_sum = sum(i * count for i, count in enumerate(error_counts))
        x2_sum = sum(i * i for i in range(n))
        
        # Calculate slope
        if n * x2_sum - x_sum * x_sum != 0:
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        else:
            slope = 0
        
        # Determine trend direction and strength
        if slope > 0.5:
            trend_direction = "increasing"
            trend_strength = min(1.0, abs(slope) / max(error_counts))
        elif slope < -0.5:
            trend_direction = "decreasing"
            trend_strength = min(1.0, abs(slope) / max(error_counts))
        else:
            trend_direction = "stable"
            trend_strength = 0.2
        
        # Project errors for next hour
        if error_counts:
            last_count = error_counts[-1]
            projected_errors = max(0, int(last_count + slope))
        else:
            projected_errors = 0
        
        # Detect anomaly periods (simple implementation)
        anomaly_periods = []
        avg_errors = sum(error_counts) / len(error_counts)
        threshold = avg_errors * 2
        
        for i, count in enumerate(error_counts):
            if count > threshold:
                anomaly_periods.append({
                    "timestamp": sorted_data[i]["timestamp"],
                    "error_count": count,
                    "threshold": threshold
                })
        
        return TrendAnalysis(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            projected_errors_next_hour=projected_errors,
            anomaly_periods=anomaly_periods
        )
    
    async def correlate_logs_with_metrics(
        self, 
        log_events: List[Dict[str, Any]],
        system_metrics: List[Dict[str, Any]],
        correlation_window_minutes: int = 5
    ) -> CorrelationAnalysis:
        """Correlate log patterns with system metrics.
        
        Args:
            log_events: Log event data
            system_metrics: System metric data
            correlation_window_minutes: Time window for correlation
            
        Returns:
            Correlation analysis result
        """
        if not log_events or not system_metrics:
            return CorrelationAnalysis(
                cpu_correlation=0.0,
                memory_correlation=0.0
            )
        
        # Align timestamps and calculate correlations
        cpu_correlation = self._calculate_correlation(
            log_events, system_metrics, "cpu_usage", correlation_window_minutes
        )
        
        memory_correlation = self._calculate_correlation(
            log_events, system_metrics, "memory_usage", correlation_window_minutes
        )
        
        # Find significant correlations
        significant_correlations = []
        
        if cpu_correlation > 0.7:
            significant_correlations.append({
                "metric": "cpu_usage",
                "correlation": cpu_correlation,
                "strength": "strong"
            })
        
        if memory_correlation > 0.7:
            significant_correlations.append({
                "metric": "memory_usage", 
                "correlation": memory_correlation,
                "strength": "strong"
            })
        
        return CorrelationAnalysis(
            cpu_correlation=cpu_correlation,
            memory_correlation=memory_correlation,
            significant_correlations=significant_correlations
        )
    
    def _calculate_correlation(
        self, 
        log_events: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        metric_name: str,
        window_minutes: int
    ) -> float:
        """Calculate correlation between log events and a metric.
        
        Args:
            log_events: Log event data
            metrics: Metric data
            metric_name: Name of metric to correlate
            window_minutes: Time window for correlation
            
        Returns:
            Correlation coefficient (0.0 to 1.0)
        """
        if not log_events or not metrics:
            return 0.0
        
        # Simple correlation calculation
        # In a real implementation, this would be more sophisticated
        
        log_error_counts = [event.get("count", 0) for event in log_events]
        metric_values = [metric.get(metric_name, 0) for metric in metrics]
        
        if len(log_error_counts) != len(metric_values):
            # Align by taking minimum length
            min_len = min(len(log_error_counts), len(metric_values))
            log_error_counts = log_error_counts[:min_len]
            metric_values = metric_values[:min_len]
        
        if len(log_error_counts) < 2:
            return 0.0
        
        # Calculate Pearson correlation coefficient
        n = len(log_error_counts)
        sum_x = sum(log_error_counts)
        sum_y = sum(metric_values)
        sum_xy = sum(x * y for x, y in zip(log_error_counts, metric_values))
        sum_x2 = sum(x * x for x in log_error_counts)
        sum_y2 = sum(y * y for y in metric_values)
        
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        correlation = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Return absolute correlation (0.0 to 1.0)
        return abs(correlation)
    
    async def generate_insights(self, log_summary: Dict[str, Any]) -> LogInsights:
        """Generate insights from log analysis.
        
        Args:
            log_summary: Summary of analyzed log data
            
        Returns:
            Generated insights
        """
        critical_issues = []
        recommendations = []
        overall_health_score = 100
        
        # Analyze error rate
        error_rate = log_summary.get("error_rate", 0.0)
        
        if error_rate > 0.1:  # More than 10% errors
            critical_issues.append("High error rate detected in logs")
            recommendations.append("Investigate error patterns and implement error reduction strategies")
            overall_health_score -= 30
        elif error_rate > 0.05:  # More than 5% errors
            recommendations.append("Monitor error rate trends and consider preventive measures")
            overall_health_score -= 15
        
        # Analyze top errors
        top_errors = log_summary.get("top_errors", [])
        
        for error in top_errors[:3]:  # Top 3 errors
            message = error.get("message", "")
            count = error.get("count", 0)
            
            if "database" in message.lower() and count > 50:
                critical_issues.append("Database connection issues detected")
                recommendations.append("Check database connectivity and optimize connection pooling")
                overall_health_score -= 20
            
            elif "timeout" in message.lower() and count > 30:
                critical_issues.append("Service timeout issues detected")
                recommendations.append("Review service performance and increase timeout thresholds if necessary")
                overall_health_score -= 15
            
            elif "authentication" in message.lower() and count > 20:
                recommendations.append("Review authentication mechanisms and user access patterns")
                overall_health_score -= 10
        
        # Analyze affected services
        affected_services = log_summary.get("affected_services", [])
        
        if "database" in affected_services:
            recommendations.append("Monitor database performance and consider scaling")
        
        if "payment" in affected_services:
            critical_issues.append("Payment service errors detected")
            recommendations.append("Prioritize payment service stability and error handling")
            overall_health_score -= 25
        
        # Analyze peak error times
        peak_times = log_summary.get("peak_error_times", [])
        
        if peak_times:
            recommendations.append(f"Investigate system load during peak error periods: {', '.join(peak_times)}")
        
        # Ensure score doesn't go below 0
        overall_health_score = max(0, overall_health_score)
        
        return LogInsights(
            critical_issues=critical_issues,
            recommendations=recommendations,
            overall_health_score=overall_health_score
        )