"""File system watcher for auto-reload functionality."""

from __future__ import annotations

import os
import time
import fnmatch
from pathlib import Path
from typing import Callable, List, Optional, Set
from threading import Event, Thread

try:
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver
    from watchdog.events import (
        FileSystemEventHandler, 
        FileModifiedEvent, 
        FileCreatedEvent,
        FileDeletedEvent,
        DirModifiedEvent,
        DirCreatedEvent,
        DirDeletedEvent
    )
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    PollingObserver = None
    FileSystemEventHandler = object
    FileModifiedEvent = None
    FileCreatedEvent = None
    FileDeletedEvent = None
    DirModifiedEvent = None
    DirCreatedEvent = None
    DirDeletedEvent = None


class FileChangeEvent:
    """Represents a file change event."""
    
    def __init__(self, event_type: str, file_path: str, is_directory: bool = False):
        self.event_type = event_type  # 'created', 'modified', 'deleted'
        self.file_path = file_path
        self.is_directory = is_directory
        self.timestamp = time.time()
    
    def __str__(self):
        return f"FileChangeEvent({self.event_type}, {self.file_path})"
    
    def __repr__(self):
        return self.__str__()


class FileWatcher:
    """File system watcher using watchdog library."""
    
    def __init__(
        self,
        path: str,
        patterns: List[str] = None,
        ignore_patterns: List[str] = None,
        callback: Optional[Callable[[FileChangeEvent], None]] = None,
        use_polling: bool = False,
        recursive: bool = True
    ):
        """Initialize file watcher.
        
        Args:
            path: Directory path to watch
            patterns: File patterns to include (e.g., ['*.py', '*.yaml'])
            ignore_patterns: File patterns to ignore (e.g., ['*.pyc', '__pycache__/*'])
            callback: Function to call when files change
            use_polling: Use polling observer instead of native
            recursive: Watch subdirectories recursively
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog library is required for file watching")
        
        self.path = Path(path).resolve()
        self.patterns = patterns or ['*']
        self.ignore_patterns = ignore_patterns or []
        self.callback = callback
        self.use_polling = use_polling
        self.recursive = recursive
        
        self._observer: Optional[Observer] = None
        self._event_handler: Optional[WatchdogEventHandler] = None
        self._stop_event = Event()
        self._debounce_events: Set[str] = set()
        self._debounce_thread: Optional[Thread] = None
        self._debounce_delay = 0.1  # 100ms debounce
        
    def start_watching(self):
        """Start watching for file changes."""
        if not self.path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {self.path}")
        
        # Create observer
        if self.use_polling:
            self._observer = PollingObserver()
        else:
            self._observer = Observer()
        
        # Create event handler
        self._event_handler = WatchdogEventHandler(
            patterns=self.patterns,
            ignore_patterns=self.ignore_patterns,
            callback=self._on_file_changed
        )
        
        # Schedule watching
        self._observer.schedule(
            self._event_handler,
            str(self.path),
            recursive=self.recursive
        )
        
        # Start observer
        self._observer.start()
        
        # Start debounce thread
        self._start_debounce_thread()
        
        try:
            # Keep watching until stopped
            while not self._stop_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_watching()
    
    def stop_watching(self):
        """Stop watching for file changes."""
        self._stop_event.set()
        
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        if self._debounce_thread and self._debounce_thread.is_alive():
            self._debounce_thread.join(timeout=1.0)
    
    def _on_file_changed(self, event: FileChangeEvent):
        """Handle file change event with debouncing."""
        # Add to debounce set
        self._debounce_events.add(event.file_path)
    
    def _start_debounce_thread(self):
        """Start thread to handle debounced events."""
        def debounce_worker():
            while not self._stop_event.is_set():
                if self._debounce_events:
                    # Get all pending events
                    events_to_process = self._debounce_events.copy()
                    self._debounce_events.clear()
                    
                    # Process unique file paths
                    for file_path in events_to_process:
                        if self.callback:
                            event = FileChangeEvent(
                                event_type='modified',
                                file_path=file_path,
                                is_directory=os.path.isdir(file_path)
                            )
                            try:
                                self.callback(event)
                            except Exception as e:
                                print(f"Error in file change callback: {e}")
                
                time.sleep(self._debounce_delay)
        
        self._debounce_thread = Thread(target=debounce_worker, daemon=True)
        self._debounce_thread.start()


class WatchdogEventHandler(FileSystemEventHandler):
    """Event handler for watchdog file system events."""
    
    def __init__(
        self,
        patterns: List[str],
        ignore_patterns: List[str],
        callback: Callable[[FileChangeEvent], None]
    ):
        super().__init__()
        self.patterns = patterns
        self.ignore_patterns = ignore_patterns
        self.callback = callback
    
    def _should_process_event(self, file_path: str) -> bool:
        """Check if event should be processed based on patterns."""
        # Convert to relative path for pattern matching
        file_name = os.path.basename(file_path)
        
        # Check if matches include patterns
        matches_include = any(
            fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern)
            for pattern in self.patterns
        )
        
        if not matches_include:
            return False
        
        # Check if matches ignore patterns
        matches_ignore = any(
            fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern)
            for pattern in self.ignore_patterns
        )
        
        return not matches_ignore
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._should_process_event(event.src_path):
            self.callback(FileChangeEvent(
                event_type='modified',
                file_path=event.src_path,
                is_directory=False
            ))
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._should_process_event(event.src_path):
            self.callback(FileChangeEvent(
                event_type='created',
                file_path=event.src_path,
                is_directory=False
            ))
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and self._should_process_event(event.src_path):
            self.callback(FileChangeEvent(
                event_type='deleted',
                file_path=event.src_path,
                is_directory=False
            ))


class FallbackFileWatcher:
    """Fallback file watcher using polling when watchdog is not available."""
    
    def __init__(
        self,
        path: str,
        patterns: List[str] = None,
        ignore_patterns: List[str] = None,
        callback: Optional[Callable[[FileChangeEvent], None]] = None,
        poll_interval: float = 1.0
    ):
        """Initialize fallback file watcher.
        
        Args:
            path: Directory path to watch
            patterns: File patterns to include
            ignore_patterns: File patterns to ignore
            callback: Function to call when files change
            poll_interval: How often to check for changes (seconds)
        """
        self.path = Path(path).resolve()
        self.patterns = patterns or ['*']
        self.ignore_patterns = ignore_patterns or []
        self.callback = callback
        self.poll_interval = poll_interval
        
        self._stop_event = Event()
        self._file_states: dict[str, float] = {}
        self._scan_thread: Optional[Thread] = None
    
    def start_watching(self):
        """Start watching for file changes using polling."""
        if not self.path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {self.path}")
        
        # Initial scan
        self._scan_files()
        
        # Start polling thread
        self._scan_thread = Thread(target=self._poll_loop, daemon=True)
        self._scan_thread.start()
        
        try:
            while not self._stop_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_watching()
    
    def stop_watching(self):
        """Stop watching for file changes."""
        self._stop_event.set()
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=1.0)
    
    def _poll_loop(self):
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                self._scan_files()
            except Exception as e:
                print(f"Error during file scan: {e}")
            
            time.sleep(self.poll_interval)
    
    def _scan_files(self):
        """Scan files and detect changes."""
        current_states = {}
        
        for file_path in self.path.rglob('*'):
            if file_path.is_file() and self._should_watch_file(str(file_path)):
                try:
                    mtime = file_path.stat().st_mtime
                    current_states[str(file_path)] = mtime
                    
                    # Check if file was modified
                    if str(file_path) in self._file_states:
                        if mtime > self._file_states[str(file_path)]:
                            self._notify_change(str(file_path), 'modified')
                    else:
                        # New file
                        self._notify_change(str(file_path), 'created')
                        
                except (OSError, PermissionError):
                    # File might have been deleted or no permission
                    continue
        
        # Check for deleted files
        for file_path in self._file_states:
            if file_path not in current_states:
                self._notify_change(file_path, 'deleted')
        
        self._file_states = current_states
    
    def _should_watch_file(self, file_path: str) -> bool:
        """Check if file should be watched based on patterns."""
        file_name = os.path.basename(file_path)
        
        # Check include patterns
        matches_include = any(
            fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern)
            for pattern in self.patterns
        )
        
        if not matches_include:
            return False
        
        # Check ignore patterns
        matches_ignore = any(
            fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern)
            for pattern in self.ignore_patterns
        )
        
        return not matches_ignore
    
    def _notify_change(self, file_path: str, event_type: str):
        """Notify callback of file change."""
        if self.callback:
            event = FileChangeEvent(
                event_type=event_type,
                file_path=file_path,
                is_directory=os.path.isdir(file_path) if os.path.exists(file_path) else False
            )
            try:
                self.callback(event)
            except Exception as e:
                print(f"Error in file change callback: {e}")


def create_file_watcher(
    path: str,
    patterns: List[str] = None,
    ignore_patterns: List[str] = None,
    callback: Optional[Callable[[FileChangeEvent], None]] = None,
    use_polling: bool = False
) -> FileWatcher | FallbackFileWatcher:
    """Create appropriate file watcher based on available libraries.
    
    Args:
        path: Directory path to watch
        patterns: File patterns to include
        ignore_patterns: File patterns to ignore
        callback: Function to call when files change
        use_polling: Force use of polling watcher
        
    Returns:
        File watcher instance
    """
    if WATCHDOG_AVAILABLE and not use_polling:
        return FileWatcher(
            path=path,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            callback=callback,
            use_polling=use_polling
        )
    else:
        return FallbackFileWatcher(
            path=path,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            callback=callback
        )