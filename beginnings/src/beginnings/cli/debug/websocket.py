"""WebSocket management for real-time debug dashboard updates."""

from __future__ import annotations

import json
import time
from typing import Dict, Any, List, Set, Optional, Callable
from threading import RLock
from dataclasses import dataclass


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    id: str
    websocket: Any  # WebSocket object (implementation dependent)
    connected_at: float
    last_ping: float
    subscriptions: Set[str]
    
    def __post_init__(self):
        self.last_ping = self.connected_at


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self._lock = RLock()
        self.connections: Dict[str, WebSocketConnection] = {}
        self._message_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self._total_connections = 0
        self._total_messages_sent = 0
        self._total_messages_received = 0
    
    def add_connection(self, connection_id: str, websocket: Any) -> WebSocketConnection:
        """Add a new WebSocket connection.
        
        Args:
            connection_id: Unique connection identifier
            websocket: WebSocket object
            
        Returns:
            WebSocketConnection instance
        """
        with self._lock:
            connection = WebSocketConnection(
                id=connection_id,
                websocket=websocket,
                connected_at=time.time(),
                last_ping=time.time(),
                subscriptions=set()
            )
            
            self.connections[connection_id] = connection
            self._total_connections += 1
            
            return connection
    
    def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection.
        
        Args:
            connection_id: Connection identifier to remove
        """
        with self._lock:
            if connection_id in self.connections:
                del self.connections[connection_id]
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a WebSocket connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            WebSocketConnection if found, None otherwise
        """
        with self._lock:
            return self.connections.get(connection_id)
    
    def subscribe(self, connection_id: str, channel: str):
        """Subscribe a connection to a channel.
        
        Args:
            connection_id: Connection identifier
            channel: Channel name to subscribe to
        """
        with self._lock:
            connection = self.connections.get(connection_id)
            if connection:
                connection.subscriptions.add(channel)
    
    def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe a connection from a channel.
        
        Args:
            connection_id: Connection identifier
            channel: Channel name to unsubscribe from
        """
        with self._lock:
            connection = self.connections.get(connection_id)
            if connection:
                connection.subscriptions.discard(channel)
    
    def broadcast(self, data: Dict[str, Any], channel: Optional[str] = None):
        """Broadcast data to all connections or specific channel subscribers.
        
        Args:
            data: Data to broadcast
            channel: Optional channel to broadcast to (broadcasts to all if None)
        """
        with self._lock:
            message = json.dumps(data)
            connections_to_send = []
            
            for connection in self.connections.values():
                if channel is None or channel in connection.subscriptions:
                    connections_to_send.append(connection)
            
            # Send messages (outside of lock to avoid blocking)
            for connection in connections_to_send:
                try:
                    self._send_message(connection, message)
                    self._total_messages_sent += 1
                except Exception as e:
                    # Remove broken connections
                    self.remove_connection(connection.id)
    
    def send_to_connection(self, connection_id: str, data: Dict[str, Any]):
        """Send data to a specific connection.
        
        Args:
            connection_id: Connection identifier
            data: Data to send
        """
        with self._lock:
            connection = self.connections.get(connection_id)
            if connection:
                try:
                    message = json.dumps(data)
                    self._send_message(connection, message)
                    self._total_messages_sent += 1
                except Exception:
                    # Remove broken connection
                    self.remove_connection(connection_id)
    
    def handle_message(self, connection_id: str, message: str):
        """Handle incoming WebSocket message.
        
        Args:
            connection_id: Connection identifier
            message: Received message
        """
        with self._lock:
            self._total_messages_received += 1
            
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type in self._message_handlers:
                    handler = self._message_handlers[message_type]
                    handler(connection_id, data)
                else:
                    # Handle built-in message types
                    self._handle_builtin_message(connection_id, data)
                    
            except json.JSONDecodeError:
                # Invalid JSON message
                self.send_error(connection_id, "Invalid JSON message")
            except Exception as e:
                # Handler error
                self.send_error(connection_id, f"Message handling error: {str(e)}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Handler function (connection_id, data) -> None
        """
        self._message_handlers[message_type] = handler
    
    def ping_connections(self):
        """Send ping to all connections to check connectivity."""
        ping_data = {
            "type": "ping",
            "timestamp": time.time()
        }
        
        self.broadcast(ping_data)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics.
        
        Returns:
            Dictionary containing connection statistics
        """
        with self._lock:
            active_connections = len(self.connections)
            
            # Calculate uptime for connections
            current_time = time.time()
            uptimes = []
            for connection in self.connections.values():
                uptime = current_time - connection.connected_at
                uptimes.append(uptime)
            
            avg_uptime = sum(uptimes) / len(uptimes) if uptimes else 0
            
            # Channel subscription stats
            channel_stats = {}
            for connection in self.connections.values():
                for channel in connection.subscriptions:
                    channel_stats[channel] = channel_stats.get(channel, 0) + 1
            
            return {
                "active_connections": active_connections,
                "total_connections_created": self._total_connections,
                "total_messages_sent": self._total_messages_sent,
                "total_messages_received": self._total_messages_received,
                "average_uptime_seconds": round(avg_uptime, 2),
                "channel_subscriptions": channel_stats
            }
    
    def send_error(self, connection_id: str, error_message: str):
        """Send error message to a connection.
        
        Args:
            connection_id: Connection identifier
            error_message: Error message to send
        """
        error_data = {
            "type": "error",
            "message": error_message,
            "timestamp": time.time()
        }
        
        self.send_to_connection(connection_id, error_data)
    
    def _send_message(self, connection: WebSocketConnection, message: str):
        """Send message to a WebSocket connection.
        
        Args:
            connection: WebSocketConnection to send to
            message: Message to send
        """
        # This is implementation-dependent based on the WebSocket library used
        # For now, we'll assume the websocket object has a send method
        if hasattr(connection.websocket, 'send'):
            connection.websocket.send(message)
        else:
            # Fallback for different WebSocket implementations
            raise NotImplementedError("WebSocket send method not implemented")
    
    def _handle_builtin_message(self, connection_id: str, data: Dict[str, Any]):
        """Handle built-in message types.
        
        Args:
            connection_id: Connection identifier
            data: Message data
        """
        message_type = data.get("type")
        
        if message_type == "subscribe":
            channel = data.get("channel")
            if channel:
                self.subscribe(connection_id, channel)
                self.send_to_connection(connection_id, {
                    "type": "subscribed",
                    "channel": channel,
                    "timestamp": time.time()
                })
        
        elif message_type == "unsubscribe":
            channel = data.get("channel")
            if channel:
                self.unsubscribe(connection_id, channel)
                self.send_to_connection(connection_id, {
                    "type": "unsubscribed",
                    "channel": channel,
                    "timestamp": time.time()
                })
        
        elif message_type == "pong":
            # Update last ping time
            with self._lock:
                connection = self.connections.get(connection_id)
                if connection:
                    connection.last_ping = time.time()
        
        elif message_type == "get_stats":
            # Send connection statistics
            stats = self.get_connection_stats()
            self.send_to_connection(connection_id, {
                "type": "stats",
                "data": stats,
                "timestamp": time.time()
            })


class DebugWebSocketHandler:
    """WebSocket handler specifically for debug dashboard."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        """Initialize debug WebSocket handler.
        
        Args:
            websocket_manager: WebSocketManager instance
        """
        self.websocket_manager = websocket_manager
        
        # Register debug-specific message handlers
        self.websocket_manager.register_message_handler("get_metrics", self._handle_get_metrics)
        self.websocket_manager.register_message_handler("get_logs", self._handle_get_logs)
        self.websocket_manager.register_message_handler("get_requests", self._handle_get_requests)
        self.websocket_manager.register_message_handler("clear_data", self._handle_clear_data)
    
    def _handle_get_metrics(self, connection_id: str, data: Dict[str, Any]):
        """Handle metrics request.
        
        Args:
            connection_id: Connection identifier
            data: Request data
        """
        # This would integrate with the metrics collector
        # For now, send mock data
        metrics_data = {
            "type": "metrics",
            "data": {
                "requests_per_minute": 42,
                "error_rate": 2.1,
                "avg_response_time": 156.7
            },
            "timestamp": time.time()
        }
        
        self.websocket_manager.send_to_connection(connection_id, metrics_data)
    
    def _handle_get_logs(self, connection_id: str, data: Dict[str, Any]):
        """Handle logs request.
        
        Args:
            connection_id: Connection identifier
            data: Request data
        """
        limit = data.get("limit", 50)
        level_filter = data.get("level_filter")
        
        # This would integrate with the log streamer
        logs_data = {
            "type": "logs",
            "data": {
                "logs": [],  # Would come from LogStreamer
                "total_count": 0
            },
            "timestamp": time.time()
        }
        
        self.websocket_manager.send_to_connection(connection_id, logs_data)
    
    def _handle_get_requests(self, connection_id: str, data: Dict[str, Any]):
        """Handle requests data request.
        
        Args:
            connection_id: Connection identifier
            data: Request data
        """
        limit = data.get("limit", 50)
        
        # This would integrate with the request tracker
        requests_data = {
            "type": "requests",
            "data": {
                "requests": [],  # Would come from RequestTracker
                "total_count": 0
            },
            "timestamp": time.time()
        }
        
        self.websocket_manager.send_to_connection(connection_id, requests_data)
    
    def _handle_clear_data(self, connection_id: str, data: Dict[str, Any]):
        """Handle clear data request.
        
        Args:
            connection_id: Connection identifier
            data: Request data
        """
        data_type = data.get("data_type", "all")
        
        # This would clear appropriate data stores
        response_data = {
            "type": "data_cleared",
            "data_type": data_type,
            "timestamp": time.time()
        }
        
        self.websocket_manager.send_to_connection(connection_id, response_data)