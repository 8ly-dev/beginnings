"""Result classes for deployment operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum


class DeploymentStatus(Enum):
    """Status of deployment operations."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success" 
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    
    success: bool
    deployment_id: str
    status: DeploymentStatus = DeploymentStatus.PENDING
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Deployment-specific results
    container_image: Optional[str] = None
    image_id: Optional[str] = None  # Added for test compatibility
    image_name: Optional[str] = None  # Added for test compatibility
    service_url: Optional[str] = None
    service_arn: Optional[str] = None
    cluster_name: Optional[str] = None
    namespace: Optional[str] = None
    deployment_name: Optional[str] = None  # Added for test compatibility
    service_name: Optional[str] = None  # Added for test compatibility
    updated: bool = False  # Added for test compatibility
    rolled_back: bool = False  # Added for test compatibility
    
    # Build and deployment logs
    build_logs: Optional[List[str]] = None  # Added for test compatibility
    deployment_logs: Optional[List[str]] = None  # Added for test compatibility
    push_logs: Optional[str] = None  # Added for test compatibility
    error: Optional[Any] = None  # Added for test compatibility
    
    # Resource information
    resources_created: List[str] = field(default_factory=list)
    resources_updated: List[str] = field(default_factory=list)
    resources_deleted: List[str] = field(default_factory=list)
    
    # Monitoring and health
    health_check_url: Optional[str] = None
    monitoring_dashboard_url: Optional[str] = None
    log_stream_url: Optional[str] = None
    
    def mark_completed(self, success: bool, message: str = ""):
        """Mark deployment as completed."""
        self.success = success
        self.status = DeploymentStatus.SUCCESS if success else DeploymentStatus.FAILED
        self.message = message
        self.completed_at = datetime.now(timezone.utc)
        
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def add_resource(self, resource_type: str, resource_id: str, action: str = "created"):
        """Add information about a resource that was created/updated/deleted."""
        resource_info = f"{resource_type}: {resource_id}"
        
        if action == "created":
            self.resources_created.append(resource_info)
        elif action == "updated":
            self.resources_updated.append(resource_info)
        elif action == "deleted":
            self.resources_deleted.append(resource_info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            'success': self.success,
            'deployment_id': self.deployment_id,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'container_image': self.container_image,
            'image_id': self.image_id,
            'image_name': self.image_name,
            'service_url': self.service_url,
            'service_arn': self.service_arn,
            'cluster_name': self.cluster_name,
            'namespace': self.namespace,
            'deployment_name': self.deployment_name,
            'service_name': self.service_name,
            'updated': self.updated,
            'rolled_back': self.rolled_back,
            'build_logs': self.build_logs,
            'deployment_logs': self.deployment_logs,
            'push_logs': self.push_logs,
            'error': self.error,
            'resources_created': self.resources_created,
            'resources_updated': self.resources_updated,
            'resources_deleted': self.resources_deleted,
            'health_check_url': self.health_check_url,
            'monitoring_dashboard_url': self.monitoring_dashboard_url,
            'log_stream_url': self.log_stream_url
        }