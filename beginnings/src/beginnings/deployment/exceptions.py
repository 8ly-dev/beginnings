"""Exception classes for deployment tools."""

from typing import Optional, Dict, Any


class DeploymentError(Exception):
    """Base exception for deployment-related errors."""
    
    def __init__(
        self, 
        message: str, 
        deployment_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.deployment_id = deployment_id
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.deployment_id:
            return f"Deployment {self.deployment_id}: {self.message}"
        return self.message


class ContainerBuildError(DeploymentError):
    """Exception raised when container building fails."""
    pass


class DockerfileGenerationError(DeploymentError):
    """Exception raised when Dockerfile generation fails."""
    pass


class CloudDeploymentError(DeploymentError):
    """Exception raised when cloud deployment fails."""
    pass


class KubernetesDeploymentError(DeploymentError):
    """Exception raised when Kubernetes deployment fails."""
    pass


class ConfigurationError(DeploymentError):
    """Exception raised when deployment configuration is invalid."""
    pass