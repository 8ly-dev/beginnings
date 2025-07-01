"""Django to Beginnings migration tool."""

from pathlib import Path
from typing import Dict, List, Any
import asyncio

from ..base import BaseMigrator


class DjangoMigrator(BaseMigrator):
    """Migrates Django applications to Beginnings framework."""
    
    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        convert_models: bool = True,
        convert_views: bool = True,
        convert_auth: bool = True,
        convert_admin: bool = False,
        verbose: bool = False
    ):
        """Initialize Django migrator.
        
        Args:
            source_dir: Django project directory
            output_dir: Output directory for Beginnings project
            convert_models: Whether to convert Django models
            convert_views: Whether to convert Django views
            convert_auth: Whether to convert Django auth
            convert_admin: Whether to convert Django admin
            verbose: Enable verbose output
        """
        super().__init__(source_dir, output_dir, verbose)
        self.convert_models = convert_models
        self.convert_views = convert_views
        self.convert_auth = convert_auth
        self.convert_admin = convert_admin
    
    async def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """Perform Django to Beginnings migration.
        
        Args:
            dry_run: If True, only analyze without creating files
            
        Returns:
            Migration results
        """
        if self.verbose:
            print(f"Starting Django migration from {self.source_dir}")
        
        # Basic analysis for now
        source_path = Path(self.source_dir)
        
        # Count Django components
        apps_count = len(list(source_path.glob("*/models.py")))
        views_count = len(list(source_path.glob("*/views.py")))
        urls_count = len(list(source_path.glob("*/urls.py")))
        models_count = 0
        
        # Count models (simplified)
        for models_file in source_path.glob("*/models.py"):
            if models_file.exists():
                content = models_file.read_text()
                models_count += content.count("class ") - content.count("class Meta")
        
        result = {
            'apps_count': apps_count,
            'models_count': models_count,
            'views_count': views_count,
            'urls_count': urls_count,
            'admin_detected': any(source_path.glob("*/admin.py")),
            'success': True
        }
        
        if not dry_run:
            # Create basic Beginnings project structure
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create directories
            (output_path / "config").mkdir(exist_ok=True)
            (output_path / "routes").mkdir(exist_ok=True)
            (output_path / "templates").mkdir(exist_ok=True)
            (output_path / "static").mkdir(exist_ok=True)
            
            # Create basic files
            (output_path / "main.py").write_text('''"""Main application file converted from Django."""

from beginnings.core.app import BeginningsApp

# Create application instance
app = BeginningsApp()

# TODO: Add converted Django routes
# TODO: Configure converted Django models

if __name__ == "__main__":
    app.run()
''')
            
            # Create basic config
            import yaml
            config = {
                'app': {
                    'name': source_path.name,
                    'debug': False
                }
            }
            
            with open(output_path / "config" / "app.yaml", 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
        
        return result
    
    def generate_report(self, result: Dict[str, Any], report_path: Path):
        """Generate detailed Django migration report."""
        report_content = f'''# Django to Beginnings Migration Report

## Project: {Path(self.source_dir).name}

**Migration Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Source Directory:** `{self.source_dir}`
- **Output Directory:** `{self.output_dir}`
- **Migration Status:** {"✅ Success" if result.get('success') else "❌ Failed"}

## Conversion Statistics

| Component | Count |
|-----------|-------|
| Django Apps | {result.get('apps_count', 0)} |
| Models | {result.get('models_count', 0)} |
| Views | {result.get('views_count', 0)} |
| URL Patterns | {result.get('urls_count', 0)} |
| Admin Interface | {"✅ Detected" if result.get('admin_detected') else "❌ Not detected"} |

## Manual Conversion Required

Django to Beginnings migration requires significant manual work:

1. **Models:** Convert Django ORM models to your preferred data layer
2. **Views:** Convert Django views to Beginnings route handlers
3. **URLs:** Convert URL patterns to Beginnings routing
4. **Templates:** Update Django template tags to Jinja2
5. **Middleware:** Convert Django middleware to Beginnings middleware
6. **Authentication:** Configure Beginnings auth extension
7. **Admin:** Implement admin interface using Beginnings patterns

This migration tool provides the basic project structure. Detailed conversion must be done manually.
'''
        
        report_path.write_text(report_content)