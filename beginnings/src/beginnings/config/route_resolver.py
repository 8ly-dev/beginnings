"""
Route configuration resolution with pattern matching and specificity ordering.

This module provides route configuration resolution based on patterns,
exact matches, and method-specific overrides with proper precedence handling.
"""

from __future__ import annotations

import re
from typing import Any


class RoutePattern:
    """
    Compiled route pattern for efficient matching.

    Handles exact paths, wildcards (*), and multi-segment wildcards (**).
    """

    def __init__(self, pattern: str, specificity: int) -> None:
        """
        Initialize route pattern.

        Args:
            pattern: Original pattern string
            specificity: Calculated specificity score
        """
        self.pattern = pattern
        self.specificity = specificity
        self._regex = self._compile_pattern(pattern)

    def matches(self, path: str) -> bool:
        """
        Check if this pattern matches the given path.

        Args:
            path: Path to match against

        Returns:
            True if pattern matches path
        """
        # Normalize trailing slashes
        normalized_path = path.rstrip("/") or "/"
        return bool(self._regex.match(normalized_path))

    def _compile_pattern(self, pattern: str) -> re.Pattern[str]:
        """
        Compile pattern string to regex.

        Args:
            pattern: Pattern with wildcards

        Returns:
            Compiled regex pattern
        """
        # Normalize trailing slashes
        normalized = pattern.rstrip("/") or "/"

        # Escape regex special characters except our wildcards
        escaped = re.escape(normalized)

        # Replace escaped wildcards with regex equivalents
        # ** matches multiple path segments
        escaped = escaped.replace(r"\*\*", r".*")
        # * matches single path segment (non-greedy, no slashes)
        escaped = escaped.replace(r"\*", r"[^/]+")

        # Anchor the pattern
        regex_pattern = f"^{escaped}/?$"

        return re.compile(regex_pattern)


def compile_route_pattern(pattern: str) -> RoutePattern:
    """
    Compile a route pattern string into a RoutePattern object.

    Args:
        pattern: Pattern string with optional wildcards

    Returns:
        Compiled RoutePattern
    """
    specificity = calculate_pattern_specificity(pattern)
    return RoutePattern(pattern, specificity)


def calculate_pattern_specificity(pattern: str) -> int:
    """
    Calculate specificity score for pattern precedence ordering.

    Higher scores = higher specificity = higher precedence.

    Args:
        pattern: Pattern string

    Returns:
        Specificity score
    """
    # Start with base score
    score = 0

    # Count literal characters (higher = more specific)
    literal_chars = len([c for c in pattern if c not in ("*", "/")])
    score += literal_chars * 10

    # Count path segments
    segments = [s for s in pattern.split("/") if s]
    score += len(segments) * 5

    # Penalty for wildcards (lower specificity)
    single_wildcards = pattern.count("*") - pattern.count("**")
    multi_wildcards = pattern.count("**")

    score -= single_wildcards * 2
    score -= multi_wildcards * 5

    # Bonus for exact paths (no wildcards)
    if "*" not in pattern:
        score += 50

    return score


class RouteConfigResolver:
    """
    Route configuration resolver with pattern matching and caching.

    Resolves route-specific configuration by matching patterns,
    exact paths, and method-specific overrides with proper precedence.
    """

    def __init__(self, configuration: dict[str, Any]) -> None:
        """
        Initialize route configuration resolver.

        Args:
            configuration: Full application configuration
        """
        self._config = configuration
        self._compiled_patterns: list[tuple[RoutePattern, dict[str, Any]]] = []
        self._exact_routes: dict[str, dict[str, Any]] = {}
        self._cache: dict[str, dict[str, Any]] = {}

        self._compile_route_patterns()

    def resolve_route_config(self, path: str, methods: list[str]) -> dict[str, Any]:
        """
        Resolve configuration for a specific route and methods.

        Args:
            path: Route path
            methods: HTTP methods for the route

        Returns:
            Merged configuration dictionary
        """
        # Create cache key
        cache_key = f"{path}:{':'.join(sorted(methods))}"

        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Start with global defaults
        config = self._get_global_defaults()

        # Collect all matching patterns (wildcard patterns only)
        matching_patterns = []
        for pattern, pattern_config in self._compiled_patterns:
            if pattern.matches(path):
                matching_patterns.append((pattern.specificity, pattern_config))

        # Sort by specificity (lowest first, so more specific overrides less specific)
        matching_patterns.sort(key=lambda x: x[0])

        # Apply pattern configurations in specificity order
        for _, pattern_config in matching_patterns:
            # Create a copy to avoid modifying the original
            config_copy = pattern_config.copy()
            # Remove method-specific config from base merge
            config_copy.pop("methods", None)
            config.update(config_copy)

        # Apply exact path configuration (highest precedence for path)
        # This should be applied AFTER patterns so exact paths override patterns
        normalized_path = path.rstrip("/") or "/"
        if normalized_path in self._exact_routes:
            exact_config = self._exact_routes[normalized_path].copy()

            # Extract method-specific config before merging
            method_configs = exact_config.pop("methods", {})

            # Apply base exact path config
            config.update(exact_config)

            # Apply method-specific config (highest precedence)
            for method in methods:
                if method in method_configs:
                    config.update(method_configs[method])

        # Cache the result
        self._cache[cache_key] = config

        return config

    def update_configuration(self, new_config: dict[str, Any]) -> None:
        """
        Update configuration and invalidate cache.

        Args:
            new_config: New configuration dictionary
        """
        self._config = new_config
        self._cache.clear()
        self._compiled_patterns.clear()
        self._exact_routes.clear()

        self._compile_route_patterns()

    def _compile_route_patterns(self) -> None:
        """Compile all route patterns for efficient matching."""
        routes_config = self._config.get("routes", {})

        patterns = []

        for route_pattern, route_config in routes_config.items():
            if not route_pattern or not isinstance(route_config, dict):
                continue

            # Check if this is an exact route or pattern
            if "*" in route_pattern:
                # It's a pattern
                compiled_pattern = compile_route_pattern(route_pattern)
                patterns.append((compiled_pattern, route_config))
            else:
                # It's an exact route
                normalized_path = route_pattern.rstrip("/") or "/"
                self._exact_routes[normalized_path] = route_config

        # Sort patterns by specificity (highest first)
        patterns.sort(key=lambda x: x[0].specificity, reverse=True)

        self._compiled_patterns = patterns

    def _get_global_defaults(self) -> dict[str, Any]:
        """
        Get global default configuration.

        Returns:
            Global configuration dictionary
        """
        global_config = self._config.get("global", {})
        return dict(global_config) if isinstance(global_config, dict) else {}

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()

    def get_pattern_info(self) -> list[dict[str, Any]]:
        """
        Get information about compiled patterns for debugging.

        Returns:
            List of pattern information dictionaries
        """
        info = []

        for pattern, config in self._compiled_patterns:
            info.append({
                "pattern": pattern.pattern,
                "specificity": pattern.specificity,
                "config_keys": list(config.keys())
            })

        # Add exact routes
        for path, config in self._exact_routes.items():
            info.append({
                "pattern": path,
                "specificity": 9999,  # Exact routes have highest specificity
                "config_keys": list(config.keys()),
                "exact": True
            })

        return info
