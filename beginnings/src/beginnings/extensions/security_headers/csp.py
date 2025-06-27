"""
Content Security Policy (CSP) management for security headers extension.

This module provides CSP directive generation, nonce generation,
and template integration capabilities.
"""

import base64
import secrets
from typing import Any


class CSPManager:
    """
    Content Security Policy manager.
    
    Handles CSP directive generation, nonce generation for inline content,
    and CSP header building with route-specific customization.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize CSP manager.
        
        Args:
            config: CSP configuration dictionary
        """
        self.enabled = config.get("enabled", True)
        self.report_only = config.get("report_only", False)
        self.directives = config.get("directives", {})
        self.report_uri = config.get("report_uri")
        self.report_to = config.get("report_to")
        
        # Nonce configuration
        nonce_config = config.get("nonce", {})
        self.nonce_enabled = nonce_config.get("enabled", False)
        self.script_nonce = nonce_config.get("script_nonce", True)
        self.style_nonce = nonce_config.get("style_nonce", True)
        self.nonce_length = nonce_config.get("nonce_length", 16)
        
        # Valid CSP directives for validation
        self.valid_directives = {
            "default_src", "script_src", "style_src", "img_src", "font_src",
            "connect_src", "media_src", "object_src", "child_src", "frame_src",
            "worker_src", "manifest_src", "base_uri", "form_action", "frame_ancestors",
            "plugin_types", "sandbox", "upgrade_insecure_requests", "block_all_mixed_content"
        }
    
    def generate_nonce(self) -> str:
        """
        Generate a cryptographically secure nonce for CSP.
        
        Returns:
            Base64-encoded nonce string
        """
        nonce_bytes = secrets.token_bytes(self.nonce_length)
        return base64.urlsafe_b64encode(nonce_bytes).decode('ascii').rstrip('=')
    
    def build_csp_header(
        self,
        script_nonce: str | None = None,
        style_nonce: str | None = None,
        route_directives: dict[str, list[str]] | None = None
    ) -> str:
        """
        Build CSP header value from directives and nonces.
        
        Args:
            script_nonce: Nonce for script-src directive
            style_nonce: Nonce for style-src directive
            route_directives: Route-specific directive overrides
            
        Returns:
            CSP header value string
        """
        if not self.enabled:
            return ""
        
        # Start with base directives
        directives = self.directives.copy()
        
        # Apply route-specific overrides
        if route_directives:
            directives.update(route_directives)
        
        # Add nonces to script-src and style-src if enabled
        if self.nonce_enabled:
            if script_nonce and self.script_nonce and "script_src" in directives:
                directives["script_src"] = directives["script_src"] + [f"'nonce-{script_nonce}'"]
            
            if style_nonce and self.style_nonce and "style_src" in directives:
                directives["style_src"] = directives["style_src"] + [f"'nonce-{style_nonce}'"]
        
        # Build CSP header
        csp_parts = []
        
        for directive, sources in directives.items():
            # Convert underscore to hyphen for CSP directive names
            directive_name = directive.replace("_", "-")
            sources_str = " ".join(sources)
            csp_parts.append(f"{directive_name} {sources_str}")
        
        # Add report-uri if configured
        if self.report_uri:
            csp_parts.append(f"report-uri {self.report_uri}")
        
        # Add report-to if configured
        if self.report_to:
            csp_parts.append(f"report-to {self.report_to}")
        
        return "; ".join(csp_parts)
    
    def build_csp_header_with_name(
        self,
        script_nonce: str | None = None,
        style_nonce: str | None = None,
        route_directives: dict[str, list[str]] | None = None
    ) -> tuple[str, str]:
        """
        Build CSP header with appropriate header name.
        
        Args:
            script_nonce: Nonce for script-src directive
            style_nonce: Nonce for style-src directive
            route_directives: Route-specific directive overrides
            
        Returns:
            Tuple of (header_name, header_value)
        """
        header_value = self.build_csp_header(script_nonce, style_nonce, route_directives)
        
        if self.report_only:
            header_name = "Content-Security-Policy-Report-Only"
        else:
            header_name = "Content-Security-Policy"
        
        return header_name, header_value
    
    def validate_config(self) -> list[str]:
        """
        Validate CSP configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.enabled:
            return errors
        
        # Validate directive names
        for directive in self.directives:
            if directive not in self.valid_directives:
                errors.append(f"Invalid CSP directive: {directive}")
        
        # Validate nonce configuration
        if self.nonce_enabled:
            if self.nonce_length < 8:
                errors.append("CSP nonce length must be at least 8 bytes")
            elif self.nonce_length > 64:
                errors.append("CSP nonce length should not exceed 64 bytes")
        
        # Validate directive values
        for directive, sources in self.directives.items():
            if not isinstance(sources, list):
                errors.append(f"CSP directive '{directive}' must be a list of sources")
                continue
            
            for source in sources:
                if not isinstance(source, str):
                    errors.append(f"CSP directive '{directive}' source must be a string: {source}")
        
        return errors