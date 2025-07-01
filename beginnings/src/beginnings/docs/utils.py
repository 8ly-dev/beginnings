"""Utility functions for documentation generation."""

from __future__ import annotations

import re
import os
import hashlib
import mimetypes
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone
import json


class DocumentationUtils:
    """Utility functions for documentation generation."""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe filesystem use.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\.+', '.', filename)
        filename = filename.strip('. ')
        
        # Ensure filename is not too long
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @staticmethod
    def generate_slug(text: str) -> str:
        """Generate URL-friendly slug from text.
        
        Args:
            text: Text to convert to slug
            
        Returns:
            URL-friendly slug
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    @staticmethod
    def extract_code_blocks(content: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown or documentation.
        
        Args:
            content: Content to extract code blocks from
            
        Returns:
            List of code blocks with language and content
        """
        code_blocks = []
        
        # Pattern for fenced code blocks
        pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            language = match.group(1) or 'text'
            code_content = match.group(2)
            
            code_blocks.append({
                'language': language,
                'content': code_content.strip(),
                'start_pos': match.start(),
                'end_pos': match.end()
            })
        
        return code_blocks
    
    @staticmethod
    def generate_table_of_contents(content: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Generate table of contents from content with headers.
        
        Args:
            content: Content with markdown headers
            max_depth: Maximum header depth to include
            
        Returns:
            List of TOC entries
        """
        toc_entries = []
        
        # Pattern for markdown headers
        pattern = r'^(#{1,' + str(max_depth) + r'})\s+(.+)$'
        
        for line_num, line in enumerate(content.split('\n'), 1):
            match = re.match(pattern, line.strip())
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                anchor = DocumentationUtils.generate_slug(title)
                
                toc_entries.append({
                    'level': level,
                    'title': title,
                    'anchor': anchor,
                    'line_number': line_num
                })
        
        return toc_entries
    
    @staticmethod
    def build_breadcrumb_path(current_path: str, base_path: str = "") -> List[Dict[str, str]]:
        """Build breadcrumb navigation path.
        
        Args:
            current_path: Current documentation path
            base_path: Base documentation path
            
        Returns:
            List of breadcrumb items
        """
        breadcrumbs = []
        
        # Remove base path if present
        if base_path:
            # Normalize paths for comparison
            normalized_base = base_path.strip('/')
            if current_path.startswith(normalized_base + '/') or current_path == normalized_base:
                current_path = current_path[len(normalized_base):].lstrip('/')
            elif current_path.startswith('/' + normalized_base + '/') or current_path == '/' + normalized_base:
                current_path = current_path[len('/' + normalized_base):].lstrip('/')
        
        # Split path into components
        path_components = [comp for comp in current_path.split('/') if comp]
        
        # Build breadcrumbs
        accumulated_path = base_path
        
        # Add home breadcrumb
        breadcrumbs.append({
            'title': 'Home',
            'url': base_path or '/',
            'is_current': len(path_components) == 0
        })
        
        # Add path component breadcrumbs
        for i, component in enumerate(path_components):
            accumulated_path = f"{accumulated_path}/{component}" if accumulated_path else component
            is_current = i == len(path_components) - 1
            
            # Clean up component name
            title = component.replace('_', ' ').replace('-', ' ')
            if title.endswith('.html'):
                title = title[:-5]
            title = title.title()
            
            breadcrumbs.append({
                'title': title,
                'url': accumulated_path,
                'is_current': is_current
            })
        
        return breadcrumbs
    
    @staticmethod
    def calculate_reading_time(content: str) -> int:
        """Calculate estimated reading time for content.
        
        Args:
            content: Text content
            
        Returns:
            Estimated reading time in minutes
        """
        # Remove code blocks and HTML tags for word count
        text = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Count words
        words = len(re.findall(r'\b\w+\b', text))
        
        # Average reading speed: 200-250 words per minute
        reading_speed = 225
        minutes = max(1, round(words / reading_speed))
        
        return minutes
    
    @staticmethod
    def extract_metadata_from_content(content: str) -> Dict[str, Any]:
        """Extract metadata from content (front matter, etc.).
        
        Args:
            content: Content with potential metadata
            
        Returns:
            Extracted metadata
        """
        metadata = {}
        
        # Check for YAML front matter
        if content.startswith('---'):
            try:
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    yaml_content = parts[1].strip()
                    
                    # Try to parse YAML
                    try:
                        import yaml
                        metadata = yaml.safe_load(yaml_content) or {}
                    except ImportError:
                        # Fallback: simple key-value parsing
                        for line in yaml_content.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                metadata[key.strip()] = value.strip()
            except Exception:
                pass
        
        # Extract title from first heading if not in metadata
        if 'title' not in metadata:
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                metadata['title'] = title_match.group(1).strip()
        
        # Extract description from first paragraph
        if 'description' not in metadata:
            # Remove front matter and find first paragraph
            content_without_fm = content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content_without_fm = parts[2]
            
            # Find first non-empty paragraph
            paragraphs = [p.strip() for p in content_without_fm.split('\n\n') if p.strip()]
            for para in paragraphs:
                if not para.startswith('#') and not para.startswith('```'):
                    # Clean up the paragraph
                    para = re.sub(r'[*_`]', '', para)  # Remove markdown formatting
                    para = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', para)  # Remove links
                    if len(para) > 20:  # Ensure it's substantial
                        metadata['description'] = para[:200] + ('...' if len(para) > 200 else '')
                        break
        
        return metadata
    
    @staticmethod
    def validate_links(content: str, base_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Validate links in content.
        
        Args:
            content: Content with links to validate
            base_path: Base path for relative links
            
        Returns:
            List of link validation results
        """
        link_results = []
        
        # Find markdown links
        markdown_links = re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for match in markdown_links:
            link_text = match.group(1)
            link_url = match.group(2)
            
            result = DocumentationUtils._validate_single_link(link_url, base_path)
            result.update({
                'text': link_text,
                'position': match.start(),
                'type': 'markdown'
            })
            link_results.append(result)
        
        # Find HTML links
        html_links = re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', content, re.IGNORECASE)
        for match in html_links:
            link_url = match.group(1)
            link_text = match.group(2)
            
            result = DocumentationUtils._validate_single_link(link_url, base_path)
            result.update({
                'text': link_text,
                'position': match.start(),
                'type': 'html'
            })
            link_results.append(result)
        
        return link_results
    
    @staticmethod
    def _validate_single_link(url: str, base_path: Optional[str] = None) -> Dict[str, Any]:
        """Validate a single link.
        
        Args:
            url: URL to validate
            base_path: Base path for relative links
            
        Returns:
            Validation result
        """
        result = {
            'url': url,
            'is_valid': False,
            'is_external': False,
            'error': None
        }
        
        try:
            parsed = urlparse(url)
            
            # Check if it's an external link
            if parsed.scheme in ['http', 'https']:
                result['is_external'] = True
                result['is_valid'] = True  # Assume external links are valid for now
            
            # Check if it's an anchor link
            elif url.startswith('#'):
                result['is_valid'] = True  # Can't easily validate anchors without full content
            
            # Check if it's a relative link
            elif not parsed.scheme:
                if base_path:
                    full_path = Path(base_path) / url
                    result['is_valid'] = full_path.exists()
                    if not result['is_valid']:
                        result['error'] = 'File not found'
                else:
                    result['error'] = 'No base path provided for relative link'
            
            else:
                result['error'] = f'Unsupported URL scheme: {parsed.scheme}'
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def generate_search_index(documentation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate search index from documentation data.
        
        Args:
            documentation_data: Documentation data to index
            
        Returns:
            Search index entries
        """
        search_entries = []
        
        # Index API endpoints
        api_data = documentation_data.get('api', {})
        for endpoint_key, endpoint in api_data.get('endpoints', {}).items():
            search_entries.append({
                'id': f"api_{endpoint_key}",
                'title': f"{endpoint.method} {endpoint.path}",
                'content': f"{endpoint.summary or ''} {endpoint.description or ''}",
                'type': 'api_endpoint',
                'url': f"api/endpoints/{endpoint_key}.html",
                'tags': endpoint.tags or []
            })
        
        # Index code documentation
        code_docs = documentation_data.get('code_documentation', {})
        for module_name, module_data in code_docs.items():
            # Get docstring - handle both dict and dataclass patterns
            if hasattr(module_data, 'docstring'):
                module_docstring = module_data.docstring or ''
            else:
                module_docstring = module_data.get('docstring', '')
            
            # Index module
            search_entries.append({
                'id': f"module_{module_name}",
                'title': f"Module: {module_name}",
                'content': module_docstring,
                'type': 'module',
                'url': f"code/modules/{module_name}.html",
                'tags': ['module']
            })
            
            # Index classes - handle both dict and dataclass patterns
            classes = module_data.classes if hasattr(module_data, 'classes') else module_data.get('classes', {})
            for class_name, class_data in classes.items():
                class_docstring = ''
                if hasattr(class_data, 'docstring'):
                    class_docstring = class_data.docstring or ''
                elif hasattr(class_data, 'get'):
                    class_docstring = class_data.get('docstring', '')
                
                search_entries.append({
                    'id': f"class_{module_name}_{class_name}",
                    'title': f"Class: {module_name}.{class_name}",
                    'content': class_docstring,
                    'type': 'class',
                    'url': f"code/classes/{module_name}.{class_name}.html",
                    'tags': ['class', module_name]
                })
            
            # Index functions - handle both dict and dataclass patterns
            functions = module_data.functions if hasattr(module_data, 'functions') else module_data.get('functions', {})
            for func_name, func_data in functions.items():
                func_docstring = ''
                if hasattr(func_data, 'docstring'):
                    func_docstring = func_data.docstring or ''
                elif hasattr(func_data, 'get'):
                    func_docstring = func_data.get('docstring', '')
                
                search_entries.append({
                    'id': f"function_{module_name}_{func_name}",
                    'title': f"Function: {module_name}.{func_name}",
                    'content': func_docstring,
                    'type': 'function',
                    'url': f"code/modules/{module_name}.html#{func_name}",
                    'tags': ['function', module_name]
                })
        
        # Index extensions
        extensions_data = documentation_data.get('extensions', {})
        for ext_name, ext_data in extensions_data.items():
            metadata = ext_data.get('metadata', {})
            search_entries.append({
                'id': f"extension_{ext_name}",
                'title': f"Extension: {ext_name}",
                'content': metadata.get('description', ''),
                'type': 'extension',
                'url': f"extensions/{ext_name}.html",
                'tags': ['extension']
            })
        
        return search_entries
    
    @staticmethod
    def optimize_images_for_docs(image_path: str, output_dir: str, max_width: int = 800) -> str:
        """Optimize images for documentation.
        
        Args:
            image_path: Path to source image
            output_dir: Output directory for optimized image
            max_width: Maximum width for optimized image
            
        Returns:
            Path to optimized image
        """
        try:
            from PIL import Image
            
            input_path = Path(image_path)
            output_path = Path(output_dir) / input_path.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with Image.open(input_path) as img:
                # Calculate new dimensions
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = rgb_img
                
                # Save optimized image
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                
            return str(output_path)
            
        except ImportError:
            # PIL not available, just copy the file
            import shutil
            output_path = Path(output_dir) / Path(image_path).name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, output_path)
            return str(output_path)
        
        except Exception:
            # Return original path if optimization fails
            return image_path
    
    @staticmethod
    def generate_sitemap(documentation_data: Dict[str, Any], base_url: str) -> str:
        """Generate XML sitemap for documentation.
        
        Args:
            documentation_data: Documentation data
            base_url: Base URL for the documentation site
            
        Returns:
            XML sitemap content
        """
        urls = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Add main pages
        urls.append({
            'loc': base_url,
            'lastmod': now,
            'priority': '1.0'
        })
        
        # Add API endpoints
        api_data = documentation_data.get('api', {})
        for endpoint_key in api_data.get('endpoints', {}):
            urls.append({
                'loc': f"{base_url}/api/endpoints/{endpoint_key}.html",
                'lastmod': now,
                'priority': '0.8'
            })
        
        # Add code documentation
        code_docs = documentation_data.get('code_documentation', {})
        for module_name in code_docs:
            urls.append({
                'loc': f"{base_url}/code/modules/{module_name}.html",
                'lastmod': now,
                'priority': '0.7'
            })
        
        # Add extensions
        extensions_data = documentation_data.get('extensions', {})
        for ext_name in extensions_data:
            urls.append({
                'loc': f"{base_url}/extensions/{ext_name}.html",
                'lastmod': now,
                'priority': '0.6'
            })
        
        # Generate XML
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        
        for url_info in urls:
            xml_lines.extend([
                '  <url>',
                f'    <loc>{url_info["loc"]}</loc>',
                f'    <lastmod>{url_info["lastmod"]}</lastmod>',
                f'    <priority>{url_info["priority"]}</priority>',
                '  </url>'
            ])
        
        xml_lines.append('</urlset>')
        
        return '\n'.join(xml_lines)
    
    @staticmethod
    def create_documentation_manifest(documentation_data: Dict[str, Any], output_dir: str) -> str:
        """Create documentation manifest file.
        
        Args:
            documentation_data: Documentation data
            output_dir: Output directory
            
        Returns:
            Path to manifest file
        """
        manifest = {
            'name': documentation_data.get('metadata', {}).get('project_name', 'Documentation'),
            'version': documentation_data.get('metadata', {}).get('project_version', '1.0.0'),
            'generated_at': documentation_data.get('metadata', {}).get('generated_at'),
            'sections': {},
            'files': [],
            'statistics': {}
        }
        
        # Add section information
        if documentation_data.get('api'):
            manifest['sections']['api'] = {
                'title': 'API Reference',
                'endpoint_count': len(documentation_data['api'].get('endpoints', {}))
            }
        
        if documentation_data.get('code_documentation'):
            code_docs = documentation_data['code_documentation']
            
            # Calculate class and function counts, handling both dict and dataclass patterns
            class_count = 0
            function_count = 0
            
            for mod in code_docs.values():
                # Handle both dictionary and dataclass patterns
                if hasattr(mod, 'classes'):
                    class_count += len(mod.classes)
                elif hasattr(mod, 'get'):
                    class_count += len(mod.get('classes', {}))
                
                if hasattr(mod, 'functions'):
                    function_count += len(mod.functions)
                elif hasattr(mod, 'get'):
                    function_count += len(mod.get('functions', {}))
            
            manifest['sections']['code'] = {
                'title': 'Code Documentation',
                'module_count': len(code_docs),
                'class_count': class_count,
                'function_count': function_count
            }
        
        if documentation_data.get('extensions'):
            manifest['sections']['extensions'] = {
                'title': 'Extensions',
                'extension_count': len(documentation_data['extensions'])
            }
        
        # Save manifest
        manifest_path = Path(output_dir) / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        
        return str(manifest_path)
    
    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """Calculate hash of content for change detection.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 hash of content
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Get file information for documentation.
        
        Args:
            file_path: Path to file
            
        Returns:
            File information
        """
        path = Path(file_path)
        
        if not path.exists():
            return {'exists': False}
        
        stat = path.stat()
        
        return {
            'exists': True,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'extension': path.suffix,
            'mime_type': mimetypes.guess_type(str(path))[0],
            'is_binary': DocumentationUtils._is_binary_file(path)
        }
    
    @staticmethod
    def _is_binary_file(file_path: Path) -> bool:
        """Check if file is binary.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is binary
        """
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return True