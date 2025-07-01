"""Renderers for different documentation output formats."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime, timezone

try:
    import markdown
    from markdown.extensions import codehilite, toc, tables
except ImportError:
    markdown = None

try:
    from weasyprint import HTML, CSS
except ImportError:
    HTML = CSS = None

from .templates import TemplateEngine, ThemeManager


class BaseRenderer(ABC):
    """Base class for documentation renderers."""
    
    def __init__(self):
        self.output_files = {}
    
    @abstractmethod
    async def render_documentation(
        self, 
        documentation_data: Dict[str, Any],
        cross_references: Dict[str, Any],
        config: Any
    ) -> Dict[str, Union[str, bytes]]:
        """Render documentation to output format.
        
        Args:
            documentation_data: Extracted documentation data
            cross_references: Cross-reference mapping
            config: Documentation configuration
            
        Returns:
            Dictionary mapping file paths to content
        """
        pass
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a name for use as filename."""
        # Replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = re.sub(r'\.+', '.', sanitized)
        sanitized = sanitized.strip('.')
        
        # Truncate to filesystem limits (255 characters for most filesystems)
        if len(sanitized) > 255:
            # Preserve file extension if present
            if '.' in sanitized:
                name_part, ext = sanitized.rsplit('.', 1)
                max_name_length = 255 - len(ext) - 1  # -1 for the dot
                sanitized = name_part[:max_name_length] + '.' + ext
            else:
                sanitized = sanitized[:255]
        
        return sanitized


class HTMLRenderer(BaseRenderer):
    """Renderer for HTML documentation."""
    
    def __init__(self, template_engine: TemplateEngine, theme_manager: ThemeManager):
        super().__init__()
        self.template_engine = template_engine
        self.theme_manager = theme_manager
        self.current_theme = "default"
    
    def _safe_get(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safely get value from object that could be dict or have attributes."""
        if hasattr(obj, key):
            return getattr(obj, key, default)
        elif hasattr(obj, 'get'):
            return obj.get(key, default)
        elif isinstance(obj, dict):
            return obj.get(key, default)
        else:
            return default
    
    async def set_theme(self, theme_name: str):
        """Set the theme for HTML rendering."""
        self.current_theme = theme_name
        await self.theme_manager.load_theme(theme_name)
    
    async def add_custom_css(self, css_path: str):
        """Add custom CSS to the renderer."""
        if Path(css_path).exists():
            css_content = Path(css_path).read_text(encoding='utf-8')
            await self.theme_manager.add_custom_css(css_content)
    
    async def render_documentation(
        self, 
        documentation_data: Dict[str, Any],
        cross_references: Dict[str, Any],
        config: Any
    ) -> Dict[str, Union[str, bytes]]:
        """Render HTML documentation."""
        output_files = {}
        
        # Render main index page
        index_html = await self._render_index_page(documentation_data, config)
        output_files["index.html"] = index_html
        
        # Render API documentation
        if documentation_data.get("api"):
            api_files = await self._render_api_documentation(
                documentation_data["api"], cross_references, config
            )
            output_files.update(api_files)
        
        # Render code documentation
        if documentation_data.get("code_documentation"):
            code_files = await self._render_code_documentation(
                documentation_data["code_documentation"], cross_references, config
            )
            output_files.update(code_files)
        
        # Render extension documentation
        if documentation_data.get("extensions"):
            ext_files = await self._render_extension_documentation(
                documentation_data["extensions"], cross_references, config
            )
            output_files.update(ext_files)
        
        # Render configuration documentation
        if documentation_data.get("configuration"):
            config_files = await self._render_config_documentation(
                documentation_data["configuration"], cross_references, config
            )
            output_files.update(config_files)
        
        # Render examples
        if documentation_data.get("examples"):
            example_files = await self._render_examples(
                documentation_data["examples"], cross_references, config
            )
            output_files.update(example_files)
        
        return output_files
    
    async def _render_index_page(self, documentation_data: Dict[str, Any], config: Any) -> str:
        """Render the main index page."""
        template_data = {
            "title": f"{config.project_name} Documentation",
            "project_name": config.project_name,
            "project_version": config.project_version,
            "project_description": config.project_description,
            "author": config.author,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "sections": self._get_available_sections(documentation_data),
            "theme": self.current_theme
        }
        
        return await self.template_engine.render_template("index.html", **template_data)
    
    def _get_available_sections(self, documentation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of available documentation sections."""
        sections = []
        
        if documentation_data.get("api"):
            sections.append({
                "name": "API Reference",
                "url": "api/index.html",
                "description": "REST API endpoints and schemas",
                "icon": "api"
            })
        
        if documentation_data.get("code_documentation"):
            sections.append({
                "name": "Code Documentation",
                "url": "code/index.html",
                "description": "Module, class, and function documentation",
                "icon": "code"
            })
        
        if documentation_data.get("extensions"):
            sections.append({
                "name": "Extensions",
                "url": "extensions/index.html",
                "description": "Available extensions and plugins",
                "icon": "extension"
            })
        
        if documentation_data.get("configuration"):
            sections.append({
                "name": "Configuration",
                "url": "config/index.html",
                "description": "Configuration options and examples",
                "icon": "config"
            })
        
        if documentation_data.get("examples"):
            sections.append({
                "name": "Examples",
                "url": "examples/index.html",
                "description": "Code examples and tutorials",
                "icon": "example"
            })
        
        return sections
    
    async def _render_api_documentation(
        self, 
        api_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> Dict[str, str]:
        """Render API documentation."""
        files = {}
        
        # API index page
        api_index = await self.template_engine.render_template(
            "api_index.html",
            title="API Reference",
            endpoints=api_data.get("endpoints", {}),
            models=api_data.get("models", {}),
            middleware=api_data.get("middleware", {}),
            base_url=config.api_base_url,
            theme=self.current_theme
        )
        files["api/index.html"] = api_index
        
        # Individual endpoint pages
        for endpoint_key, endpoint_data in api_data.get("endpoints", {}).items():
            endpoint_html = await self.template_engine.render_template(
                "api_endpoint.html",
                title=f"{endpoint_data.method} {endpoint_data.path}",
                endpoint=endpoint_data,
                cross_references=cross_references,
                include_examples=config.include_request_examples,
                theme=self.current_theme
            )
            
            filename = self._sanitize_filename(f"api/endpoints/{endpoint_key}.html")
            files[filename] = endpoint_html
        
        # Model documentation pages
        for model_name, model_data in api_data.get("models", {}).items():
            model_html = await self.template_engine.render_template(
                "api_model.html",
                title=f"Model: {model_name}",
                model=model_data,
                cross_references=cross_references,
                theme=self.current_theme
            )
            
            filename = self._sanitize_filename(f"api/models/{model_name}.html")
            files[filename] = model_html
        
        return files
    
    async def _render_code_documentation(
        self, 
        code_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> Dict[str, str]:
        """Render code documentation."""
        files = {}
        
        # Code index page
        code_index = await self.template_engine.render_template(
            "code_index.html",
            title="Code Documentation",
            modules=code_data,
            theme=self.current_theme
        )
        files["code/index.html"] = code_index
        
        # Individual module pages
        for module_name, module_data in code_data.items():
            module_html = await self.template_engine.render_template(
                "code_module.html",
                title=f"Module: {module_name}",
                module=module_data,
                module_name=module_name,
                cross_references=cross_references,
                include_source_links=config.include_source_links,
                theme=self.current_theme
            )
            
            filename = self._sanitize_filename(f"code/modules/{module_name}.html")
            files[filename] = module_html
            
            # Individual class pages for detailed view
            classes = self._safe_get(module_data, "classes", {})
            for class_name, class_data in classes.items():
                class_html = await self.template_engine.render_template(
                    "code_class.html",
                    title=f"Class: {module_name}.{class_name}",
                    class_data=class_data,
                    class_name=class_name,
                    module_name=module_name,
                    cross_references=cross_references,
                    theme=self.current_theme
                )
                
                filename = self._sanitize_filename(f"code/classes/{module_name}.{class_name}.html")
                files[filename] = class_html
        
        return files
    
    async def _render_extension_documentation(
        self, 
        extensions_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> Dict[str, str]:
        """Render extension documentation."""
        files = {}
        
        # Extensions index page
        ext_index = await self.template_engine.render_template(
            "extensions_index.html",
            title="Extensions",
            extensions=extensions_data,
            theme=self.current_theme
        )
        files["extensions/index.html"] = ext_index
        
        # Individual extension pages
        for ext_name, ext_data in extensions_data.items():
            ext_html = await self.template_engine.render_template(
                "extension.html",
                title=f"Extension: {ext_name}",
                extension=ext_data,
                extension_name=ext_name,
                cross_references=cross_references,
                include_examples=config.include_extension_examples,
                theme=self.current_theme
            )
            
            filename = self._sanitize_filename(f"extensions/{ext_name}.html")
            files[filename] = ext_html
        
        return files
    
    async def _render_config_documentation(
        self, 
        config_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> Dict[str, str]:
        """Render configuration documentation."""
        files = {}
        
        # Configuration index page
        config_index = await self.template_engine.render_template(
            "config_index.html",
            title="Configuration",
            config_files=config_data,
            theme=self.current_theme
        )
        files["config/index.html"] = config_index
        
        # Individual configuration file pages
        for config_file, config_info in config_data.items():
            config_html = await self.template_engine.render_template(
                "config_file.html",
                title=f"Configuration: {config_file}",
                config_info=config_info,
                config_file=config_file,
                theme=self.current_theme
            )
            
            filename = self._sanitize_filename(f"config/{config_file}.html")
            files[filename] = config_html
        
        return files
    
    async def _render_examples(
        self, 
        examples_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> Dict[str, str]:
        """Render examples documentation."""
        files = {}
        
        # Examples index page
        examples_index = await self.template_engine.render_template(
            "examples_index.html",
            title="Examples",
            examples=examples_data,
            theme=self.current_theme
        )
        files["examples/index.html"] = examples_index
        
        # Individual example pages
        for example_name, example_data in examples_data.items():
            example_html = await self.template_engine.render_template(
                "example.html",
                title=f"Example: {example_data.get('title', example_name)}",
                example=example_data,
                example_name=example_name,
                cross_references=cross_references,
                theme=self.current_theme
            )
            
            filename = self._sanitize_filename(f"examples/{example_name}.html")
            files[filename] = example_html
        
        return files


class MarkdownRenderer(BaseRenderer):
    """Renderer for Markdown documentation."""
    
    def __init__(self):
        super().__init__()
        self.markdown_processor = None
    
    def _safe_get(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safely get value from object that could be dict or have attributes."""
        if hasattr(obj, key):
            return getattr(obj, key, default)
        elif hasattr(obj, 'get'):
            return obj.get(key, default)
        elif isinstance(obj, dict):
            return obj.get(key, default)
        else:
            return default
        
        if markdown:
            self.markdown_processor = markdown.Markdown(
                extensions=['codehilite', 'toc', 'tables', 'fenced_code'],
                extension_configs={
                    'codehilite': {
                        'guess_lang': True,
                        'use_pygments': True
                    },
                    'toc': {
                        'permalink': True
                    }
                }
            )
    
    async def render_documentation(
        self, 
        documentation_data: Dict[str, Any],
        cross_references: Dict[str, Any],
        config: Any
    ) -> Dict[str, str]:
        """Render Markdown documentation."""
        output_files = {}
        
        # Main README
        readme_content = await self._render_readme(documentation_data, config)
        output_files["README.md"] = readme_content
        
        # API documentation
        if documentation_data.get("api"):
            api_content = await self._render_api_markdown(
                documentation_data["api"], cross_references, config
            )
            output_files["API.md"] = api_content
        
        # Code documentation
        if documentation_data.get("code_documentation"):
            code_content = await self._render_code_markdown(
                documentation_data["code_documentation"], cross_references, config
            )
            output_files["CODE.md"] = code_content
        
        # Extensions documentation
        if documentation_data.get("extensions"):
            ext_content = await self._render_extensions_markdown(
                documentation_data["extensions"], cross_references, config
            )
            output_files["EXTENSIONS.md"] = ext_content
        
        # Configuration documentation
        if documentation_data.get("configuration"):
            config_content = await self._render_config_markdown(
                documentation_data["configuration"], config
            )
            output_files["CONFIGURATION.md"] = config_content
        
        return output_files
    
    async def _render_readme(self, documentation_data: Dict[str, Any], config: Any) -> str:
        """Render main README file."""
        content = []
        
        # Title and description
        content.append(f"# {config.project_name}")
        content.append("")
        if config.project_description:
            content.append(config.project_description)
            content.append("")
        
        # Version and author info
        if config.project_version:
            content.append(f"**Version:** {config.project_version}")
        if config.author:
            content.append(f"**Author:** {config.author}")
        content.append("")
        
        # Table of contents
        content.append("## Table of Contents")
        content.append("")
        
        if documentation_data.get("api"):
            content.append("- [API Reference](API.md)")
        if documentation_data.get("code_documentation"):
            content.append("- [Code Documentation](CODE.md)")
        if documentation_data.get("extensions"):
            content.append("- [Extensions](EXTENSIONS.md)")
        if documentation_data.get("configuration"):
            content.append("- [Configuration](CONFIGURATION.md)")
        
        content.append("")
        
        # Quick start section
        content.append("## Quick Start")
        content.append("")
        content.append("<!-- Add quick start instructions here -->")
        content.append("")
        
        # Generation info
        content.append("---")
        content.append(f"*Documentation generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*")
        
        return "\n".join(content)
    
    async def _render_api_markdown(
        self, 
        api_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> str:
        """Render API documentation in Markdown."""
        content = []
        
        content.append("# API Reference")
        content.append("")
        
        # Endpoints
        endpoints = api_data.get("endpoints", {})
        if endpoints:
            content.append("## Endpoints")
            content.append("")
            
            for endpoint_key, endpoint in endpoints.items():
                content.append(f"### {endpoint.method} {endpoint.path}")
                content.append("")
                
                if endpoint.summary:
                    content.append(endpoint.summary)
                    content.append("")
                
                if endpoint.description:
                    content.append(endpoint.description)
                    content.append("")
                
                # Parameters
                if endpoint.parameters:
                    content.append("**Parameters:**")
                    content.append("")
                    for param in endpoint.parameters:
                        param_line = f"- `{param['name']}` ({param.get('type', 'string')})"
                        if param.get('required'):
                            param_line += " *required*"
                        if param.get('description'):
                            param_line += f": {param['description']}"
                        content.append(param_line)
                    content.append("")
                
                # Responses
                if endpoint.responses:
                    content.append("**Responses:**")
                    content.append("")
                    for status_code, response_info in endpoint.responses.items():
                        content.append(f"- `{status_code}`: {response_info.get('description', 'Success')}")
                    content.append("")
                
                content.append("---")
                content.append("")
        
        # Models
        models = api_data.get("models", {})
        if models:
            content.append("## Data Models")
            content.append("")
            
            for model_name, model in models.items():
                content.append(f"### {model_name}")
                content.append("")
                
                if model.description:
                    content.append(model.description)
                    content.append("")
                
                if model.fields:
                    content.append("**Fields:**")
                    content.append("")
                    content.append("| Field | Type | Required | Description |")
                    content.append("|-------|------|----------|-------------|")
                    
                    for field_name, field_info in model.fields.items():
                        required = "Yes" if field_name in model.required_fields else "No"
                        description = field_info.get('description', '')
                        field_type = field_info.get('type', 'any')
                        content.append(f"| {field_name} | {field_type} | {required} | {description} |")
                    
                    content.append("")
                
                content.append("---")
                content.append("")
        
        return "\n".join(content)
    
    async def _render_code_markdown(
        self, 
        code_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> str:
        """Render code documentation in Markdown."""
        content = []
        
        content.append("# Code Documentation")
        content.append("")
        
        for module_name, module_data in code_data.items():
            content.append(f"## Module: {module_name}")
            content.append("")
            
            docstring = self._safe_get(module_data, "docstring")
            if docstring:
                content.append(docstring)
                content.append("")
            
            # Classes
            classes = self._safe_get(module_data, "classes", {})
            if classes:
                content.append("### Classes")
                content.append("")
                
                for class_name, class_data in classes.items():
                    content.append(f"#### {class_name}")
                    content.append("")
                    
                    class_docstring = self._safe_get(class_data, "docstring")
                    if class_docstring:
                        content.append(class_docstring)
                        content.append("")
                    
                    # Base classes
                    base_classes = self._safe_get(class_data, "base_classes")
                    if base_classes:
                        content.append(f"**Inherits from:** {', '.join(base_classes)}")
                        content.append("")
                    
                    # Methods
                    methods = self._safe_get(class_data, "methods", {})
                    if methods:
                        content.append("**Methods:**")
                        content.append("")
                        
                        for method_name, method_data in methods.items():
                            method_signature = f"{method_name}("
                            parameters = self._safe_get(method_data, "parameters")
                            if parameters:
                                params = []
                                for param in parameters:
                                    param_str = self._safe_get(param, "name", "")
                                    param_type = self._safe_get(param, "type")
                                    if param_type:
                                        param_str += f": {param_type}"
                                    param_default = self._safe_get(param, "default")
                                    if param_default is not None:
                                        param_str += f" = {param_default}"
                                    params.append(param_str)
                                method_signature += ", ".join(params)
                            method_signature += ")"
                            
                            return_type = self._safe_get(method_data, "return_type")
                            if return_type:
                                method_signature += f" -> {return_type}"
                            
                            content.append(f"- `{method_signature}`")
                            method_docstring = self._safe_get(method_data, "docstring")
                            if method_docstring:
                                content.append(f"  {method_docstring}")
                        
                        content.append("")
            
            # Functions
            functions = self._safe_get(module_data, "functions", {})
            if functions:
                content.append("### Functions")
                content.append("")
                
                for func_name, func_data in functions.items():
                    func_signature = f"{func_name}("
                    parameters = self._safe_get(func_data, "parameters")
                    if parameters:
                        params = []
                        for param in parameters:
                            param_str = self._safe_get(param, "name", "")
                            param_type = self._safe_get(param, "type")
                            if param_type:
                                param_str += f": {param_type}"
                            param_default = self._safe_get(param, "default")
                            if param_default is not None:
                                param_str += f" = {param_default}"
                            params.append(param_str)
                        func_signature += ", ".join(params)
                    func_signature += ")"
                    
                    return_type = self._safe_get(func_data, "return_type")
                    if return_type:
                        func_signature += f" -> {return_type}"
                    
                    content.append(f"#### {func_signature}")
                    content.append("")
                    
                    func_docstring = self._safe_get(func_data, "docstring")
                    if func_docstring:
                        content.append(func_docstring)
                        content.append("")
            
            content.append("---")
            content.append("")
        
        return "\n".join(content)
    
    async def _render_extensions_markdown(
        self, 
        extensions_data: Dict[str, Any], 
        cross_references: Dict[str, Any], 
        config: Any
    ) -> str:
        """Render extensions documentation in Markdown."""
        content = []
        
        content.append("# Extensions")
        content.append("")
        
        for ext_name, ext_data in extensions_data.items():
            content.append(f"## {ext_name}")
            content.append("")
            
            # Metadata
            metadata = ext_data.get("metadata", {})
            if metadata.get("description"):
                content.append(metadata["description"])
                content.append("")
            
            if metadata.get("version"):
                content.append(f"**Version:** {metadata['version']}")
            if metadata.get("author"):
                content.append(f"**Author:** {metadata['author']}")
            
            # Dependencies
            if metadata.get("dependencies"):
                content.append(f"**Dependencies:** {', '.join(metadata['dependencies'])}")
            
            content.append("")
            
            # Configuration
            configuration = ext_data.get("configuration", {})
            if configuration:
                content.append("### Configuration")
                content.append("")
                content.append("```json")
                content.append(json.dumps(configuration, indent=2))
                content.append("```")
                content.append("")
            
            # API Endpoints
            api_endpoints = ext_data.get("api_endpoints", {})
            if api_endpoints:
                content.append("### API Endpoints")
                content.append("")
                for endpoint_key, endpoint in api_endpoints.items():
                    content.append(f"- `{endpoint.method} {endpoint.path}`")
                    if endpoint.summary:
                        content.append(f"  {endpoint.summary}")
                content.append("")
            
            content.append("---")
            content.append("")
        
        return "\n".join(content)
    
    async def _render_config_markdown(
        self, 
        config_data: Dict[str, Any], 
        config: Any
    ) -> str:
        """Render configuration documentation in Markdown."""
        content = []
        
        content.append("# Configuration")
        content.append("")
        
        for config_file, config_info in config_data.items():
            content.append(f"## {config_file}")
            content.append("")
            
            file_format = config_info.get("format", "unknown")
            content.append(f"**Format:** {file_format}")
            content.append("")
            
            # Schema information
            schema = config_info.get("schema", {})
            if schema and isinstance(schema, dict):
                content.append("### Configuration Options")
                content.append("")
                self._render_schema_markdown(schema, content, level=0)
            
            # Documentation from comments
            documentation = config_info.get("documentation", {})
            if documentation:
                content.append("### Documentation")
                content.append("")
                for key, doc in documentation.items():
                    content.append(f"- `{key}`: {doc}")
                content.append("")
            
            content.append("---")
            content.append("")
        
        return "\n".join(content)
    
    def _render_schema_markdown(self, schema: Dict[str, Any], content: List[str], level: int = 0):
        """Render configuration schema in Markdown."""
        indent = "  " * level
        
        if schema.get("type") == "object" and "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                prop_type = prop_schema.get("type", "unknown")
                content.append(f"{indent}- `{prop_name}` ({prop_type})")
                
                if prop_schema.get("value") is not None:
                    content.append(f"{indent}  Default: `{prop_schema['value']}`")
                
                if prop_schema.get("type") == "object" and "properties" in prop_schema:
                    self._render_schema_markdown(prop_schema, content, level + 1)


class PDFRenderer(BaseRenderer):
    """Renderer for PDF documentation."""
    
    def __init__(self):
        super().__init__()
        self.html_renderer = None
        
        if HTML and CSS:
            # PDF rendering is available
            pass
    
    def _safe_get(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safely get value from object that could be dict or have attributes."""
        if hasattr(obj, key):
            return getattr(obj, key, default)
        elif hasattr(obj, 'get'):
            return obj.get(key, default)
        elif isinstance(obj, dict):
            return obj.get(key, default)
        else:
            return default
    
    async def render_documentation(
        self, 
        documentation_data: Dict[str, Any],
        cross_references: Dict[str, Any],
        config: Any
    ) -> Dict[str, bytes]:
        """Render PDF documentation."""
        if not (HTML and CSS):
            raise RuntimeError("PDF rendering requires WeasyPrint (pip install weasyprint)")
        
        output_files = {}
        
        # Create a single comprehensive PDF
        pdf_content = await self._render_comprehensive_pdf(
            documentation_data, cross_references, config
        )
        output_files["documentation.pdf"] = pdf_content
        
        return output_files
    
    async def _render_comprehensive_pdf(
        self, 
        documentation_data: Dict[str, Any],
        cross_references: Dict[str, Any],
        config: Any
    ) -> bytes:
        """Render comprehensive PDF documentation."""
        # Generate HTML content for PDF
        html_content = await self._generate_pdf_html(
            documentation_data, cross_references, config
        )
        
        # Convert to PDF
        html_doc = HTML(string=html_content)
        css_styles = CSS(string=self._get_pdf_css())
        
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_styles])
        return pdf_bytes
    
    async def _generate_pdf_html(
        self, 
        documentation_data: Dict[str, Any],
        cross_references: Dict[str, Any],
        config: Any
    ) -> str:
        """Generate HTML content suitable for PDF conversion."""
        content = []
        
        # HTML document structure
        content.append("<!DOCTYPE html>")
        content.append("<html>")
        content.append("<head>")
        content.append(f"<title>{config.project_name} Documentation</title>")
        content.append('<meta charset="utf-8">')
        content.append("</head>")
        content.append("<body>")
        
        # Title page
        content.append(f"<h1>{config.project_name}</h1>")
        if config.project_description:
            content.append(f"<p>{config.project_description}</p>")
        if config.project_version:
            content.append(f"<p><strong>Version:</strong> {config.project_version}</p>")
        if config.author:
            content.append(f"<p><strong>Author:</strong> {config.author}</p>")
        
        content.append('<div style="page-break-after: always;"></div>')
        
        # Table of contents
        content.append("<h2>Table of Contents</h2>")
        content.append("<ul>")
        if documentation_data.get("api"):
            content.append("<li><a href=\"#api\">API Reference</a></li>")
        if documentation_data.get("code_documentation"):
            content.append("<li><a href=\"#code\">Code Documentation</a></li>")
        if documentation_data.get("extensions"):
            content.append("<li><a href=\"#extensions\">Extensions</a></li>")
        if documentation_data.get("configuration"):
            content.append("<li><a href=\"#configuration\">Configuration</a></li>")
        content.append("</ul>")
        
        content.append('<div style="page-break-after: always;"></div>')
        
        # Content sections
        if documentation_data.get("api"):
            content.extend(await self._generate_api_html_section(documentation_data["api"]))
        
        if documentation_data.get("code_documentation"):
            content.extend(await self._generate_code_html_section(documentation_data["code_documentation"]))
        
        if documentation_data.get("extensions"):
            content.extend(await self._generate_extensions_html_section(documentation_data["extensions"]))
        
        if documentation_data.get("configuration"):
            content.extend(await self._generate_config_html_section(documentation_data["configuration"]))
        
        content.append("</body>")
        content.append("</html>")
        
        return "\n".join(content)
    
    async def _generate_api_html_section(self, api_data: Dict[str, Any]) -> List[str]:
        """Generate HTML for API section."""
        content = []
        content.append('<h2 id="api">API Reference</h2>')
        
        endpoints = api_data.get("endpoints", {})
        for endpoint_key, endpoint in endpoints.items():
            content.append(f"<h3>{endpoint.method} {endpoint.path}</h3>")
            if endpoint.summary:
                content.append(f"<p>{endpoint.summary}</p>")
            if endpoint.description:
                content.append(f"<p>{endpoint.description}</p>")
            
            # Parameters table
            if endpoint.parameters:
                content.append("<h4>Parameters</h4>")
                content.append("<table>")
                content.append("<tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr>")
                for param in endpoint.parameters:
                    required = "Yes" if param.get("required") else "No"
                    content.append(f"<tr>")
                    content.append(f"<td>{param['name']}</td>")
                    content.append(f"<td>{param.get('type', 'string')}</td>")
                    content.append(f"<td>{required}</td>")
                    content.append(f"<td>{param.get('description', '')}</td>")
                    content.append(f"</tr>")
                content.append("</table>")
        
        return content
    
    async def _generate_code_html_section(self, code_data: Dict[str, Any]) -> List[str]:
        """Generate HTML for code documentation section."""
        content = []
        content.append('<h2 id="code">Code Documentation</h2>')
        
        for module_name, module_data in code_data.items():
            content.append(f"<h3>Module: {module_name}</h3>")
            docstring = self._safe_get(module_data, "docstring")
            if docstring:
                content.append(f"<p>{docstring}</p>")
            
            # Classes
            classes = self._safe_get(module_data, "classes", {})
            for class_name, class_data in classes.items():
                content.append(f"<h4>Class: {class_name}</h4>")
                if class_data.get("docstring"):
                    content.append(f"<p>{class_data['docstring']}</p>")
        
        return content
    
    async def _generate_extensions_html_section(self, extensions_data: Dict[str, Any]) -> List[str]:
        """Generate HTML for extensions section."""
        content = []
        content.append('<h2 id="extensions">Extensions</h2>')
        
        for ext_name, ext_data in extensions_data.items():
            content.append(f"<h3>{ext_name}</h3>")
            metadata = ext_data.get("metadata", {})
            if metadata.get("description"):
                content.append(f"<p>{metadata['description']}</p>")
        
        return content
    
    async def _generate_config_html_section(self, config_data: Dict[str, Any]) -> List[str]:
        """Generate HTML for configuration section."""
        content = []
        content.append('<h2 id="configuration">Configuration</h2>')
        
        for config_file, config_info in config_data.items():
            content.append(f"<h3>{config_file}</h3>")
            content.append(f"<p><strong>Format:</strong> {config_info.get('format', 'unknown')}</p>")
        
        return content
    
    def _get_pdf_css(self) -> str:
        """Get CSS styles for PDF generation."""
        return """
        body {
            font-family: Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            margin: 2cm;
        }
        
        h1 {
            font-size: 24pt;
            margin-bottom: 20pt;
            color: #333;
        }
        
        h2 {
            font-size: 18pt;
            margin-top: 20pt;
            margin-bottom: 10pt;
            color: #444;
            page-break-before: always;
        }
        
        h3 {
            font-size: 14pt;
            margin-top: 15pt;
            margin-bottom: 8pt;
            color: #555;
        }
        
        h4 {
            font-size: 12pt;
            margin-top: 10pt;
            margin-bottom: 5pt;
            color: #666;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10pt 0;
        }
        
        th, td {
            border: 1pt solid #ccc;
            padding: 5pt;
            text-align: left;
        }
        
        th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        code {
            font-family: 'Courier New', monospace;
            background-color: #f8f8f8;
            padding: 2pt;
            border-radius: 2pt;
        }
        
        pre {
            background-color: #f8f8f8;
            padding: 10pt;
            border-radius: 4pt;
            overflow-x: auto;
        }
        """