"""Main application entry point for {{ project_name }}."""

from beginnings import App
from beginnings.config.enhanced_loader import load_config_with_includes
{% if include_html %}
from routes.html import register_html_routes
{% endif %}
{% if include_api %}
from routes.api import register_api_routes
{% endif %}


def create_app() -> App:
    """Create and configure the application."""
    # Load configuration
    config = load_config_with_includes("config")
    
    # Create app instance
    app = App(config=config)
    
    {% if include_html %}
    # Register HTML routes
    register_html_routes(app)
    {% endif %}
    
    {% if include_api %}
    # Register API routes
    register_api_routes(app)
    {% endif %}
    
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