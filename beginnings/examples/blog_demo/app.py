"""
Blog Demo Application - Template-based implementation.

This example demonstrates how to build a blog application using 
Jinja templates and static file serving with the Beginnings framework.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from beginnings import App
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
    author: str


# Authentication helpers
def get_current_user(request: Request) -> str | None:
    """Get the current user from cookies."""
    return request.cookies.get("username")


def require_auth(request: Request) -> str:
    """Require authentication, redirect to login if not authenticated."""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=307, detail="Authentication required", headers={"Location": "/login"})
    return username


def create_blog_demo_app() -> App:
    """Create and configure the blog demo application."""
    # Initialize the database
    init_database()
    
    # Initialize the Beginnings app
    app = App()
    
    # Set up template directory
    current_dir = Path(__file__).parent
    template_dir = current_dir / "templates"
    static_dir = current_dir / "static"
    
    # Initialize Jinja2 templates
    templates = Jinja2Templates(directory=str(template_dir))
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Create HTML router for browser-facing pages
    html_router = app.create_html_router()
    
    # Create API router for programmatic access
    api_router = app.create_api_router(prefix="/api/v1")
    
    # HTML Routes (for browsers)
    @html_router.get("/")
    def blog_home(request: Request) -> HTMLResponse:
        """Blog home page with list of posts."""
        posts_data = get_all_posts()
        # Convert to BlogPost objects for template compatibility
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
        
        return templates.TemplateResponse("home.html", {
            "request": request,
            "posts": posts,
            "active_page": "home",
            "current_user": get_current_user(request)
        })
    
    @html_router.get("/posts/{post_id}")
    def blog_post(request: Request, post_id: int) -> HTMLResponse:
        """Individual blog post page."""
        post_data = get_post_by_id(post_id)
        if not post_data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Convert to BlogPost object for template compatibility
        post = BlogPost(
            id=post_data["id"],
            title=post_data["title"],
            content=post_data["content"],
            author=post_data["author"],
            created_at=datetime.fromisoformat(post_data["created_at"]),
            published=bool(post_data["published"])
        )
        
        return templates.TemplateResponse("post.html", {
            "request": request,
            "post": post,
            "active_page": None,
            "current_user": get_current_user(request)
        })
    
    @html_router.get("/about")
    def about_page(request: Request) -> HTMLResponse:
        """About page."""
        return templates.TemplateResponse("about.html", {
            "request": request,
            "active_page": "about",
            "current_user": get_current_user(request)
        })
    
    @html_router.get("/login")
    def login_page(request: Request) -> HTMLResponse:
        """Login page."""
        # Redirect if already logged in
        if get_current_user(request):
            return RedirectResponse(url="/", status_code=302)
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "active_page": "login",
            "current_user": None
        })
    
    @html_router.post("/login")
    def login_submit(username: str = Form(...)) -> RedirectResponse:
        """Handle login form submission."""
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="username", value=username, max_age=86400 * 7)  # 7 days
        return response
    
    @html_router.get("/logout")
    def logout(request: Request) -> RedirectResponse:
        """Logout and clear cookies."""
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie(key="username")
        return response
    
    @html_router.get("/new-post")
    def new_post_page(request: Request, username: str = Depends(require_auth)) -> HTMLResponse:
        """New post creation page (requires authentication)."""
        return templates.TemplateResponse("new_post.html", {
            "request": request,
            "active_page": "new_post",
            "current_user": username
        })
    
    @html_router.post("/new-post")
    def create_new_post(
        request: Request,
        title: str = Form(...),
        content: str = Form(...),
        username: str = Depends(require_auth)
    ) -> RedirectResponse:
        """Handle new post creation."""
        create_post(title, content, username)
        return RedirectResponse(url="/", status_code=302)
    
    # API Routes (for programmatic access)
    @api_router.get("/posts")
    def list_posts() -> list[BlogPost]:
        """Get all published posts."""
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
    def get_post(post_id: int) -> BlogPost:
        """Get a specific post."""
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
    def create_post_api(post_data: CreatePostRequest) -> BlogPost:
        """Create a new blog post via API."""
        post_data_dict = create_post(post_data.title, post_data.content, post_data.author)
        
        return BlogPost(
            id=post_data_dict["id"],
            title=post_data_dict["title"],
            content=post_data_dict["content"],
            author=post_data_dict["author"],
            created_at=datetime.fromisoformat(post_data_dict["created_at"]),
            published=bool(post_data_dict["published"])
        )
    
    # Include routers
    app.include_router(html_router)
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_blog_demo_app()


if __name__ == "__main__":
    # Run the blog demo application
    print("Starting Blog Demo Application...")
    print("Web Interface: http://localhost:8000/")
    print("API Documentation: http://localhost:8000/docs")
    print("API Endpoints: http://localhost:8000/api/v1/posts")
    
    app.run(host="0.0.0.0", port=8888, reload=False)
