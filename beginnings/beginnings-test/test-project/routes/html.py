"""HTML route handlers for test-project."""

from fastapi import Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse



def register_html_routes(app):
    """Register HTML routes with the application."""
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Home page."""
        return app.templates.TemplateResponse(
            "index.html",
            {"request": request, "title": "Welcome to Test Project"}
        )
    
    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        """About page."""
        return app.templates.TemplateResponse(
            "about.html",
            {
                "request": request, 
                "title": "About",
                "content": "About Test Project"
            }
        )
    
    