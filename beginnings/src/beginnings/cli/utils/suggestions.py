"""Intelligent suggestion system for CLI error handling and user assistance."""

import re
import difflib
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import os


class CommandSuggester:
    """Provides intelligent command suggestions based on user input and context."""
    
    def __init__(self):
        """Initialize command suggester with known commands and patterns."""
        # Available commands and subcommands
        self.commands = {
            "new": {
                "description": "Create a new beginnings project",
                "options": ["--template", "--output-dir", "--no-git", "--no-deps"],
                "templates": ["minimal", "standard", "api", "full", "custom"],
                "common_patterns": [
                    "beginnings new my-project",
                    "beginnings new my-api --template api",
                    "beginnings new frontend --template minimal"
                ]
            },
            "config": {
                "description": "Manage configuration files",
                "subcommands": ["validate", "show", "audit", "fix", "generate", "diff"],
                "options": ["--config", "--security-audit", "--production", "--environment"],
                "common_patterns": [
                    "beginnings config validate",
                    "beginnings config show --format json",
                    "beginnings config audit --severity warning"
                ]
            },
            "run": {
                "description": "Start the development server",
                "options": ["--host", "--port", "--debug", "--no-reload", "--production-preview"],
                "common_patterns": [
                    "beginnings run",
                    "beginnings run --debug",
                    "beginnings run --host 0.0.0.0 --port 8080"
                ]
            },
            "extension": {
                "description": "Manage extensions",
                "subcommands": ["new", "validate", "list", "test"],
                "options": ["--type", "--provider-base", "--output-dir", "--interactive"],
                "types": ["middleware", "auth_provider", "feature", "integration"],
                "common_patterns": [
                    "beginnings extension new my-auth --type auth_provider",
                    "beginnings extension list",
                    "beginnings extension validate my-extension"
                ]
            },
            "debug": {
                "description": "Start debugging dashboard",
                "options": ["--host", "--port", "--enable-profiler", "--monitor-app"],
                "common_patterns": [
                    "beginnings debug",
                    "beginnings debug --enable-profiler"
                ]
            },
            "docs": {
                "description": "Generate and manage documentation",
                "subcommands": ["generate", "serve", "validate"],
                "options": ["--output", "--format", "--level"],
                "common_patterns": [
                    "beginnings docs generate",
                    "beginnings docs serve --port 8080"
                ]
            },
            "migrate": {
                "description": "Run database and code migrations",
                "subcommands": ["run", "list", "create", "rollback"],
                "options": ["--target", "--dry-run", "--force"],
                "common_patterns": [
                    "beginnings migrate run",
                    "beginnings migrate list"
                ]
            }
        }
        
        # Common error patterns and their solutions
        self.error_patterns = {
            r"no module named ['\"](\w+)['\"]": {
                "type": "missing_dependency",
                "suggestions": [
                    "Install the missing dependency: pip install {module}",
                    "Check if the module is correctly listed in requirements.txt",
                    "Verify virtual environment is activated"
                ]
            },
            r"permission denied": {
                "type": "permission_error",
                "suggestions": [
                    "Check file/directory permissions",
                    "Run with appropriate user privileges",
                    "Ensure you have write access to the target directory"
                ]
            },
            r"file not found|no such file": {
                "type": "file_not_found",
                "suggestions": [
                    "Verify the file path is correct",
                    "Check if the file exists in the expected location",
                    "Ensure you're in the correct working directory"
                ]
            },
            r"invalid project name": {
                "type": "invalid_name",
                "suggestions": [
                    "Use only letters, numbers, hyphens, and underscores",
                    "Start with a letter or underscore",
                    "Avoid special characters and spaces"
                ]
            },
            r"yaml|syntax error": {
                "type": "yaml_error",
                "suggestions": [
                    "Check YAML syntax - ensure proper indentation",
                    "Verify quotes and brackets are properly closed",
                    "Use a YAML validator to check file structure"
                ]
            },
            r"port.*already in use|address already in use": {
                "type": "port_in_use",
                "suggestions": [
                    "Use a different port with --port option",
                    "Stop the process using the port",
                    "Check for other running servers"
                ]
            }
        }
    
    def suggest_command_fix(self, user_input: str, available_commands: List[str] = None) -> List[str]:
        """Suggest command fixes for typos and similar issues.
        
        Args:
            user_input: The command the user typed
            available_commands: List of available commands (defaults to built-in list)
            
        Returns:
            List of suggested command corrections
        """
        if available_commands is None:
            available_commands = list(self.commands.keys())
        
        suggestions = []
        
        # Check for close matches
        close_matches = difflib.get_close_matches(
            user_input, available_commands, n=3, cutoff=0.6
        )
        
        for match in close_matches:
            suggestions.append(f"Did you mean: beginnings {match}")
        
        # Check for common typos
        typo_fixes = self._check_common_typos(user_input)
        suggestions.extend(typo_fixes)
        
        return suggestions
    
    def suggest_subcommand_fix(self, command: str, subcommand: str) -> List[str]:
        """Suggest subcommand fixes.
        
        Args:
            command: Main command (e.g., "config")
            subcommand: Subcommand user typed
            
        Returns:
            List of suggested subcommand corrections
        """
        suggestions = []
        
        if command in self.commands and "subcommands" in self.commands[command]:
            available_subcommands = self.commands[command]["subcommands"]
            
            close_matches = difflib.get_close_matches(
                subcommand, available_subcommands, n=3, cutoff=0.6
            )
            
            for match in close_matches:
                suggestions.append(f"Did you mean: beginnings {command} {match}")
        
        return suggestions
    
    def suggest_option_fix(self, option: str, command: str = None) -> List[str]:
        """Suggest option/flag fixes.
        
        Args:
            option: Option user typed (e.g., "--templete")
            command: Command context
            
        Returns:
            List of suggested option corrections
        """
        suggestions = []
        
        # Collect available options
        available_options = []
        if command and command in self.commands:
            available_options.extend(self.commands[command].get("options", []))
        
        # Add global options
        global_options = ["--help", "--verbose", "--quiet", "--config-dir", "--env"]
        available_options.extend(global_options)
        
        close_matches = difflib.get_close_matches(
            option, available_options, n=3, cutoff=0.6
        )
        
        for match in close_matches:
            suggestions.append(f"Did you mean: {match}")
        
        return suggestions
    
    def get_contextual_suggestions(self, command: str, current_args: List[str] = None) -> List[str]:
        """Get contextual suggestions based on current command and arguments.
        
        Args:
            command: Current command being typed
            current_args: Arguments already provided
            
        Returns:
            List of contextual suggestions
        """
        suggestions = []
        current_args = current_args or []
        
        if command in self.commands:
            cmd_info = self.commands[command]
            
            # Suggest subcommands if available
            if "subcommands" in cmd_info:
                suggestions.append("Available subcommands:")
                for subcmd in cmd_info["subcommands"]:
                    suggestions.append(f"  beginnings {command} {subcmd}")
            
            # Suggest common options
            if "options" in cmd_info:
                suggestions.append("Common options:")
                for option in cmd_info["options"][:3]:  # Limit to top 3
                    suggestions.append(f"  {option}")
            
            # Show common patterns
            if "common_patterns" in cmd_info:
                suggestions.append("Common usage patterns:")
                for pattern in cmd_info["common_patterns"][:2]:  # Limit to top 2
                    suggestions.append(f"  {pattern}")
        
        return suggestions
    
    def suggest_based_on_error(self, error_message: str, context: Dict[str, Any] = None) -> List[str]:
        """Suggest fixes based on error message content.
        
        Args:
            error_message: The error message text
            context: Additional context about the error
            
        Returns:
            List of suggested fixes
        """
        suggestions = []
        context = context or {}
        
        error_lower = error_message.lower()
        
        # Match against known error patterns
        for pattern, solution in self.error_patterns.items():
            match = re.search(pattern, error_lower)
            if match:
                # Replace placeholders in suggestions
                for suggestion in solution["suggestions"]:
                    if "{module}" in suggestion and match.groups():
                        suggestion = suggestion.replace("{module}", match.group(1))
                    suggestions.append(suggestion)
                break
        
        # Add context-specific suggestions
        if "command" in context:
            command = context["command"]
            if command == "new" and "project name" in error_lower:
                suggestions.extend([
                    "Use alphanumeric characters, hyphens, and underscores only",
                    "Example valid names: my-app, webapp_v2, blog-site"
                ])
            elif command == "run" and "port" in error_lower:
                suggestions.extend([
                    "Try a different port: beginnings run --port 8080",
                    "Check what's using the port: lsof -i :8000"
                ])
        
        # Add project-context suggestions
        if self._is_in_project_directory():
            suggestions.append("You appear to be in a beginnings project directory")
        else:
            suggestions.append("Consider running 'beginnings new' to create a project first")
        
        return suggestions
    
    def get_next_step_suggestions(self, completed_action: str, context: Dict[str, Any] = None) -> List[str]:
        """Suggest next steps after completing an action.
        
        Args:
            completed_action: Action that was just completed
            context: Context about what was done
            
        Returns:
            List of suggested next steps
        """
        suggestions = []
        context = context or {}
        
        if completed_action == "project_created":
            project_name = context.get("project_name", "your-project")
            suggestions.extend([
                f"cd {project_name}",
                "beginnings run",
                "beginnings config validate",
                "Open http://localhost:8000 in your browser"
            ])
        
        elif completed_action == "config_validated":
            if context.get("has_errors"):
                suggestions.extend([
                    "beginnings config fix --dry-run",
                    "Review configuration file manually",
                    "beginnings config audit --severity error"
                ])
            else:
                suggestions.extend([
                    "beginnings run",
                    "beginnings config show --format json"
                ])
        
        elif completed_action == "extension_created":
            extension_name = context.get("extension_name", "your-extension")
            suggestions.extend([
                f"cd {extension_name}",
                f"beginnings extension validate {extension_name}",
                f"beginnings extension test {extension_name}",
                "Edit extension.py to implement your logic"
            ])
        
        elif completed_action == "server_started":
            suggestions.extend([
                "Visit http://localhost:8000 to see your app",
                "beginnings debug (in another terminal)",
                "Press Ctrl+C to stop the server"
            ])
        
        return suggestions
    
    def _check_common_typos(self, user_input: str) -> List[str]:
        """Check for common typos in commands.
        
        Args:
            user_input: User's input command
            
        Returns:
            List of typo corrections
        """
        typo_map = {
            "begimnnings": "beginnings",
            "begninings": "beginnings",
            "biginnings": "beginnings",
            "runn": "run",
            "comfig": "config",
            "confg": "config",
            "extention": "extension",
            "debugg": "debug",
            "migrte": "migrate",
            "migarte": "migrate"
        }
        
        suggestions = []
        if user_input in typo_map:
            suggestions.append(f"Did you mean: {typo_map[user_input]}")
        
        return suggestions
    
    def _is_in_project_directory(self) -> bool:
        """Check if current directory appears to be a beginnings project."""
        current_dir = Path.cwd()
        
        # Look for beginnings project indicators
        indicators = [
            current_dir / "config" / "app.yaml",
            current_dir / "config" / "app.yml",
            current_dir / "main.py",
            current_dir / "pyproject.toml"
        ]
        
        return any(indicator.exists() for indicator in indicators)


class ContextualHelpProvider:
    """Provides context-aware help based on current project state and user actions."""
    
    def __init__(self):
        """Initialize contextual help provider."""
        self.help_cache: Dict[str, List[str]] = {}
    
    def get_contextual_help(self, command: str = None, error_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get contextual help information.
        
        Args:
            command: Current command being executed
            error_context: Context about any errors
            
        Returns:
            Dictionary with help information
        """
        help_info = {
            "quick_help": [],
            "examples": [],
            "troubleshooting": [],
            "related_commands": []
        }
        
        # Get project context
        project_context = self._analyze_project_context()
        
        if command == "new":
            help_info.update(self._get_new_command_help(project_context))
        elif command == "config":
            help_info.update(self._get_config_command_help(project_context))
        elif command == "run":
            help_info.update(self._get_run_command_help(project_context))
        elif command == "extension":
            help_info.update(self._get_extension_command_help(project_context))
        else:
            help_info.update(self._get_general_help(project_context))
        
        # Add error-specific help if available
        if error_context:
            error_help = self._get_error_specific_help(error_context)
            help_info["troubleshooting"].extend(error_help)
        
        return help_info
    
    def _analyze_project_context(self) -> Dict[str, Any]:
        """Analyze current project context.
        
        Returns:
            Dictionary with project context information
        """
        context = {
            "is_project_directory": False,
            "has_config": False,
            "has_main_file": False,
            "config_files": [],
            "template_type": "unknown",
            "extensions_used": []
        }
        
        current_dir = Path.cwd()
        
        # Check for project directory
        config_dir = current_dir / "config"
        if config_dir.exists():
            context["is_project_directory"] = True
            
            # Find config files
            for config_file in ["app.yaml", "app.yml"]:
                config_path = config_dir / config_file
                if config_path.exists():
                    context["has_config"] = True
                    context["config_files"].append(str(config_path))
        
        # Check for main file
        main_candidates = ["main.py", "app.py", "run.py"]
        for main_file in main_candidates:
            if (current_dir / main_file).exists():
                context["has_main_file"] = True
                break
        
        # Try to determine template type and extensions
        if context["has_config"]:
            context.update(self._analyze_config_content(context["config_files"][0]))
        
        return context
    
    def _analyze_config_content(self, config_path: str) -> Dict[str, Any]:
        """Analyze configuration file content.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Dictionary with configuration analysis
        """
        analysis = {
            "template_type": "unknown",
            "extensions_used": []
        }
        
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if isinstance(config, dict):
                # Analyze extensions
                extensions = config.get("extensions", [])
                if extensions:
                    analysis["extensions_used"] = [
                        ext.split(":")[-1] if ":" in ext else ext 
                        for ext in extensions
                    ]
                
                # Determine template type based on extensions
                if not extensions:
                    analysis["template_type"] = "minimal"
                elif len(extensions) >= 4:
                    analysis["template_type"] = "full"
                elif "auth" in str(extensions).lower():
                    analysis["template_type"] = "standard"
                elif "api" in str(config).lower():
                    analysis["template_type"] = "api"
        
        except Exception:
            pass
        
        return analysis
    
    def _get_new_command_help(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get help for the 'new' command."""
        return {
            "quick_help": [
                "Creates a new beginnings project with specified template",
                "Use --template to choose project type (minimal, standard, api, full, custom)",
                "Project will be created in current directory unless --output-dir specified"
            ],
            "examples": [
                "beginnings new my-blog --template standard",
                "beginnings new api-service --template api",
                "beginnings new custom-app --template custom --output-dir ~/projects"
            ],
            "troubleshooting": [
                "If directory exists, choose different name or remove existing directory",
                "Ensure you have write permissions in target directory",
                "Use --no-git if git is not available or not wanted"
            ],
            "related_commands": [
                "beginnings config validate (after creation)",
                "beginnings run (to start development server)"
            ]
        }
    
    def _get_config_command_help(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get help for the 'config' command."""
        help_info = {
            "quick_help": [
                "Manage and validate configuration files",
                "Use 'validate' to check configuration syntax and security",
                "Use 'show' to view merged configuration"
            ],
            "examples": [
                "beginnings config validate",
                "beginnings config show --format json",
                "beginnings config audit --severity warning"
            ],
            "related_commands": [
                "beginnings run --validate-config",
                "beginnings config fix --dry-run"
            ]
        }
        
        if context["is_project_directory"]:
            if context["has_config"]:
                help_info["troubleshooting"] = [
                    "Configuration found - validate it with 'beginnings config validate'",
                    "View current config with 'beginnings config show'"
                ]
            else:
                help_info["troubleshooting"] = [
                    "No configuration file found",
                    "Create one with 'beginnings config generate --output config/app.yaml'"
                ]
        else:
            help_info["troubleshooting"] = [
                "Not in a beginnings project directory",
                "Use 'beginnings new' to create a project first"
            ]
        
        return help_info
    
    def _get_run_command_help(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get help for the 'run' command."""
        help_info = {
            "quick_help": [
                "Start the development server with auto-reload",
                "Use --debug for enhanced debugging features",
                "Use --production-preview for production-like environment"
            ],
            "examples": [
                "beginnings run",
                "beginnings run --debug --port 8080",
                "beginnings run --production-preview"
            ],
            "related_commands": [
                "beginnings debug (debugging dashboard)",
                "beginnings config validate (check config first)"
            ]
        }
        
        if not context["is_project_directory"]:
            help_info["troubleshooting"] = [
                "Not in a beginnings project directory",
                "Use 'beginnings new' to create a project first",
                "Or navigate to existing project directory"
            ]
        elif not context["has_main_file"]:
            help_info["troubleshooting"] = [
                "No main application file found",
                "Ensure main.py or app.py exists in project root",
                "Check project structure is correct"
            ]
        else:
            help_info["troubleshooting"] = [
                "If port is in use, try --port with different number",
                "Use --validate-config to check configuration first",
                "Check firewall settings if server is not accessible"
            ]
        
        return help_info
    
    def _get_extension_command_help(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get help for the 'extension' command."""
        return {
            "quick_help": [
                "Create and manage custom extensions",
                "Use 'new' to create extension scaffolding",
                "Use 'validate' to check extension structure"
            ],
            "examples": [
                "beginnings extension new my-auth --type auth_provider",
                "beginnings extension list",
                "beginnings extension test my-extension"
            ],
            "troubleshooting": [
                "Extensions created in ./extensions/ by default",
                "Use --output-dir to specify different location",
                "Validate extension structure before use"
            ],
            "related_commands": [
                "beginnings extension validate <name>",
                "beginnings extension test <name>"
            ]
        }
    
    def _get_general_help(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get general help information."""
        help_info = {
            "quick_help": [
                "beginnings - Web framework with powerful CLI tools",
                "Use 'beginnings --help' for command overview",
                "Use 'beginnings <command> --help' for specific command help"
            ],
            "examples": [
                "beginnings new my-project",
                "beginnings run",
                "beginnings config validate"
            ],
            "related_commands": [
                "beginnings --help",
                "beginnings <command> --help"
            ]
        }
        
        if context["is_project_directory"]:
            help_info["quick_help"].insert(0, "You are in a beginnings project directory")
            help_info["examples"] = [
                "beginnings run (start development server)",
                "beginnings config validate (check configuration)",
                "beginnings debug (open debugging dashboard)"
            ]
        else:
            help_info["troubleshooting"] = [
                "To get started: beginnings new my-project",
                "Then: cd my-project && beginnings run"
            ]
        
        return help_info
    
    def _get_error_specific_help(self, error_context: Dict[str, Any]) -> List[str]:
        """Get help specific to an error context."""
        help_items = []
        
        error_type = error_context.get("type", "unknown")
        
        if error_type == "permission_error":
            help_items.extend([
                "Check file and directory permissions",
                "Ensure you have write access to target location",
                "On Unix systems, consider using 'chmod' to fix permissions"
            ])
        elif error_type == "yaml_error":
            help_items.extend([
                "Check YAML syntax with an online validator",
                "Verify indentation is consistent (use spaces, not tabs)",
                "Ensure all quotes and brackets are properly closed"
            ])
        elif error_type == "dependency_error":
            help_items.extend([
                "Install missing dependencies with pip",
                "Check if virtual environment is activated",
                "Verify requirements.txt is up to date"
            ])
        
        return help_items