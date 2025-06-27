"""Project scaffolding commands."""

import click
import os
from typing import Optional

from ..utils.colors import success, error, info, highlight
from ..utils.errors import ProjectError
from ..utils.progress import spinner_context


@click.command(name="new")
@click.argument("project_name", type=str)
@click.option(
    "--template",
    type=click.Choice(["minimal", "standard", "api", "full", "custom"]),
    default="standard",
    help="Project template to use"
)
@click.option(
    "--no-git",
    is_flag=True,
    help="Skip git repository initialization"
)
@click.option(
    "--no-deps",
    is_flag=True,
    help="Skip dependency installation"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory (default: current directory)"
)
@click.pass_context
def new_command(
    ctx: click.Context,
    project_name: str,
    template: str,
    no_git: bool,
    no_deps: bool,
    output_dir: Optional[str]
):
    """Create a new beginnings project.
    
    Creates a new project with the specified template and initializes
    it with proper configuration, dependencies, and optional git repository.
    
    Templates:
    - minimal: Core framework only, no extensions
    - standard: Common extensions (auth, CSRF, security)  
    - api: API-focused with rate limiting and authentication
    - full: All bundled extensions with complete configuration
    - custom: Interactive selection of features
    """
    verbose = ctx.obj.get("verbose", False)
    
    # Validate project name
    if not _is_valid_project_name(project_name):
        raise ProjectError(
            f"Invalid project name: {project_name}",
            suggestions=[
                "Use only letters, numbers, hyphens, and underscores",
                "Start with a letter or underscore",
                "Keep it short and descriptive"
            ]
        )
    
    # Determine output directory
    target_dir = os.path.join(output_dir or os.getcwd(), project_name)
    
    if os.path.exists(target_dir):
        raise ProjectError(
            f"Directory already exists: {target_dir}",
            suggestions=[
                "Choose a different project name",
                "Remove the existing directory",
                "Use --output-dir to specify a different location"
            ]
        )
    
    click.echo(info(f"Creating new beginnings project: {highlight(project_name)}"))
    click.echo(info(f"Template: {highlight(template)}"))
    click.echo(info(f"Location: {highlight(target_dir)}"))
    
    try:
        # Create project structure
        with spinner_context("Creating project structure"):
            _create_project_structure(target_dir, project_name, template, verbose)
        
        click.echo(success("Project structure created"))
        
        # Initialize git repository
        if not no_git:
            with spinner_context("Initializing git repository"):
                _initialize_git_repo(target_dir, verbose)
            click.echo(success("Git repository initialized"))
        
        # Install dependencies  
        if not no_deps:
            with spinner_context("Installing dependencies"):
                _install_dependencies(target_dir, verbose)
            click.echo(success("Dependencies installed"))
        
        # Show next steps
        _show_next_steps(project_name, target_dir)
        
    except Exception as e:
        # Clean up on failure
        import shutil
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        
        raise ProjectError(
            f"Failed to create project: {e}",
            suggestions=[
                "Ensure you have write permissions",
                "Check available disk space",
                "Verify network connectivity for dependencies"
            ]
        )


def _is_valid_project_name(name: str) -> bool:
    """Validate project name follows conventions."""
    import re
    # Allow letters, numbers, hyphens, underscores
    # Must start with letter or underscore
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, name)) and len(name) <= 50


def _create_project_structure(target_dir: str, project_name: str, template: str, verbose: bool):
    """Create the project directory structure and files."""
    os.makedirs(target_dir, exist_ok=True)
    
    # Create basic structure
    dirs_to_create = [
        "config",
        "routes", 
        "templates",
        "static/css",
        "static/js",
        "tests"
    ]
    
    for dir_path in dirs_to_create:
        full_path = os.path.join(target_dir, dir_path)
        os.makedirs(full_path, exist_ok=True)
        if verbose:
            click.echo(f"  Created directory: {dir_path}")
    
    # Create configuration files based on template
    _create_config_files(target_dir, project_name, template, verbose)
    
    # Create route files
    _create_route_files(target_dir, template, verbose)
    
    # Create template files
    _create_template_files(target_dir, template, verbose)
    
    # Create application entry point
    _create_main_file(target_dir, project_name, template, verbose)
    
    # Create project metadata
    _create_project_metadata(target_dir, project_name, template, verbose)


def _create_config_files(target_dir: str, project_name: str, template: str, verbose: bool):
    """Create configuration files based on template."""
    config_dir = os.path.join(target_dir, "config")
    
    # Base configuration
    base_config = _get_base_config(project_name, template)
    
    with open(os.path.join(config_dir, "app.yaml"), "w") as f:
        import yaml
        yaml.dump(base_config, f, default_flow_style=False, indent=2)
    
    if verbose:
        click.echo("  Created config/app.yaml")
    
    # Environment-specific configs
    dev_config = {"app": {"debug": True}, "include": ["../config/app.yaml"]}
    
    with open(os.path.join(config_dir, "app.dev.yaml"), "w") as f:
        import yaml
        yaml.dump(dev_config, f, default_flow_style=False, indent=2)
    
    if verbose:
        click.echo("  Created config/app.dev.yaml")


def _create_route_files(target_dir: str, template: str, verbose: bool):
    """Create route handler files."""
    routes_dir = os.path.join(target_dir, "routes")
    
    # Create __init__.py
    with open(os.path.join(routes_dir, "__init__.py"), "w") as f:
        f.write('"""Route modules."""\n')
    
    # Create HTML routes
    html_routes = _get_html_routes_template(template)
    with open(os.path.join(routes_dir, "html.py"), "w") as f:
        f.write(html_routes)
    
    if verbose:
        click.echo("  Created routes/html.py")
    
    # Create API routes if template includes API
    if template in ["api", "full", "standard"]:
        api_routes = _get_api_routes_template(template)
        with open(os.path.join(routes_dir, "api.py"), "w") as f:
            f.write(api_routes)
        
        if verbose:
            click.echo("  Created routes/api.py")


def _create_template_files(target_dir: str, template: str, verbose: bool):
    """Create template files."""
    templates_dir = os.path.join(target_dir, "templates")
    
    # Base template
    base_template = _get_base_template()
    with open(os.path.join(templates_dir, "base.html"), "w") as f:
        f.write(base_template)
    
    # Index template
    index_template = _get_index_template()
    with open(os.path.join(templates_dir, "index.html"), "w") as f:
        f.write(index_template)
    
    if verbose:
        click.echo("  Created template files")


def _create_main_file(target_dir: str, project_name: str, template: str, verbose: bool):
    """Create main application file."""
    main_content = _get_main_file_template(project_name, template)
    
    with open(os.path.join(target_dir, "main.py"), "w") as f:
        f.write(main_content)
    
    if verbose:
        click.echo("  Created main.py")


def _create_project_metadata(target_dir: str, project_name: str, template: str, verbose: bool):
    """Create project metadata files."""
    # pyproject.toml
    pyproject_content = _get_pyproject_template(project_name)
    with open(os.path.join(target_dir, "pyproject.toml"), "w") as f:
        f.write(pyproject_content)
    
    # .gitignore
    gitignore_content = _get_gitignore_template()
    with open(os.path.join(target_dir, ".gitignore"), "w") as f:
        f.write(gitignore_content)
    
    # README.md
    readme_content = _get_readme_template(project_name, template)
    with open(os.path.join(target_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    if verbose:
        click.echo("  Created project metadata files")


def _initialize_git_repo(target_dir: str, verbose: bool):
    """Initialize git repository."""
    import subprocess
    
    subprocess.run(["git", "init"], cwd=target_dir, check=True, capture_output=not verbose)
    subprocess.run(["git", "add", "."], cwd=target_dir, check=True, capture_output=not verbose)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit: beginnings project setup"],
        cwd=target_dir,
        check=True,
        capture_output=not verbose
    )


def _install_dependencies(target_dir: str, verbose: bool):
    """Install project dependencies."""
    import subprocess
    
    # Use uv for dependency management
    subprocess.run(
        ["uv", "sync"],
        cwd=target_dir,
        check=True,
        capture_output=not verbose
    )


def _show_next_steps(project_name: str, target_dir: str):
    """Show next steps to the user."""
    click.echo(f"\n{success('Project created successfully!')}")
    click.echo(f"\nNext steps:")
    click.echo(f"  {highlight('1.')} cd {project_name}")
    click.echo(f"  {highlight('2.')} beginnings run")
    click.echo(f"  {highlight('3.')} Open http://localhost:8000 in your browser")
    click.echo(f"\nProject location: {highlight(target_dir)}")


# Template content functions
def _get_base_config(project_name: str, template: str) -> dict:
    """Get base configuration for template."""
    config = {
        "app": {
            "name": project_name,
            "debug": False,
            "host": "127.0.0.1",
            "port": 8000
        },
        "routers": {
            "html": {
                "prefix": "",
                "default_response_class": "HTMLResponse"
            }
        }
    }
    
    if template in ["api", "full", "standard"]:
        config["routers"]["api"] = {
            "prefix": "/api",
            "default_response_class": "JSONResponse"
        }
    
    if template in ["full", "standard"]:
        config["extensions"] = [
            "beginnings.extensions.auth:AuthExtension",
            "beginnings.extensions.csrf:CSRFExtension",
            "beginnings.extensions.security_headers:SecurityHeadersExtension"
        ]
    
    return config


def _get_html_routes_template(template: str) -> str:
    """Get HTML routes template."""
    return '''"""HTML route handlers."""

from fastapi import Request
from fastapi.responses import HTMLResponse

def register_html_routes(app):
    """Register HTML routes with the application."""
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Home page."""
        return app.templates.TemplateResponse(
            "index.html",
            {"request": request, "title": "Welcome"}
        )
    
    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        """About page."""
        return app.templates.TemplateResponse(
            "base.html",
            {"request": request, "title": "About", "content": "About this application"}
        )
'''


def _get_api_routes_template(template: str) -> str:
    """Get API routes template."""
    return '''"""API route handlers."""

from fastapi import HTTPException
from typing import dict, List

def register_api_routes(app):
    """Register API routes with the application."""
    
    @app.get("/api/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "service": "beginnings-app"}
    
    @app.get("/api/info")
    async def app_info() -> dict:
        """Application information."""
        return {
            "name": app.config.get("app", {}).get("name", "Unknown"),
            "version": "1.0.0",
            "framework": "beginnings"
        }
'''


def _get_base_template() -> str:
    """Get base HTML template."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ title | default("Beginnings App") }}{% endblock %}</title>
    <link href="{{ url_for('static', path='/css/style.css') }}" rel="stylesheet">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
    </header>
    
    <main>
        {% block content %}
        <h1>{{ title | default("Welcome") }}</h1>
        <p>{{ content | default("Welcome to your beginnings application!") }}</p>
        {% endblock %}
    </main>
    
    <footer>
        <p>Powered by beginnings framework</p>
    </footer>
</body>
</html>'''


def _get_index_template() -> str:
    """Get index template."""
    return '''{% extends "base.html" %}

{% block content %}
<h1>Welcome to {{ title }}</h1>
<p>Your beginnings application is ready!</p>

<div class="features">
    <h2>Framework Features</h2>
    <ul>
        <li>Configuration-driven architecture</li>
        <li>Security by default</li>
        <li>Extension system</li>
        <li>Developer-friendly tools</li>
    </ul>
</div>

<div class="next-steps">
    <h2>Next Steps</h2>
    <ol>
        <li>Explore the configuration in <code>config/app.yaml</code></li>
        <li>Add your routes in <code>routes/</code></li>
        <li>Customize templates in <code>templates/</code></li>
        <li>Run <code>beginnings --help</code> for more commands</li>
    </ol>
</div>
{% endblock %}'''


def _get_main_file_template(project_name: str, template: str) -> str:
    """Get main application file template."""
    return f'''"""Main application entry point for {project_name}."""

from beginnings import App
from beginnings.config import load_config
from routes.html import register_html_routes

def create_app() -> App:
    """Create and configure the application."""
    # Load configuration
    config = load_config()
    
    # Create app instance
    app = App(config=config)
    
    # Register routes
    register_html_routes(app)
    
    # Register API routes if available
    try:
        from routes.api import register_api_routes
        register_api_routes(app)
    except ImportError:
        pass  # API routes not available in this template
    
    return app


# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    config = app.config.get("app", {{}})
    uvicorn.run(
        "main:app",
        host=config.get("host", "127.0.0.1"),
        port=config.get("port", 8000),
        reload=config.get("debug", False)
    )
'''


def _get_pyproject_template(project_name: str) -> str:
    """Get pyproject.toml template."""
    return f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "A beginnings web application"
dependencies = [
    "beginnings",
    "uvicorn[standard]",
]

[tool.uv]
dev-dependencies = [
    "pytest",
    "pytest-asyncio",
    "httpx",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''


def _get_gitignore_template() -> str:
    """Get .gitignore template."""
    return '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# Secrets
.env.local
.env.production
secrets/
'''


def _get_readme_template(project_name: str, template: str) -> str:
    """Get README.md template."""
    return f'''# {project_name}

A web application built with the beginnings framework.

## Features

- Configuration-driven architecture
- Security by default  
- Extension system
- Developer-friendly tools

## Getting Started

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run the development server:**
   ```bash
   beginnings run
   ```

3. **Open your browser:**
   Visit http://localhost:8000

## Project Structure

```
{project_name}/
├── config/              # Configuration files
│   ├── app.yaml        # Main configuration
│   └── app.dev.yaml    # Development overrides
├── routes/             # Route handlers
│   ├── html.py        # HTML routes
│   └── api.py         # API routes (if applicable)
├── templates/          # HTML templates
├── static/            # Static assets
├── tests/             # Test suite
└── main.py           # Application entry point
```

## Configuration

The application is configured through YAML files in the `config/` directory. 
See `config/app.yaml` for the main configuration and framework documentation 
for available options.

## Development

- `beginnings run` - Start development server with auto-reload
- `beginnings config validate` - Validate configuration files
- `beginnings config show` - Display merged configuration
- `beginnings --help` - See all available commands

## Deployment

For production deployment:

1. Set `BEGINNINGS_ENV=production`
2. Configure your production settings in `config/app.yaml`
3. Use a production WSGI server like gunicorn or uvicorn

## Learn More

- [Beginnings Documentation](https://beginnings.8ly.xyz/docs)
- [Configuration Reference](https://beginnings.8ly.xyz/docs/configuration)
- [Extension Development](https://beginnings.8ly.xyz/docs/extensions)
'''