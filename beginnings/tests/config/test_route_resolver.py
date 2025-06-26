"""Tests for route configuration resolution with pattern matching."""

from __future__ import annotations

from beginnings.config.route_resolver import (
    RouteConfigResolver,
    calculate_pattern_specificity,
    compile_route_pattern,
)


class TestRoutePatternMatching:
    """Test route pattern compilation and matching."""

    def test_exact_path_matching(self) -> None:
        """Test exact path pattern matching."""
        pattern = compile_route_pattern("/api/users")

        assert pattern.matches("/api/users")
        assert not pattern.matches("/api/users/123")
        assert not pattern.matches("/api/user")
        assert not pattern.matches("/admin/users")

    def test_wildcard_pattern_matching(self) -> None:
        """Test wildcard pattern matching."""
        pattern = compile_route_pattern("/api/*")

        assert pattern.matches("/api/users")
        assert pattern.matches("/api/posts")
        assert pattern.matches("/api/admin")
        assert not pattern.matches("/api/users/123")
        assert not pattern.matches("/admin/users")
        assert not pattern.matches("/api")

    def test_multi_segment_wildcard_matching(self) -> None:
        """Test multi-segment wildcard patterns."""
        pattern = compile_route_pattern("/api/**")

        assert pattern.matches("/api/users")
        assert pattern.matches("/api/users/123")
        assert pattern.matches("/api/admin/settings")
        assert not pattern.matches("/admin/users")
        assert not pattern.matches("/api")

    def test_mixed_wildcard_patterns(self) -> None:
        """Test patterns with multiple wildcards."""
        pattern = compile_route_pattern("/api/*/admin/*")

        assert pattern.matches("/api/v1/admin/users")
        assert pattern.matches("/api/v2/admin/settings")
        assert not pattern.matches("/api/v1/users")
        assert not pattern.matches("/api/admin/users")
        assert not pattern.matches("/api/v1/admin/users/123")

    def test_root_pattern_matching(self) -> None:
        """Test root and near-root pattern matching."""
        root_pattern = compile_route_pattern("/")
        slash_pattern = compile_route_pattern("/*")

        assert root_pattern.matches("/")
        assert not root_pattern.matches("/api")

        assert slash_pattern.matches("/api")
        assert slash_pattern.matches("/admin")
        assert not slash_pattern.matches("/")
        assert not slash_pattern.matches("/api/users")

    def test_pattern_specificity_calculation(self) -> None:
        """Test pattern specificity ranking for precedence."""
        patterns = [
            "/api/users/admin",  # Most specific
            "/api/users/*",
            "/api/*",
            "/*",  # Least specific
        ]

        specificities = [calculate_pattern_specificity(p) for p in patterns]

        # Higher specificity values should be more specific
        assert specificities[0] > specificities[1]
        assert specificities[1] > specificities[2]
        assert specificities[2] > specificities[3]

    def test_trailing_slash_normalization(self) -> None:
        """Test trailing slash handling in patterns."""
        pattern_no_slash = compile_route_pattern("/api/users")
        pattern_with_slash = compile_route_pattern("/api/users/")

        # Both should match both forms
        assert pattern_no_slash.matches("/api/users")
        assert pattern_no_slash.matches("/api/users/")
        assert pattern_with_slash.matches("/api/users")
        assert pattern_with_slash.matches("/api/users/")


class TestRouteConfigurationResolution:
    """Test route configuration resolution logic."""

    def test_empty_configuration_returns_empty_dict(self) -> None:
        """Test resolver with no configuration returns empty dict."""
        resolver = RouteConfigResolver({})

        config = resolver.resolve_route_config("/api/users", ["GET"])
        assert config == {}

    def test_global_default_configuration(self) -> None:
        """Test global default configuration applied to all routes."""
        config = {
            "global": {
                "timeout": 30,
                "retries": 3,
            }
        }

        resolver = RouteConfigResolver(config)
        result = resolver.resolve_route_config("/api/users", ["GET"])

        assert result["timeout"] == 30
        assert result["retries"] == 3

    def test_pattern_configuration_override(self) -> None:
        """Test pattern-specific configuration overrides global."""
        config = {
            "global": {
                "timeout": 30,
                "retries": 3,
            },
            "routes": {
                "/api/*": {
                    "timeout": 60,
                    "auth_required": True,
                }
            }
        }

        resolver = RouteConfigResolver(config)
        result = resolver.resolve_route_config("/api/users", ["GET"])

        assert result["timeout"] == 60  # Overridden
        assert result["retries"] == 3   # From global
        assert result["auth_required"] is True  # From pattern

    def test_exact_path_highest_precedence(self) -> None:
        """Test exact path configuration has highest precedence."""
        config = {
            "global": {
                "timeout": 30,
            },
            "routes": {
                "/api/*": {
                    "timeout": 60,
                },
                "/api/users": {
                    "timeout": 90,
                    "cache_enabled": True,
                }
            }
        }

        resolver = RouteConfigResolver(config)
        result = resolver.resolve_route_config("/api/users", ["GET"])

        assert result["timeout"] == 90  # From exact path
        assert result["cache_enabled"] is True

    def test_method_specific_configuration(self) -> None:
        """Test method-specific configuration overrides."""
        config = {
            "routes": {
                "/api/users": {
                    "timeout": 60,
                    "methods": {
                        "POST": {
                            "timeout": 120,
                            "validation_strict": True,
                        },
                        "GET": {
                            "cache_enabled": True,
                        }
                    }
                }
            }
        }

        resolver = RouteConfigResolver(config)

        # Test POST method
        post_result = resolver.resolve_route_config("/api/users", ["POST"])
        assert post_result["timeout"] == 120
        assert post_result["validation_strict"] is True
        assert "cache_enabled" not in post_result

        # Test GET method
        get_result = resolver.resolve_route_config("/api/users", ["GET"])
        assert get_result["timeout"] == 60  # From base route
        assert get_result["cache_enabled"] is True
        assert "validation_strict" not in get_result

    def test_pattern_specificity_ordering(self) -> None:
        """Test multiple patterns are applied in specificity order."""
        config = {
            "routes": {
                "/**": {  # Multi-segment wildcard to match any nested path
                    "basic_auth": True,
                },
                "/api/**": {  # Multi-segment wildcard for API paths
                    "api_key_required": True,
                },
                "/api/admin/*": {  # Single-segment wildcard for admin resources
                    "admin_required": True,
                },
                "/api/admin/users": {  # Exact path
                    "special_handling": True,
                }
            }
        }

        resolver = RouteConfigResolver(config)
        result = resolver.resolve_route_config("/api/admin/users", ["GET"])

        # All applicable patterns should be applied
        assert result["basic_auth"] is True
        assert result["api_key_required"] is True
        assert result["admin_required"] is True
        assert result["special_handling"] is True

    def test_configuration_merging_behavior(self) -> None:
        """Test configuration merging uses dict.update semantics."""
        config = {
            "routes": {
                "/api/*": {
                    "middleware": ["auth", "logging"],
                    "settings": {
                        "timeout": 60,
                        "retries": 3,
                    }
                },
                "/api/users": {
                    "middleware": ["validation"],  # Completely replaces
                    "settings": {
                        "timeout": 90,  # Partial replacement
                    }
                }
            }
        }

        resolver = RouteConfigResolver(config)
        result = resolver.resolve_route_config("/api/users", ["GET"])

        # List should be completely replaced
        assert result["middleware"] == ["validation"]

        # Dict should be completely replaced
        assert result["settings"] == {"timeout": 90}

    def test_configuration_caching(self) -> None:
        """Test configuration resolution is cached for performance."""
        config = {
            "routes": {
                "/api/*": {
                    "timeout": 60,
                }
            }
        }

        resolver = RouteConfigResolver(config)

        # First resolution
        result1 = resolver.resolve_route_config("/api/users", ["GET"])

        # Second resolution should be cached
        result2 = resolver.resolve_route_config("/api/users", ["GET"])

        assert result1 == result2
        assert result1 is result2  # Same object reference (cached)

    def test_different_methods_cached_separately(self) -> None:
        """Test different HTTP methods are cached separately."""
        config = {
            "routes": {
                "/api/users": {
                    "methods": {
                        "GET": {
                            "cache_enabled": True,
                        },
                        "POST": {
                            "validation_strict": True,
                        }
                    }
                }
            }
        }

        resolver = RouteConfigResolver(config)

        get_result = resolver.resolve_route_config("/api/users", ["GET"])
        post_result = resolver.resolve_route_config("/api/users", ["POST"])

        assert get_result["cache_enabled"] is True
        assert "validation_strict" not in get_result

        assert post_result["validation_strict"] is True
        assert "cache_enabled" not in post_result

    def test_cache_invalidation_on_config_change(self) -> None:
        """Test cache is invalidated when configuration changes."""
        initial_config = {
            "routes": {
                "/api/*": {
                    "timeout": 60,
                }
            }
        }

        resolver = RouteConfigResolver(initial_config)
        result1 = resolver.resolve_route_config("/api/users", ["GET"])
        assert result1["timeout"] == 60

        # Update configuration
        new_config = {
            "routes": {
                "/api/*": {
                    "timeout": 90,
                }
            }
        }

        resolver.update_configuration(new_config)
        result2 = resolver.resolve_route_config("/api/users", ["GET"])
        assert result2["timeout"] == 90

    def test_empty_route_list_handling(self) -> None:
        """Test handling of empty route patterns and edge cases."""
        config = {
            "routes": {
                "": {  # Empty pattern
                    "default": True,
                }
            }
        }

        resolver = RouteConfigResolver(config)
        result = resolver.resolve_route_config("/api/users", ["GET"])

        # Empty pattern should not match anything
        assert "default" not in result
