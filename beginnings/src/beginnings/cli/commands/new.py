"""Project scaffolding commands."""

import click
import os
from typing import Optional

from ..utils.colors import success, error, info, highlight
from ..utils.errors import ProjectError
from ..utils.progress import spinner_context
from ..templates import TemplateEngine, get_template_config, AVAILABLE_TEMPLATES
from ..templates.templates import get_interactive_selections, validate_feature_dependencies, get_security_recommendations
from ..templates.engine import create_template_context
from ..templates.security import show_security_summary


@click.command(name="new")
@click.argument("project_name", type=str)
@click.option(
    "--template",
    type=click.Choice(list(AVAILABLE_TEMPLATES.keys())),
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
    
    # Get template configuration
    try:
        template_config = get_template_config(template)
        click.echo(info(f"Creating new beginnings project: {highlight(project_name)}"))
        click.echo(info(f"Template: {highlight(template_config['name'])} - {template_config['description']}"))
        click.echo(info(f"Location: {highlight(target_dir)}"))
        
        # Get user selections for custom template
        if template == "custom":
            click.echo(f"\n{highlight('Interactive Project Setup')}")
            user_selections = get_interactive_selections()
            user_selections = validate_feature_dependencies(user_selections)
            get_security_recommendations(user_selections)
        else:
            user_selections = template_config["features"]
        
        # Create template context
        template_context = create_template_context(project_name, template_config, user_selections)
        
        # Create project with template engine
        template_engine = TemplateEngine()
        
        with spinner_context("Generating project files"):
            template_engine.generate_project(
                "base",  # Use base template for all types
                target_dir,
                template_context,
                progress_callback=lambda msg: click.echo(info(msg)) if verbose else None
            )
        
        click.echo(success("Project files generated"))
        
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
        
        # Show security summary and next steps
        show_security_summary(user_selections, template_context.get("security_defaults", {}))
        _show_next_steps(project_name, target_dir, user_selections)
        
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
                "Verify network connectivity for dependencies",
                f"Try a different template: {', '.join(AVAILABLE_TEMPLATES.keys())}"
            ]
        )


def _is_valid_project_name(name: str) -> bool:
    """Validate project name follows conventions."""
    import re
    # Allow letters, numbers, hyphens, underscores
    # Must start with letter or underscore
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, name)) and len(name) <= 50


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


def _show_next_steps(project_name: str, target_dir: str, user_selections: dict):
    """Show next steps to the user."""
    click.echo(f"\n{success('Project created successfully!')}")
    click.echo(f"\nNext steps:")
    click.echo(f"  {highlight('1.')} cd {project_name}")
    click.echo(f"  {highlight('2.')} beginnings run")
    
    if user_selections.get("include_html", True):
        click.echo(f"  {highlight('3.')} Open http://localhost:8000 in your browser")
    if user_selections.get("include_api", False):
        click.echo(f"  {highlight('4.')} Explore API docs at http://localhost:8000/docs")
    
    click.echo(f"\nProject location: {highlight(target_dir)}")
    
    # Show feature-specific tips
    tips = []
    if user_selections.get("include_auth", False):
        tips.append("🔐 Authentication is configured - any username/password works for demo")
    if user_selections.get("include_csrf", False):
        tips.append("🛡️ CSRF protection is active - tokens are auto-handled in templates")
    if user_selections.get("include_rate_limiting", False):
        tips.append("⚡ Rate limiting is enabled - check config/app.yaml for limits")
    
    if tips:
        click.echo(f"\n{highlight('Features enabled:')}")
        for tip in tips:
            click.echo(f"  • {tip}")
    
    click.echo(f"\n{highlight('Useful commands:')}")
    click.echo("  • beginnings config validate  - Validate your configuration")
    click.echo("  • beginnings config show     - View merged configuration")
    click.echo("  • beginnings --help          - See all available commands")