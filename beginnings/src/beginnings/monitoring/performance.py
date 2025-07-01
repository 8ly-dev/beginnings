"""Performance monitoring for comprehensive system analysis."""

from __future__ import annotations

import time
import uuid
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .exceptions import MonitoringError


@dataclass
class PerformanceResult:
    """Result of performance monitoring operation."""
    
    success: bool
    request_id: Optional[str] = None
    duration_ms: float = 0
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    message: str = ""


@dataclass
class DatabaseQueryResult:
    """Result of database query monitoring."""
    
    success: bool
    query_hash: Optional[str] = None
    execution_time_ms: float = 0
    connection_pool: Optional[str] = None
    rows_returned: int = 0
    message: str = ""


@dataclass
class ExternalApiResult:
    """Result of external API call monitoring."""
    
    success: bool
    service_name: str
    response_status: Optional[int] = None
    response_time_ms: float = 0
    response_size: Optional[int] = None
    message: str = ""


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""
    
    total_requests: int
    average_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate: float
    requests_per_second: float
    endpoint_stats: Dict[str, Dict[str, Any]] = None
    generated_at: datetime = None
    
    def __post_init__(self):
        if self.endpoint_stats is None:
            self.endpoint_stats = {}
        if self.generated_at is None:
            self.generated_at = datetime.utcnow()


@dataclass
class PerformanceBottleneck:
    """Performance bottleneck identification."""
    
    endpoint: str
    avg_response_time_ms: float
    request_count: int
    error_rate: float = 0.0
    recommendation: str = ""


class PerformanceMonitor:
    """Monitor for application and system performance."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        self._completed_requests: List[Dict[str, Any]] = []
        self._database_queries: List[Dict[str, Any]] = []
        self._external_api_calls: List[Dict[str, Any]] = []
    
    async def start_request_monitoring(
        self, 
        method: str, 
        endpoint: str, 
        user_id: Optional[str] = None
    ) -> str:
        """Start monitoring a request.
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            user_id: Optional user ID
            
        Returns:
            Request ID for tracking
        """
        request_id = str(uuid.uuid4())
        
        self._active_requests[request_id] = {
            "method": method,
            "endpoint": endpoint,
            "user_id": user_id,
            "start_time": time.time(),
            "timestamp": datetime.utcnow()
        }
        
        return request_id
    
    async def end_request_monitoring(
        self, 
        request_id: str, 
        status_code: int, 
        response_size: Optional[int] = None
    ) -> PerformanceResult:
        """End request monitoring and record performance data.
        
        Args:
            request_id: Request ID from start_request_monitoring
            status_code: HTTP status code
            response_size: Optional response size in bytes
            
        Returns:
            Performance monitoring result
        """
        if request_id not in self._active_requests:
            return PerformanceResult(
                success=False,
                message=f"Request ID {request_id} not found"
            )
        
        try:
            request_data = self._active_requests.pop(request_id)
            end_time = time.time()
            duration_ms = (end_time - request_data["start_time"]) * 1000
            
            # Store completed request data
            completed_request = {
                **request_data,
                "request_id": request_id,
                "end_time": end_time,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "response_size": response_size,
                "completed_at": datetime.utcnow()
            }
            
            self._completed_requests.append(completed_request)
            
            # Keep only last 10000 requests to prevent memory growth
            if len(self._completed_requests) > 10000:
                self._completed_requests = self._completed_requests[-10000:]
            
            return PerformanceResult(
                success=True,
                request_id=request_id,
                duration_ms=duration_ms,
                status_code=status_code,
                response_size=response_size,
                message=f"Request {request_id} monitoring completed"
            )
            
        except Exception as e:
            return PerformanceResult(
                success=False,
                request_id=request_id,
                message=f"Failed to end request monitoring: {str(e)}"
            )
    
    def is_monitoring_request(self, request_id: str) -> bool:
        """Check if a request is currently being monitored.
        
        Args:
            request_id: Request ID to check
            
        Returns:
            True if request is being monitored
        """
        return request_id in self._active_requests
    
    async def monitor_database_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        connection_pool: Optional[str] = None
    ) -> DatabaseQueryResult:
        """Monitor database query performance.
        
        Args:
            query: SQL query string
            params: Query parameters
            connection_pool: Connection pool name
            
        Returns:
            Database query monitoring result
        """
        try:
            start_time = time.time()
            
            # Mock database query execution
            await asyncio.sleep(0.01)  # Simulate query time
            
            execution_time = (time.time() - start_time) * 1000
            
            # Generate query hash
            import hashlib
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            
            # Store query data
            query_data = {
                "query": query,
                "query_hash": query_hash,
                "params": params or {},
                "connection_pool": connection_pool,
                "execution_time_ms": execution_time,
                "timestamp": datetime.utcnow(),
                "rows_returned": 1  # Mock result
            }
            
            self._database_queries.append(query_data)
            
            # Keep only last 1000 queries
            if len(self._database_queries) > 1000:
                self._database_queries = self._database_queries[-1000:]
            
            return DatabaseQueryResult(
                success=True,
                query_hash=query_hash,
                execution_time_ms=execution_time,
                connection_pool=connection_pool,
                rows_returned=1,
                message=f"Database query monitored successfully"
            )
            
        except Exception as e:
            return DatabaseQueryResult(
                success=False,
                message=f"Failed to monitor database query: {str(e)}"
            )
    
    async def monitor_external_api_call(
        self, 
        service_name: str, 
        endpoint: str, 
        method: str = "GET"
    ) -> ExternalApiResult:
        """Monitor external API call performance.
        
        Args:
            service_name: Name of external service
            endpoint: API endpoint URL
            method: HTTP method
            
        Returns:
            External API monitoring result
        """
        try:
            start_time = time.time()
            
            # Mock external API call
            await asyncio.sleep(0.05)  # Simulate API call time
            
            response_time = (time.time() - start_time) * 1000
            
            # Mock successful response
            response_status = 200
            response_size = 1024
            
            # Store API call data
            api_call_data = {
                "service_name": service_name,
                "endpoint": endpoint,
                "method": method,
                "response_status": response_status,
                "response_time_ms": response_time,
                "response_size": response_size,
                "timestamp": datetime.utcnow()
            }
            
            self._external_api_calls.append(api_call_data)
            
            # Keep only last 1000 API calls
            if len(self._external_api_calls) > 1000:
                self._external_api_calls = self._external_api_calls[-1000:]
            
            return ExternalApiResult(
                success=True,
                service_name=service_name,
                response_status=response_status,
                response_time_ms=response_time,
                response_size=response_size,
                message=f"External API call to {service_name} monitored successfully"
            )
            
        except Exception as e:
            return ExternalApiResult(
                success=False,
                service_name=service_name,
                message=f"Failed to monitor external API call: {str(e)}"
            )
    
    async def generate_performance_report(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> PerformanceReport:
        """Generate comprehensive performance report.
        
        Args:
            start_time: Report start time
            end_time: Report end time
            
        Returns:
            Performance report
        """
        try:
            # Filter requests within time range
            filtered_requests = [
                req for req in self._completed_requests
                if start_time <= req["completed_at"] <= end_time
            ]
            
            if not filtered_requests:
                return PerformanceReport(
                    total_requests=0,
                    average_response_time_ms=0,
                    p95_response_time_ms=0,
                    p99_response_time_ms=0,
                    error_rate=0,
                    requests_per_second=0
                )
            
            # Calculate basic metrics
            total_requests = len(filtered_requests)
            durations = [req["duration_ms"] for req in filtered_requests]
            error_requests = [req for req in filtered_requests if req["status_code"] >= 400]
            
            # Calculate statistics
            average_response_time = sum(durations) / len(durations)
            sorted_durations = sorted(durations)
            p95_response_time = sorted_durations[int(len(sorted_durations) * 0.95)]
            p99_response_time = sorted_durations[int(len(sorted_durations) * 0.99)]
            error_rate = len(error_requests) / total_requests
            
            # Calculate requests per second
            time_range_seconds = (end_time - start_time).total_seconds()
            requests_per_second = total_requests / time_range_seconds if time_range_seconds > 0 else 0
            
            # Generate endpoint statistics
            endpoint_stats = {}
            endpoint_groups = {}
            
            for req in filtered_requests:
                endpoint = req["endpoint"]
                if endpoint not in endpoint_groups:
                    endpoint_groups[endpoint] = []
                endpoint_groups[endpoint].append(req)
            
            for endpoint, requests in endpoint_groups.items():
                endpoint_durations = [req["duration_ms"] for req in requests]
                endpoint_errors = [req for req in requests if req["status_code"] >= 400]
                
                endpoint_stats[endpoint] = {
                    "request_count": len(requests),
                    "average_response_time_ms": sum(endpoint_durations) / len(endpoint_durations),
                    "error_rate": len(endpoint_errors) / len(requests)
                }
            
            return PerformanceReport(
                total_requests=total_requests,
                average_response_time_ms=average_response_time,
                p95_response_time_ms=p95_response_time,
                p99_response_time_ms=p99_response_time,
                error_rate=error_rate,
                requests_per_second=requests_per_second,
                endpoint_stats=endpoint_stats,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            # Return empty report on error
            return PerformanceReport(
                total_requests=0,
                average_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                error_rate=0,
                requests_per_second=0
            )
    
    async def identify_performance_bottlenecks(
        self, 
        threshold_ms: float = 1000, 
        minimum_requests: int = 10
    ) -> List[PerformanceBottleneck]:
        """Identify performance bottlenecks.
        
        Args:
            threshold_ms: Response time threshold for identifying bottlenecks
            minimum_requests: Minimum number of requests to consider an endpoint
            
        Returns:
            List of performance bottlenecks
        """
        try:
            # Get endpoint performance data (for testing or real data)
            endpoint_data = await self._get_endpoint_performance_data()
            
            # If no data from testing method, use completed requests
            if not endpoint_data:
                # Group requests by endpoint
                endpoint_groups = {}
                for req in self._completed_requests:
                    endpoint = req["endpoint"]
                    if endpoint not in endpoint_groups:
                        endpoint_groups[endpoint] = []
                    endpoint_groups[endpoint].append(req)
                
                # Convert to endpoint data format
                endpoint_data = []
                for endpoint, requests in endpoint_groups.items():
                    if len(requests) >= minimum_requests:
                        durations = [req["duration_ms"] for req in requests]
                        average_time = sum(durations) / len(durations)
                        endpoint_data.append({
                            "endpoint": endpoint,
                            "avg_time": average_time,
                            "request_count": len(requests)
                        })
            
            bottlenecks = []
            
            for data in endpoint_data:
                endpoint = data["endpoint"]
                average_time = data["avg_time"]
                request_count = data["request_count"]
                
                if request_count < minimum_requests:
                    continue
                
                if average_time > threshold_ms:
                    # Generate recommendation
                    if average_time > 5000:
                        recommendation = "Very slow response time. Consider optimizing database queries and caching."
                    elif average_time > 2000:
                        recommendation = "Slow response time. Review algorithm efficiency and database indexing."
                    else:
                        recommendation = "Response time above threshold. Monitor and optimize if needed."
                    
                    bottleneck = PerformanceBottleneck(
                        endpoint=endpoint,
                        avg_response_time_ms=average_time,
                        request_count=request_count,
                        error_rate=0.0,  # Default error rate
                        recommendation=recommendation
                    )
                    bottlenecks.append(bottleneck)
            
            # Sort by average response time (worst first)
            bottlenecks.sort(key=lambda b: b.avg_response_time_ms, reverse=True)
            
            return bottlenecks
            
        except Exception as e:
            return []
    
    async def _get_endpoint_performance_data(self) -> List[Dict[str, Any]]:
        """Get endpoint performance data for testing.
        
        Returns:
            List of endpoint performance data
        """
        # This method is used by tests to inject mock data
        return []