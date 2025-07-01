"""Auto-reload runner for managing application processes."""

from __future__ import annotations

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import List, Optional, Callable
from threading import Thread, Event, Timer

from .watcher import FileChangeEvent, create_file_watcher
from .config import ReloadConfig


class AutoReloadRunner:
    """Manages application process with auto-reload on file changes."""
    
    def __init__(
        self,
        app_file: str,
        watch_paths: List[str] = None,
        patterns: List[str] = None,
        ignore_patterns: List[str] = None,
        reload_delay: float = 1.0,
        max_restart_attempts: int = 3,
        use_polling: bool = False
    ):
        """Initialize auto-reload runner.
        
        Args:
            app_file: Path to main application file
            watch_paths: Directories to watch for changes
            patterns: File patterns to watch
            ignore_patterns: File patterns to ignore
            reload_delay: Delay before reloading after change
            max_restart_attempts: Maximum restart attempts before giving up
            use_polling: Use polling instead of native file watching
        """
        self.app_file = Path(app_file).resolve()
        self.watch_paths = watch_paths or [str(self.app_file.parent)]
        self.patterns = patterns or ['*.py', '*.yaml', '*.yml', '*.json']
        self.ignore_patterns = ignore_patterns or [
            '*.pyc', '*.pyo', '__pycache__/*', '.git/*', '*.log'
        ]
        self.reload_delay = reload_delay
        self.max_restart_attempts = max_restart_attempts
        self.use_polling = use_polling
        
        self.process: Optional[subprocess.Popen] = None
        self.watchers: List = []
        self.reload_timer: Optional[Timer] = None
        self.restart_count = 0
        self.is_running = False
        self.shutdown_event = Event()
        
        # Callbacks
        self.on_reload_callback: Optional[Callable[[str], None]] = None
        self.on_process_start_callback: Optional[Callable[[], None]] = None
        self.on_process_stop_callback: Optional[Callable[[], None]] = None
    
    def start(self):
        """Start the auto-reload runner."""
        if self.is_running:
            return
        
        self.is_running = True
        
        try:
            # Start initial process
            self.start_process()
            
            # Start file watchers
            self.start_watchers()
            
            # Wait for shutdown signal
            while self.is_running and not self.shutdown_event.is_set():
                time.sleep(0.1)
                
                # Check if process died unexpectedly
                if self.process and self.process.poll() is not None:
                    print(f"Process exited with code {self.process.returncode}")
                    if self.restart_count < self.max_restart_attempts:
                        print(f"Restarting process (attempt {self.restart_count + 1}/{self.max_restart_attempts})")
                        self.restart_process()
                    else:
                        print("Maximum restart attempts reached. Stopping auto-reload.")
                        break
                        
        except KeyboardInterrupt:
            print("\nShutting down auto-reload...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the auto-reload runner."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.shutdown_event.set()
        
        # Cancel pending reload timer
        if self.reload_timer:
            self.reload_timer.cancel()
        
        # Stop file watchers
        self.stop_watchers()
        
        # Stop process
        self.stop_process()
    
    def start_process(self):
        """Start the application process."""
        if self.process:
            self.stop_process()
        
        cmd = [sys.executable, str(self.app_file)]
        
        try:
            # Set environment variables for child process
            env = os.environ.copy()
            env['BEGINNINGS_AUTO_RELOAD'] = 'true'
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start thread to read output
            Thread(
                target=self._read_process_output,
                daemon=True
            ).start()
            
            self.restart_count = 0
            print(f"Started process: {' '.join(cmd)} (PID: {self.process.pid})")
            
            if self.on_process_start_callback:
                self.on_process_start_callback()
                
        except Exception as e:
            print(f"Failed to start process: {e}")
            self.process = None
    
    def stop_process(self):
        """Stop the application process."""
        if not self.process:
            return
        
        print(f"Stopping process (PID: {self.process.pid})")
        
        try:
            # Try graceful shutdown first
            if hasattr(signal, 'SIGTERM'):
                self.process.send_signal(signal.SIGTERM)
            else:
                self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                print("Graceful shutdown timed out, force killing process")
                self.process.kill()
                self.process.wait()
                
        except ProcessLookupError:
            # Process already dead
            pass
        except Exception as e:
            print(f"Error stopping process: {e}")
        
        self.process = None
        
        if self.on_process_stop_callback:
            self.on_process_stop_callback()
    
    def restart_process(self):
        """Restart the application process."""
        self.restart_count += 1
        print(f"Restarting application... (attempt {self.restart_count})")
        
        self.stop_process()
        time.sleep(0.5)  # Brief pause before restart
        self.start_process()
        
        if self.on_reload_callback:
            self.on_reload_callback(f"Process restarted (attempt {self.restart_count})")
    
    def start_watchers(self):
        """Start file watchers for all watch paths."""
        for watch_path in self.watch_paths:
            if not os.path.exists(watch_path):
                print(f"Warning: Watch path does not exist: {watch_path}")
                continue
            
            try:
                watcher = create_file_watcher(
                    path=watch_path,
                    patterns=self.patterns,
                    ignore_patterns=self.ignore_patterns,
                    callback=self.on_file_changed,
                    use_polling=self.use_polling
                )
                
                # Start watcher in separate thread
                watcher_thread = Thread(
                    target=watcher.start_watching,
                    daemon=True
                )
                watcher_thread.start()
                
                self.watchers.append((watcher, watcher_thread))
                print(f"Watching: {watch_path}")
                
            except Exception as e:
                print(f"Failed to start watcher for {watch_path}: {e}")
    
    def stop_watchers(self):
        """Stop all file watchers."""
        for watcher, thread in self.watchers:
            try:
                watcher.stop_watching()
            except Exception as e:
                print(f"Error stopping watcher: {e}")
        
        self.watchers.clear()
    
    def on_file_changed(self, event: FileChangeEvent):
        """Handle file change events."""
        if not self.is_running:
            return
        
        # Cancel existing timer
        if self.reload_timer:
            self.reload_timer.cancel()
        
        # Start new timer for debounced reload
        self.reload_timer = Timer(self.reload_delay, self._trigger_reload, [event])
        self.reload_timer.start()
    
    def _trigger_reload(self, event: FileChangeEvent):
        """Trigger application reload."""
        if not self.is_running:
            return
        
        print(f"File changed: {event.file_path} ({event.event_type})")
        
        # Reset restart count on file change
        self.restart_count = 0
        
        self.restart_process()
    
    def _read_process_output(self):
        """Read and display process output."""
        if not self.process or not self.process.stdout:
            return
        
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    print(f"[APP] {line.rstrip()}")
                
                if self.process.poll() is not None:
                    break
                    
        except Exception as e:
            print(f"Error reading process output: {e}")
    
    def set_reload_callback(self, callback: Callable[[str], None]):
        """Set callback for reload events."""
        self.on_reload_callback = callback
    
    def set_process_callbacks(
        self,
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None
    ):
        """Set callbacks for process start/stop events."""
        self.on_process_start_callback = on_start
        self.on_process_stop_callback = on_stop


def create_auto_reload_runner(
    app_file: str,
    config: Optional[ReloadConfig] = None
) -> AutoReloadRunner:
    """Create auto-reload runner from configuration.
    
    Args:
        app_file: Path to main application file
        config: Reload configuration
        
    Returns:
        AutoReloadRunner instance
    """
    if config is None:
        config = ReloadConfig()
    
    return AutoReloadRunner(
        app_file=app_file,
        watch_paths=config.watch_paths,
        patterns=config.include_patterns,
        ignore_patterns=config.exclude_patterns,
        reload_delay=config.reload_delay,
        max_restart_attempts=config.max_reload_attempts,
        use_polling=config.use_polling
    )