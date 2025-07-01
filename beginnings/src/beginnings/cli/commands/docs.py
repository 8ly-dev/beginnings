"""Documentation generation and management commands."""

import click
import asyncio
import json
import os
from typing import Optional
from pathlib import Path

from ..utils.colors import success, error, info, highlight, warning
from ..utils.errors import CLIError
from ...docs.generator import (
    DocumentationGenerator, DocumentationConfig, OutputFormat, DocumentationLevel
)
from ...docs.utils import DocumentationUtils


@click.group(name="docs")
def docs_group():
    """Documentation generation and management commands."""
    pass


@click.command(name="generate")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="docs",
    help="Output directory for generated documentation"
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["html", "markdown", "pdf", "json"]),
    multiple=True,
    default=["html"],
    help="Output format(s) for documentation"
)
@click.option(
    "--level",
    type=click.Choice(["basic", "detailed", "comprehensive"]),
    default="detailed",
    help="Documentation detail level"
)
@click.option(
    "--include-api",
    is_flag=True,
    help="Include API reference documentation"
)
@click.option(
    "--include-config",
    is_flag=True,
    default=True,
    help="Include configuration documentation"
)
@click.option(
    "--include-extensions",
    is_flag=True,
    default=True,
    help="Include extension documentation"
)
@click.option(
    "--theme",
    type=str,
    default="default",
    help="Documentation theme"
)
@click.option(
    "--project-name",
    type=str,
    help="Project name for documentation"
)
@click.option(
    "--project-version",
    type=str,
    default="1.0.0",
    help="Project version for documentation"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def generate_command(
    ctx: click.Context,
    config: Optional[str],
    output: str,
    output_format: tuple,
    level: str,
    include_api: bool,
    include_config: bool,
    include_extensions: bool,
    theme: str,
    project_name: Optional[str],
    project_version: str,
    verbose: bool
):
    """Generate comprehensive documentation for the project.
    
    This command analyzes your Beginnings project and generates complete
    documentation including API references, configuration guides, and
    extension documentation.
    """
    try:
        if verbose:
            info("Starting documentation generation...")
        
        # Determine project name from config or directory
        if not project_name:
            if config:
                import yaml
                with open(config) as f:
                    config_data = yaml.safe_load(f)
                    project_name = config_data.get("app", {}).get("name", "Beginnings Project")
            else:
                project_name = Path.cwd().name.replace("-", " ").replace("_", " ").title()
        
        # Convert output formats
        formats = [OutputFormat(fmt) for fmt in output_format]
        doc_level = DocumentationLevel(level)
        
        # Create documentation configuration
        doc_config = DocumentationConfig(
            output_dir=output,
            output_formats=formats,
            project_name=project_name,
            project_version=project_version,
            detail_level=doc_level,
            include_api_reference=include_api,
            include_configuration_docs=include_config,
            include_extension_docs=include_extensions,
            theme=theme,
            config_file=config
        )
        
        if verbose:
            info(f"Configuration: {project_name} v{project_version}")
            info(f"Output formats: {', '.join(output_format)}")
            info(f"Output directory: {output}")
        
        # Initialize documentation generator
        generator = DocumentationGenerator(doc_config)
        
        # Generate documentation
        result = asyncio.run(generator.generate())
        
        if result.success:
            success(f"Documentation generated successfully!")
            info(f"Output directory: {highlight(output)}")
            
            if verbose:
                info(f"Generated {len(result.generated_files)} files")
                for file_path in result.generated_files:
                    info(f"  - {file_path}")
            
            # Show summary
            click.echo()
            click.echo("📖 Documentation Summary:")
            for fmt in formats:
                format_dir = Path(output) / fmt.value
                if format_dir.exists():
                    file_count = len(list(format_dir.rglob("*")))
                    click.echo(f"  {fmt.value.upper()}: {file_count} files")
            
            if OutputFormat.HTML in formats:
                html_index = Path(output) / "html" / "index.html"
                if html_index.exists():
                    click.echo(f"\n🌐 View documentation: file://{html_index.absolute()}")
            
        else:
            error("Documentation generation failed!")
            if result.errors:
                for err in result.errors:
                    error(f"  - {err}")
            ctx.exit(1)
            
    except Exception as e:
        error(f"Documentation generation failed: {e}")
        if verbose:
            import traceback
            error(traceback.format_exc())
        ctx.exit(1)


@click.command(name="serve")
@click.option(
    "--docs-dir", "-d",
    type=click.Path(exists=True),
    default="docs",
    help="Documentation directory to serve"
)
@click.option(
    "--port", "-p",
    type=int,
    default=8080,
    help="Port to serve documentation on"
)
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host to bind server to"
)
@click.option(
    "--auto-reload",
    is_flag=True,
    help="Auto-reload documentation when files change"
)
@click.option(
    "--open-browser",
    is_flag=True,
    default=True,
    help="Open browser automatically"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def serve_command(
    ctx: click.Context,
    docs_dir: str,
    port: int,
    host: str,
    auto_reload: bool,
    open_browser: bool,
    verbose: bool
):
    """Serve documentation locally with live preview.
    
    This command starts a local web server to preview your generated
    documentation. Optionally enables auto-reload when documentation
    files change.
    """
    try:
        docs_path = Path(docs_dir)
        
        if not docs_path.exists():
            error(f"Documentation directory not found: {docs_dir}")
            error("Run 'beginnings docs generate' first to create documentation.")
            ctx.exit(1)
        
        # Look for HTML documentation
        html_dir = docs_path / "html"
        if html_dir.exists():
            serve_dir = html_dir
        else:
            serve_dir = docs_path
        
        if verbose:
            info(f"Serving documentation from: {serve_dir}")
            info(f"Server address: http://{host}:{port}")
        
        # Import and start documentation server
        from ...docs.generator import DocumentationServer
        
        server = DocumentationServer(
            docs_dir=str(serve_dir),
            host=host,
            port=port,
            auto_reload=auto_reload,
            verbose=verbose
        )
        
        success(f"Starting documentation server on http://{host}:{port}")
        
        if open_browser:
            import webbrowser
            webbrowser.open(f"http://{host}:{port}")
        
        info("Press Ctrl+C to stop the server")
        
        # Start the server
        server.serve()
        
    except KeyboardInterrupt:
        info("\nDocumentation server stopped.")
    except Exception as e:
        error(f"Failed to start documentation server: {e}")
        if verbose:
            import traceback
            error(traceback.format_exc())
        ctx.exit(1)


@click.command(name="validate")
@click.option(
    "--docs-dir", "-d",
    type=click.Path(exists=True),
    default="docs",
    help="Documentation directory to validate"
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for validation results"
)
@click.option(
    "--check-links",
    is_flag=True,
    help="Check for broken links"
)
@click.option(
    "--check-accessibility",
    is_flag=True,
    help="Check accessibility compliance"
)
@click.option(
    "--check-required",
    is_flag=True,
    help="Check for required documentation pages"
)
@click.option(
    "--check-html",
    is_flag=True,
    default=True,
    help="Validate HTML syntax"
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning", "info"]),
    default="warning",
    help="Minimum severity level to report"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def validate_command(
    ctx: click.Context,
    docs_dir: str,
    output_format: str,
    check_links: bool,
    check_accessibility: bool,
    check_required: bool,
    check_html: bool,
    severity: str,
    verbose: bool
):
    """Validate generated documentation for errors and compliance.
    
    This command performs comprehensive validation of your documentation
    including HTML syntax, broken links, accessibility compliance, and
    completeness checks.
    """
    try:
        docs_path = Path(docs_dir)
        
        if not docs_path.exists():
            error(f"Documentation directory not found: {docs_dir}")
            ctx.exit(1)
        
        if verbose:
            info(f"Validating documentation in: {docs_dir}")
        
        # Initialize documentation validator
        from ...docs.utils import DocumentationValidator
        
        validator = DocumentationValidator(
            docs_dir=str(docs_path),
            check_links=check_links,
            check_accessibility=check_accessibility,
            check_required_pages=check_required,
            check_html_syntax=check_html,
            min_severity=severity,
            verbose=verbose
        )
        
        # Run validation
        results = asyncio.run(validator.validate())
        
        if output_format == "json":
            # Output JSON results
            click.echo(json.dumps(results.to_dict(), indent=2))
        else:
            # Output human-readable results
            _display_validation_results(results, verbose)
        
        # Exit with appropriate code
        if results.has_errors():
            ctx.exit(1)
        elif results.has_warnings() and severity in ["error", "warning"]:
            ctx.exit(1)
        else:
            ctx.exit(0)
            
    except Exception as e:
        error(f"Documentation validation failed: {e}")
        if verbose:
            import traceback
            error(traceback.format_exc())
        ctx.exit(1)


def _display_validation_results(results, verbose: bool = False):
    """Display validation results in human-readable format."""
    
    total_errors = len(results.errors)
    total_warnings = len(results.warnings)
    total_info = len(results.info)
    
    # Summary
    click.echo("\n📋 Documentation Validation Results")
    click.echo("=" * 50)
    
    if total_errors == 0 and total_warnings == 0:
        success("✓ All validation checks passed!")
    else:
        if total_errors > 0:
            error(f"✗ {total_errors} error(s) found")
        if total_warnings > 0:
            warning(f"⚠ {total_warnings} warning(s) found")
        if total_info > 0:
            info(f"ℹ {total_info} info message(s)")
    
    # Detailed results
    if verbose or total_errors > 0:
        
        # Show errors
        if results.errors:
            click.echo("\n🚫 Errors:")
            for error_item in results.errors:
                click.echo(f"  ✗ {error_item['message']}")
                if 'file' in error_item:
                    click.echo(f"    File: {error_item['file']}")
                if 'line' in error_item:
                    click.echo(f"    Line: {error_item['line']}")
        
        # Show warnings
        if results.warnings:
            click.echo("\n⚠️  Warnings:")
            for warning_item in results.warnings:
                click.echo(f"  ⚠ {warning_item['message']}")
                if 'file' in warning_item:
                    click.echo(f"    File: {warning_item['file']}")
        
        # Show info
        if verbose and results.info:
            click.echo("\nℹ️  Information:")
            for info_item in results.info:
                click.echo(f"  ℹ {info_item['message']}")
    
    # Recommendations
    if total_errors > 0 or total_warnings > 0:
        click.echo("\n💡 Recommendations:")
        if total_errors > 0:
            click.echo("  • Fix all errors before deploying documentation")
        if total_warnings > 0:
            click.echo("  • Review warnings for potential improvements")
        click.echo("  • Run validation again after making changes")


# Add commands to group
docs_group.add_command(generate_command)
docs_group.add_command(serve_command)
docs_group.add_command(validate_command)