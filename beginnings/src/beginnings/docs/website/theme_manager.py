"""Theme management for documentation website.

This module provides theme support with customization, dark mode,
and responsive design. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum


class ThemeType(Enum):
    """Types of themes available."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


@dataclass
class ColorScheme:
    """Color scheme configuration."""
    
    primary: str = "#2563eb"
    secondary: str = "#64748b"
    accent: str = "#0ea5e9"
    background: str = "#ffffff"
    surface: str = "#f8fafc"
    text_primary: str = "#1e293b"
    text_secondary: str = "#64748b"
    border: str = "#e2e8f0"
    success: str = "#059669"
    warning: str = "#d97706"
    error: str = "#dc2626"
    info: str = "#0ea5e9"


@dataclass
class Typography:
    """Typography configuration."""
    
    font_family_sans: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    font_family_mono: str = "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace"
    font_size_base: str = "16px"
    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_semibold: int = 600
    font_weight_bold: int = 700
    line_height_base: float = 1.5
    line_height_tight: float = 1.25
    line_height_loose: float = 1.75


@dataclass
class Spacing:
    """Spacing and layout configuration."""
    
    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"
    xxl: str = "3rem"
    container_max_width: str = "1200px"
    sidebar_width: str = "280px"
    content_padding: str = "2rem"


@dataclass
class ThemeConfig:
    """Complete theme configuration."""
    
    name: str
    display_name: str
    description: str = ""
    type: ThemeType = ThemeType.LIGHT
    colors: ColorScheme = field(default_factory=ColorScheme)
    typography: Typography = field(default_factory=Typography)
    spacing: Spacing = field(default_factory=Spacing)
    custom_css: str = ""
    template_overrides: Dict[str, str] = field(default_factory=dict)
    assets: List[str] = field(default_factory=list)
    responsive_breakpoints: Dict[str, str] = field(default_factory=lambda: {
        "sm": "640px",
        "md": "768px",
        "lg": "1024px",
        "xl": "1280px"
    })


@dataclass
class ThemeApplicationResult:
    """Result of theme application."""
    
    success: bool
    theme_name: str = ""
    css_files_generated: int = 0
    template_files_copied: int = 0
    assets_copied: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CSSGenerator:
    """Generates CSS from theme configuration.
    
    Follows Single Responsibility Principle - only handles CSS generation.
    """
    
    def __init__(self, theme_config: ThemeConfig):
        """Initialize CSS generator.
        
        Args:
            theme_config: Theme configuration
        """
        self.config = theme_config
    
    def generate_css(self) -> str:
        """Generate complete CSS from theme configuration.
        
        Returns:
            Generated CSS content
        """
        css_parts = [
            self._generate_css_variables(),
            self._generate_base_styles(),
            self._generate_layout_styles(),
            self._generate_component_styles(),
            self._generate_utility_classes(),
            self._generate_responsive_styles(),
            self.config.custom_css
        ]
        
        return "\n\n".join(filter(None, css_parts))
    
    def _generate_css_variables(self) -> str:
        """Generate CSS custom properties."""
        colors = self.config.colors
        typography = self.config.typography
        spacing = self.config.spacing
        
        return f"""
/* CSS Custom Properties - {self.config.display_name} Theme */
:root {{
    /* Colors */
    --color-primary: {colors.primary};
    --color-secondary: {colors.secondary};
    --color-accent: {colors.accent};
    --color-background: {colors.background};
    --color-surface: {colors.surface};
    --color-text-primary: {colors.text_primary};
    --color-text-secondary: {colors.text_secondary};
    --color-border: {colors.border};
    --color-success: {colors.success};
    --color-warning: {colors.warning};
    --color-error: {colors.error};
    --color-info: {colors.info};
    
    /* Typography */
    --font-family-sans: {typography.font_family_sans};
    --font-family-mono: {typography.font_family_mono};
    --font-size-base: {typography.font_size_base};
    --font-weight-normal: {typography.font_weight_normal};
    --font-weight-medium: {typography.font_weight_medium};
    --font-weight-semibold: {typography.font_weight_semibold};
    --font-weight-bold: {typography.font_weight_bold};
    --line-height-base: {typography.line_height_base};
    --line-height-tight: {typography.line_height_tight};
    --line-height-loose: {typography.line_height_loose};
    
    /* Spacing */
    --spacing-xs: {spacing.xs};
    --spacing-sm: {spacing.sm};
    --spacing-md: {spacing.md};
    --spacing-lg: {spacing.lg};
    --spacing-xl: {spacing.xl};
    --spacing-xxl: {spacing.xxl};
    --container-max-width: {spacing.container_max_width};
    --sidebar-width: {spacing.sidebar_width};
    --content-padding: {spacing.content_padding};
    
    /* Derived colors */
    --color-primary-light: color-mix(in srgb, var(--color-primary) 20%, white);
    --color-primary-dark: color-mix(in srgb, var(--color-primary) 80%, black);
    --color-surface-hover: color-mix(in srgb, var(--color-surface) 95%, var(--color-primary));
}}
        """
    
    def _generate_base_styles(self) -> str:
        """Generate base HTML element styles."""
        return """
/* Base Styles */
*, *::before, *::after {
    box-sizing: border-box;
}

html {
    font-size: var(--font-size-base);
    line-height: var(--line-height-base);
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family: var(--font-family-sans);
    color: var(--color-text-primary);
    background-color: var(--color-background);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4, h5, h6 {
    margin: 0 0 var(--spacing-md) 0;
    font-weight: var(--font-weight-semibold);
    line-height: var(--line-height-tight);
    color: var(--color-text-primary);
}

h1 { font-size: 2.25rem; }
h2 { font-size: 1.875rem; }
h3 { font-size: 1.5rem; }
h4 { font-size: 1.25rem; }
h5 { font-size: 1.125rem; }
h6 { font-size: 1rem; }

p {
    margin: 0 0 var(--spacing-md) 0;
    line-height: var(--line-height-base);
}

a {
    color: var(--color-primary);
    text-decoration: none;
    transition: color 0.2s ease;
}

a:hover {
    color: var(--color-primary-dark);
    text-decoration: underline;
}

code, pre {
    font-family: var(--font-family-mono);
    font-size: 0.875rem;
}

code {
    background: var(--color-surface);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    border: 1px solid var(--color-border);
}

pre {
    background: var(--color-surface);
    padding: var(--spacing-md);
    border-radius: 0.5rem;
    border: 1px solid var(--color-border);
    overflow-x: auto;
    margin: 0 0 var(--spacing-md) 0;
}

pre code {
    background: none;
    padding: 0;
    border: none;
    border-radius: 0;
}

blockquote {
    margin: 0 0 var(--spacing-md) 0;
    padding: var(--spacing-md);
    border-left: 4px solid var(--color-primary);
    background: var(--color-surface);
    font-style: italic;
}

img {
    max-width: 100%;
    height: auto;
    border-radius: 0.5rem;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 var(--spacing-md) 0;
}

th, td {
    padding: var(--spacing-sm) var(--spacing-md);
    text-align: left;
    border-bottom: 1px solid var(--color-border);
}

th {
    background: var(--color-surface);
    font-weight: var(--font-weight-semibold);
}
        """
    
    def _generate_layout_styles(self) -> str:
        """Generate layout and structural styles."""
        return """
/* Layout Styles */
.site-container {
    display: flex;
    min-height: 100vh;
    max-width: var(--container-max-width);
    margin: 0 auto;
}

.site-sidebar {
    width: var(--sidebar-width);
    background: var(--color-surface);
    border-right: 1px solid var(--color-border);
    padding: var(--spacing-lg);
    overflow-y: auto;
    position: sticky;
    top: 0;
    height: 100vh;
}

.site-main {
    flex: 1;
    padding: var(--content-padding);
    overflow-x: hidden;
}

.site-header {
    background: var(--color-background);
    border-bottom: 1px solid var(--color-border);
    padding: var(--spacing-md) 0;
    margin-bottom: var(--spacing-lg);
    position: sticky;
    top: 0;
    z-index: 100;
}

.site-footer {
    background: var(--color-surface);
    border-top: 1px solid var(--color-border);
    padding: var(--spacing-lg) 0;
    margin-top: var(--spacing-xxl);
    text-align: center;
    color: var(--color-text-secondary);
}

.content-area {
    max-width: 65ch;
    margin: 0 auto;
}

.navigation {
    margin-bottom: var(--spacing-lg);
}

.nav-section {
    margin-bottom: var(--spacing-lg);
}

.nav-section-title {
    font-size: 0.875rem;
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--spacing-sm);
}

.nav-link {
    display: block;
    padding: var(--spacing-sm) 0;
    color: var(--color-text-secondary);
    transition: color 0.2s ease;
    border-left: 2px solid transparent;
    padding-left: var(--spacing-sm);
}

.nav-link:hover {
    color: var(--color-primary);
    text-decoration: none;
}

.nav-link.active {
    color: var(--color-primary);
    border-left-color: var(--color-primary);
    font-weight: var(--font-weight-medium);
}

.breadcrumb {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-lg);
    font-size: 0.875rem;
    color: var(--color-text-secondary);
}

.breadcrumb-separator {
    color: var(--color-border);
}
        """
    
    def _generate_component_styles(self) -> str:
        """Generate component-specific styles."""
        return """
/* Component Styles */
.btn {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 0.875rem;
    font-weight: var(--font-weight-medium);
    text-decoration: none;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    background: var(--color-background);
    color: var(--color-text-primary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn:hover {
    background: var(--color-surface-hover);
    border-color: var(--color-primary);
    text-decoration: none;
}

.btn-primary {
    background: var(--color-primary);
    color: white;
    border-color: var(--color-primary);
}

.btn-primary:hover {
    background: var(--color-primary-dark);
    border-color: var(--color-primary-dark);
    color: white;
}

.card {
    background: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
}

.card-header {
    margin-bottom: var(--spacing-md);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--color-border);
}

.card-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: var(--font-weight-semibold);
}

.alert {
    padding: var(--spacing-md);
    border-radius: 0.375rem;
    border: 1px solid;
    margin-bottom: var(--spacing-md);
}

.alert-info {
    background: color-mix(in srgb, var(--color-info) 10%, white);
    border-color: var(--color-info);
    color: var(--color-info);
}

.alert-success {
    background: color-mix(in srgb, var(--color-success) 10%, white);
    border-color: var(--color-success);
    color: var(--color-success);
}

.alert-warning {
    background: color-mix(in srgb, var(--color-warning) 10%, white);
    border-color: var(--color-warning);
    color: var(--color-warning);
}

.alert-error {
    background: color-mix(in srgb, var(--color-error) 10%, white);
    border-color: var(--color-error);
    color: var(--color-error);
}

.code-block {
    position: relative;
}

.code-block-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-bottom: none;
    border-radius: 0.5rem 0.5rem 0 0;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 0.75rem;
    color: var(--color-text-secondary);
}

.code-block pre {
    margin: 0;
    border-radius: 0 0 0.5rem 0.5rem;
}

.copy-btn {
    background: none;
    border: none;
    color: var(--color-text-secondary);
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
}

.copy-btn:hover {
    background: var(--color-surface-hover);
    color: var(--color-primary);
}

.search-box {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    background: var(--color-background);
    font-size: 0.875rem;
    margin-bottom: var(--spacing-md);
}

.search-box:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.toc {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
}

.toc-title {
    font-size: 0.875rem;
    font-weight: var(--font-weight-semibold);
    margin-bottom: var(--spacing-sm);
    color: var(--color-text-secondary);
}

.toc-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.toc-item {
    margin-bottom: 0.25rem;
}

.toc-link {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    padding: 0.125rem 0;
    display: block;
}

.toc-link:hover {
    color: var(--color-primary);
}
        """
    
    def _generate_utility_classes(self) -> str:
        """Generate utility CSS classes."""
        return """
/* Utility Classes */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

.text-center { text-align: center; }
.text-right { text-align: right; }
.text-left { text-align: left; }

.text-primary { color: var(--color-primary); }
.text-secondary { color: var(--color-text-secondary); }
.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-error { color: var(--color-error); }

.bg-primary { background-color: var(--color-primary); }
.bg-surface { background-color: var(--color-surface); }
.bg-success { background-color: var(--color-success); }
.bg-warning { background-color: var(--color-warning); }
.bg-error { background-color: var(--color-error); }

.border { border: 1px solid var(--color-border); }
.border-primary { border-color: var(--color-primary); }
.border-success { border-color: var(--color-success); }
.border-warning { border-color: var(--color-warning); }
.border-error { border-color: var(--color-error); }

.rounded { border-radius: 0.375rem; }
.rounded-lg { border-radius: 0.5rem; }
.rounded-full { border-radius: 9999px; }

.shadow { box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); }
.shadow-md { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }
.shadow-lg { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }

.hidden { display: none; }
.block { display: block; }
.inline { display: inline; }
.inline-block { display: inline-block; }
.flex { display: flex; }
.inline-flex { display: inline-flex; }
.grid { display: grid; }

.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.items-end { align-items: flex-end; }

.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.justify-start { justify-content: flex-start; }
.justify-end { justify-content: flex-end; }

.gap-xs { gap: var(--spacing-xs); }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }
.gap-lg { gap: var(--spacing-lg); }
.gap-xl { gap: var(--spacing-xl); }

.p-xs { padding: var(--spacing-xs); }
.p-sm { padding: var(--spacing-sm); }
.p-md { padding: var(--spacing-md); }
.p-lg { padding: var(--spacing-lg); }
.p-xl { padding: var(--spacing-xl); }

.m-xs { margin: var(--spacing-xs); }
.m-sm { margin: var(--spacing-sm); }
.m-md { margin: var(--spacing-md); }
.m-lg { margin: var(--spacing-lg); }
.m-xl { margin: var(--spacing-xl); }

.mb-xs { margin-bottom: var(--spacing-xs); }
.mb-sm { margin-bottom: var(--spacing-sm); }
.mb-md { margin-bottom: var(--spacing-md); }
.mb-lg { margin-bottom: var(--spacing-lg); }
.mb-xl { margin-bottom: var(--spacing-xl); }

.mt-xs { margin-top: var(--spacing-xs); }
.mt-sm { margin-top: var(--spacing-sm); }
.mt-md { margin-top: var(--spacing-md); }
.mt-lg { margin-top: var(--spacing-lg); }
.mt-xl { margin-top: var(--spacing-xl); }
        """
    
    def _generate_responsive_styles(self) -> str:
        """Generate responsive design styles."""
        breakpoints = self.config.responsive_breakpoints
        
        return f"""
/* Responsive Styles */
@media (max-width: {breakpoints['md']}) {{
    .site-container {{
        flex-direction: column;
    }}
    
    .site-sidebar {{
        width: 100%;
        height: auto;
        position: static;
        border-right: none;
        border-bottom: 1px solid var(--color-border);
    }}
    
    .site-main {{
        padding: var(--spacing-md);
    }}
    
    .content-area {{
        max-width: none;
    }}
    
    h1 {{ font-size: 1.875rem; }}
    h2 {{ font-size: 1.5rem; }}
    h3 {{ font-size: 1.25rem; }}
    
    .hidden-mobile {{ display: none; }}
    .block-mobile {{ display: block; }}
}}

@media (max-width: {breakpoints['sm']}) {{
    .site-main {{
        padding: var(--spacing-sm);
    }}
    
    .card {{
        padding: var(--spacing-md);
    }}
    
    .btn {{
        padding: var(--spacing-xs) var(--spacing-sm);
        font-size: 0.75rem;
    }}
    
    pre {{
        padding: var(--spacing-sm);
        font-size: 0.75rem;
    }}
}}

@media (min-width: {breakpoints['lg']}) {{
    .content-area {{
        max-width: 75ch;
    }}
    
    .hidden-desktop {{ display: none; }}
    .block-desktop {{ display: block; }}
}}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }}
}}

@media (prefers-color-scheme: dark) {{
    [data-theme="auto"] {{
        --color-background: #0f172a;
        --color-surface: #1e293b;
        --color-text-primary: #f1f5f9;
        --color-text-secondary: #94a3b8;
        --color-border: #334155;
    }}
}}
        """


class ThemeManager:
    """Manages themes for documentation website.
    
    Follows Single Responsibility Principle - orchestrates theme management.
    Uses Dependency Inversion - depends on CSS generator abstraction.
    """
    
    def __init__(self, themes_directory: Optional[Path] = None):
        """Initialize theme manager.
        
        Args:
            themes_directory: Directory containing theme files
        """
        self.themes_directory = themes_directory
        self.available_themes = {}
        self.current_theme = None
        
        # Load built-in themes
        self._load_builtin_themes()
        
        # Load custom themes if directory provided
        if themes_directory and themes_directory.exists():
            self._load_custom_themes()
    
    def _load_builtin_themes(self) -> None:
        """Load built-in theme configurations."""
        # Light theme
        light_theme = ThemeConfig(
            name="light",
            display_name="Light",
            description="Clean light theme with modern styling",
            type=ThemeType.LIGHT
        )
        
        # Dark theme
        dark_colors = ColorScheme(
            primary="#3b82f6",
            secondary="#64748b", 
            accent="#06b6d4",
            background="#0f172a",
            surface="#1e293b",
            text_primary="#f1f5f9",
            text_secondary="#94a3b8",
            border="#334155",
            success="#10b981",
            warning="#f59e0b",
            error="#ef4444",
            info="#06b6d4"
        )
        
        dark_theme = ThemeConfig(
            name="dark",
            display_name="Dark",
            description="Elegant dark theme for reduced eye strain",
            type=ThemeType.DARK,
            colors=dark_colors
        )
        
        # Auto theme (system preference)
        auto_theme = ThemeConfig(
            name="auto",
            display_name="Auto",
            description="Automatically switches between light and dark based on system preference",
            type=ThemeType.AUTO
        )
        
        self.available_themes = {
            "light": light_theme,
            "dark": dark_theme,
            "auto": auto_theme
        }
        
        # Set default theme
        self.current_theme = light_theme
    
    def _load_custom_themes(self) -> None:
        """Load custom themes from themes directory."""
        if not self.themes_directory:
            return
        
        for theme_file in self.themes_directory.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                
                theme_config = self._parse_theme_data(theme_data)
                if theme_config:
                    self.available_themes[theme_config.name] = theme_config
            except Exception:
                # Skip invalid theme files
                continue
    
    def _parse_theme_data(self, theme_data: Dict[str, Any]) -> Optional[ThemeConfig]:
        """Parse theme data from JSON."""
        try:
            colors_data = theme_data.get('colors', {})
            colors = ColorScheme(
                primary=colors_data.get('primary', '#2563eb'),
                secondary=colors_data.get('secondary', '#64748b'),
                accent=colors_data.get('accent', '#0ea5e9'),
                background=colors_data.get('background', '#ffffff'),
                surface=colors_data.get('surface', '#f8fafc'),
                text_primary=colors_data.get('text_primary', '#1e293b'),
                text_secondary=colors_data.get('text_secondary', '#64748b'),
                border=colors_data.get('border', '#e2e8f0'),
                success=colors_data.get('success', '#059669'),
                warning=colors_data.get('warning', '#d97706'),
                error=colors_data.get('error', '#dc2626'),
                info=colors_data.get('info', '#0ea5e9')
            )
            
            typography_data = theme_data.get('typography', {})
            typography = Typography(
                font_family_sans=typography_data.get('font_family_sans', Typography().font_family_sans),
                font_family_mono=typography_data.get('font_family_mono', Typography().font_family_mono),
                font_size_base=typography_data.get('font_size_base', '16px'),
                font_weight_normal=typography_data.get('font_weight_normal', 400),
                font_weight_medium=typography_data.get('font_weight_medium', 500),
                font_weight_semibold=typography_data.get('font_weight_semibold', 600),
                font_weight_bold=typography_data.get('font_weight_bold', 700),
                line_height_base=typography_data.get('line_height_base', 1.5),
                line_height_tight=typography_data.get('line_height_tight', 1.25),
                line_height_loose=typography_data.get('line_height_loose', 1.75)
            )
            
            spacing_data = theme_data.get('spacing', {})
            spacing = Spacing(
                xs=spacing_data.get('xs', '0.25rem'),
                sm=spacing_data.get('sm', '0.5rem'),
                md=spacing_data.get('md', '1rem'),
                lg=spacing_data.get('lg', '1.5rem'),
                xl=spacing_data.get('xl', '2rem'),
                xxl=spacing_data.get('xxl', '3rem'),
                container_max_width=spacing_data.get('container_max_width', '1200px'),
                sidebar_width=spacing_data.get('sidebar_width', '280px'),
                content_padding=spacing_data.get('content_padding', '2rem')
            )
            
            return ThemeConfig(
                name=theme_data['name'],
                display_name=theme_data.get('display_name', theme_data['name'].title()),
                description=theme_data.get('description', ''),
                type=ThemeType(theme_data.get('type', 'light')),
                colors=colors,
                typography=typography,
                spacing=spacing,
                custom_css=theme_data.get('custom_css', ''),
                template_overrides=theme_data.get('template_overrides', {}),
                assets=theme_data.get('assets', []),
                responsive_breakpoints=theme_data.get('responsive_breakpoints', {
                    "sm": "640px", "md": "768px", "lg": "1024px", "xl": "1280px"
                })
            )
        except Exception:
            return None
    
    def get_available_themes(self) -> List[ThemeConfig]:
        """Get list of available themes.
        
        Returns:
            List of available theme configurations
        """
        return list(self.available_themes.values())
    
    def get_theme(self, theme_name: str) -> Optional[ThemeConfig]:
        """Get theme configuration by name.
        
        Args:
            theme_name: Name of the theme
            
        Returns:
            Theme configuration or None if not found
        """
        return self.available_themes.get(theme_name)
    
    def set_current_theme(self, theme_name: str) -> bool:
        """Set the current active theme.
        
        Args:
            theme_name: Name of the theme to activate
            
        Returns:
            True if theme was set successfully
        """
        theme = self.get_theme(theme_name)
        if theme:
            self.current_theme = theme
            return True
        return False
    
    def apply_theme(self, theme_name: str, output_dir: Path) -> ThemeApplicationResult:
        """Apply theme to output directory.
        
        Args:
            theme_name: Name of theme to apply
            output_dir: Directory to apply theme to
            
        Returns:
            Application result with statistics
        """
        result = ThemeApplicationResult(success=True, theme_name=theme_name)
        
        try:
            theme = self.get_theme(theme_name)
            if not theme:
                result.success = False
                result.errors.append(f"Theme '{theme_name}' not found")
                return result
            
            # Generate and save CSS
            css_generator = CSSGenerator(theme)
            css_content = css_generator.generate_css()
            
            css_dir = output_dir / "css"
            css_dir.mkdir(exist_ok=True)
            
            css_file = css_dir / "theme.css"
            css_file.write_text(css_content, encoding='utf-8')
            result.css_files_generated = 1
            
            # Copy theme assets if any
            if theme.assets and self.themes_directory:
                theme_assets_dir = self.themes_directory / theme.name / "assets"
                if theme_assets_dir.exists():
                    assets_dir = output_dir / "assets" / "theme"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    
                    for asset_file in theme_assets_dir.rglob('*'):
                        if asset_file.is_file():
                            relative_path = asset_file.relative_to(theme_assets_dir)
                            target_path = assets_dir / relative_path
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(asset_file, target_path)
                            result.assets_copied += 1
            
            # Copy template overrides if any
            if theme.template_overrides and self.themes_directory:
                templates_dir = self.themes_directory / theme.name / "templates"
                if templates_dir.exists():
                    output_templates_dir = output_dir / "templates"
                    output_templates_dir.mkdir(exist_ok=True)
                    
                    for template_file in templates_dir.rglob('*.html'):
                        relative_path = template_file.relative_to(templates_dir)
                        target_path = output_templates_dir / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(template_file, target_path)
                        result.template_files_copied += 1
            
            # Generate theme configuration file
            theme_config_file = output_dir / "theme-config.json"
            theme_config_data = {
                "name": theme.name,
                "display_name": theme.display_name,
                "type": theme.type.value,
                "colors": {
                    "primary": theme.colors.primary,
                    "background": theme.colors.background,
                    "text_primary": theme.colors.text_primary
                }
            }
            
            with open(theme_config_file, 'w', encoding='utf-8') as f:
                json.dump(theme_config_data, f, indent=2)
            
            self.current_theme = theme
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to apply theme: {str(e)}")
        
        return result
    
    def create_theme_from_config(self, config_data: Dict[str, Any]) -> Optional[ThemeConfig]:
        """Create theme configuration from data.
        
        Args:
            config_data: Theme configuration data
            
        Returns:
            Theme configuration or None if invalid
        """
        return self._parse_theme_data(config_data)
    
    def save_theme(self, theme: ThemeConfig, output_path: Path) -> bool:
        """Save theme configuration to file.
        
        Args:
            theme: Theme configuration to save
            output_path: Path to save theme file
            
        Returns:
            True if saved successfully
        """
        try:
            theme_data = {
                "name": theme.name,
                "display_name": theme.display_name,
                "description": theme.description,
                "type": theme.type.value,
                "colors": {
                    "primary": theme.colors.primary,
                    "secondary": theme.colors.secondary,
                    "accent": theme.colors.accent,
                    "background": theme.colors.background,
                    "surface": theme.colors.surface,
                    "text_primary": theme.colors.text_primary,
                    "text_secondary": theme.colors.text_secondary,
                    "border": theme.colors.border,
                    "success": theme.colors.success,
                    "warning": theme.colors.warning,
                    "error": theme.colors.error,
                    "info": theme.colors.info
                },
                "typography": {
                    "font_family_sans": theme.typography.font_family_sans,
                    "font_family_mono": theme.typography.font_family_mono,
                    "font_size_base": theme.typography.font_size_base,
                    "font_weight_normal": theme.typography.font_weight_normal,
                    "font_weight_medium": theme.typography.font_weight_medium,
                    "font_weight_semibold": theme.typography.font_weight_semibold,
                    "font_weight_bold": theme.typography.font_weight_bold,
                    "line_height_base": theme.typography.line_height_base,
                    "line_height_tight": theme.typography.line_height_tight,
                    "line_height_loose": theme.typography.line_height_loose
                },
                "spacing": {
                    "xs": theme.spacing.xs,
                    "sm": theme.spacing.sm,
                    "md": theme.spacing.md,
                    "lg": theme.spacing.lg,
                    "xl": theme.spacing.xl,
                    "xxl": theme.spacing.xxl,
                    "container_max_width": theme.spacing.container_max_width,
                    "sidebar_width": theme.spacing.sidebar_width,
                    "content_padding": theme.spacing.content_padding
                },
                "custom_css": theme.custom_css,
                "template_overrides": theme.template_overrides,
                "assets": theme.assets,
                "responsive_breakpoints": theme.responsive_breakpoints
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2)
            
            return True
        except Exception:
            return False