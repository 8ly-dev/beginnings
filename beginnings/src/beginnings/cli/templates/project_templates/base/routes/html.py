"""HTML route handlers for {{ project_name }}."""

from fastapi import Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
{% if include_auth %}
from beginnings.extensions.auth.rbac import require_role, get_current_user
{% endif %}


def register_html_routes(app):
    """Register HTML routes with the application."""
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Home page."""
        return app.templates.TemplateResponse(
            "index.html",
            {"request": request, "title": "Welcome to {{ project_name_title }}"}
        )
    
    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        """About page."""
        return app.templates.TemplateResponse(
            "about.html",
            {
                "request": request, 
                "title": "About",
                "content": "About {{ project_name_title }}"
            }
        )
    
    {% if include_auth %}
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Login page."""
        return app.templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "title": "Login"}
        )
    
    @app.post("/login")
    async def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...)
    ):
        """Process login form."""
        # Get auth extension
        auth_ext = app.get_extension("auth")
        if not auth_ext:
            raise HTTPException(status_code=500, detail="Authentication not configured")
        
        # Authenticate user (this is a simple example)
        # In a real app, you'd validate against a database
        if username and password:  # Basic validation for demo
            # Create session or JWT token
            # This is simplified - use proper authentication in production
            response = RedirectResponse(url="/dashboard", status_code=302)
            response.set_cookie("session", f"user:{username}")
            return response
        else:
            return app.templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request, 
                    "title": "Login",
                    "error": "Invalid credentials"
                }
            )
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """User dashboard (requires authentication)."""
        # Simple session check for demo
        session = request.cookies.get("session")
        if not session:
            return RedirectResponse(url="/login")
        
        username = session.split(":")[-1] if ":" in session else "User"
        return app.templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "Dashboard", 
                "username": username
            }
        )
    
    @app.post("/logout")
    async def logout():
        """Logout user."""
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie("session")
        return response
    {% endif %}