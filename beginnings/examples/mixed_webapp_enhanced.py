"""
Enhanced Mixed Web Application - Complete Framework Integration

This example demonstrates the ultimate power of the Beginnings framework:
- Dual HTML/API interfaces sharing the same backend
- Session authentication for HTML routes
- JWT authentication for API routes
- Shared user context across both interfaces
- Complete security stack (CSRF, Rate Limiting, Security Headers)
- Configuration-driven architecture
- Template engine with security integration
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, Form, Request, Depends, Security
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from beginnings import App
from beginnings.config import load_config
from beginnings.extensions.auth import AuthExtension
from beginnings.extensions.csrf import CSRFExtension
from beginnings.extensions.rate_limiting import RateLimitExtension
from beginnings.extensions.security_headers import SecurityHeadersExtension


# Data models
class Task(BaseModel):
    """Task data model."""
    id: int
    title: str
    description: str
    completed: bool = False
    created_at: datetime
    priority: str = "medium"  # low, medium, high
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskCreate(BaseModel):
    """Task creation request model."""
    title: str
    description: str
    priority: str = "medium"
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    """Task update request model."""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    completed: Optional[bool] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class User(BaseModel):
    """User model for authentication."""
    id: int
    username: str
    email: str
    role: str
    created_at: datetime


# Mock database
TASKS: dict[int, Task] = {
    1: Task(
        id=1,
        title="Implement authentication system",
        description="Add user authentication with JWT and sessions",
        completed=True,
        created_at=datetime(2024, 1, 1, 9, 0, 0),
        priority="high",
        assigned_to="developer"
    ),
    2: Task(
        id=2,
        title="Add security headers",
        description="Implement comprehensive security headers with CSP",
        completed=True,
        created_at=datetime(2024, 1, 2, 10, 0, 0),
        priority="high",
        assigned_to="security-team"
    ),
    3: Task(
        id=3,
        title="Write API documentation",
        description="Create comprehensive API documentation with examples",
        completed=False,
        created_at=datetime(2024, 1, 3, 11, 0, 0),
        priority="medium",
        assigned_to="tech-writer"
    ),
    4: Task(
        id=4,
        title="Performance optimization",
        description="Optimize application performance and add monitoring",
        completed=False,
        created_at=datetime(2024, 1, 4, 14, 0, 0),
        priority="medium",
        assigned_to="devops"
    ),
    5: Task(
        id=5,
        title="Add rate limiting",
        description="Implement API rate limiting with multiple algorithms",
        completed=True,
        created_at=datetime(2024, 1, 5, 16, 0, 0),
        priority="high",
        assigned_to="backend-team"
    ),
}
NEXT_TASK_ID = 6

# Mock users
USERS: dict[str, User] = {
    "admin": User(id=1, username="admin", email="admin@example.com", role="admin", created_at=datetime.now()),
    "user": User(id=2, username="user", email="user@example.com", role="user", created_at=datetime.now()),
    "manager": User(id=3, username="manager", email="manager@example.com", role="manager", created_at=datetime.now()),
}

# Security scheme for API
security = HTTPBearer()


def create_mixed_app_config() -> dict:
    """Create configuration for the mixed application."""
    return {
        "app": {
            "name": "Enhanced Task Manager",
            "description": "Mixed web application demonstrating HTML + API interfaces",
            "version": "2.0.0",
            "environment": "production",
            "debug": False
        },
        "routers": {
            "html": {
                "prefix": "",
                "default_response_class": "HTMLResponse",
                "middleware_order": ["security", "auth", "csrf", "rate_limiting"]
            },
            "api": {
                "prefix": "/api/v1",
                "default_response_class": "JSONResponse",
                "middleware_order": ["security", "auth", "rate_limiting"]
            }
        },
        "templates": {
            "directory": "templates",
            "auto_reload": True,
            "auto_escape": True,
            "globals": {
                "site_name": "Enhanced Task Manager",
                "version": "2.0.0"
            }
        },
        "auth": {
            "providers": {
                "session": {
                    "secret_key": os.getenv("SESSION_SECRET", "mixed-app-session-secret-key"),
                    "session_timeout": 3600,
                    "cookie_name": "task_session",
                    "cookie_secure": False,
                    "cookie_httponly": True,
                    "cookie_samesite": "lax"
                },
                "jwt": {
                    "secret_key": os.getenv("JWT_SECRET", "mixed-app-jwt-secret-key-32-chars"),
                    "algorithm": "HS256",
                    "token_expire_minutes": 60,
                    "issuer": "task-manager-api",
                    "audience": "task-api-users"
                }
            },
            "protected_routes": {
                "/tasks": {
                    "required": True,
                    "provider": "session",
                    "redirect_unauthorized": "/login"
                },
                "/tasks/*": {
                    "required": True,
                    "provider": "session",
                    "redirect_unauthorized": "/login"
                },
                "/admin": {
                    "required": True,
                    "provider": "session",
                    "roles": ["admin"],
                    "redirect_unauthorized": "/login"
                },
                "/api/v1/tasks": {
                    "required": True,
                    "provider": "jwt",
                    "error_unauthorized": {"error": "API authentication required", "status": 401}
                },
                "/api/v1/tasks/*": {
                    "required": True,
                    "provider": "jwt",
                    "error_unauthorized": {"error": "API authentication required", "status": 401}
                },
                "/api/v1/admin/*": {
                    "required": True,
                    "provider": "jwt",
                    "roles": ["admin"],
                    "error_unauthorized": {"error": "Admin API access required", "status": 403}
                }
            },
            "rbac": {
                "roles": {
                    "user": {
                        "description": "Standard user",
                        "permissions": ["read:tasks", "create:tasks", "update:own_tasks"]
                    },
                    "manager": {
                        "description": "Task manager",
                        "permissions": ["read:tasks", "create:tasks", "update:tasks", "assign:tasks"],
                        "inherits": ["user"]
                    },
                    "admin": {
                        "description": "Administrator",
                        "permissions": ["*"],
                        "inherits": ["manager"]
                    }
                }
            }
        },
        "csrf": {
            "enabled": True,
            "protected_methods": ["POST", "PUT", "PATCH", "DELETE"],
            "protected_routes": {
                "/tasks": {"enabled": True},
                "/tasks/*": {"enabled": True},
                "/login": {"enabled": True},
                "/api/v1/*": {"enabled": False}  # APIs use JWT instead
            },
            "template_integration": {
                "enabled": True,
                "template_function_name": "csrf_token"
            }
        },
        "rate_limiting": {
            "storage": {"type": "memory"},
            "global": {
                "algorithm": "sliding_window",
                "requests": 1000,
                "window_seconds": 3600,
                "identifier": "ip"
            },
            "routes": {
                "/login": {
                    "algorithm": "fixed_window",
                    "requests": 5,
                    "window_seconds": 300,
                    "identifier": "ip"
                },
                "/tasks": {
                    "algorithm": "token_bucket",
                    "requests": 50,
                    "window_seconds": 60,
                    "identifier": "user"
                },
                "/api/v1/tasks": {
                    "algorithm": "sliding_window",
                    "requests": 100,
                    "window_seconds": 60,
                    "identifier": "user"
                }
            }
        },
        "security": {
            "headers": {
                "x_frame_options": "SAMEORIGIN",
                "x_content_type_options": "nosniff",
                "strict_transport_security": {
                    "max_age": 31536000,
                    "include_subdomains": True
                }
            },
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'self'"],
                    "script_src": ["'self'", "'unsafe-inline'"],
                    "style_src": ["'self'", "'unsafe-inline'"],
                    "img_src": ["'self'", "data:"],
                    "connect_src": ["'self'"]
                },
                "nonce": {"enabled": True, "script_nonce": True, "style_nonce": True}
            },
            "routes": {
                "/api/v1/*": {
                    "csp": {
                        "directives": {"default_src": ["'none'"]}
                    }
                }
            }
        }
    }


def create_enhanced_mixed_app() -> App:
    """Create and configure the enhanced mixed application."""
    # Load configuration
    config = create_mixed_app_config()
    
    # Initialize the Beginnings app with configuration
    app = App(config=config)
    
    # Load and configure extensions
    auth_ext = AuthExtension(config.get('auth', {}))
    csrf_ext = CSRFExtension(config.get('csrf', {}))
    rate_limit_ext = RateLimitExtension(config.get('rate_limiting', {}))
    security_ext = SecurityHeadersExtension(config.get('security', {}))
    
    # Add extensions to the app
    app.add_extension("auth", auth_ext)
    app.add_extension("csrf", csrf_ext)
    app.add_extension("rate_limiting", rate_limit_ext)
    app.add_extension("security", security_ext)
    
    # Create routers
    html_router = app.create_html_router()
    api_router = app.create_api_router()
    
    # Authentication dependencies
    def get_current_user_session(request: Request) -> Optional[User]:
        """Get current user from session (for HTML routes)."""
        # This would be handled by the auth extension
        # For demo, we'll simulate it
        username = request.cookies.get("username")
        return USERS.get(username) if username else None
    
    def get_current_user_jwt(credentials = Security(security)) -> User:
        """Get current user from JWT (for API routes)."""
        # This would be handled by the auth extension
        # For demo, we'll simulate it
        token = credentials.credentials
        # Simple token validation (in real app, JWT would be properly decoded)
        if token.startswith("user-"):
            username = token.split("-")[1]
            if username in USERS:
                return USERS[username]
        raise HTTPException(status_code=401, detail="Invalid token")
    
    def require_auth_session(request: Request) -> User:
        """Require session authentication."""
        user = get_current_user_session(request)
        if not user:
            raise HTTPException(
                status_code=307,
                detail="Authentication required",
                headers={"Location": "/login"}
            )
        return user
    
    def require_admin_session(request: Request) -> User:
        """Require admin role for session auth."""
        user = require_auth_session(request)
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return user
    
    def require_admin_jwt(user: User = Depends(get_current_user_jwt)) -> User:
        """Require admin role for JWT auth."""
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin API access required")
        return user
    
    # Template rendering helper
    async def render_template_with_context(template: str, context: dict, request: Request):
        """Render template with common context."""
        base_context = {
            "request": request,
            "current_user": get_current_user_session(request),
            "site_name": "Enhanced Task Manager"
        }
        return await app.render_template(template, {**base_context, **context})
    
    # HTML Routes (Web Interface)
    @html_router.get("/")
    async def home_page(request: Request) -> HTMLResponse:
        """Task dashboard home page."""
        current_user = get_current_user_session(request)
        
        if not current_user:
            return await render_template_with_context("landing.html", {
                "total_tasks": len(TASKS),
                "completed_tasks": sum(1 for t in TASKS.values() if t.completed),
                "active_page": "home"
            }, request)
        
        # Filter tasks based on user role
        visible_tasks = list(TASKS.values())
        if current_user.role == "user":
            # Users only see their assigned tasks
            visible_tasks = [t for t in TASKS.values() if t.assigned_to == current_user.username]
        
        stats = {
            "total": len(visible_tasks),
            "completed": sum(1 for t in visible_tasks if t.completed),
            "pending": sum(1 for t in visible_tasks if not t.completed),
            "high_priority": sum(1 for t in visible_tasks if t.priority == "high" and not t.completed)
        }
        
        return await render_template_with_context("dashboard.html", {
            "tasks": sorted(visible_tasks, key=lambda t: t.created_at, reverse=True),
            "stats": stats,
            "active_page": "dashboard"
        }, request)
    
    @html_router.get("/login")
    async def login_page(request: Request) -> HTMLResponse:
        """Login page."""
        current_user = get_current_user_session(request)
        if current_user:
            return RedirectResponse(url="/", status_code=302)
        
        return await render_template_with_context("login.html", {
            "active_page": "login",
            "demo_users": list(USERS.keys())
        }, request)
    
    @html_router.post("/login")
    async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)) -> RedirectResponse:
        """Handle login form submission."""
        # For demo, accept any password for existing users
        if username in USERS:
            response = RedirectResponse(url="/", status_code=302)
            response.set_cookie("username", username, max_age=3600)
            return response
        else:
            raise HTTPException(status_code=400, detail="Invalid username")
    
    @html_router.get("/logout")
    async def logout(request: Request) -> RedirectResponse:
        """Logout and clear session."""
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie("username")
        return response
    
    @html_router.get("/tasks")
    async def tasks_page(request: Request, user: User = Depends(require_auth_session)) -> HTMLResponse:
        """Tasks management page."""
        # Filter tasks based on user role
        visible_tasks = list(TASKS.values())
        if user.role == "user":
            visible_tasks = [t for t in TASKS.values() if t.assigned_to == user.username]
        
        return await render_template_with_context("tasks.html", {
            "tasks": sorted(visible_tasks, key=lambda t: t.created_at, reverse=True),
            "user_role": user.role,
            "active_page": "tasks"
        }, request)
    
    @html_router.get("/tasks/new")
    async def new_task_page(request: Request, user: User = Depends(require_auth_session)) -> HTMLResponse:
        """New task creation page."""
        return await render_template_with_context("new_task.html", {
            "priorities": ["low", "medium", "high"],
            "assignees": list(USERS.keys()) if user.role in ["admin", "manager"] else [user.username],
            "active_page": "tasks"
        }, request)
    
    @html_router.post("/tasks")
    async def create_task_form(
        request: Request,
        title: str = Form(...),
        description: str = Form(...),
        priority: str = Form("medium"),
        assigned_to: str = Form(None),
        user: User = Depends(require_auth_session)
    ) -> RedirectResponse:
        """Create new task from form."""
        global NEXT_TASK_ID
        
        # Users can only assign tasks to themselves
        if user.role == "user":
            assigned_to = user.username
        
        new_task = Task(
            id=NEXT_TASK_ID,
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to or user.username,
            created_at=datetime.now()
        )
        
        TASKS[NEXT_TASK_ID] = new_task
        NEXT_TASK_ID += 1
        
        return RedirectResponse(url="/tasks", status_code=302)
    
    @html_router.post("/tasks/{task_id}/toggle")
    async def toggle_task_form(
        request: Request,
        task_id: int,
        user: User = Depends(require_auth_session)
    ) -> RedirectResponse:
        """Toggle task completion status."""
        if task_id in TASKS:
            task = TASKS[task_id]
            # Users can only toggle their own tasks
            if user.role == "user" and task.assigned_to != user.username:
                raise HTTPException(status_code=403, detail="Can only modify your own tasks")
            task.completed = not task.completed
        
        return RedirectResponse(url="/tasks", status_code=302)
    
    @html_router.get("/admin")
    async def admin_page(request: Request, admin: User = Depends(require_admin_session)) -> HTMLResponse:
        """Admin dashboard."""
        stats = {
            "total_tasks": len(TASKS),
            "completed_tasks": sum(1 for t in TASKS.values() if t.completed),
            "total_users": len(USERS),
            "tasks_by_priority": {
                "high": sum(1 for t in TASKS.values() if t.priority == "high"),
                "medium": sum(1 for t in TASKS.values() if t.priority == "medium"),
                "low": sum(1 for t in TASKS.values() if t.priority == "low")
            },
            "tasks_by_user": {}
        }
        
        for task in TASKS.values():
            user = task.assigned_to or "unassigned"
            stats["tasks_by_user"][user] = stats["tasks_by_user"].get(user, 0) + 1
        
        return await render_template_with_context("admin.html", {
            "stats": stats,
            "users": USERS,
            "recent_tasks": sorted(TASKS.values(), key=lambda t: t.created_at, reverse=True)[:5],
            "active_page": "admin"
        }, request)
    
    # API Routes (JSON Interface)
    @api_router.post("/auth/login")
    async def api_login(username: str, password: str) -> dict[str, str]:
        """API login endpoint."""
        if username in USERS:
            # For demo, generate a simple token
            token = f"user-{username}-{int(time.time())}"
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": username,
                "role": USERS[username].role
            }
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    @api_router.get("/tasks")
    async def list_tasks_api(user: User = Depends(get_current_user_jwt)) -> list[Task]:
        """Get all tasks via API."""
        # Filter based on user role
        if user.role == "user":
            return [t for t in TASKS.values() if t.assigned_to == user.username]
        return list(TASKS.values())
    
    @api_router.get("/tasks/{task_id}")
    async def get_task_api(task_id: int, user: User = Depends(get_current_user_jwt)) -> Task:
        """Get specific task via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = TASKS[task_id]
        # Users can only access their own tasks
        if user.role == "user" and task.assigned_to != user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return task
    
    @api_router.post("/tasks")
    async def create_task_api(
        task_data: TaskCreate,
        user: User = Depends(get_current_user_jwt)
    ) -> Task:
        """Create new task via API."""
        global NEXT_TASK_ID
        
        # Users can only assign tasks to themselves
        assigned_to = task_data.assigned_to
        if user.role == "user":
            assigned_to = user.username
        
        new_task = Task(
            id=NEXT_TASK_ID,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            assigned_to=assigned_to or user.username,
            due_date=task_data.due_date,
            created_at=datetime.now()
        )
        
        TASKS[NEXT_TASK_ID] = new_task
        NEXT_TASK_ID += 1
        
        return new_task
    
    @api_router.put("/tasks/{task_id}")
    async def update_task_api(
        task_id: int,
        task_data: TaskUpdate,
        user: User = Depends(get_current_user_jwt)
    ) -> Task:
        """Update task via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = TASKS[task_id]
        # Users can only update their own tasks
        if user.role == "user" and task.assigned_to != user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update fields if provided
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.priority is not None:
            task.priority = task_data.priority
        if task_data.completed is not None:
            task.completed = task_data.completed
        if task_data.assigned_to is not None and user.role in ["admin", "manager"]:
            task.assigned_to = task_data.assigned_to
        if task_data.due_date is not None:
            task.due_date = task_data.due_date
        
        return task
    
    @api_router.delete("/tasks/{task_id}")
    async def delete_task_api(
        task_id: int,
        user: User = Depends(get_current_user_jwt)
    ) -> dict[str, str]:
        """Delete task via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = TASKS[task_id]
        # Users can only delete their own tasks, admins can delete any
        if user.role == "user" and task.assigned_to != user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        del TASKS[task_id]
        return {"message": "Task deleted successfully"}
    
    @api_router.get("/admin/stats")
    async def get_admin_stats_api(admin: User = Depends(require_admin_jwt)) -> dict[str, Any]:
        """Get detailed statistics via API (admin only)."""
        return {
            "total_tasks": len(TASKS),
            "completed_tasks": sum(1 for t in TASKS.values() if t.completed),
            "pending_tasks": sum(1 for t in TASKS.values() if not t.completed),
            "total_users": len(USERS),
            "tasks_by_priority": {
                "high": sum(1 for t in TASKS.values() if t.priority == "high"),
                "medium": sum(1 for t in TASKS.values() if t.priority == "medium"),
                "low": sum(1 for t in TASKS.values() if t.priority == "low")
            },
            "completion_rate": round((sum(1 for t in TASKS.values() if t.completed) / len(TASKS) * 100) if TASKS else 0, 2)
        }
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "enhanced-task-manager",
            "features": {
                "dual_interface": True,
                "session_auth": True,
                "jwt_auth": True,
                "csrf_protection": True,
                "rate_limiting": True,
                "security_headers": True,
                "role_based_access": True
            }
        }
    
    # Include routers
    app.include_router(html_router)
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_enhanced_mixed_app()


if __name__ == "__main__":
    # Set environment variables for demo
    os.environ.setdefault("SESSION_SECRET", "mixed-app-session-secret-key")
    os.environ.setdefault("JWT_SECRET", "mixed-app-jwt-secret-key-32-chars")
    
    # Run the enhanced mixed application
    print("🚀 Starting Enhanced Mixed Web Application...")
    print("🌐 Web Interface: http://localhost:8002/")
    print("🔗 API Documentation: http://localhost:8002/docs")
    print("🔍 Health Check: http://localhost:8002/health")
    print("📊 Admin Dashboard: http://localhost:8002/admin")
    print("🔑 API Endpoints: http://localhost:8002/api/v1/tasks")
    print()
    print("✨ Dual Interface Features:")
    print("  - 🖥️  HTML Interface: Session-based authentication + CSRF protection")
    print("  - 🔌 API Interface: JWT authentication + comprehensive headers")
    print("  - 👥 Shared Backend: Same data and business logic")
    print("  - ⚡ Smart Rate Limiting: Different limits for web vs API")
    print("  - 🔒 Role-Based Access: User, Manager, Admin roles")
    print("  - 🛡️ Complete Security: All framework security features enabled")
    print()
    print("🧪 Demo Users:")
    print("  - admin (full access to both interfaces)")
    print("  - manager (task management capabilities)")
    print("  - user (basic task access)")
    print()
    print("🔗 API Authentication:")
    print("  curl -X POST http://localhost:8002/api/v1/auth/login \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"username\": \"admin\", \"password\": \"any\"}'")
    print()
    
    app.run(host="127.0.0.1", port=8002, reload=False)