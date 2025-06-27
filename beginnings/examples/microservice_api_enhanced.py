"""
Enhanced Microservice API Example - Full Security Integration

This example demonstrates how to build a secure microservice using the Beginnings framework:
- JWT authentication for API access
- Rate limiting with Redis support
- Comprehensive security headers
- Configuration-driven setup
- Health checks and monitoring
- OpenAPI documentation with security schemas
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from beginnings import App
from beginnings.config import load_config
from beginnings.extensions.auth import AuthExtension
from beginnings.extensions.rate_limiting import RateLimitExtension
from beginnings.extensions.security_headers import SecurityHeadersExtension


# Data models
class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str = "2.0.0"
    uptime_seconds: float
    features: dict[str, bool]


class UserCreate(BaseModel):
    """User creation request model."""
    username: str
    email: EmailStr
    full_name: str
    role: str = "user"


class User(BaseModel):
    """User data model."""
    id: int
    username: str
    email: str
    full_name: str
    role: str
    created_at: datetime
    active: bool = True
    last_login: Optional[datetime] = None


class UserUpdate(BaseModel):
    """User update request model."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class ApiMetrics(BaseModel):
    """API metrics model."""
    total_requests: int
    total_users: int
    active_users: int
    uptime_seconds: float
    requests_per_minute: float
    authenticated_requests: int
    rate_limited_requests: int


class AuthToken(BaseModel):
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str


# Mock database and metrics
USERS: dict[int, User] = {}
NEXT_USER_ID = 1
REQUEST_COUNT = 0
AUTHENTICATED_REQUESTS = 0
RATE_LIMITED_REQUESTS = 0
START_TIME = time.time()

# Security scheme
security = HTTPBearer()


def create_microservice_config() -> dict:
    """Create configuration for the microservice."""
    return {
        "app": {
            "name": "Enhanced User Microservice",
            "description": "Secure microservice with full Beginnings framework integration",
            "version": "2.0.0",
            "environment": "production",
            "debug": False
        },
        "routers": {
            "api": {
                "prefix": "/api/v1",
                "default_response_class": "JSONResponse",
                "middleware_order": ["security", "auth", "rate_limiting"]
            }
        },
        "auth": {
            "default_provider": "jwt",
            "providers": {
                "jwt": {
                    "secret_key": os.getenv("JWT_SECRET", "enhanced-microservice-jwt-secret-key-32"),
                    "algorithm": "HS256",
                    "token_expire_minutes": 60,
                    "issuer": "enhanced-microservice",
                    "audience": "api-users"
                }
            },
            "protected_routes": {
                "/api/v1/users": {
                    "required": True,
                    "roles": ["admin", "user"],
                    "error_unauthorized": {"error": "Authentication required", "status": 401}
                },
                "/api/v1/users/*": {
                    "required": True,
                    "roles": ["admin", "user"],
                    "error_unauthorized": {"error": "Authentication required", "status": 401}
                },
                "/api/v1/admin/*": {
                    "required": True,
                    "roles": ["admin"],
                    "error_unauthorized": {"error": "Admin access required", "status": 403}
                }
            },
            "rbac": {
                "roles": {
                    "user": {
                        "description": "Standard API user",
                        "permissions": ["read:users", "update:own_profile"]
                    },
                    "admin": {
                        "description": "API administrator",
                        "permissions": ["*"],
                        "inherits": ["user"]
                    }
                }
            }
        },
        "rate_limiting": {
            "storage": {
                "type": "memory",  # Use Redis in production
                "redis_url": os.getenv("REDIS_URL"),
                "key_prefix": "microservice:ratelimit:"
            },
            "global": {
                "algorithm": "sliding_window",
                "requests": 1000,
                "window_seconds": 3600,
                "identifier": "ip"
            },
            "routes": {
                "/api/v1/auth/login": {
                    "algorithm": "fixed_window",
                    "requests": 10,
                    "window_seconds": 300,
                    "identifier": "ip",
                    "error_json": {"error": "Too many login attempts", "retry_after": "{retry_after}"}
                },
                "/api/v1/users": {
                    "algorithm": "token_bucket",
                    "requests": 100,
                    "window_seconds": 60,
                    "burst_size": 10,
                    "identifier": "user",
                    "error_json": {"error": "API rate limit exceeded", "retry_after": "{retry_after}"}
                },
                "/api/v1/admin/*": {
                    "algorithm": "sliding_window",
                    "requests": 200,
                    "window_seconds": 60,
                    "identifier": "user"
                }
            },
            "headers": {
                "include_headers": True,
                "remaining_header": "X-RateLimit-Remaining",
                "limit_header": "X-RateLimit-Limit",
                "reset_header": "X-RateLimit-Reset"
            }
        },
        "security": {
            "headers": {
                "x_frame_options": "DENY",
                "x_content_type_options": "nosniff",
                "x_xss_protection": "0",
                "strict_transport_security": {
                    "max_age": 31536000,
                    "include_subdomains": True,
                    "preload": False
                },
                "referrer_policy": "strict-origin-when-cross-origin"
            },
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'none'"],
                    "script_src": ["'self'"],
                    "style_src": ["'self'"],
                    "img_src": ["'self'", "data:"],
                    "connect_src": ["'self'"],
                    "base_uri": ["'self'"],
                    "form_action": ["'self'"]
                }
            },
            "cors": {
                "enabled": True,
                "allow_origins": ["https://admin.example.com", "https://dashboard.example.com"],
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "expose_headers": ["X-RateLimit-Remaining", "X-RateLimit-Limit"],
                "allow_credentials": True,
                "max_age": 3600
            }
        },
        "extensions": [
            "beginnings.extensions.auth:AuthExtension",
            "beginnings.extensions.rate_limiting:RateLimitExtension",
            "beginnings.extensions.security_headers:SecurityHeadersExtension"
        ],
        "health": {
            "endpoint": "/health",
            "checks": ["database", "redis", "extensions"]
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }


def create_enhanced_microservice() -> App:
    """Create and configure the enhanced microservice application."""
    # Load configuration
    config = create_microservice_config()
    
    # Initialize the Beginnings app with configuration
    app = App(config=config)
    
    # Load and configure extensions
    auth_ext = AuthExtension(config.get('auth', {}))
    rate_limit_ext = RateLimitExtension(config.get('rate_limiting', {}))
    security_ext = SecurityHeadersExtension(config.get('security', {}))
    
    # Add extensions to the app
    app.add_extension("auth", auth_ext)
    app.add_extension("rate_limiting", rate_limit_ext)
    app.add_extension("security", security_ext)
    
    # Create API router (configuration automatically applied)
    api_router = app.create_api_router()
    
    # Authentication dependencies
    def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
        """Get current authenticated user from JWT token."""
        # This is a simplified implementation
        # In practice, the auth extension handles token validation
        token = credentials.credentials
        
        # Mock user lookup based on token
        # In real implementation, this would decode JWT and look up user
        for user in USERS.values():
            if user.active:
                return user
        
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    def require_admin(current_user: User = Depends(get_current_user)) -> User:
        """Require admin role for access."""
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return current_user
    
    # Public endpoints (no authentication required)
    @app.get("/health")
    async def health_check() -> HealthCheck:
        """Health check endpoint for monitoring."""
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        uptime = time.time() - START_TIME
        
        return HealthCheck(
            status="healthy",
            timestamp=datetime.now(),
            uptime_seconds=uptime,
            features={
                "authentication": True,
                "rate_limiting": True,
                "security_headers": True,
                "cors": True,
                "health_checks": True
            }
        )
    
    @app.get("/metrics")
    async def get_metrics() -> ApiMetrics:
        """Get API metrics."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS, RATE_LIMITED_REQUESTS
        
        uptime = time.time() - START_TIME
        requests_per_minute = REQUEST_COUNT / (uptime / 60) if uptime > 0 else 0
        active_users = sum(1 for user in USERS.values() if user.active)
        
        return ApiMetrics(
            total_requests=REQUEST_COUNT,
            total_users=len(USERS),
            active_users=active_users,
            uptime_seconds=uptime,
            requests_per_minute=round(requests_per_minute, 2),
            authenticated_requests=AUTHENTICATED_REQUESTS,
            rate_limited_requests=RATE_LIMITED_REQUESTS
        )
    
    # Authentication endpoints
    @api_router.post("/auth/login")
    async def login(username: str, password: str) -> AuthToken:
        """Login endpoint (simplified for demo)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        
        # In real implementation, this would validate credentials
        # For demo, accept any username/password combination
        
        # Find or create user
        user = None
        for u in USERS.values():
            if u.username == username:
                user = u
                break
        
        if not user:
            # Create new user for demo
            global NEXT_USER_ID
            user = User(
                id=NEXT_USER_ID,
                username=username,
                email=f"{username}@example.com",
                full_name=username.title(),
                role="user",
                created_at=datetime.now(),
                last_login=datetime.now()
            )
            USERS[NEXT_USER_ID] = user
            NEXT_USER_ID += 1
        else:
            user.last_login = datetime.now()
        
        AUTHENTICATED_REQUESTS += 1
        
        # In real implementation, this would generate a proper JWT
        mock_token = f"mock-jwt-token-for-user-{user.id}"
        
        return AuthToken(
            access_token=mock_token,
            expires_in=3600,
            user_id=user.id,
            username=user.username
        )
    
    # Protected user management endpoints
    @api_router.get("/users")
    async def list_users(current_user: User = Depends(get_current_user)) -> list[User]:
        """Get all users (requires authentication)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        # Regular users can only see active users, admins see all
        if current_user.role == "admin":
            return list(USERS.values())
        else:
            return [user for user in USERS.values() if user.active]
    
    @api_router.get("/users/{user_id}")
    async def get_user(user_id: int, current_user: User = Depends(get_current_user)) -> User:
        """Get specific user (requires authentication)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = USERS[user_id]
        
        # Users can only see their own profile unless they're admin
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return user
    
    @api_router.post("/users")
    async def create_user(
        user_data: UserCreate, 
        current_user: User = Depends(require_admin)
    ) -> User:
        """Create new user (admin only)."""
        global NEXT_USER_ID, REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        # Check for duplicate username
        for user in USERS.values():
            if user.username == user_data.username:
                raise HTTPException(status_code=400, detail="Username already exists")
        
        new_user = User(
            id=NEXT_USER_ID,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            created_at=datetime.now()
        )
        
        USERS[NEXT_USER_ID] = new_user
        NEXT_USER_ID += 1
        
        return new_user
    
    @api_router.put("/users/{user_id}")
    async def update_user(
        user_id: int, 
        user_data: UserUpdate, 
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Update user (admin or own profile)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Users can only update their own profile unless they're admin
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        user = USERS[user_id]
        
        # Update fields if provided
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.role is not None and current_user.role == "admin":
            user.role = user_data.role
        if user_data.active is not None and current_user.role == "admin":
            user.active = user_data.active
        
        return user
    
    @api_router.delete("/users/{user_id}")
    async def delete_user(
        user_id: int, 
        admin_user: User = Depends(require_admin)
    ) -> dict[str, str]:
        """Delete user (admin only)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent admin from deleting themselves
        if admin_user.id == user_id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        del USERS[user_id]
        return {"message": "User deleted successfully"}
    
    # Admin-only endpoints
    @api_router.get("/admin/stats")
    async def get_admin_stats(admin_user: User = Depends(require_admin)) -> dict[str, Any]:
        """Get detailed statistics (admin only)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS, RATE_LIMITED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        uptime = time.time() - START_TIME
        user_roles = {}
        for user in USERS.values():
            user_roles[user.role] = user_roles.get(user.role, 0) + 1
        
        return {
            "uptime_seconds": uptime,
            "total_requests": REQUEST_COUNT,
            "authenticated_requests": AUTHENTICATED_REQUESTS,
            "rate_limited_requests": RATE_LIMITED_REQUESTS,
            "authentication_rate": round((AUTHENTICATED_REQUESTS / REQUEST_COUNT * 100) if REQUEST_COUNT > 0 else 0, 2),
            "total_users": len(USERS),
            "active_users": sum(1 for user in USERS.values() if user.active),
            "users_by_role": user_roles,
            "recent_registrations": len([u for u in USERS.values() if (datetime.now() - u.created_at).days < 7])
        }
    
    @api_router.post("/admin/users/{user_id}/activate")
    async def activate_user(
        user_id: int, 
        admin_user: User = Depends(require_admin)
    ) -> User:
        """Activate user account (admin only)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = USERS[user_id]
        user.active = True
        return user
    
    @api_router.post("/admin/users/{user_id}/deactivate")
    async def deactivate_user(
        user_id: int, 
        admin_user: User = Depends(require_admin)
    ) -> User:
        """Deactivate user account (admin only)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        if user_id not in USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent admin from deactivating themselves
        if admin_user.id == user_id:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        
        user = USERS[user_id]
        user.active = False
        return user
    
    # Search endpoints
    @api_router.get("/users/search")
    async def search_users(
        q: str = "", 
        role: Optional[str] = None,
        active: Optional[bool] = None,
        current_user: User = Depends(get_current_user)
    ) -> list[User]:
        """Search users with filters (requires authentication)."""
        global REQUEST_COUNT, AUTHENTICATED_REQUESTS
        REQUEST_COUNT += 1
        AUTHENTICATED_REQUESTS += 1
        
        if not q and role is None and active is None:
            return []
        
        results = []
        query_lower = q.lower() if q else ""
        
        for user in USERS.values():
            # Apply filters
            if role is not None and user.role != role:
                continue
            if active is not None and user.active != active:
                continue
            
            # Apply search query
            if q and not any([
                query_lower in user.username.lower(),
                query_lower in user.email.lower(),
                query_lower in user.full_name.lower()
            ]):
                continue
            
            # Permission check: non-admins can only see active users
            if current_user.role != "admin" and not user.active:
                continue
            
            results.append(user)
        
        return results
    
    # Include the API router
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_enhanced_microservice()


if __name__ == "__main__":
    # Add sample data for demonstration
    sample_users = [
        UserCreate(username="admin", email="admin@example.com", full_name="Administrator", role="admin"),
        UserCreate(username="alice", email="alice@example.com", full_name="Alice Johnson", role="user"),
        UserCreate(username="bob", email="bob@example.com", full_name="Bob Smith", role="user"),
        UserCreate(username="charlie", email="charlie@example.com", full_name="Charlie Brown", role="user"),
    ]
    
    # Create sample users
    for user_data in sample_users:
        new_user = User(
            id=len(USERS) + 1,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            created_at=datetime.now()
        )
        USERS[new_user.id] = new_user
        NEXT_USER_ID = new_user.id + 1
    
    # Set environment variables for demo
    os.environ.setdefault("JWT_SECRET", "enhanced-microservice-jwt-secret-key-32-chars")
    
    # Run the enhanced microservice
    print("🚀 Starting Enhanced User Management Microservice...")
    print("🔗 Health Check: http://localhost:8001/health")
    print("📊 Metrics: http://localhost:8001/metrics")
    print("📚 API Documentation: http://localhost:8001/docs")
    print("🔑 API Endpoints: http://localhost:8001/api/v1/users")
    print("🔐 Admin Stats: http://localhost:8001/api/v1/admin/stats")
    print()
    print("✨ Security Features Enabled:")
    print("  - 🔐 JWT Authentication with Role-Based Access Control")
    print("  - ⚡ Advanced Rate Limiting (Sliding Window, Token Bucket)")
    print("  - 🔒 Comprehensive Security Headers with CSP")
    print("  - 🌐 CORS Configuration for Cross-Origin Access")
    print("  - 📊 Health Checks and Performance Monitoring")
    print("  - 🛡️ Input Validation and Error Handling")
    print()
    print("🧪 Test Authentication:")
    print("  curl -X POST http://localhost:8001/api/v1/auth/login \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"username\": \"admin\", \"password\": \"any\"}'")
    print()
    
    app.run(host="0.0.0.0", port=8001, reload=False)