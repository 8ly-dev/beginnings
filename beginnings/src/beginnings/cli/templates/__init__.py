"""Template system for project scaffolding."""

from .engine import TemplateEngine
from .templates import get_template_config, AVAILABLE_TEMPLATES

__all__ = ["TemplateEngine", "get_template_config", "AVAILABLE_TEMPLATES"]