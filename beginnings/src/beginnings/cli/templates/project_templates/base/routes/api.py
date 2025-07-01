"""API route handlers for {{ project_name }}."""

from fastapi import HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict, Any
{% if include_auth %}
from beginnings.extensions.auth.rbac import require_role, get_current_user
{% endif %}


# Pydantic models for API
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str = "1.0.0"


class InfoResponse(BaseModel):
    """Application info response."""
    name: str
    version: str
    framework: str = "beginnings"
    {% if include_auth %}
    auth_enabled: bool = True
    {% else %}
    auth_enabled: bool = False
    {% endif %}


{% if include_auth %}
class UserResponse(BaseModel):
    """User information response."""
    id: int
    username: str
    email: str
    roles: List[str]


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Mock user data for demo
MOCK_USERS = [
    {"id": 1, "username": "admin", "email": "admin@example.com", "roles": ["admin"]},
    {"id": 2, "username": "user", "email": "user@example.com", "roles": ["user"]},
]
{% endif %}


def register_api_routes(app):
    """Register API routes with the application."""
    
    @app.get("/api/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            service="{{ project_name }}"
        )
    
    @app.get("/api/info", response_model=InfoResponse)
    async def app_info() -> InfoResponse:
        """Application information."""
        return InfoResponse(
            name=app.config.get("app", {}).get("name", "{{ project_name }}"),
            version="1.0.0"
        )
    
    {% if include_auth %}
    @app.post("/api/v1/auth/login", response_model=LoginResponse)
    async def api_login(login_data: LoginRequest) -> LoginResponse:
        """API login endpoint."""
        # Get auth extension
        auth_ext = app.get_extension("auth")
        if not auth_ext:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication not configured"
            )
        
        # Simple authentication for demo (use proper auth in production)
        user = next(
            (u for u in MOCK_USERS if u["username"] == login_data.username),
            None
        )
        
        if user and login_data.password:  # Basic validation for demo
            # In a real app, you'd generate a proper JWT token
            return LoginResponse(
                access_token=f"jwt_token_for_{user['username']}",
                expires_in=3600
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    
    @app.get("/api/v1/users", response_model=List[UserResponse])
    async def get_users() -> List[UserResponse]:
        """Get list of users (requires authentication)."""
        # Simple demo endpoint - add proper auth in production
        return [
            UserResponse(**user) for user in MOCK_USERS
        ]
    
    @app.get("/api/v1/users/me", response_model=UserResponse)
    async def get_current_user_info() -> UserResponse:
        """Get current user information (requires authentication)."""
        # Simple demo - return first user
        # In production, get actual current user from auth system
        return UserResponse(**MOCK_USERS[0])
    
    @app.get("/api/v1/protected")
    async def protected_endpoint() -> Dict[str, Any]:
        """Protected endpoint example (requires authentication)."""
        return {
            "message": "This is a protected endpoint",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": "Sensitive information"
        }
    {% endif %}
    
    # Additional API endpoints
    @app.get("/api/v1/status")
    async def get_status() -> Dict[str, Any]:
        """Get application status."""
        return {
            "status": "running",
            "uptime": "0d 0h 0m 0s",  # Calculate actual uptime in production
            {% if include_auth %}
            "auth_enabled": True,
            {% endif %}
            {% if include_rate_limiting %}
            "rate_limiting_enabled": True,
            {% endif %}
            "environment": app.config.get("app", {}).get("debug", False) and "development" or "production"
        }