"""Main application entry point for test-project."""

from beginnings import App
from beginnings.config.enhanced_loader import load_config_with_includes

from routes.html import register_html_routes




def create_app() -> App:
    """Create and configure the application."""
    # Load configuration
    config = load_config_with_includes("config")
    
    # Create app instance
    app = App(config=config)
    
    
    # Register HTML routes
    register_html_routes(app)
    
    
    
    
    return app


# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    config = app.config.get("app", {})
    uvicorn.run(
        "main:app",
        host=config.get("host", "127.0.0.1"),
        port=config.get("port", 8000),
        reload=config.get("debug", False)
    )