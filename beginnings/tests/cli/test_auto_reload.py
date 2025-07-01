"""Tests for auto-reload system and file watching."""

import pytest
import tempfile
import os
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from src.beginnings.cli.main import cli


class TestAutoReloadSystem:
    """Test auto-reload system and file watching capabilities."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dev_command_with_auto_reload(self):
        """Test development server with auto-reload enabled."""
        # Create basic app structure
        app_path = os.path.join(self.temp_dir, "main.py")
        config_path = os.path.join(self.temp_dir, "app.yaml")
        
        with open(app_path, "w") as f:
            f.write("""
from beginnings import Beginnings

app = Beginnings()

@app.route("/")
def home():
    return {"message": "Hello World"}

if __name__ == "__main__":
    app.run()
""")
        
        with open(config_path, "w") as f:
            f.write("""
app:
  name: test-app
  debug: true
  auto_reload: true
""")
        
        # Test dev command with auto-reload
        with patch('src.beginnings.cli.commands.run.AutoReloadRunner') as mock_runner:
            mock_instance = MagicMock()
            mock_runner.return_value = mock_instance
            
            result = self.runner.invoke(cli, [
                "dev",
                "--app", app_path,
                "--config", config_path,
                "--reload"
            ])
            
            assert result.exit_code == 0
            mock_runner.assert_called_once()
            mock_instance.start.assert_called_once()
    
    def test_watch_command_monitors_files(self):
        """Test watch command monitors file changes."""
        # Create files to watch
        watch_file = os.path.join(self.temp_dir, "watched.py")
        with open(watch_file, "w") as f:
            f.write("# Initial content")
        
        with patch('src.beginnings.cli.commands.run.FileWatcher') as mock_watcher:
            mock_instance = MagicMock()
            mock_watcher.return_value = mock_instance
            
            result = self.runner.invoke(cli, [
                "watch",
                "--path", self.temp_dir,
                "--pattern", "*.py"
            ])
            
            assert result.exit_code == 0
            mock_watcher.assert_called_once()
            mock_instance.start_watching.assert_called_once()
    
    def test_reload_command_restarts_application(self):
        """Test reload command triggers application restart."""
        with patch('src.beginnings.cli.commands.run.trigger_reload') as mock_reload:
            result = self.runner.invoke(cli, [
                "reload",
                "--signal", "graceful"
            ])
            
            assert result.exit_code == 0
            mock_reload.assert_called_once_with("graceful")


class TestFileWatcher:
    """Test file watching functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_watcher_initialization(self):
        """Test file watcher can be initialized."""
        from src.beginnings.cli.reload.watcher import FileWatcher
        
        watcher = FileWatcher(
            path=self.temp_dir,
            patterns=["*.py", "*.yaml"],
            ignore_patterns=["*.pyc", "__pycache__/*"]
        )
        
        assert watcher.path == self.temp_dir
        assert "*.py" in watcher.patterns
        assert "*.yaml" in watcher.patterns
        assert "*.pyc" in watcher.ignore_patterns
    
    def test_file_watcher_detects_changes(self):
        """Test file watcher detects file changes."""
        from src.beginnings.cli.reload.watcher import FileWatcher
        
        # Create callback to track changes
        changes = []
        def on_change(event):
            changes.append(event)
        
        watcher = FileWatcher(
            path=self.temp_dir,
            patterns=["*.py"],
            callback=on_change
        )
        
        # Start watching in thread
        watch_thread = threading.Thread(target=watcher.start_watching)
        watch_thread.daemon = True
        watch_thread.start()
        
        # Give watcher time to start
        time.sleep(0.1)
        
        # Create a new file
        test_file = os.path.join(self.temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("print('hello')")
        
        # Give time for event to be detected
        time.sleep(0.2)
        
        watcher.stop_watching()
        
        # Should have detected the file creation
        assert len(changes) > 0
    
    def test_file_watcher_ignores_patterns(self):
        """Test file watcher ignores specified patterns."""
        from src.beginnings.cli.reload.watcher import FileWatcher
        
        changes = []
        def on_change(event):
            changes.append(event)
        
        watcher = FileWatcher(
            path=self.temp_dir,
            patterns=["*.py"],
            ignore_patterns=["*.pyc"],
            callback=on_change
        )
        
        watch_thread = threading.Thread(target=watcher.start_watching)
        watch_thread.daemon = True
        watch_thread.start()
        
        time.sleep(0.1)
        
        # Create ignored file
        ignored_file = os.path.join(self.temp_dir, "test.pyc")
        with open(ignored_file, "w") as f:
            f.write("compiled")
        
        time.sleep(0.2)
        
        watcher.stop_watching()
        
        # Should not have detected the ignored file
        assert len(changes) == 0
    
    def test_file_watcher_handles_directory_changes(self):
        """Test file watcher handles directory creation/deletion."""
        from src.beginnings.cli.reload.watcher import FileWatcher
        
        changes = []
        def on_change(event):
            changes.append(event)
        
        watcher = FileWatcher(
            path=self.temp_dir,
            patterns=["*"],
            callback=on_change
        )
        
        watch_thread = threading.Thread(target=watcher.start_watching)
        watch_thread.daemon = True
        watch_thread.start()
        
        time.sleep(0.1)
        
        # Create directory
        new_dir = os.path.join(self.temp_dir, "newdir")
        os.makedirs(new_dir)
        
        time.sleep(0.2)
        
        watcher.stop_watching()
        
        # Should have detected directory creation
        assert len(changes) > 0


class TestAutoReloadRunner:
    """Test auto-reload runner functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_auto_reload_runner_initialization(self):
        """Test auto-reload runner can be initialized."""
        from src.beginnings.cli.reload.runner import AutoReloadRunner
        
        app_file = os.path.join(self.temp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("# Test app")
        
        runner = AutoReloadRunner(
            app_file=app_file,
            watch_paths=[self.temp_dir],
            patterns=["*.py"],
            reload_delay=1.0
        )
        
        assert runner.app_file == app_file
        assert self.temp_dir in runner.watch_paths
        assert "*.py" in runner.patterns
        assert runner.reload_delay == 1.0
    
    def test_auto_reload_runner_starts_process(self):
        """Test auto-reload runner starts application process."""
        from src.beginnings.cli.reload.runner import AutoReloadRunner
        
        app_file = os.path.join(self.temp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("""
import time
print("App started")
time.sleep(10)  # Keep running
""")
        
        runner = AutoReloadRunner(
            app_file=app_file,
            watch_paths=[self.temp_dir],
            patterns=["*.py"]
        )
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            runner.start_process()
            
            mock_popen.assert_called_once()
            assert runner.process == mock_process
    
    def test_auto_reload_runner_handles_file_changes(self):
        """Test auto-reload runner handles file changes by restarting."""
        from src.beginnings.cli.reload.runner import AutoReloadRunner
        
        app_file = os.path.join(self.temp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("print('version 1')")
        
        runner = AutoReloadRunner(
            app_file=app_file,
            watch_paths=[self.temp_dir],
            patterns=["*.py"],
            reload_delay=0.1  # Fast for testing
        )
        
        with patch.object(runner, 'restart_process') as mock_restart:
            # Simulate file change event
            from watchdog.events import FileModifiedEvent
            event = FileModifiedEvent(app_file)
            
            runner.on_file_changed(event)
            
            # Give time for debouncing
            time.sleep(0.2)
            
            mock_restart.assert_called_once()
    
    def test_auto_reload_runner_debounces_changes(self):
        """Test auto-reload runner debounces rapid file changes."""
        from src.beginnings.cli.reload.runner import AutoReloadRunner
        
        app_file = os.path.join(self.temp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("print('test')")
        
        runner = AutoReloadRunner(
            app_file=app_file,
            watch_paths=[self.temp_dir],
            patterns=["*.py"],
            reload_delay=0.2
        )
        
        with patch.object(runner, 'restart_process') as mock_restart:
            from watchdog.events import FileModifiedEvent
            
            # Simulate rapid changes
            for _ in range(5):
                event = FileModifiedEvent(app_file)
                runner.on_file_changed(event)
                time.sleep(0.05)  # Changes faster than reload delay
            
            # Wait for debounce period
            time.sleep(0.3)
            
            # Should only restart once despite multiple changes
            assert mock_restart.call_count == 1
    
    def test_auto_reload_runner_graceful_shutdown(self):
        """Test auto-reload runner can shutdown gracefully."""
        from src.beginnings.cli.reload.runner import AutoReloadRunner
        
        app_file = os.path.join(self.temp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("import time; time.sleep(1)")
        
        runner = AutoReloadRunner(
            app_file=app_file,
            watch_paths=[self.temp_dir],
            patterns=["*.py"]
        )
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Process is running
            mock_popen.return_value = mock_process
            
            runner.start_process()
            runner.shutdown()
            
            # Should terminate the process
            mock_process.terminate.assert_called_once()


class TestReloadCommands:
    """Test reload-related CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dev_command_exists(self):
        """Test dev command is available."""
        result = self.runner.invoke(cli, ["dev", "--help"])
        assert result.exit_code == 0
        assert "development server" in result.output.lower()
    
    def test_watch_command_exists(self):
        """Test watch command is available."""
        result = self.runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "watch" in result.output.lower()
    
    def test_reload_command_exists(self):
        """Test reload command is available."""
        result = self.runner.invoke(cli, ["reload", "--help"])
        assert result.exit_code == 0
        assert "reload" in result.output.lower()


class TestHotReloadIntegration:
    """Test hot-reload integration with the framework."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_hot_reload_detects_route_changes(self):
        """Test hot reload detects changes to route files."""
        from src.beginnings.cli.reload.hot_reload import HotReloadManager
        
        routes_file = os.path.join(self.temp_dir, "routes.py")
        with open(routes_file, "w") as f:
            f.write("""
def home():
    return {"message": "Hello"}
""")
        
        manager = HotReloadManager(
            watch_paths=[self.temp_dir],
            include_patterns=["*.py"]
        )
        
        changes = []
        def on_reload(change_type, file_path):
            changes.append((change_type, file_path))
        
        manager.set_reload_callback(on_reload)
        
        # Start monitoring
        monitor_thread = threading.Thread(target=manager.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        time.sleep(0.1)
        
        # Modify the routes file
        with open(routes_file, "w") as f:
            f.write("""
def home():
    return {"message": "Hello World Updated"}
""")
        
        time.sleep(0.2)
        
        manager.stop_monitoring()
        
        # Should have detected the change
        assert len(changes) > 0
        assert any("routes.py" in str(change[1]) for change in changes)
    
    def test_hot_reload_detects_config_changes(self):
        """Test hot reload detects configuration changes."""
        from src.beginnings.cli.reload.hot_reload import HotReloadManager
        
        config_file = os.path.join(self.temp_dir, "app.yaml")
        with open(config_file, "w") as f:
            f.write("""
app:
  debug: false
""")
        
        manager = HotReloadManager(
            watch_paths=[self.temp_dir],
            include_patterns=["*.yaml", "*.yml"]
        )
        
        changes = []
        def on_reload(change_type, file_path):
            changes.append((change_type, file_path))
        
        manager.set_reload_callback(on_reload)
        
        monitor_thread = threading.Thread(target=manager.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        time.sleep(0.1)
        
        # Update config
        with open(config_file, "w") as f:
            f.write("""
app:
  debug: true
  new_setting: value
""")
        
        time.sleep(0.2)
        
        manager.stop_monitoring()
        
        # Should have detected config change
        assert len(changes) > 0
        assert any("app.yaml" in str(change[1]) for change in changes)
    
    def test_hot_reload_ignores_temp_files(self):
        """Test hot reload ignores temporary and cache files."""
        from src.beginnings.cli.reload.hot_reload import HotReloadManager
        
        manager = HotReloadManager(
            watch_paths=[self.temp_dir],
            include_patterns=["*.py"],
            exclude_patterns=["*.pyc", "*.tmp", "__pycache__/*"]
        )
        
        changes = []
        def on_reload(change_type, file_path):
            changes.append((change_type, file_path))
        
        manager.set_reload_callback(on_reload)
        
        monitor_thread = threading.Thread(target=manager.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        time.sleep(0.1)
        
        # Create files that should be ignored
        temp_file = os.path.join(self.temp_dir, "temp.pyc")
        with open(temp_file, "w") as f:
            f.write("compiled")
        
        cache_dir = os.path.join(self.temp_dir, "__pycache__")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "module.pyc")
        with open(cache_file, "w") as f:
            f.write("cached")
        
        time.sleep(0.2)
        
        manager.stop_monitoring()
        
        # Should not have detected ignored files
        assert len(changes) == 0


class TestReloadConfiguration:
    """Test auto-reload configuration options."""
    
    def test_reload_config_from_yaml(self):
        """Test loading reload configuration from YAML."""
        from src.beginnings.cli.reload.config import ReloadConfig
        
        config_data = {
            "auto_reload": {
                "enabled": True,
                "watch_paths": ["src/", "config/"],
                "include_patterns": ["*.py", "*.yaml"],
                "exclude_patterns": ["*.pyc", "__pycache__/*"],
                "reload_delay": 1.5,
                "use_polling": False
            }
        }
        
        reload_config = ReloadConfig.from_dict(config_data)
        
        assert reload_config.enabled is True
        assert "src/" in reload_config.watch_paths
        assert "config/" in reload_config.watch_paths
        assert "*.py" in reload_config.include_patterns
        assert "*.yaml" in reload_config.include_patterns
        assert "*.pyc" in reload_config.exclude_patterns
        assert reload_config.reload_delay == 1.5
        assert reload_config.use_polling is False
    
    def test_reload_config_defaults(self):
        """Test reload configuration with default values."""
        from src.beginnings.cli.reload.config import ReloadConfig
        
        reload_config = ReloadConfig()
        
        assert reload_config.enabled is False  # Default disabled
        assert "." in reload_config.watch_paths  # Watch current directory
        assert "*.py" in reload_config.include_patterns
        assert "*.pyc" in reload_config.exclude_patterns
        assert reload_config.reload_delay == 1.0
        assert reload_config.use_polling is False
    
    def test_reload_config_validation(self):
        """Test reload configuration validation."""
        from src.beginnings.cli.reload.config import ReloadConfig
        
        # Test invalid delay
        with pytest.raises(ValueError, match="reload_delay must be positive"):
            ReloadConfig(reload_delay=-1.0)
        
        # Test empty watch paths
        with pytest.raises(ValueError, match="watch_paths cannot be empty"):
            ReloadConfig(watch_paths=[])
        
        # Test invalid patterns
        with pytest.raises(ValueError, match="include_patterns cannot be empty"):
            ReloadConfig(include_patterns=[])