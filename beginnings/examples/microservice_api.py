"""
Microservice API Example - Demonstrates API-only application.

This example shows how to build a microservice using the Beginnings framework
with pure API endpoints, health checks, and metrics.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from beginnings import App


# Data models
class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    uptime_seconds: float


class UserCreate(BaseModel):
    """User creation request model."""
    username: str
    email: str
    full_name: str


class User(BaseModel):
    """User data model."""
    id: int
    username: str
    email: str
    full_name: str
    created_at: datetime
    active: bool = True


class ApiMetrics(BaseModel):
    """API metrics model."""
    total_requests: int
    total_users: int
    uptime_seconds: float
    requests_per_minute: float


# Mock database and metrics
USERS: dict[int, User] = {}
NEXT_USER_ID = 1
REQUEST_COUNT = 0
START_TIME = time.time()


def create_microservice_app() -> App:
    """Create and configure the microservice application."""
    # Initialize the Beginnings app
    app = App(config_dir="config", environment="production")
    
    # Create API router for all endpoints
    api_router = app.create_api_router(prefix="/api/v1")
    
    # Health check endpoint (no prefix for easier monitoring)
    @app.get("/health")
    def health_check() -> HealthCheck:
        """Health check endpoint for monitoring."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        return HealthCheck(
            status="healthy",
            timestamp=datetime.now(),
            uptime_seconds=time.time() - START_TIME
        )
    
    @app.get("/metrics")
    def get_metrics() -> ApiMetrics:
        """Get API metrics."""
        uptime = time.time() - START_TIME
        requests_per_minute = REQUEST_COUNT / (uptime / 60) if uptime > 0 else 0
        
        return ApiMetrics(
            total_requests=REQUEST_COUNT,
            total_users=len(USERS),
            uptime_seconds=uptime,
            requests_per_minute=round(requests_per_minute, 2)
        )
    
    # User management endpoints
    @api_router.get("/users")
    def list_users() -> list[User]:
        """Get all users."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        return list(USERS.values())
    
    @api_router.get("/users/{user_id}")
    def get_user(user_id: int) -> User:
        """Get a specific user."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        return USERS[user_id]
    
    @api_router.post("/users")
    def create_user(user_data: UserCreate) -> User:
        """Create a new user."""
        global NEXT_USER_ID, REQUEST_COUNT
        REQUEST_COUNT += 1
        
        # Check for duplicate username
        for user in USERS.values():
            if user.username == user_data.username:
                raise HTTPException(status_code=400, detail="Username already exists")
        
        new_user = User(
            id=NEXT_USER_ID,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=datetime.now()
        )
        
        USERS[NEXT_USER_ID] = new_user
        NEXT_USER_ID += 1
        
        return new_user
    
    @api_router.put("/users/{user_id}")
    def update_user(user_id: int, user_data: UserCreate) -> User:
        """Update an existing user."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = USERS[user_id]
        user.username = user_data.username
        user.email = user_data.email
        user.full_name = user_data.full_name
        
        return user
    
    @api_router.delete("/users/{user_id}")
    def delete_user(user_id: int) -> dict[str, str]:
        """Delete a user."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        del USERS[user_id]
        return {"message": "User deleted successfully"}
    
    @api_router.post("/users/{user_id}/deactivate")
    def deactivate_user(user_id: int) -> User:
        """Deactivate a user account."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = USERS[user_id]
        user.active = False
        return user
    
    @api_router.post("/users/{user_id}/activate")
    def activate_user(user_id: int) -> User:
        """Activate a user account."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = USERS[user_id]
        user.active = True
        return user
    
    # Search endpoints
    @api_router.get("/users/search")
    def search_users(q: str = "") -> list[User]:
        """Search users by username or email."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        if not q:
            return []
        
        results = []
        query_lower = q.lower()
        
        for user in USERS.values():
            if (query_lower in user.username.lower() or 
                query_lower in user.email.lower() or
                query_lower in user.full_name.lower()):
                results.append(user)
        
        return results
    
    # Include the API router
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_microservice_app()


if __name__ == "__main__":
    # Add some sample data for demonstration
    from datetime import datetime
    
    sample_users = [
        UserCreate(username="admin", email="admin@example.com", full_name="Administrator"),
        UserCreate(username="john_doe", email="john@example.com", full_name="John Doe"),
        UserCreate(username="jane_smith", email="jane@example.com", full_name="Jane Smith"),
    ]
    
    # Create sample users
    for user_data in sample_users:
        new_user = User(
            id=len(USERS) + 1,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=datetime.now()
        )
        USERS[new_user.id] = new_user
        NEXT_USER_ID = new_user.id + 1
    
    # Run the microservice
    print("Starting User Management Microservice...")
    print("Health Check: http://localhost:8001/health")
    print("Metrics: http://localhost:8001/metrics")
    print("API Documentation: http://localhost:8001/docs")
    print("Users API: http://localhost:8001/api/v1/users")
    
    app.run(host="0.0.0.0", port=8001, reload=False)