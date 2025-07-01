"""Notification manager for alert delivery."""

from __future__ import annotations

import time
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .models import NotificationConfig, NotificationResult
from .exceptions import NotificationError


class NotificationManager:
    """Manager for notification channel management and delivery."""
    
    def __init__(self):
        """Initialize notification manager."""
        self._notification_channels: Dict[str, NotificationConfig] = {}
        self._delivery_history: List[NotificationResult] = []
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._channel_stats: Dict[str, Dict[str, Any]] = {}
    
    async def register_notification_channel(self, config: NotificationConfig) -> NotificationResult:
        """Register a notification channel.
        
        Args:
            config: Notification channel configuration
            
        Returns:
            Registration result
        """
        try:
            # Validate configuration
            errors = config.validate()
            if errors:
                return NotificationResult(
                    success=False,
                    error_message=f"Configuration validation failed: {', '.join(errors)}"
                )
            
            # Generate channel ID
            channel_id = str(uuid.uuid4())
            
            # Store configuration
            self._notification_channels[config.channel_name] = config
            
            # Initialize rate limiting
            self._rate_limits[config.channel_name] = {
                "count": 0,
                "window_start": datetime.utcnow(),
                "max_per_minute": config.rate_limit_per_minute
            }
            
            # Initialize statistics
            self._channel_stats[config.channel_name] = {
                "total_sent": 0,
                "successful_deliveries": 0,
                "failed_deliveries": 0,
                "average_delivery_time_ms": 0.0
            }
            
            return NotificationResult(
                success=True,
                channel_id=channel_id,
                channel_name=config.channel_name,
                channel_type=config.channel_type
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                error_message=f"Failed to register notification channel: {str(e)}"
            )
    
    async def send_notification(
        self, 
        channel_name: str, 
        alert_data: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> NotificationResult:
        """Send notification to specified channel.
        
        Args:
            channel_name: Name of notification channel
            alert_data: Alert data to send
            max_retries: Maximum retry attempts
            
        Returns:
            Notification delivery result
        """
        start_time = time.time()
        
        try:
            # Check if channel exists
            if channel_name not in self._notification_channels:
                return NotificationResult(
                    success=False,
                    channel_name=channel_name,
                    error_message=f"Notification channel '{channel_name}' not found"
                )
            
            config = self._notification_channels[channel_name]
            
            # Check if channel is enabled
            if not config.enabled:
                return NotificationResult(
                    success=False,
                    channel_name=channel_name,
                    error_message=f"Notification channel '{channel_name}' is disabled"
                )
            
            # Check rate limiting
            if not self._check_rate_limit(channel_name):
                return NotificationResult(
                    success=False,
                    channel_name=channel_name,
                    error_message=f"Rate limit exceeded for channel '{channel_name}'"
                )
            
            # Set retry count
            if max_retries is None:
                max_retries = config.retry_count
            
            # Attempt delivery with retries
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    delivery_result = await self._deliver_notification(config, alert_data)
                    
                    if delivery_result.success:
                        delivery_time = (time.time() - start_time) * 1000
                        
                        # Update rate limiting
                        self._update_rate_limit(channel_name)
                        
                        # Update statistics
                        self._update_channel_stats(channel_name, True, delivery_time)
                        
                        result = NotificationResult(
                            success=True,
                            channel_name=channel_name,
                            channel_type=config.channel_type,
                            message_id=delivery_result.message_id,
                            delivery_time_ms=delivery_time,
                            retry_count=attempt
                        )
                        
                        # Store in history
                        self._delivery_history.append(result)
                        return result
                    else:
                        last_error = delivery_result.error_message
                        
                except Exception as e:
                    last_error = str(e)
                
                # Wait before retry (exponential backoff)
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
            
            # All retries failed
            delivery_time = (time.time() - start_time) * 1000
            self._update_channel_stats(channel_name, False, delivery_time)
            
            return NotificationResult(
                success=False,
                channel_name=channel_name,
                channel_type=config.channel_type,
                delivery_time_ms=delivery_time,
                retry_count=max_retries,
                error_message=f"Failed after {max_retries} retries. Last error: {last_error}"
            )
            
        except Exception as e:
            delivery_time = (time.time() - start_time) * 1000
            return NotificationResult(
                success=False,
                channel_name=channel_name,
                delivery_time_ms=delivery_time,
                error_message=f"Failed to send notification: {str(e)}"
            )
    
    async def _deliver_notification(
        self, 
        config: NotificationConfig, 
        alert_data: Dict[str, Any]
    ) -> NotificationResult:
        """Deliver notification via specific channel type.
        
        Args:
            config: Notification configuration
            alert_data: Alert data to send
            
        Returns:
            Delivery result
        """
        if config.channel_type == "email":
            return await self._send_email_notification(config, alert_data)
        elif config.channel_type == "slack":
            return await self._send_slack_notification(config, alert_data)
        elif config.channel_type == "pagerduty":
            return await self._send_pagerduty_notification(config, alert_data)
        elif config.channel_type == "webhook":
            return await self._send_webhook_notification(config, alert_data)
        elif config.channel_type == "sms":
            return await self._send_sms_notification(config, alert_data)
        else:
            return NotificationResult(
                success=False,
                error_message=f"Unsupported channel type: {config.channel_type}"
            )
    
    async def _send_email_notification(
        self, 
        config: NotificationConfig, 
        alert_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send email notification.
        
        Args:
            config: Email notification configuration
            alert_data: Alert data
            
        Returns:
            Email delivery result
        """
        try:
            # Mock email sending with aiosmtplib
            # In real implementation, would use aiosmtplib.send()
            
            # Simulate email delivery time
            await asyncio.sleep(0.1)
            
            message_id = str(uuid.uuid4())
            
            return NotificationResult(
                success=True,
                message_id=message_id,
                channel_name=config.channel_name,
                channel_type="email"
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                error_message=f"Email delivery failed: {str(e)}"
            )
    
    async def _send_slack_notification(
        self, 
        config: NotificationConfig, 
        alert_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send Slack notification.
        
        Args:
            config: Slack notification configuration
            alert_data: Alert data
            
        Returns:
            Slack delivery result
        """
        try:
            # Mock Slack webhook call
            # In real implementation, would use aiohttp to post to webhook
            
            # Simulate API call time
            await asyncio.sleep(0.05)
            
            message_id = f"slack_{int(time.time())}"
            
            return NotificationResult(
                success=True,
                message_id=message_id,
                channel_name=config.channel_name,
                channel_type="slack"
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                error_message=f"Slack delivery failed: {str(e)}"
            )
    
    async def _send_pagerduty_notification(
        self, 
        config: NotificationConfig, 
        alert_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send PagerDuty notification.
        
        Args:
            config: PagerDuty notification configuration
            alert_data: Alert data
            
        Returns:
            PagerDuty delivery result
        """
        try:
            # Mock PagerDuty API call
            await asyncio.sleep(0.08)
            
            message_id = f"pd_{int(time.time())}"
            
            return NotificationResult(
                success=True,
                message_id=message_id,
                channel_name=config.channel_name,
                channel_type="pagerduty"
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                error_message=f"PagerDuty delivery failed: {str(e)}"
            )
    
    async def _send_webhook_notification(
        self, 
        config: NotificationConfig, 
        alert_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send webhook notification.
        
        Args:
            config: Webhook notification configuration
            alert_data: Alert data
            
        Returns:
            Webhook delivery result
        """
        try:
            # Mock webhook POST request
            await asyncio.sleep(0.03)
            
            message_id = f"webhook_{int(time.time())}"
            
            return NotificationResult(
                success=True,
                message_id=message_id,
                channel_name=config.channel_name,
                channel_type="webhook"
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                error_message=f"Webhook delivery failed: {str(e)}"
            )
    
    async def _send_sms_notification(
        self, 
        config: NotificationConfig, 
        alert_data: Dict[str, Any]
    ) -> NotificationResult:
        """Send SMS notification.
        
        Args:
            config: SMS notification configuration
            alert_data: Alert data
            
        Returns:
            SMS delivery result
        """
        try:
            # Mock SMS API call
            await asyncio.sleep(0.2)
            
            message_id = f"sms_{int(time.time())}"
            
            return NotificationResult(
                success=True,
                message_id=message_id,
                channel_name=config.channel_name,
                channel_type="sms"
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                error_message=f"SMS delivery failed: {str(e)}"
            )
    
    async def batch_send_notifications(
        self, 
        channel_names: List[str], 
        alert_data: Dict[str, Any]
    ) -> List[NotificationResult]:
        """Send notifications to multiple channels.
        
        Args:
            channel_names: List of channel names
            alert_data: Alert data to send
            
        Returns:
            List of delivery results
        """
        tasks = []
        for channel_name in channel_names:
            task = self.send_notification(channel_name, alert_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed NotificationResults
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(NotificationResult(
                    success=False,
                    channel_name=channel_names[i],
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def configure_rate_limiting(
        self, 
        channel_name: str, 
        max_notifications_per_minute: int
    ) -> bool:
        """Configure rate limiting for a channel.
        
        Args:
            channel_name: Name of channel
            max_notifications_per_minute: Maximum notifications per minute
            
        Returns:
            True if configured successfully
        """
        try:
            if channel_name not in self._notification_channels:
                return False
            
            # Update channel configuration
            self._notification_channels[channel_name].rate_limit_per_minute = max_notifications_per_minute
            
            # Update rate limiting state
            self._rate_limits[channel_name]["max_per_minute"] = max_notifications_per_minute
            
            return True
            
        except Exception:
            return False
    
    def _check_rate_limit(self, channel_name: str) -> bool:
        """Check if channel is within rate limits.
        
        Args:
            channel_name: Name of channel to check
            
        Returns:
            True if within rate limits
        """
        if channel_name not in self._rate_limits:
            return True
        
        rate_limit = self._rate_limits[channel_name]
        current_time = datetime.utcnow()
        
        # Check if we need to reset the window
        time_since_window_start = (current_time - rate_limit["window_start"]).total_seconds()
        if time_since_window_start >= 60:  # 1 minute window
            rate_limit["count"] = 0
            rate_limit["window_start"] = current_time
        
        # Check if under limit
        return rate_limit["count"] < rate_limit["max_per_minute"]
    
    def _update_rate_limit(self, channel_name: str):
        """Update rate limit counter after successful delivery.
        
        Args:
            channel_name: Name of channel
        """
        if channel_name in self._rate_limits:
            self._rate_limits[channel_name]["count"] += 1
    
    def _update_channel_stats(self, channel_name: str, success: bool, delivery_time_ms: float):
        """Update channel statistics.
        
        Args:
            channel_name: Name of channel
            success: Whether delivery was successful
            delivery_time_ms: Delivery time in milliseconds
        """
        if channel_name not in self._channel_stats:
            return
        
        stats = self._channel_stats[channel_name]
        stats["total_sent"] += 1
        
        if success:
            stats["successful_deliveries"] += 1
        else:
            stats["failed_deliveries"] += 1
        
        # Update average delivery time
        current_avg = stats["average_delivery_time_ms"]
        total_successful = stats["successful_deliveries"]
        
        if success and total_successful > 0:
            new_avg = ((current_avg * (total_successful - 1)) + delivery_time_ms) / total_successful
            stats["average_delivery_time_ms"] = new_avg