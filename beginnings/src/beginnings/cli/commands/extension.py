"""Extension management commands."""

import click
import os
import re
from typing import Optional, List
from pathlib import Path

from ..utils.colors import success, error, info, highlight
from ..utils.errors import ProjectError
from ..utils.progress import ProgressBar
from ..templates.engine import TemplateEngine
from ..templates.security import generate_secure_defaults


@click.group(name="extension")
def extension_group():
    """Extension development and management commands."""
    pass


@click.command(name="new")
@click.argument("name")
@click.option(
    "--type", "-t",
    type=click.Choice(["middleware", "auth_provider", "feature", "integration"]),
    default="middleware",
    help="Type of extension to create"
)
@click.option(
    "--provider-base",
    type=click.Choice(["auth", "storage", "cache", "notification"]),
    help="Base provider type (for auth_provider type)"
)
@click.option(
    "--include-tests",
    is_flag=True,
    default=True,
    help="Include test scaffolding"
)
@click.option(
    "--include-docs",
    is_flag=True,
    default=True,
    help="Include documentation templates"
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory (default: ./extensions/)"
)
@click.option(
    "--interactive", "-i",
    is_flag=True,
    help="Interactive mode with guided questions"
)
@click.pass_context
def new_extension(
    ctx: click.Context,
    name: str,
    type: str,
    provider_base: Optional[str],
    include_tests: bool,
    include_docs: bool,
    output_dir: Optional[str],
    interactive: bool
):
    """Create a new extension with proper scaffolding.
    
    Creates a complete extension structure with:
    - Base extension class
    - Configuration handling
    - Middleware integration
    - Test scaffolding
    - Documentation templates
    
    Examples:
        beginnings extension new my_auth --type auth_provider --provider-base auth
        beginnings extension new rate_limiter --type middleware --interactive
        beginnings extension new webhook_handler --type integration
    """
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Creating new {type} extension: {name}"))
    
    try:
        # Validate extension name
        _validate_extension_name(name)
        
        # Interactive mode
        if interactive:
            type, provider_base, include_tests, include_docs = _interactive_extension_setup(
                name, type, provider_base, include_tests, include_docs
            )
        
        # Determine output directory
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "extensions")
        
        extension_dir = os.path.join(output_dir, name)
        
        # Check if extension already exists
        if os.path.exists(extension_dir):
            raise ProjectError(
                f"Extension directory already exists: {extension_dir}",
                suggestions=["Choose a different name", "Remove existing directory", "Use --output-dir to specify different location"]
            )
        
        # Create extension structure
        scaffolder = ExtensionScaffolder(
            name=name,
            extension_type=type,
            provider_base=provider_base,
            include_tests=include_tests,
            include_docs=include_docs,
            output_dir=output_dir,
            verbose=verbose,
            quiet=quiet
        )
        
        scaffolder.create_extension()
        
        if not quiet:
            click.echo(success(f"Extension '{name}' created successfully!"))
            click.echo(info(f"Location: {extension_dir}"))
            click.echo(info("Next steps:"))
            click.echo("  1. Review the generated files")
            click.echo("  2. Implement your extension logic")
            click.echo("  3. Run tests: pytest tests/")
            click.echo("  4. Add to your application configuration")
    
    except Exception as e:
        raise ProjectError(f"Failed to create extension: {e}")


@click.command(name="validate")
@click.argument("extension_path")
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Configuration file to validate against"
)
@click.pass_context
def validate_extension(
    ctx: click.Context,
    extension_path: str,
    config_file: Optional[str]
):
    """Validate extension structure and configuration."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    if not quiet:
        click.echo(info(f"Validating extension: {extension_path}"))
    
    try:
        validator = ExtensionValidator(extension_path, verbose=verbose)
        result = validator.validate()
        
        if result["valid"]:
            if not quiet:
                click.echo(success("Extension validation passed"))
                if verbose and result["warnings"]:
                    click.echo(info("Warnings:"))
                    for warning in result["warnings"]:
                        click.echo(f"  • {warning}")
        else:
            click.echo(error("Extension validation failed"))
            for err in result["errors"]:
                click.echo(f"  ✗ {err}")
            
            if result["suggestions"]:
                click.echo(info("Suggestions:"))
                for suggestion in result["suggestions"]:
                    click.echo(f"  • {suggestion}")
            
            raise click.Abort()
    
    except Exception as e:
        raise ProjectError(f"Validation failed: {e}")


@click.command(name="list")
@click.option(
    "--installed-only",
    is_flag=True,
    help="Show only installed extensions"
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format"
)
@click.pass_context
def list_extensions(
    ctx: click.Context,
    installed_only: bool,
    format: str
):
    """List available extensions."""
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    try:
        lister = ExtensionLister(verbose=verbose)
        extensions = lister.list_extensions(installed_only=installed_only)
        
        if format == "table":
            _display_extensions_table(extensions, quiet)
        elif format == "json":
            import json
            click.echo(json.dumps(extensions, indent=2))
        elif format == "yaml":
            import yaml
            click.echo(yaml.dump(extensions, default_flow_style=False))
    
    except Exception as e:
        raise ProjectError(f"Failed to list extensions: {e}")


def _validate_extension_name(name: str):
    """Validate extension name follows Python module naming conventions."""
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ProjectError(
            f"Invalid extension name: {name}",
            suggestions=[
                "Use lowercase letters, numbers, and underscores only",
                "Start with a letter",
                "Examples: my_auth, rate_limiter, webhook_handler"
            ]
        )
    
    if len(name) > 50:
        raise ProjectError("Extension name too long (max 50 characters)")


def _interactive_extension_setup(name, ext_type, provider_base, include_tests, include_docs):
    """Interactive setup for extension creation."""
    click.echo(highlight(f"Setting up extension: {name}"))
    click.echo()
    
    # Extension type
    click.echo("What type of extension would you like to create?")
    click.echo("  1. Middleware - Request/response processing")
    click.echo("  2. Auth Provider - Authentication mechanism")
    click.echo("  3. Feature - Complete feature with routes")
    click.echo("  4. Integration - Third-party service integration")
    
    choice = click.prompt("Choose type", type=click.IntRange(1, 4), default=1)
    type_map = {1: "middleware", 2: "auth_provider", 3: "feature", 4: "integration"}
    ext_type = type_map[choice]
    
    # Provider base for auth providers
    if ext_type == "auth_provider":
        click.echo()
        click.echo("What type of authentication provider?")
        click.echo("  1. auth - Standard authentication")
        click.echo("  2. storage - Storage-based auth")
        click.echo("  3. cache - Cache-based auth")
        click.echo("  4. notification - Notification-based auth")
        
        choice = click.prompt("Choose provider base", type=click.IntRange(1, 4), default=1)
        provider_map = {1: "auth", 2: "storage", 3: "cache", 4: "notification"}
        provider_base = provider_map[choice]
    
    # Additional options
    click.echo()
    include_tests = click.confirm("Include test scaffolding?", default=include_tests)
    include_docs = click.confirm("Include documentation templates?", default=include_docs)
    
    return ext_type, provider_base, include_tests, include_docs


def _display_extensions_table(extensions: List[dict], quiet: bool):
    """Display extensions in table format."""
    if not extensions:
        if not quiet:
            click.echo(info("No extensions found"))
        return
    
    if not quiet:
        click.echo(info(f"Found {len(extensions)} extension(s):"))
        click.echo()
    
    # Simple table display
    max_name = max(len(ext["name"]) for ext in extensions)
    max_type = max(len(ext["type"]) for ext in extensions)
    
    if not quiet:
        click.echo(f"{'Name':<{max_name}} {'Type':<{max_type}} Status")
        click.echo("-" * (max_name + max_type + 20))
    
    for ext in extensions:
        status = "✓ Installed" if ext["installed"] else "Available"
        if not quiet:
            click.echo(f"{ext['name']:<{max_name}} {ext['type']:<{max_type}} {status}")


class ExtensionScaffolder:
    """Handles creation of extension scaffolding."""
    
    def __init__(
        self,
        name: str,
        extension_type: str,
        provider_base: Optional[str] = None,
        include_tests: bool = True,
        include_docs: bool = True,
        output_dir: str = "extensions",
        verbose: bool = False,
        quiet: bool = False
    ):
        self.name = name
        self.extension_type = extension_type
        self.provider_base = provider_base
        self.include_tests = include_tests
        self.include_docs = include_docs
        self.output_dir = output_dir
        self.verbose = verbose
        self.quiet = quiet
        
        self.template_engine = TemplateEngine()
    
    def create_extension(self):
        """Create the complete extension structure."""
        extension_dir = Path(self.output_dir) / self.name
        extension_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.quiet:
            with ProgressBar(7, "Creating extension structure") as progress:
                self._create_core_files(extension_dir)
                progress.update(1)
                self._create_extension_class(extension_dir)
                progress.update(1)
                
                if self.extension_type == "auth_provider":
                    self._create_provider_files(extension_dir)
                elif self.extension_type == "feature":
                    self._create_feature_files(extension_dir)
                elif self.extension_type == "integration":
                    self._create_integration_files(extension_dir)
                progress.update(1)
                
                if self.include_tests:
                    self._create_test_files(extension_dir)
                    progress.update(1)
                
                if self.include_docs:
                    self._create_documentation(extension_dir)
                    progress.update(1)
        else:
            self._create_core_files(extension_dir)
            self._create_extension_class(extension_dir)
            
            if self.extension_type == "auth_provider":
                self._create_provider_files(extension_dir)
            elif self.extension_type == "feature":
                self._create_feature_files(extension_dir)
            elif self.extension_type == "integration":
                self._create_integration_files(extension_dir)
            
            if self.include_tests:
                self._create_test_files(extension_dir)
            
            if self.include_docs:
                self._create_documentation(extension_dir)
    
    def _create_core_files(self, extension_dir: Path):
        """Create core extension files."""
        # __init__.py
        init_content = self.template_engine.render_template(
            "extension_init.py.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (extension_dir / "__init__.py").write_text(init_content)
        
        # pyproject.toml for the extension
        pyproject_content = self.template_engine.render_template(
            "extension_pyproject.toml.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (extension_dir / "pyproject.toml").write_text(pyproject_content)
        
        # README.md
        readme_content = self.template_engine.render_template(
            "extension_readme.md.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (extension_dir / "README.md").write_text(readme_content)
    
    def _create_extension_class(self, extension_dir: Path):
        """Create the main extension class."""
        class_content = self.template_engine.render_template(
            f"extension_{self.extension_type}.py.j2",
            extension_name=self.name,
            provider_base=self.provider_base,
            security_defaults=generate_secure_defaults({})
        )
        (extension_dir / "extension.py").write_text(class_content)
    
    def _create_provider_files(self, extension_dir: Path):
        """Create provider-specific files for auth_provider type."""
        providers_dir = extension_dir / "providers"
        providers_dir.mkdir(exist_ok=True)
        
        # Base provider
        base_content = self.template_engine.render_template(
            f"provider_base_{self.provider_base}.py.j2",
            extension_name=self.name,
            provider_base=self.provider_base
        )
        (providers_dir / "base.py").write_text(base_content)
        
        # Provider __init__.py
        provider_init = self.template_engine.render_template(
            "provider_init.py.j2",
            extension_name=self.name,
            provider_base=self.provider_base
        )
        (providers_dir / "__init__.py").write_text(provider_init)
    
    def _create_feature_files(self, extension_dir: Path):
        """Create feature-specific files."""
        # Routes module
        routes_content = self.template_engine.render_template(
            "extension_routes.py.j2",
            extension_name=self.name
        )
        (extension_dir / "routes.py").write_text(routes_content)
        
        # Models module
        models_content = self.template_engine.render_template(
            "extension_models.py.j2",
            extension_name=self.name
        )
        (extension_dir / "models.py").write_text(models_content)
    
    def _create_integration_files(self, extension_dir: Path):
        """Create integration-specific files."""
        # Client module
        client_content = self.template_engine.render_template(
            "extension_client.py.j2",
            extension_name=self.name
        )
        (extension_dir / "client.py").write_text(client_content)
        
        # Webhooks module
        webhooks_content = self.template_engine.render_template(
            "extension_webhooks.py.j2",
            extension_name=self.name
        )
        (extension_dir / "webhooks.py").write_text(webhooks_content)
    
    def _create_test_files(self, extension_dir: Path):
        """Create test scaffolding."""
        tests_dir = extension_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        
        # Test __init__.py
        (tests_dir / "__init__.py").write_text("")
        
        # conftest.py
        conftest_content = self.template_engine.render_template(
            "test_conftest.py.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (tests_dir / "conftest.py").write_text(conftest_content)
        
        # Main test file
        test_content = self.template_engine.render_template(
            f"test_{self.extension_type}.py.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (tests_dir / f"test_{self.name}.py").write_text(test_content)
    
    def _create_documentation(self, extension_dir: Path):
        """Create documentation templates."""
        docs_dir = extension_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # User guide
        guide_content = self.template_engine.render_template(
            "extension_user_guide.md.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (docs_dir / "user_guide.md").write_text(guide_content)
        
        # Configuration reference
        config_content = self.template_engine.render_template(
            "extension_config_reference.md.j2",
            extension_name=self.name,
            extension_type=self.extension_type
        )
        (docs_dir / "configuration.md").write_text(config_content)


class ExtensionValidator:
    """Validates extension structure and configuration."""
    
    def __init__(self, extension_path: str, verbose: bool = False):
        self.extension_path = Path(extension_path)
        self.verbose = verbose
    
    def validate(self) -> dict:
        """Validate the extension."""
        errors = []
        warnings = []
        suggestions = []
        
        # Check directory exists
        if not self.extension_path.exists():
            errors.append(f"Extension directory not found: {self.extension_path}")
            return {"valid": False, "errors": errors, "warnings": warnings, "suggestions": suggestions}
        
        # Check required files
        required_files = ["__init__.py", "extension.py"]
        for file in required_files:
            if not (self.extension_path / file).exists():
                errors.append(f"Required file missing: {file}")
        
        # Check extension class
        if (self.extension_path / "extension.py").exists():
            try:
                self._validate_extension_class()
            except Exception as e:
                errors.append(f"Extension class validation failed: {e}")
        
        # Check test structure
        if (self.extension_path / "tests").exists():
            test_warnings = self._validate_test_structure()
            warnings.extend(test_warnings)
        else:
            warnings.append("No tests directory found")
            suggestions.append("Add test scaffolding with: beginnings extension new --include-tests")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    def _validate_extension_class(self):
        """Validate the extension class implementation."""
        # This would import and check the extension class
        # For now, just check basic syntax
        extension_file = self.extension_path / "extension.py"
        content = extension_file.read_text()
        
        if "BaseExtension" not in content:
            raise ValueError("Extension must inherit from BaseExtension")
        
        if "def get_middleware_factory" not in content:
            raise ValueError("Extension must implement get_middleware_factory method")
    
    def _validate_test_structure(self) -> List[str]:
        """Validate test structure and return warnings."""
        warnings = []
        tests_dir = self.extension_path / "tests"
        
        if not (tests_dir / "conftest.py").exists():
            warnings.append("No conftest.py found in tests directory")
        
        test_files = list(tests_dir.glob("test_*.py"))
        if not test_files:
            warnings.append("No test files found (test_*.py)")
        
        return warnings


class ExtensionLister:
    """Lists available and installed extensions."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def list_extensions(self, installed_only: bool = False) -> List[dict]:
        """List extensions."""
        extensions = []
        
        # Scan current directory for extensions
        current_dir = Path.cwd()
        
        # Check extensions directory
        extensions_dir = current_dir / "extensions"
        if extensions_dir.exists():
            for ext_dir in extensions_dir.iterdir():
                if ext_dir.is_dir() and (ext_dir / "__init__.py").exists():
                    ext_info = self._get_extension_info(ext_dir)
                    if not installed_only or ext_info["installed"]:
                        extensions.append(ext_info)
        
        # Check builtin extensions
        if not installed_only:
            builtin_extensions = [
                {"name": "auth", "type": "auth_provider", "installed": True},
                {"name": "csrf", "type": "middleware", "installed": True},
                {"name": "rate_limiting", "type": "middleware", "installed": True},
                {"name": "security_headers", "type": "middleware", "installed": True},
            ]
            extensions.extend(builtin_extensions)
        
        return sorted(extensions, key=lambda x: x["name"])
    
    def _get_extension_info(self, ext_dir: Path) -> dict:
        """Get extension information."""
        extension_type = "unknown"
        installed = True
        
        # Try to determine type from extension.py
        extension_file = ext_dir / "extension.py"
        if extension_file.exists():
            content = extension_file.read_text()
            if "AuthProvider" in content:
                extension_type = "auth_provider"
            elif "routes.py" in str(ext_dir):
                extension_type = "feature"
            elif "client.py" in str(ext_dir):
                extension_type = "integration"
            else:
                extension_type = "middleware"
        
        return {
            "name": ext_dir.name,
            "type": extension_type,
            "installed": installed
        }


@click.command(name="test")
@click.argument("extension_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--performance", "-p",
    is_flag=True,
    help="Run performance benchmarks"
)
@click.option(
    "--benchmark", "-b",
    is_flag=True,
    help="Run comprehensive benchmark suite"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Custom benchmark configuration file"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file for benchmark results"
)
@click.option(
    "--duration",
    type=int,
    default=30,
    help="Benchmark duration in seconds (default: 30)"
)
@click.option(
    "--concurrent",
    type=int,
    default=10,
    help="Number of concurrent requests (default: 10)"
)
@click.option(
    "--threshold-ms",
    type=float,
    default=500.0,
    help="Response time threshold in milliseconds (default: 500)"
)
@click.pass_context
def test_extension(
    ctx,
    extension_path: str,
    performance: bool,
    benchmark: bool,
    config: Optional[str],
    output: Optional[str],
    duration: int,
    concurrent: int,
    threshold_ms: float
):
    """Test an extension with optional performance benchmarking."""
    from ...testing import (
        ExtensionTestRunner, 
        BenchmarkConfiguration,
        PerformanceBenchmarkFixtures
    )
    import importlib.util
    import sys
    import json
    from datetime import datetime
    
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    extension_dir = Path(extension_path)
    
    if not extension_dir.exists():
        raise ProjectError(f"Extension directory not found: {extension_path}")
    
    try:
        # Load the extension module
        extension_module_path = extension_dir / "__init__.py"
        if not extension_module_path.exists():
            extension_module_path = extension_dir / f"{extension_dir.name}.py"
        
        if not extension_module_path.exists():
            raise ProjectError(f"No extension module found in {extension_path}")
        
        # Import the extension
        spec = importlib.util.spec_from_file_location("test_extension", extension_module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_extension"] = module
        spec.loader.exec_module(module)
        
        # Find the extension class
        extension_class = None
        for name, obj in vars(module).items():
            if (hasattr(obj, '__bases__') and 
                any('BaseExtension' in str(base) for base in obj.__bases__)):
                extension_class = obj
                break
        
        if not extension_class:
            raise ProjectError("No extension class found in module")
        
        if verbose and not quiet:
            click.echo(info(f"Testing extension: {extension_class.__name__}"))
            click.echo()
        
        # Load benchmark configuration
        benchmark_config = BenchmarkConfiguration(
            duration_seconds=duration,
            concurrent_requests=concurrent,
            response_time_threshold_ms=threshold_ms
        )
        
        if config:
            import yaml
            with open(config, 'r') as f:
                config_data = yaml.safe_load(f)
                
                # Update benchmark config with file values
                for key, value in config_data.items():
                    if hasattr(benchmark_config, key):
                        setattr(benchmark_config, key, value)
        
        # Initialize test runner
        runner = ExtensionTestRunner(
            extension_class,
            extension_path=str(extension_dir),
            verbose=verbose and not quiet
        )
        
        # Run tests based on options
        if benchmark or performance:
            # Run full tests with benchmarks
            results = runner.run_all_tests_with_benchmarks(
                include_benchmarks=True,
                benchmark_config=benchmark_config
            )
            
            if not quiet:
                _display_test_results_with_benchmarks(results, verbose)
        else:
            # Run standard tests only
            results = runner.run_all_tests()
            
            if not quiet:
                _display_test_results(results, verbose)
        
        # Export results if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            if verbose and not quiet:
                click.echo(success(f"Results exported to: {output}"))
        
        # Exit with error code if tests failed
        if benchmark or performance:
            if results.get("benchmarks", {}).get("validation", {}).get("passed", True):
                if results["total_failed"] == 0:
                    if not quiet:
                        click.echo(success("All tests and benchmarks passed!"))
                else:
                    if not quiet:
                        click.echo(error(f"Tests failed: {results['total_failed']} failures"))
                    sys.exit(1)
            else:
                if not quiet:
                    click.echo(error("Performance benchmarks failed requirements"))
                sys.exit(1)
        else:
            if results["total_failed"] == 0:
                if not quiet:
                    click.echo(success("All tests passed!"))
            else:
                if not quiet:
                    click.echo(error(f"Tests failed: {results['total_failed']} failures"))
                sys.exit(1)
    
    except Exception as e:
        raise ProjectError(f"Extension testing failed: {e}")


def _display_test_results(results: dict, verbose: bool):
    """Display standard test results."""
    click.echo(highlight("Test Results"))
    click.echo("=" * 50)
    
    click.echo(f"Extension: {results.get('extension', 'Unknown')}")
    click.echo(f"Total Passed: {results['total_passed']}")
    click.echo(f"Total Failed: {results['total_failed']}")
    
    if results["all_errors"]:
        click.echo("\nErrors:")
        for error in results["all_errors"]:
            click.echo(f"  - {error}")
    
    if verbose:
        click.echo(f"\nConfiguration Tests: {results['config_tests']['passed']}/{results['config_tests']['passed'] + results['config_tests']['failed']}")
        click.echo(f"Middleware Tests: {results['middleware_tests']['passed']}/{results['middleware_tests']['passed'] + results['middleware_tests']['failed']}")
        click.echo(f"Lifecycle Tests: {results['lifecycle_tests']['passed']}/{results['lifecycle_tests']['passed'] + results['lifecycle_tests']['failed']}")


def _display_test_results_with_benchmarks(results: dict, verbose: bool):
    """Display test results including benchmark data."""
    # Display standard test results first
    _display_test_results(results, verbose)
    
    # Display benchmark results
    if "benchmarks" in results:
        benchmarks = results["benchmarks"]
        
        click.echo("\n" + highlight("Performance Benchmarks"))
        click.echo("=" * 50)
        
        click.echo(f"Performance Score: {benchmarks['performance_score']:.1f}/100")
        
        validation = benchmarks.get("validation", {})
        requirements_met = "✓" if validation.get("passed", False) else "✗"
        click.echo(f"Requirements Met: {requirements_met}")
        
        # Display individual benchmark results
        for benchmark in benchmarks.get("benchmarks", []):
            bench_type = benchmark["type"]
            result = benchmark["result"]
            
            click.echo(f"\n{bench_type.title()} Benchmark:")
            
            if bench_type == "startup":
                click.echo(f"  Startup Time: {result['duration_ms']:.2f}ms")
                click.echo(f"  Memory Usage: {result['memory_usage_mb']:.2f}MB")
                click.echo(f"  CPU Usage: {result['cpu_usage_percent']:.1f}%")
            
            elif bench_type == "middleware":
                click.echo(f"  Requests/Second: {result['requests_per_second']:.2f}")
                click.echo(f"  Error Rate: {result['error_rate']:.2%}")
                if result['percentiles']:
                    click.echo(f"  P95 Response Time: {result['percentiles'].get('p95', 0):.2f}ms")
                    click.echo(f"  Average Response Time: {result['percentiles'].get('avg', 0):.2f}ms")
            
            elif bench_type == "throughput":
                click.echo(f"  Throughput: {result['requests_per_second']:.2f} req/s")
                click.echo(f"  Error Rate: {result['error_rate']:.2%}")
                if result['percentiles']:
                    click.echo(f"  P95 Response Time: {result['percentiles'].get('p95', 0):.2f}ms")
            
            elif bench_type == "memory":
                if isinstance(result['memory_usage_mb'], dict):
                    click.echo(f"  Peak Memory: {result['memory_usage_mb'].get('max', 0):.2f}MB")
                    click.echo(f"  Average Memory: {result['memory_usage_mb'].get('avg', 0):.2f}MB")
                click.echo(f"  Memory Growth: {result['memory_growth_mb']:.2f}MB")
        
        # Display violations if any
        if validation.get("violations"):
            click.echo(f"\n{error('Performance Violations:')}")
            for violation in validation["violations"]:
                click.echo(f"  - {violation['message']}")


# Add commands to the group
extension_group.add_command(new_extension)
extension_group.add_command(validate_extension)
extension_group.add_command(list_extensions)
extension_group.add_command(test_extension)