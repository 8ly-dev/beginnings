"""Main documentation generator and configuration."""

from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, List, Optional, Union, Set
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .parsers import CodeParser, ConfigParser, ExtensionParser
from .renderers import HTMLRenderer, MarkdownRenderer, PDFRenderer
from .extractors import APIExtractor, RouteExtractor, ExtensionExtractor
from .templates import TemplateEngine, ThemeManager
from .utils import DocumentationUtils
import http.server
import socketserver
import webbrowser
import threading
from urllib.parse import urlparse


class OutputFormat(Enum):
    """Documentation output formats."""
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"


class DocumentationLevel(Enum):
    """Documentation detail levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class DocumentationConfig:
    """Configuration for documentation generation."""
    
    # Input paths
    source_paths: List[str] = field(default_factory=lambda: ["src"])
    config_paths: List[str] = field(default_factory=lambda: ["config"])
    extension_paths: List[str] = field(default_factory=lambda: ["extensions"])
    
    # Output configuration
    output_dir: str = "docs"
    output_formats: List[OutputFormat] = field(default_factory=lambda: [OutputFormat.HTML])
    
    # Content configuration
    project_name: str = "Beginnings Project"
    project_version: str = "1.0.0"
    project_description: str = ""
    author: str = ""
    
    # Feature flags
    include_api_reference: bool = True
    include_configuration_docs: bool = True
    include_extension_docs: bool = True
    config_file: Optional[str] = None
    
    # Generation options
    include_private: bool = False
    include_tests: bool = False
    include_examples: bool = True
    include_source_links: bool = True
    auto_cross_reference: bool = True
    
    # Detail level
    detail_level: DocumentationLevel = DocumentationLevel.DETAILED
    
    # Theme and styling
    theme: str = "default"
    custom_css: Optional[str] = None
    logo_path: Optional[str] = None
    
    # Advanced options
    exclude_patterns: List[str] = field(default_factory=lambda: ["__pycache__", "*.pyc", ".git"])
    include_patterns: List[str] = field(default_factory=lambda: ["*.py", "*.md", "*.rst"])
    
    # API documentation
    api_base_url: Optional[str] = None
    include_request_examples: bool = True
    include_response_examples: bool = True
    
    # Extension documentation
    extension_auto_discovery: bool = True
    include_extension_examples: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "source_paths": self.source_paths,
            "config_paths": self.config_paths,
            "extension_paths": self.extension_paths,
            "output_dir": self.output_dir,
            "output_formats": [fmt.value for fmt in self.output_formats],
            "project_name": self.project_name,
            "project_version": self.project_version,
            "project_description": self.project_description,
            "author": self.author,
            "include_private": self.include_private,
            "include_tests": self.include_tests,
            "include_examples": self.include_examples,
            "include_source_links": self.include_source_links,
            "auto_cross_reference": self.auto_cross_reference,
            "detail_level": self.detail_level.value,
            "theme": self.theme,
            "custom_css": self.custom_css,
            "logo_path": self.logo_path,
            "exclude_patterns": self.exclude_patterns,
            "include_patterns": self.include_patterns,
            "api_base_url": self.api_base_url,
            "include_request_examples": self.include_request_examples,
            "include_response_examples": self.include_response_examples,
            "extension_auto_discovery": self.extension_auto_discovery,
            "include_extension_examples": self.include_extension_examples
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DocumentationConfig:
        """Create configuration from dictionary."""
        config = cls()
        
        # Update fields from dictionary
        for key, value in data.items():
            if hasattr(config, key):
                if key == "output_formats":
                    config.output_formats = [OutputFormat(fmt) for fmt in value]
                elif key == "detail_level":
                    config.detail_level = DocumentationLevel(value)
                else:
                    setattr(config, key, value)
        
        return config


class DocumentationGenerator:
    """Main documentation generator."""
    
    def __init__(self, config: Optional[DocumentationConfig] = None):
        """Initialize documentation generator.
        
        Args:
            config: Documentation configuration
        """
        self.config = config or DocumentationConfig()
        
        # Initialize components
        self.code_parser = CodeParser()
        self.config_parser = ConfigParser()
        self.extension_parser = ExtensionParser()
        
        self.api_extractor = APIExtractor()
        self.route_extractor = RouteExtractor()
        self.extension_extractor = ExtensionExtractor()
        
        self.template_engine = TemplateEngine()
        self.theme_manager = ThemeManager()
        
        # Initialize renderers
        self.renderers = {
            OutputFormat.HTML: HTMLRenderer(self.template_engine, self.theme_manager),
            OutputFormat.MARKDOWN: MarkdownRenderer(),
            OutputFormat.PDF: PDFRenderer(),
        }
        
        # Documentation data
        self.documentation_data = {}
        self.cross_references = {}
        
    async def generate(self, config_override: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate complete documentation.
        
        Args:
            config_override: Optional configuration overrides
            
        Returns:
            Generation results
        """
        # Apply configuration overrides
        if config_override:
            for key, value in config_override.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        result = GenerationResult()
        
        start_time = datetime.utcnow()
        
        try:
            # Prepare output directory
            await self._prepare_output_directory()
            
            # Create a basic index.html file for now
            output_path = Path(self.config.output_dir)
            for output_format in self.config.output_formats:
                format_dir = output_path / output_format.value
                format_dir.mkdir(parents=True, exist_ok=True)
                
                if output_format == OutputFormat.HTML:
                    index_file = format_dir / "index.html"
                    with open(index_file, 'w') as f:
                        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.config.project_name} Documentation</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .generated {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{self.config.project_name} Documentation</h1>
    <p>Version: {self.config.project_version}</p>
    <p class="generated">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    
    <h2>Project Overview</h2>
    <p>Welcome to the {self.config.project_name} documentation.</p>
    
    <h2>Sections</h2>
    <ul>
        <li><a href="#api">API Reference</a></li>
        <li><a href="#configuration">Configuration</a></li>
        <li><a href="#extensions">Extensions</a></li>
    </ul>
    
    <h3 id="api">API Reference</h3>
    <p>API documentation coming soon...</p>
    
    <h3 id="configuration">Configuration</h3>
    <p>Configuration documentation coming soon...</p>
    
    <h3 id="extensions">Extensions</h3>
    <p>Extension documentation coming soon...</p>
</body>
</html>""")
                    result.generated_files.append(str(index_file))
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Documentation generation failed: {e}")
        
        return result
    
    async def generate_api_documentation(self) -> Dict[str, Any]:
        """Generate API documentation only.
        
        Returns:
            API documentation data
        """
        api_data = {}
        
        # Extract API routes and endpoints
        for source_path in self.config.source_paths:
            path = Path(source_path)
            if path.exists():
                routes = await self.route_extractor.extract_routes(path)
                api_endpoints = await self.api_extractor.extract_api_endpoints(path)
                
                api_data.update({
                    "routes": routes,
                    "endpoints": api_endpoints,
                    "models": await self.api_extractor.extract_models(path),
                    "middleware": await self.api_extractor.extract_middleware(path)
                })
        
        return api_data
    
    async def generate_extension_documentation(self) -> Dict[str, Any]:
        """Generate extension documentation only.
        
        Returns:
            Extension documentation data
        """
        extension_data = {}
        
        # Extract extension information
        for extension_path in self.config.extension_paths:
            path = Path(extension_path)
            if path.exists():
                extensions = await self.extension_extractor.extract_extensions(path)
                extension_data.update(extensions)
        
        return extension_data
    
    async def generate_config_documentation(self) -> Dict[str, Any]:
        """Generate configuration documentation only.
        
        Returns:
            Configuration documentation data
        """
        config_data = {}
        
        # Parse configuration files
        for config_path in self.config.config_paths:
            path = Path(config_path)
            if path.exists():
                configs = await self.config_parser.parse_config_files(path)
                config_data.update(configs)
        
        return config_data
    
    async def update_documentation(self, changed_files: List[str]) -> Dict[str, Any]:
        """Update documentation for changed files.
        
        Args:
            changed_files: List of files that have changed
            
        Returns:
            Update results
        """
        results = {
            "updated_files": [],
            "errors": [],
            "warnings": []
        }
        
        # Determine which documentation needs updating
        affected_sections = await self._determine_affected_sections(changed_files)
        
        # Update affected sections
        for section in affected_sections:
            try:
                await self._update_documentation_section(section, results)
            except Exception as e:
                results["errors"].append(f"Failed to update {section}: {e}")
        
        return results
    
    async def validate_documentation(self) -> Dict[str, Any]:
        """Validate documentation for completeness and accuracy.
        
        Returns:
            Validation results
        """
        validation_results = {
            "missing_docstrings": [],
            "broken_links": [],
            "orphaned_files": [],
            "incomplete_api_docs": [],
            "warnings": [],
            "score": 0.0
        }
        
        # Check for missing docstrings
        await self._check_missing_docstrings(validation_results)
        
        # Validate cross-references and links
        await self._validate_links(validation_results)
        
        # Check API documentation completeness
        await self._validate_api_documentation(validation_results)
        
        # Calculate documentation score
        validation_results["score"] = await self._calculate_documentation_score(validation_results)
        
        return validation_results
    
    async def _prepare_output_directory(self):
        """Prepare output directory structure."""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different output formats
        for output_format in self.config.output_formats:
            format_dir = output_path / output_format.value
            format_dir.mkdir(exist_ok=True)
    
    async def _extract_documentation_data(self, results: Dict[str, Any]):
        """Extract all documentation data from source files."""
        self.documentation_data = {
            "api": {},
            "extensions": {},
            "configuration": {},
            "code_documentation": {},
            "examples": {},
            "metadata": {
                "project_name": self.config.project_name,
                "project_version": self.config.project_version,
                "project_description": self.config.project_description,
                "author": self.config.author,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        try:
            # Extract API documentation
            self.documentation_data["api"] = await self.generate_api_documentation()
            
            # Extract extension documentation
            self.documentation_data["extensions"] = await self.generate_extension_documentation()
            
            # Extract configuration documentation
            self.documentation_data["configuration"] = await self.generate_config_documentation()
            
            # Extract code documentation
            await self._extract_code_documentation()
            
            # Extract examples
            if self.config.include_examples:
                await self._extract_examples()
                
        except Exception as e:
            results["errors"].append(f"Data extraction failed: {e}")
    
    async def _extract_code_documentation(self):
        """Extract documentation from code files."""
        code_docs = {}
        
        for source_path in self.config.source_paths:
            path = Path(source_path)
            if path.exists():
                modules = await self.code_parser.parse_modules(
                    path,
                    include_private=self.config.include_private,
                    include_tests=self.config.include_tests
                )
                code_docs.update(modules)
        
        self.documentation_data["code_documentation"] = code_docs
    
    async def _extract_examples(self):
        """Extract code examples and tutorials."""
        examples = {}
        
        # Look for example files
        for source_path in self.config.source_paths:
            path = Path(source_path)
            if path.exists():
                example_files = path.glob("**/examples/**/*.py")
                for example_file in example_files:
                    example_content = await self.code_parser.parse_example_file(example_file)
                    if example_content:
                        examples[str(example_file.relative_to(path))] = example_content
        
        self.documentation_data["examples"] = examples
    
    async def _build_cross_references(self):
        """Build cross-reference map for documentation."""
        self.cross_references = {}
        
        # Build references from API data
        api_data = self.documentation_data.get("api", {})
        for endpoint_name, endpoint_data in api_data.get("endpoints", {}).items():
            self.cross_references[endpoint_name] = {
                "type": "api_endpoint",
                "path": f"api/endpoints/{endpoint_name}",
                "title": endpoint_data.get("summary", endpoint_name)
            }
        
        # Build references from extension data
        extensions_data = self.documentation_data.get("extensions", {})
        for extension_name, extension_data in extensions_data.items():
            self.cross_references[extension_name] = {
                "type": "extension",
                "path": f"extensions/{extension_name}",
                "title": extension_data.get("description", extension_name)
            }
        
        # Build references from code documentation
        code_docs = self.documentation_data.get("code_documentation", {})
        for module_name, module_data in code_docs.items():
            self.cross_references[module_name] = {
                "type": "module",
                "path": f"code/{module_name}",
                "title": module_data.docstring or module_name
            }
            
            # Add class and function references
            for class_name, class_data in module_data.classes.items():
                full_name = f"{module_name}.{class_name}"
                self.cross_references[full_name] = {
                    "type": "class",
                    "path": f"code/{module_name}#{class_name}",
                    "title": class_data.docstring or class_name
                }
                
                for method_name in class_data.methods:
                    method_full_name = f"{full_name}.{method_name}"
                    self.cross_references[method_full_name] = {
                        "type": "method",
                        "path": f"code/{module_name}#{class_name}.{method_name}",
                        "title": method_name
                    }
    
    async def _generate_format_documentation(self, output_format: OutputFormat, results: Dict[str, Any]):
        """Generate documentation for specific output format."""
        try:
            renderer = self.renderers[output_format]
            
            # Set theme for the renderer
            if output_format == OutputFormat.HTML:
                await renderer.set_theme(self.config.theme)
                if self.config.custom_css:
                    await renderer.add_custom_css(self.config.custom_css)
            
            # Generate documentation files
            generated_files = await renderer.render_documentation(
                self.documentation_data,
                self.cross_references,
                self.config
            )
            
            # Save files to output directory
            output_dir = Path(self.config.output_dir) / output_format.value
            for file_path, content in generated_files.items():
                full_path = output_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(content, str):
                    full_path.write_text(content, encoding='utf-8')
                else:
                    full_path.write_bytes(content)
                
                results["generated_files"].append(str(full_path))
                
        except Exception as e:
            results["errors"].append(f"Failed to generate {output_format.value} documentation: {e}")
    
    async def _copy_static_assets(self, results: Dict[str, Any]):
        """Copy static assets like CSS, JavaScript, images."""
        try:
            # Copy theme assets
            for output_format in self.config.output_formats:
                if output_format == OutputFormat.HTML:
                    theme_assets = await self.theme_manager.get_theme_assets(self.config.theme)
                    output_dir = Path(self.config.output_dir) / output_format.value
                    
                    for asset_path, asset_content in theme_assets.items():
                        full_path = output_dir / "assets" / asset_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        if isinstance(asset_content, str):
                            full_path.write_text(asset_content, encoding='utf-8')
                        else:
                            full_path.write_bytes(asset_content)
                        
                        results["generated_files"].append(str(full_path))
            
            # Copy logo if specified
            if self.config.logo_path and Path(self.config.logo_path).exists():
                logo_path = Path(self.config.logo_path)
                for output_format in self.config.output_formats:
                    output_dir = Path(self.config.output_dir) / output_format.value
                    logo_dest = output_dir / "assets" / f"logo{logo_path.suffix}"
                    logo_dest.parent.mkdir(parents=True, exist_ok=True)
                    logo_dest.write_bytes(logo_path.read_bytes())
                    results["generated_files"].append(str(logo_dest))
                    
        except Exception as e:
            results["warnings"].append(f"Failed to copy some static assets: {e}")
    
    async def _generate_statistics(self) -> Dict[str, Any]:
        """Generate documentation statistics."""
        stats = {
            "total_modules": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_api_endpoints": 0,
            "total_extensions": 0,
            "documentation_coverage": 0.0,
            "generated_files_count": 0
        }
        
        # Count code documentation items
        code_docs = self.documentation_data.get("code_documentation", {})
        stats["total_modules"] = len(code_docs)
        
        for module_data in code_docs.values():
            stats["total_classes"] += len(module_data.classes)
            stats["total_functions"] += len(module_data.functions)
        
        # Count API endpoints
        api_data = self.documentation_data.get("api", {})
        stats["total_api_endpoints"] = len(api_data.get("endpoints", {}))
        
        # Count extensions
        extensions_data = self.documentation_data.get("extensions", {})
        stats["total_extensions"] = len(extensions_data)
        
        # Calculate documentation coverage (simplified)
        documented_items = 0
        total_items = 0
        
        for module_data in code_docs.values():
            for class_data in module_data.classes.values():
                total_items += 1
                if class_data.docstring:
                    documented_items += 1
                    
                for method_data in class_data.methods.values():
                    total_items += 1
                    if method_data.docstring:
                        documented_items += 1
            
            for func_data in module_data.functions.values():
                total_items += 1
                if func_data.docstring:
                    documented_items += 1
        
        if total_items > 0:
            stats["documentation_coverage"] = (documented_items / total_items) * 100
        
        return stats
    
    async def _determine_affected_sections(self, changed_files: List[str]) -> Set[str]:
        """Determine which documentation sections are affected by file changes."""
        affected_sections = set()
        
        for file_path in changed_files:
            path = Path(file_path)
            
            # Check if it's a source file
            if any(path.is_relative_to(src_path) for src_path in self.config.source_paths):
                affected_sections.add("code_documentation")
                affected_sections.add("api")
            
            # Check if it's a configuration file
            if any(path.is_relative_to(cfg_path) for cfg_path in self.config.config_paths):
                affected_sections.add("configuration")
            
            # Check if it's an extension file
            if any(path.is_relative_to(ext_path) for ext_path in self.config.extension_paths):
                affected_sections.add("extensions")
        
        return affected_sections
    
    async def _update_documentation_section(self, section: str, results: Dict[str, Any]):
        """Update specific documentation section."""
        if section == "code_documentation":
            await self._extract_code_documentation()
        elif section == "api":
            self.documentation_data["api"] = await self.generate_api_documentation()
        elif section == "configuration":
            self.documentation_data["configuration"] = await self.generate_config_documentation()
        elif section == "extensions":
            self.documentation_data["extensions"] = await self.generate_extension_documentation()
        
        results["updated_files"].append(section)
    
    async def _check_missing_docstrings(self, validation_results: Dict[str, Any]):
        """Check for missing docstrings in code."""
        missing_docstrings = []
        
        code_docs = self.documentation_data.get("code_documentation", {})
        for module_name, module_data in code_docs.items():
            # Check module docstring
            if not module_data.docstring:
                missing_docstrings.append(f"Module: {module_name}")
            
            # Check class docstrings
            for class_name, class_data in module_data.classes.items():
                if not class_data.docstring:
                    missing_docstrings.append(f"Class: {module_name}.{class_name}")
                
                # Check method docstrings
                for method_name, method_data in class_data.methods.items():
                    if not method_data.docstring:
                        missing_docstrings.append(f"Method: {module_name}.{class_name}.{method_name}")
            
            # Check function docstrings
            for func_name, func_data in module_data.functions.items():
                if not func_data.docstring:
                    missing_docstrings.append(f"Function: {module_name}.{func_name}")
        
        validation_results["missing_docstrings"] = missing_docstrings
    
    async def _validate_links(self, validation_results: Dict[str, Any]):
        """Validate cross-references and external links."""
        broken_links = []
        
        # This would implement link validation
        # For now, just placeholder
        validation_results["broken_links"] = broken_links
    
    async def _validate_api_documentation(self, validation_results: Dict[str, Any]):
        """Validate API documentation completeness."""
        incomplete_api_docs = []
        
        api_data = self.documentation_data.get("api", {})
        for endpoint_name, endpoint_data in api_data.get("endpoints", {}).items():
            if not endpoint_data.get("description"):
                incomplete_api_docs.append(f"Endpoint {endpoint_name} missing description")
            
            if not endpoint_data.get("parameters"):
                incomplete_api_docs.append(f"Endpoint {endpoint_name} missing parameter documentation")
            
            if not endpoint_data.get("responses"):
                incomplete_api_docs.append(f"Endpoint {endpoint_name} missing response documentation")
        
        validation_results["incomplete_api_docs"] = incomplete_api_docs
    
    async def _calculate_documentation_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall documentation quality score."""
        total_issues = (
            len(validation_results["missing_docstrings"]) +
            len(validation_results["broken_links"]) +
            len(validation_results["incomplete_api_docs"])
        )
        
        # Simple scoring: 100 - (issues * penalty)
        penalty_per_issue = 2.0
        score = max(0.0, 100.0 - (total_issues * penalty_per_issue))
        
        return score


@dataclass 
class GenerationResult:
    """Result of documentation generation."""
    success: bool = False
    generated_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    
class DocumentationServer:
    """Simple HTTP server for serving documentation."""
    
    def __init__(
        self,
        docs_dir: str,
        host: str = "127.0.0.1",
        port: int = 8080,
        auto_reload: bool = False,
        verbose: bool = False
    ):
        self.docs_dir = Path(docs_dir)
        self.host = host
        self.port = port
        self.auto_reload = auto_reload
        self.verbose = verbose
        self.server = None
        
    def serve(self):
        """Start serving documentation."""
        if not self.docs_dir.exists():
            raise FileNotFoundError(f"Documentation directory not found: {self.docs_dir}")
        
        # Change to docs directory 
        original_cwd = os.getcwd()
        os.chdir(self.docs_dir)
        
        try:
            with socketserver.TCPServer((self.host, self.port), http.server.SimpleHTTPRequestHandler) as httpd:
                self.server = httpd
                if self.verbose:
                    print(f"Serving documentation at http://{self.host}:{self.port}")
                httpd.serve_forever()
        finally:
            os.chdir(original_cwd)


