"""Progress indicators for CLI operations."""

import click
import threading
import time
from typing import Optional, Iterator
from contextlib import contextmanager


class ProgressBar:
    """Simple progress bar for CLI operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.description = description
        self.current = 0
        self._bar = None
    
    def __enter__(self):
        self._bar = click.progressbar(
            length=self.total,
            label=self.description,
            show_percent=True,
            show_pos=True
        )
        self._bar.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._bar:
            self._bar.__exit__(exc_type, exc_val, exc_tb)
    
    def update(self, amount: int = 1):
        """Update progress by specified amount."""
        if self._bar:
            self.current += amount
            self._bar.update(amount)
    
    def set_description(self, description: str):
        """Update the progress description."""
        self.description = description
        if self._bar:
            self._bar.label = description


class Spinner:
    """Spinning progress indicator for indeterminate operations."""
    
    def __init__(self, message: str = "Working"):
        self.message = message
        self.spinning = False
        self.thread = None
        self.chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    
    def _spin(self):
        """Internal spinning loop."""
        idx = 0
        while self.spinning:
            char = self.chars[idx % len(self.chars)]
            click.echo(f"\r{char} {self.message}", nl=False)
            time.sleep(0.1)
            idx += 1
    
    def start(self):
        """Start the spinner."""
        self.spinning = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self, final_message: Optional[str] = None):
        """Stop the spinner."""
        self.spinning = False
        if self.thread:
            self.thread.join()
        
        # Clear the line and print final message
        click.echo("\r" + " " * (len(self.message) + 2) + "\r", nl=False)
        if final_message:
            click.echo(final_message)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.stop("✗ Failed")
        else:
            self.stop("✓ Done")


@contextmanager
def progress_context(total: int, description: str = "Processing") -> Iterator[ProgressBar]:
    """Context manager for progress operations.
    
    Args:
        total: Total number of items to process
        description: Description of the operation
        
    Yields:
        ProgressBar instance
    """
    with ProgressBar(total, description) as bar:
        yield bar


@contextmanager  
def spinner_context(message: str = "Working") -> Iterator[Spinner]:
    """Context manager for spinner operations.
    
    Args:
        message: Message to display while spinning
        
    Yields:
        Spinner instance
    """
    with Spinner(message) as spinner:
        yield spinner