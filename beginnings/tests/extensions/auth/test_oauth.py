"""
Tests for OAuth authentication provider.

This module tests OAuth flow implementation, provider integration,
and user profile mapping features.
"""

import base64
import hashlib
import json
import secrets
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beginnings.extensions.auth.providers.oauth_provider import OAuthProvider
from beginnings.extensions.auth.providers.base import AuthenticationError, User


class TestOAuthProvider:
    """Test OAuth authentication provider."""
    
    def test_oauth_provider_initialization(self):
        """Test OAuth provider initializes correctly."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret",
                    "authorization_url": "https://accounts.google.com/o/oauth2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                    "scopes": ["openid", "email", "profile"]
                },
                "github": {
                    "client_id": "github-client-id",
                    "client_secret": "github-client-secret",
                    "authorization_url": "https://github.com/login/oauth/authorize",
                    "token_url": "https://github.com/login/oauth/access_token",
                    "user_info_url": "https://api.github.com/user",
                    "scopes": ["user:email"]
                }
            },
            "redirect_uri": "http://localhost:8000/auth/callback",
            "state_secret": "test-state-secret"
        }
        
        provider = OAuthProvider(config)
        
        assert "google" in provider.providers
        assert "github" in provider.providers
        assert provider.redirect_uri == "http://localhost:8000/auth/callback"
        assert provider.state_secret == "test-state-secret"
        
        google_config = provider.providers["google"]
        assert google_config["client_id"] == "google-client-id"
        assert google_config["scopes"] == ["openid", "email", "profile"]
    
    def test_oauth_provider_default_configuration(self):
        """Test OAuth provider with minimal configuration."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret"
                }
            }
        }
        
        provider = OAuthProvider(config)
        
        # Should use default URLs for Google
        google_config = provider.providers["google"]
        assert "authorization_url" in google_config
        assert "token_url" in google_config
        assert "user_info_url" in google_config
    
    def test_generate_state_parameter(self):
        """Test state parameter generation for CSRF protection."""
        config = {
            "providers": {"google": {"client_id": "test", "client_secret": "test"}},
            "state_secret": "test-secret"
        }
        provider = OAuthProvider(config)
        
        state1 = provider.generate_state()
        state2 = provider.generate_state()
        
        # States should be different
        assert state1 != state2
        # Should be URL-safe
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=" for c in state1)
    
    def test_validate_state_parameter(self):
        """Test state parameter validation."""
        config = {
            "providers": {"google": {"client_id": "test", "client_secret": "test"}},
            "state_secret": "test-secret"
        }
        provider = OAuthProvider(config)
        
        # Generate valid state
        state = provider.generate_state()
        
        # Should validate correctly
        assert provider.validate_state(state) is True
        
        # Invalid state should fail
        assert provider.validate_state("invalid-state") is False
        assert provider.validate_state("") is False
    
    def test_generate_pkce_challenge(self):
        """Test PKCE code challenge generation."""
        config = {
            "providers": {"google": {"client_id": "test", "client_secret": "test"}}
        }
        provider = OAuthProvider(config)
        
        code_verifier, code_challenge = provider.generate_pkce_challenge()
        
        # Verify code verifier format
        assert len(code_verifier) >= 43
        assert len(code_verifier) <= 128
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~" for c in code_verifier)
        
        # Verify code challenge is SHA256 hash of verifier
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        assert code_challenge == expected_challenge
    
    def test_build_authorization_url_google(self):
        """Test building Google OAuth authorization URL."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret",
                    "scopes": ["openid", "email", "profile"]
                }
            },
            "redirect_uri": "http://localhost:8000/auth/callback"
        }
        provider = OAuthProvider(config)
        
        state = "test-state"
        code_verifier = "test-code-verifier"
        code_challenge = "test-code-challenge"
        
        auth_url = provider.build_authorization_url(
            "google", state, code_challenge
        )
        
        # Parse URL and verify parameters
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        assert parsed.netloc == "accounts.google.com"
        assert params["client_id"][0] == "google-client-id"
        assert params["redirect_uri"][0] == "http://localhost:8000/auth/callback"
        assert params["scope"][0] == "openid email profile"
        assert params["state"][0] == state
        assert params["code_challenge"][0] == code_challenge
        assert params["code_challenge_method"][0] == "S256"
        assert params["response_type"][0] == "code"
    
    def test_build_authorization_url_github(self):
        """Test building GitHub OAuth authorization URL."""
        config = {
            "providers": {
                "github": {
                    "client_id": "github-client-id",
                    "client_secret": "github-client-secret",
                    "scopes": ["user:email"]
                }
            },
            "redirect_uri": "http://localhost:8000/auth/callback"
        }
        provider = OAuthProvider(config)
        
        state = "test-state"
        code_challenge = "test-code-challenge"
        
        auth_url = provider.build_authorization_url(
            "github", state, code_challenge
        )
        
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        assert parsed.netloc == "github.com"
        assert params["client_id"][0] == "github-client-id"
        assert params["scope"][0] == "user:email"
        assert params["state"][0] == state
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self):
        """Test successful OAuth code exchange for access token."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret",
                    "token_url": "https://oauth2.googleapis.com/token"
                }
            },
            "redirect_uri": "http://localhost:8000/auth/callback"
        }
        provider = OAuthProvider(config)
        
        # Mock successful token response
        mock_response = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test-refresh-token",
            "scope": "openid email profile"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj
            
            result = await provider.exchange_code_for_token(
                "google", "auth-code", "code-verifier"
            )
            
            assert result["access_token"] == "test-access-token"
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 3600
            
            # Verify request parameters
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["data"]["client_id"] == "google-client-id"
            assert call_kwargs["data"]["client_secret"] == "google-client-secret"
            assert call_kwargs["data"]["code"] == "auth-code"
            assert call_kwargs["data"]["code_verifier"] == "code-verifier"
            assert call_kwargs["data"]["grant_type"] == "authorization_code"
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_failure(self):
        """Test OAuth code exchange failure."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret",
                    "token_url": "https://oauth2.googleapis.com/token"
                }
            }
        }
        provider = OAuthProvider(config)
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 400
            mock_response_obj.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Invalid authorization code"
            }
            mock_response_obj.content = b'{"error": "invalid_grant"}'
            mock_post.return_value = mock_response_obj
            
            with pytest.raises(AuthenticationError) as exc_info:
                await provider.exchange_code_for_token(
                    "google", "invalid-code", "code-verifier"
                )
            
            assert "OAuth token exchange failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_info_google(self):
        """Test fetching Google user information."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret",
                    "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo"
                }
            }
        }
        provider = OAuthProvider(config)
        
        mock_user_data = {
            "id": "google-user-123",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_user_data
            mock_get.return_value = mock_response_obj
            
            user_info = await provider.get_user_info("google", "access-token")
            
            assert user_info["id"] == "google-user-123"
            assert user_info["email"] == "user@example.com"
            assert user_info["name"] == "Test User"
            
            # Verify authorization header
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer access-token"
    
    @pytest.mark.asyncio
    async def test_get_user_info_github(self):
        """Test fetching GitHub user information."""
        config = {
            "providers": {
                "github": {
                    "client_id": "github-client-id",
                    "client_secret": "github-client-secret",
                    "user_info_url": "https://api.github.com/user"
                }
            }
        }
        provider = OAuthProvider(config)
        
        mock_user_data = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "user@example.com",
            "avatar_url": "https://github.com/avatar.jpg"
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_user_data
            mock_get.return_value = mock_response_obj
            
            user_info = await provider.get_user_info("github", "access-token")
            
            assert user_info["id"] == 12345
            assert user_info["login"] == "testuser"
            assert user_info["email"] == "user@example.com"
    
    def test_map_user_data_google(self):
        """Test mapping Google user data to User object."""
        config = {
            "providers": {
                "google": {
                    "client_id": "test",
                    "client_secret": "test"
                }
            }
        }
        provider = OAuthProvider(config)
        
        google_data = {
            "id": "google-user-123",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        user = provider.map_user_data("google", google_data)
        
        assert user.user_id == "oauth:google:google-user-123"
        assert user.username == "user@example.com"
        assert user.email == "user@example.com"
        assert user.metadata["full_name"] == "Test User"
        assert user.metadata["avatar_url"] == "https://example.com/avatar.jpg"
        assert user.metadata["provider"] == "oauth"
        assert user.metadata["oauth_provider"] == "google"
        assert user.metadata["oauth_id"] == "google-user-123"
    
    def test_map_user_data_github(self):
        """Test mapping GitHub user data to User object."""
        config = {
            "providers": {
                "github": {
                    "client_id": "test",
                    "client_secret": "test"
                }
            }
        }
        provider = OAuthProvider(config)
        
        github_data = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "user@example.com",
            "avatar_url": "https://github.com/avatar.jpg"
        }
        
        user = provider.map_user_data("github", github_data)
        
        assert user.user_id == "oauth:github:12345"
        assert user.username == "testuser"
        assert user.email == "user@example.com"
        assert user.metadata["full_name"] == "Test User"
        assert user.metadata["avatar_url"] == "https://github.com/avatar.jpg"
        assert user.metadata["oauth_provider"] == "github"
        assert user.metadata["oauth_id"] == "12345"
    
    @pytest.mark.asyncio
    async def test_authenticate_oauth_flow_success(self):
        """Test complete OAuth authentication flow."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret"
                }
            }
        }
        provider = OAuthProvider(config)
        
        # Mock request with OAuth callback parameters
        request = MagicMock()
        request.query_params = {
            "code": "auth-code",
            "state": provider.generate_state()
        }
        request.session = {
            "oauth_state": request.query_params["state"],
            "oauth_code_verifier": "test-code-verifier",
            "oauth_provider": "google"
        }
        
        # Mock token exchange
        mock_token_response = {
            "access_token": "access-token",
            "token_type": "Bearer"
        }
        
        # Mock user info
        mock_user_data = {
            "id": "google-user-123",
            "email": "user@example.com",
            "name": "Test User"
        }
        
        with patch.object(provider, 'exchange_code_for_token', return_value=mock_token_response), \
             patch.object(provider, 'get_user_info', return_value=mock_user_data):
            
            user = await provider.authenticate(request)
            
            assert user is not None
            assert user.user_id == "oauth:google:google-user-123"
            assert user.email == "user@example.com"
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_code(self):
        """Test OAuth authentication with missing authorization code."""
        config = {
            "providers": {
                "google": {
                    "client_id": "test",
                    "client_secret": "test"
                }
            }
        }
        provider = OAuthProvider(config)
        
        request = MagicMock()
        request.query_params = {}  # No code parameter
        
        user = await provider.authenticate(request)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_state(self):
        """Test OAuth authentication with invalid state parameter."""
        config = {
            "providers": {
                "google": {
                    "client_id": "test",
                    "client_secret": "test"
                }
            }
        }
        provider = OAuthProvider(config)
        
        request = MagicMock()
        request.query_params = {
            "code": "auth-code",
            "state": "invalid-state"
        }
        request.session = {
            "oauth_state": "different-state"
        }
        
        with pytest.raises(AuthenticationError) as exc_info:
            await provider.authenticate(request)
        
        assert "Invalid OAuth state parameter" in str(exc_info.value)
    
    def test_validate_config_valid(self):
        """Test OAuth configuration validation with valid config."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id",
                    "client_secret": "google-client-secret"
                }
            },
            "redirect_uri": "http://localhost:8000/auth/callback",
            "state_secret": "secure-state-secret"
        }
        provider = OAuthProvider(config)
        
        errors = provider.validate_config()
        assert errors == []
    
    def test_validate_config_missing_client_id(self):
        """Test OAuth configuration validation with missing client ID."""
        config = {
            "providers": {
                "google": {
                    "client_secret": "google-client-secret"
                }
            }
        }
        provider = OAuthProvider(config)
        
        errors = provider.validate_config()
        assert len(errors) > 0
        assert any("client_id" in error for error in errors)
    
    def test_validate_config_missing_client_secret(self):
        """Test OAuth configuration validation with missing client secret."""
        config = {
            "providers": {
                "google": {
                    "client_id": "google-client-id"
                }
            }
        }
        provider = OAuthProvider(config)
        
        errors = provider.validate_config()
        assert len(errors) > 0
        assert any("client_secret" in error for error in errors)