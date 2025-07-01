"""Configuration classes for deployment tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


@dataclass
class ContainerConfig:
    """Configuration for container building and deployment."""
    
    image_name: str
    tag: str = "latest"
    base_image: str = "python:3.11-slim"
    expose_port: int = 8000
    working_dir: str = "/app"
    environment_vars: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)
    requirements_file: Optional[str] = None
    install_dependencies: bool = False
    copy_source: bool = True
    entry_point: Optional[List[str]] = None
    cmd: Optional[List[str]] = None
    user: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    multi_stage: bool = False
    build_stage_image: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate container configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.image_name or not self.image_name.strip():
            errors.append("image_name cannot be empty")
        
        if not self.tag or not self.tag.strip():
            errors.append("tag cannot be empty")
        
        if not self.base_image or not self.base_image.strip():
            errors.append("base_image cannot be empty")
        
        if self.expose_port <= 0 or self.expose_port > 65535:
            errors.append("expose_port must be between 1 and 65535")
        
        if not self.working_dir or not self.working_dir.strip():
            errors.append("working_dir cannot be empty")
        
        # Validate volume mount syntax
        for volume in self.volumes:
            if ':' in volume and len(volume.split(':')) != 2:
                errors.append(f"Invalid volume mount syntax: {volume}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'image_name': self.image_name,
            'tag': self.tag,
            'base_image': self.base_image,
            'expose_port': self.expose_port,
            'working_dir': self.working_dir,
            'environment_vars': self.environment_vars,
            'volumes': self.volumes,
            'requirements_file': self.requirements_file,
            'install_dependencies': self.install_dependencies,
            'copy_source': self.copy_source,
            'entry_point': self.entry_point,
            'cmd': self.cmd,
            'user': self.user,
            'labels': self.labels,
            'multi_stage': self.multi_stage,
            'build_stage_image': self.build_stage_image
        }


@dataclass
class CloudConfig:
    """Configuration for cloud deployment."""
    
    provider: str  # Changed from CloudProvider enum to match tests
    region: str
    service_type: str  # Added to match tests (ecs, cloud_run, container_instances)
    service_name: str = "default-service"
    cpu: int = 256
    memory: int = 512
    min_instances: int = 1
    max_instances: int = 10
    environment_vars: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    credentials: Dict[str, str] = field(default_factory=dict)  # Added to match tests
    
    # AWS-specific fields
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = field(default_factory=list)
    security_group_ids: List[str] = field(default_factory=list)
    load_balancer_arn: Optional[str] = None
    cluster_name: Optional[str] = None
    execution_role_arn: Optional[str] = None
    task_role_arn: Optional[str] = None
    
    # GCP-specific fields
    project_id: Optional[str] = None
    
    # Azure-specific fields
    resource_group: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate cloud configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.provider or not self.provider.strip():
            errors.append("provider cannot be empty")
        
        if self.provider not in ["aws", "gcp", "azure"]:
            errors.append("provider must be one of: aws, gcp, azure")
        
        if not self.region or not self.region.strip():
            errors.append("region cannot be empty")
        
        if not self.service_type or not self.service_type.strip():
            errors.append("service_type cannot be empty")
        
        if not self.service_name or not self.service_name.strip():
            errors.append("service_name cannot be empty")
        
        if self.cpu <= 0:
            errors.append("cpu must be greater than 0")
        
        if self.memory <= 0:
            errors.append("memory must be greater than 0")
        
        if self.min_instances < 0:
            errors.append("min_instances cannot be negative")
        
        if self.max_instances < self.min_instances:
            errors.append("max_instances must be >= min_instances")
        
        # Provider-specific validations
        if self.provider == "aws" and not self.cluster_name:
            errors.append("cluster_name is required for AWS deployments")
        
        if self.provider == "gcp" and not self.project_id:
            errors.append("project_id is required for GCP deployments")
        
        if self.provider == "azure" and not self.resource_group:
            errors.append("resource_group is required for Azure deployments")
        
        return errors


@dataclass 
class DeploymentConfig:
    """Complete deployment configuration."""
    
    project_name: str
    container_config: ContainerConfig
    version: str = "1.0.0"  # Added for test compatibility
    environment: str = "development"  # Made optional with default
    cloud_config: Optional[CloudConfig] = None
    kubernetes_config: Optional[Dict[str, Any]] = None
    monitoring_enabled: bool = True
    logging_enabled: bool = True
    health_check_enabled: bool = True
    auto_scaling_enabled: bool = True
    backup_enabled: bool = False
    health_check_path: str = "/health"  # Added for test compatibility
    auto_scaling: Optional[Dict[str, Any]] = None  # Added for test compatibility
    
    def validate(self) -> List[str]:
        """Validate complete deployment configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.project_name or not self.project_name.strip():
            errors.append("project_name cannot be empty")
        
        if not self.environment or not self.environment.strip():
            errors.append("environment cannot be empty")
        
        # Validate container config
        container_errors = self.container_config.validate()
        errors.extend([f"container: {error}" for error in container_errors])
        
        # Validate cloud config if present
        if self.cloud_config:
            cloud_errors = self.cloud_config.validate()
            errors.extend([f"cloud: {error}" for error in cloud_errors])
        
        return errors