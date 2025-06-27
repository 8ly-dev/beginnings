"""Color and formatting utilities for CLI output."""

import click
from enum import Enum


class Colors(Enum):
    """Color constants for CLI output."""
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    WHITE = "white"
    BRIGHT_RED = "bright_red"
    BRIGHT_GREEN = "bright_green"
    BRIGHT_YELLOW = "bright_yellow"
    BRIGHT_BLUE = "bright_blue"


def format_message(message: str, color: Colors, bold: bool = False) -> str:
    """Format a message with color and styling.
    
    Args:
        message: The message to format
        color: Color to apply
        bold: Whether to make text bold
        
    Returns:
        Formatted message string
    """
    return click.style(message, fg=color.value, bold=bold)


def success(message: str) -> str:
    """Format a success message."""
    return format_message(f"✓ {message}", Colors.GREEN, bold=True)


def error(message: str) -> str:
    """Format an error message.""" 
    return format_message(f"✗ {message}", Colors.RED, bold=True)


def warning(message: str) -> str:
    """Format a warning message."""
    return format_message(f"⚠ {message}", Colors.YELLOW, bold=True)


def info(message: str) -> str:
    """Format an info message."""
    return format_message(f"ℹ {message}", Colors.BLUE)


def highlight(message: str) -> str:
    """Highlight important text."""
    return format_message(message, Colors.CYAN, bold=True)