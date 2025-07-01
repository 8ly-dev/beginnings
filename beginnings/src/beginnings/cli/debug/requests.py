"""Request tracking for debugging dashboard."""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from threading import RLock


@dataclass
class TrackedRequest:
    """Tracked request information."""
    id: str
    start_time: float
    end_time: Optional[float] = None
    path: str = ""
    method: str = ""
    status_code: Optional[int] = None
    request_headers: Dict[str, str] = field(default_factory=dict)
    response_headers: Dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    response_body: str = ""
    user_agent: str = ""
    ip_address: str = ""
    query_params: Dict[str, str] = field(default_factory=dict)
    form_data: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        """Get request duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000
    
    @property
    def is_complete(self) -> bool:
        """Check if request is complete."""
        return self.end_time is not None


class RequestTracker:
    """Tracks HTTP requests for debugging purposes."""
    
    def __init__(
        self,
        max_requests: int = 1000,
        track_headers: bool = True,
        track_body: bool = False,
        max_body_size: int = 10240  # 10KB
    ):
        """Initialize request tracker.
        
        Args:
            max_requests: Maximum number of requests to track
            track_headers: Whether to track request/response headers
            track_body: Whether to track request/response bodies
            max_body_size: Maximum body size to track (bytes)
        """
        self.max_requests = max_requests
        self.track_headers = track_headers
        self.track_body = track_body
        self.max_body_size = max_body_size
        
        self._lock = RLock()
        self._requests: deque[TrackedRequest] = deque(maxlen=max_requests)
        self._active_requests: Dict[str, TrackedRequest] = {}
        
        # Statistics
        self._total_requests = 0
        self._total_errors = 0
    
    def start_request(
        self,
        path: str,
        method: str,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        body: str = "",
        user_agent: str = "",
        ip_address: str = ""
    ) -> str:
        """Start tracking a new request.
        
        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            query_params: Query parameters
            body: Request body
            user_agent: User agent string
            ip_address: Client IP address
            
        Returns:
            Request ID for tracking
        """
        with self._lock:
            request_id = str(uuid.uuid4())
            
            # Limit body size if tracking is enabled
            tracked_body = ""
            if self.track_body and body:
                if len(body) <= self.max_body_size:
                    tracked_body = body
                else:
                    tracked_body = body[:self.max_body_size] + "... [truncated]"
            
            request = TrackedRequest(
                id=request_id,
                start_time=time.time(),
                path=path,
                method=method,
                request_headers=headers.copy() if self.track_headers and headers else {},
                request_body=tracked_body,
                user_agent=user_agent,
                ip_address=ip_address,
                query_params=query_params.copy() if query_params else {}
            )
            
            self._active_requests[request_id] = request
            self._total_requests += 1
            
            return request_id
    
    def end_request(
        self,
        request_id: str,
        status_code: int,
        response_headers: Optional[Dict[str, str]] = None,
        response_body: str = "",
        error: Optional[str] = None
    ):
        """End tracking for a request.
        
        Args:
            request_id: Request ID from start_request
            status_code: HTTP status code
            response_headers: Response headers
            response_body: Response body
            error: Error message if request failed
        """
        with self._lock:
            if request_id not in self._active_requests:
                return
            
            request = self._active_requests.pop(request_id)
            request.end_time = time.time()
            request.status_code = status_code
            request.error = error
            
            if self.track_headers and response_headers:
                request.response_headers = response_headers.copy()
            
            # Limit response body size if tracking is enabled
            if self.track_body and response_body:
                if len(response_body) <= self.max_body_size:
                    request.response_body = response_body
                else:
                    request.response_body = response_body[:self.max_body_size] + "... [truncated]"
            
            if error or status_code >= 400:
                self._total_errors += 1
            
            self._requests.append(request)
    
    def get_request(self, request_id: str) -> Optional[TrackedRequest]:
        """Get a specific tracked request.
        
        Args:
            request_id: Request ID to look up
            
        Returns:
            TrackedRequest if found, None otherwise
        """
        with self._lock:
            # Check active requests first
            if request_id in self._active_requests:
                return self._active_requests[request_id]
            
            # Check completed requests
            for request in self._requests:
                if request.id == request_id:
                    return request
            
            return None
    
    def get_recent_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent requests.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of request data dictionaries
        """
        with self._lock:
            # Combine active and completed requests
            all_requests = list(self._active_requests.values()) + list(self._requests)
            
            # Sort by start time (most recent first)
            all_requests.sort(key=lambda r: r.start_time, reverse=True)
            
            # Take the most recent ones
            recent = all_requests[:limit]
            
            return [self._request_to_dict(request) for request in recent]
    
    def get_requests_by_path(self, path: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get requests for a specific path.
        
        Args:
            path: Request path to filter by
            limit: Maximum number of requests to return
            
        Returns:
            List of request data dictionaries
        """
        with self._lock:
            matching_requests = []
            
            # Check completed requests
            for request in self._requests:
                if request.path == path:
                    matching_requests.append(request)
            
            # Check active requests
            for request in self._active_requests.values():
                if request.path == path:
                    matching_requests.append(request)
            
            # Sort by start time (most recent first)
            matching_requests.sort(key=lambda r: r.start_time, reverse=True)
            
            return [self._request_to_dict(request) for request in matching_requests[:limit]]
    
    def get_slow_requests(self, min_duration_ms: float = 1000, limit: int = 25) -> List[Dict[str, Any]]:
        """Get slow requests above a duration threshold.
        
        Args:
            min_duration_ms: Minimum duration in milliseconds
            limit: Maximum number of requests to return
            
        Returns:
            List of slow request data dictionaries
        """
        with self._lock:
            slow_requests = []
            
            for request in self._requests:
                if request.is_complete and request.duration_ms >= min_duration_ms:
                    slow_requests.append(request)
            
            # Sort by duration (slowest first)
            slow_requests.sort(key=lambda r: r.duration_ms, reverse=True)
            
            return [self._request_to_dict(request) for request in slow_requests[:limit]]
    
    def get_error_requests(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get requests that resulted in errors.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of error request data dictionaries
        """
        with self._lock:
            error_requests = []
            
            for request in self._requests:
                if request.error or (request.status_code and request.status_code >= 400):
                    error_requests.append(request)
            
            # Sort by start time (most recent first)
            error_requests.sort(key=lambda r: r.start_time, reverse=True)
            
            return [self._request_to_dict(request) for request in error_requests[:limit]]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get request tracking statistics.
        
        Returns:
            Dictionary containing statistics
        """
        with self._lock:
            active_count = len(self._active_requests)
            completed_count = len(self._requests)
            
            # Calculate averages for completed requests
            completed_requests = [r for r in self._requests if r.is_complete]
            avg_duration = 0
            if completed_requests:
                avg_duration = sum(r.duration_ms for r in completed_requests) / len(completed_requests)
            
            # Status code breakdown
            status_codes = {}
            for request in self._requests:
                if request.status_code:
                    code_group = f"{request.status_code // 100}xx"
                    status_codes[code_group] = status_codes.get(code_group, 0) + 1
            
            # Error rate
            error_rate = (self._total_errors / self._total_requests * 100) if self._total_requests > 0 else 0
            
            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "active_requests": active_count,
                "completed_requests": completed_count,
                "error_rate_percent": round(error_rate, 2),
                "avg_duration_ms": round(avg_duration, 2),
                "status_code_breakdown": status_codes,
                "tracking_settings": {
                    "max_requests": self.max_requests,
                    "track_headers": self.track_headers,
                    "track_body": self.track_body,
                    "max_body_size": self.max_body_size
                }
            }
    
    def clear_requests(self):
        """Clear all tracked requests."""
        with self._lock:
            self._requests.clear()
            self._active_requests.clear()
            self._total_requests = 0
            self._total_errors = 0
    
    def _request_to_dict(self, request: TrackedRequest) -> Dict[str, Any]:
        """Convert TrackedRequest to dictionary.
        
        Args:
            request: TrackedRequest to convert
            
        Returns:
            Request data as dictionary
        """
        return {
            "id": request.id,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "duration_ms": request.duration_ms,
            "path": request.path,
            "method": request.method,
            "status_code": request.status_code,
            "request_headers": request.request_headers,
            "response_headers": request.response_headers,
            "request_body": request.request_body,
            "response_body": request.response_body,
            "user_agent": request.user_agent,
            "ip_address": request.ip_address,
            "query_params": request.query_params,
            "form_data": request.form_data,
            "error": request.error,
            "is_complete": request.is_complete,
            "formatted_start_time": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(request.start_time)
            )
        }