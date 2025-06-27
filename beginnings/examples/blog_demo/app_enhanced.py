"""
Enhanced Blog Demo Application - Full Beginnings Framework Integration

This example demonstrates the complete power of the Beginnings framework:
- Configuration-driven setup
- Built-in authentication with multiple providers
- CSRF protection for forms
- Rate limiting for security
- Comprehensive security headers
- Framework template engine integration
- Dual HTML/API interfaces
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

from beginnings import App
from beginnings.config import load_config
from beginnings.extensions.auth import AuthExtension
from beginnings.extensions.csrf import CSRFExtension
from beginnings.extensions.rate_limiting import RateLimitExtension
from beginnings.extensions.security_headers import SecurityHeadersExtension
from database import init_database, get_all_posts, get_post_by_id, create_post


# Data models
class BlogPost(BaseModel):
    """Blog post data model."""
    id: int
    title: str
    content: str
    author: str
    created_at: datetime
    published: bool = True


class CreatePostRequest(BaseModel):
    """Request model for creating blog posts."""
    title: str
    content: str


class UserRegistration(BaseModel):
    """User registration model."""
    username: str
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    """User login model."""
    username: str
    password: str


def create_enhanced_blog_app() -> App:
    """Create and configure the enhanced blog application."""
    # Initialize the database
    init_database()
    
    # Get the current directory for configuration and templates
    current_dir = Path(__file__).parent
    config_path = current_dir / "blog_config.yaml"
    
    # Load configuration
    config = load_config(str(config_path))
    
    # Initialize the Beginnings app with configuration
    app = App(config=config)
    
    # Set template and static directories
    template_dir = current_dir / "templates"
    static_dir = current_dir / "static"
    
    # Configure template and static paths
    app.configure_templates(str(template_dir))
    app.configure_static_files(str(static_dir))
    
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
    
    # Create routers (configuration automatically applied)
    html_router = app.create_html_router()
    api_router = app.create_api_router()
    
    # Authentication dependency
    def get_current_user(request: Request) -> Optional[str]:
        """Get current authenticated user from request context."""
        return getattr(request.state, 'user', None)
    
    def require_auth(request: Request) -> str:
        """Require authentication for protected routes."""
        user = get_current_user(request)
        if not user:
            raise HTTPException(
                status_code=307, 
                detail="Authentication required",
                headers={"Location": "/login"}
            )
        return user.username if hasattr(user, 'username') else str(user)
    
    # HTML Routes (Browser Interface)
    @html_router.get("/")
    async def blog_home(request: Request) -> HTMLResponse:
        """Blog home page with list of posts."""
        posts_data = get_all_posts()
        # Convert to BlogPost objects
        posts = [
            BlogPost(
                id=post["id"],
                title=post["title"],
                content=post["content"],
                author=post["author"],
                created_at=datetime.fromisoformat(post["created_at"]),
                published=bool(post["published"])
            )
            for post in posts_data
        ]
        
        current_user = get_current_user(request)
        
        return await app.render_template("home.html", {
            "request": request,
            "posts": posts,
            "active_page": "home",
            "current_user": current_user,
            "site_title": "Blog Demo - Home"
        })
    
    @html_router.get("/posts/{post_id}")
    async def blog_post(request: Request, post_id: int) -> HTMLResponse:
        """Individual blog post page."""
        post_data = get_post_by_id(post_id)
        if not post_data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post = BlogPost(
            id=post_data["id"],
            title=post_data["title"],
            content=post_data["content"],
            author=post_data["author"],
            created_at=datetime.fromisoformat(post_data["created_at"]),
            published=bool(post_data["published"])
        )
        
        current_user = get_current_user(request)
        
        return await app.render_template("post.html", {
            "request": request,
            "post": post,
            "current_user": current_user,
            "site_title": f"{post.title} - Blog Demo"
        })
    
    @html_router.get("/about")
    async def about_page(request: Request) -> HTMLResponse:
        """About page showcasing framework features."""
        current_user = get_current_user(request)
        
        return await app.render_template("about.html", {
            "request": request,
            "active_page": "about",
            "current_user": current_user,
            "site_title": "About - Blog Demo",
            "framework_features": [
                "Configuration-driven architecture",
                "Multiple authentication providers (Session, JWT, OAuth)",
                "CSRF protection with auto-injection",
                "Rate limiting with multiple algorithms",
                "Comprehensive security headers with CSP",
                "Template engine with security integration",
                "Dual HTML/API interfaces",
                "Role-based access control (RBAC)"
            ]
        })
    
    @html_router.get("/login")
    async def login_page(request: Request) -> HTMLResponse:
        """Login page with CSRF protection."""
        current_user = get_current_user(request)
        
        # Redirect if already logged in
        if current_user:
            return RedirectResponse(url="/", status_code=302)
        
        return await app.render_template("login.html", {
            "request": request,
            "active_page": "login",
            "current_user": None,
            "site_title": "Login - Blog Demo"
        })
    
    @html_router.post("/login")
    async def login_submit(
        request: Request,
        username: str = Form(...),
        password: str = Form(...)
    ) -> RedirectResponse:
        """Handle login form submission with authentication."""
        # Authentication will be handled by the AuthExtension middleware
        # This is a simplified example - in practice, the auth extension
        # handles the authentication flow
        
        # For demo purposes, accept any username/password combination
        # In a real app, this would validate against a user database
        if username and password:
            response = RedirectResponse(url="/", status_code=302)
            # The session provider will handle session creation
            return response
        else:
            raise HTTPException(status_code=400, detail="Invalid credentials")
    
    @html_router.get("/register")
    async def register_page(request: Request) -> HTMLResponse:
        """User registration page."""
        current_user = get_current_user(request)
        
        # Redirect if already logged in
        if current_user:
            return RedirectResponse(url="/", status_code=302)
        
        return await app.render_template("register.html", {
            "request": request,
            "active_page": "register",
            "current_user": None,
            "site_title": "Register - Blog Demo"
        })
    
    @html_router.post("/register")
    async def register_submit(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
    ) -> RedirectResponse:
        """Handle user registration."""
        # Registration logic would be handled by AuthExtension
        # This is a simplified demo implementation
        
        # Validate the registration data
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        # In a real implementation, this would:
        # 1. Check if username/email already exists
        # 2. Hash the password
        # 3. Store user in database
        # 4. Log the user in
        
        return RedirectResponse(url="/login", status_code=302)
    
    @html_router.get("/logout")
    async def logout(request: Request) -> RedirectResponse:
        """Logout and clear session."""
        response = RedirectResponse(url="/", status_code=302)
        # The auth extension handles session cleanup
        return response
    
    @html_router.get("/new-post")
    async def new_post_page(
        request: Request, 
        username: str = Depends(require_auth)
    ) -> HTMLResponse:
        """New post creation page (requires authentication)."""
        return await app.render_template("new_post.html", {
            "request": request,
            "active_page": "new_post",
            "current_user": username,
            "site_title": "New Post - Blog Demo"
        })
    
    @html_router.post("/new-post")
    async def create_new_post(
        request: Request,
        title: str = Form(...),
        content: str = Form(...),
        username: str = Depends(require_auth)
    ) -> RedirectResponse:
        """Handle new post creation with CSRF protection."""
        # CSRF protection is automatically handled by CSRFExtension
        create_post(title, content, username)
        return RedirectResponse(url="/", status_code=302)
    
    # API Routes (JSON Interface) 
    @api_router.get("/posts")
    async def list_posts_api() -> list[BlogPost]:
        """Get all published posts via API."""
        posts_data = get_all_posts()
        return [
            BlogPost(
                id=post["id"],
                title=post["title"],
                content=post["content"],
                author=post["author"],
                created_at=datetime.fromisoformat(post["created_at"]),
                published=bool(post["published"])
            )
            for post in posts_data
        ]
    
    @api_router.get("/posts/{post_id}")
    async def get_post_api(post_id: int) -> BlogPost:
        """Get a specific post via API."""
        post_data = get_post_by_id(post_id)
        if not post_data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return BlogPost(
            id=post_data["id"],
            title=post_data["title"],
            content=post_data["content"],
            author=post_data["author"],
            created_at=datetime.fromisoformat(post_data["created_at"]),
            published=bool(post_data["published"])
        )
    
    @api_router.post("/posts")
    async def create_post_api(
        request: Request,
        post_data: CreatePostRequest,
        username: str = Depends(require_auth)
    ) -> BlogPost:
        """Create a new blog post via API (requires JWT auth)."""
        post_data_dict = create_post(post_data.title, post_data.content, username)
        
        return BlogPost(
            id=post_data_dict["id"],
            title=post_data_dict["title"],
            content=post_data_dict["content"],
            author=post_data_dict["author"],
            created_at=datetime.fromisoformat(post_data_dict["created_at"]),
            published=bool(post_data_dict["published"])
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "blog-demo",
            "timestamp": datetime.now().isoformat(),
            "features": {
                "authentication": True,
                "csrf_protection": True,
                "rate_limiting": True,
                "security_headers": True,
                "template_engine": True
            }
        }
    
    # CSP Report endpoint (for security monitoring)
    @app.post("/csp-report")
    async def csp_report(request: Request):
        """Handle CSP violation reports."""
        # In production, you would log these reports for security monitoring
        report = await request.json()
        print(f"CSP Violation: {report}")
        return {"status": "received"}
    
    # Include routers in the app
    app.include_router(html_router)
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_enhanced_blog_app()


if __name__ == "__main__":
    # Run the enhanced blog demo application
    print("🚀 Starting Enhanced Blog Demo Application...")
    print("📱 Web Interface: http://localhost:8888/")
    print("🔗 API Documentation: http://localhost:8888/docs")
    print("🔍 Health Check: http://localhost:8888/health")
    print()
    print("✨ Framework Features Enabled:")
    print("  - 🔐 Multi-provider Authentication (Session, JWT)")
    print("  - 🛡️  CSRF Protection with Auto-injection")
    print("  - ⚡ Rate Limiting with Multiple Algorithms")
    print("  - 🔒 Comprehensive Security Headers with CSP")
    print("  - 🎨 Framework Template Engine")
    print("  - 🌐 Dual HTML/API Interfaces")
    print("  - ⚖️  Role-based Access Control")
    print()
    
    # Set environment variables for demo
    os.environ.setdefault("SESSION_SECRET", "demo-session-secret-key-for-development")
    os.environ.setdefault("JWT_SECRET", "demo-jwt-secret-key-32-chars-long")
    
    app.run(host="0.0.0.0", port=8888, reload=True)