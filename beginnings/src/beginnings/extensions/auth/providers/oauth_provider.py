"""
OAuth authentication provider for Beginnings framework.

This module provides OAuth 2.0 authentication with PKCE support
for multiple providers (Google, GitHub, etc.).
"""

import base64
import hashlib
import hmac
import secrets
import urllib.parse
from typing import Any

import httpx
from fastapi import Request

from beginnings.extensions.auth.providers.base import BaseAuthProvider, AuthenticationError, User


class OAuthProvider(BaseAuthProvider):
    """
    OAuth 2.0 authentication provider.
    
    Supports multiple OAuth providers with PKCE for security,
    state parameter validation, and user profile mapping.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize OAuth provider.
        
        Args:
            config: OAuth configuration dictionary
        """
        super().__init__(config)
        
        self.providers = config.get("providers", {})
        self.redirect_uri = config.get("redirect_uri", "http://localhost:8000/auth/callback")
        self.state_secret = config.get("state_secret", secrets.token_urlsafe(32))
        
        # Add default configurations for known providers
        self._add_default_provider_configs()
    
    def _add_default_provider_configs(self) -> None:
        """Add default configurations for known OAuth providers."""
        defaults = {
            "google": {
                "authorization_url": "https://accounts.google.com/o/oauth2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "scopes": ["openid", "email", "profile"]
            },
            "github": {
                "authorization_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_info_url": "https://api.github.com/user",
                "scopes": ["user:email"]
            }
        }
        
        for provider_name, provider_config in self.providers.items():
            if provider_name in defaults:
                # Merge defaults with user configuration
                default_config = defaults[provider_name].copy()
                default_config.update(provider_config)
                self.providers[provider_name] = default_config
    
    def generate_state(self, expire_minutes: int = 10) -> str:
        """
        Generate state parameter for CSRF protection with expiration.
        
        Args:
            expire_minutes: State expiration time in minutes
        
        Returns:
            URL-safe state parameter
        """
        import time
        import struct
        
        # Generate random data
        random_data = secrets.token_bytes(16)
        
        # Add timestamp for expiration (4 bytes)
        expire_time = int(time.time()) + (expire_minutes * 60)
        timestamp_data = struct.pack('>I', expire_time)
        
        # Combine random data and timestamp
        payload = random_data + timestamp_data
        
        # Create HMAC signature
        signature = hmac.new(
            self.state_secret.encode(),
            payload,
            hashlib.sha256
        ).digest()
        
        # Combine and encode
        state_data = payload + signature
        return base64.urlsafe_b64encode(state_data).decode().rstrip('=')
    
    def validate_state(self, state: str) -> bool:
        """
        Validate state parameter with expiration check.
        
        Args:
            state: State parameter to validate
            
        Returns:
            True if state is valid and not expired
        """
        if not state:
            return False
        
        try:
            import time
            import struct
            
            # Add padding and decode
            padded_state = state + '=' * (4 - len(state) % 4)
            state_bytes = base64.urlsafe_b64decode(padded_state)
            
            if len(state_bytes) < 52:  # 16 bytes random + 4 bytes timestamp + 32 bytes signature
                return False
            
            # Split payload and signature
            payload = state_bytes[:20]  # 16 bytes random + 4 bytes timestamp
            received_signature = state_bytes[20:52]
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.state_secret.encode(),
                payload,
                hashlib.sha256
            ).digest()
            
            # Compare signatures
            if not hmac.compare_digest(received_signature, expected_signature):
                return False
            
            # Check expiration
            timestamp_data = payload[16:20]
            expire_time = struct.unpack('>I', timestamp_data)[0]
            current_time = int(time.time())
            
            return current_time <= expire_time
            
        except Exception:
            return False
    
    def generate_pkce_challenge(self) -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode().rstrip('=')
        
        # Generate code challenge (SHA256 of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        return code_verifier, code_challenge
    
    def build_authorization_url(
        self,
        provider_name: str,
        state: str,
        code_challenge: str
    ) -> str:
        """
        Build OAuth authorization URL.
        
        Args:
            provider_name: OAuth provider name
            state: State parameter for CSRF protection
            code_challenge: PKCE code challenge
            
        Returns:
            Authorization URL
        """
        provider_config = self.providers.get(provider_name)
        if not provider_config:
            raise ValueError(f"OAuth provider '{provider_name}' not configured")
        
        # Build authorization parameters
        params = {
            "client_id": provider_config["client_id"],
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(provider_config.get("scopes", [])),
            "response_type": "code",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        # Build URL
        auth_url = provider_config["authorization_url"]
        query_string = urllib.parse.urlencode(params)
        
        return f"{auth_url}?{query_string}"
    
    async def exchange_code_for_token(
        self,
        provider_name: str,
        code: str,
        code_verifier: str
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            provider_name: OAuth provider name
            code: Authorization code
            code_verifier: PKCE code verifier
            
        Returns:
            Token response dictionary
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        provider_config = self.providers.get(provider_name)
        if not provider_config:
            raise AuthenticationError(f"OAuth provider '{provider_name}' not configured")
        
        # Prepare token request
        token_data = {
            "client_id": provider_config["client_id"],
            "client_secret": provider_config["client_secret"],
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider_config["token_url"],
                data=token_data,
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error_description", "OAuth token exchange failed")
                raise AuthenticationError(f"OAuth token exchange failed: {error_msg}")
            
            return response.json()
    
    async def get_user_info(
        self,
        provider_name: str,
        access_token: str
    ) -> dict[str, Any]:
        """
        Get user information from OAuth provider.
        
        Args:
            provider_name: OAuth provider name
            access_token: Access token
            
        Returns:
            User information dictionary
            
        Raises:
            AuthenticationError: If user info request fails
        """
        provider_config = self.providers.get(provider_name)
        if not provider_config:
            raise AuthenticationError(f"OAuth provider '{provider_name}' not configured")
        
        # Request user information
        async with httpx.AsyncClient() as client:
            response = await client.get(
                provider_config["user_info_url"],
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Failed to fetch user information from OAuth provider")
            
            return response.json()
    
    def map_user_data(self, provider_name: str, user_data: dict[str, Any]) -> User:
        """
        Map OAuth user data to User object.
        
        Args:
            provider_name: OAuth provider name
            user_data: User data from OAuth provider
            
        Returns:
            User object
        """
        if provider_name == "google":
            return self._map_google_user_data(user_data)
        elif provider_name == "github":
            return self._map_github_user_data(user_data)
        else:
            return self._map_generic_user_data(provider_name, user_data)
    
    def _map_google_user_data(self, user_data: dict[str, Any]) -> User:
        """Map Google user data to User object."""
        user_id = f"oauth:google:{user_data['id']}"
        
        return User(
            user_id=user_id,
            username=user_data.get("email"),
            email=user_data.get("email"),
            roles=["user"],  # Default role
            permissions=["read:profile"],  # Default permissions
            metadata={
                "provider": "oauth",
                "oauth_provider": "google",
                "oauth_id": user_data["id"],
                "verified_email": user_data.get("verified_email", False),
                "full_name": user_data.get("name"),
                "avatar_url": user_data.get("picture")
            }
        )
    
    def _map_github_user_data(self, user_data: dict[str, Any]) -> User:
        """Map GitHub user data to User object."""
        user_id = f"oauth:github:{user_data['id']}"
        
        return User(
            user_id=user_id,
            username=user_data.get("login"),
            email=user_data.get("email"),
            roles=["user"],  # Default role
            permissions=["read:profile"],  # Default permissions
            metadata={
                "provider": "oauth",
                "oauth_provider": "github",
                "oauth_id": str(user_data["id"]),
                "github_login": user_data.get("login"),
                "full_name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url")
            }
        )
    
    def _map_generic_user_data(self, provider_name: str, user_data: dict[str, Any]) -> User:
        """Map generic OAuth user data to User object."""
        # Try to extract common fields
        user_id_field = user_data.get("id") or user_data.get("user_id") or user_data.get("sub")
        if not user_id_field:
            raise AuthenticationError("OAuth user data missing required 'id' field")
        
        user_id = f"oauth:{provider_name}:{user_id_field}"
        
        return User(
            user_id=user_id,
            username=user_data.get("username") or user_data.get("login") or user_data.get("email"),
            email=user_data.get("email"),
            roles=["user"],
            permissions=["read:profile"],
            metadata={
                "provider": "oauth",
                "oauth_provider": provider_name,
                "oauth_id": str(user_id_field),
                "full_name": user_data.get("name") or user_data.get("display_name"),
                "avatar_url": user_data.get("avatar_url") or user_data.get("picture"),
                "raw_data": user_data  # Store raw data for debugging
            }
        )
    
    async def authenticate(self, request: Request) -> User | None:
        """
        Authenticate user via OAuth callback.
        
        Args:
            request: Request object with OAuth callback parameters
            
        Returns:
            User object if authentication successful, None otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Check for OAuth callback parameters
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        
        if not code:
            return None  # Not an OAuth callback
        
        # Validate state parameter using cryptographic validation
        if not self.validate_state(state):
            raise AuthenticationError("Invalid OAuth state parameter")
        
        # Get stored OAuth parameters
        code_verifier = getattr(request, "session", {}).get("oauth_code_verifier")
        provider_name = getattr(request, "session", {}).get("oauth_provider")
        
        if not code_verifier or not provider_name:
            raise AuthenticationError("Missing OAuth session data")
        
        try:
            # Exchange code for token
            token_response = await self.exchange_code_for_token(
                provider_name, code, code_verifier
            )
            
            # Get user information
            access_token = token_response["access_token"]
            user_data = await self.get_user_info(provider_name, access_token)
            
            # Map to User object
            user = self.map_user_data(provider_name, user_data)
            
            # Store token information in user metadata
            user.metadata.update({
                "access_token": access_token,
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in"),
                "refresh_token": token_response.get("refresh_token")
            })
            
            return user
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"OAuth authentication failed: {str(e)}")
    
    async def login(
        self,
        request: Request,
        username: str,
        password: str
    ) -> tuple[User, dict[str, Any]]:
        """
        OAuth doesn't use username/password login.
        
        Raises:
            AuthenticationError: Always, as OAuth uses authorization flow
        """
        raise AuthenticationError("OAuth provider uses authorization flow, not username/password")
    
    async def logout(
        self,
        request: Request,
        user: User
    ) -> dict[str, Any]:
        """
        Logout OAuth user.
        
        Args:
            request: Request object
            user: User to logout
            
        Returns:
            Logout response data
        """
        # Clear OAuth session data
        if hasattr(request, "session"):
            session_keys = [
                "oauth_state", "oauth_code_verifier", "oauth_provider",
                "oauth_access_token", "oauth_refresh_token"
            ]
            for key in session_keys:
                request.session.pop(key, None)
        
        return {
            "message": "OAuth logout successful",
            "provider": user.metadata.get("oauth_provider")
        }
    
    def validate_config(self) -> list[str]:
        """
        Validate OAuth provider configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.providers:
            errors.append("At least one OAuth provider must be configured")
            return errors
        
        # Validate each provider
        for provider_name, provider_config in self.providers.items():
            if not provider_config.get("client_id"):
                errors.append(f"OAuth provider '{provider_name}' missing client_id")
            
            if not provider_config.get("client_secret"):
                errors.append(f"OAuth provider '{provider_name}' missing client_secret")
            
            # Validate required URLs
            required_urls = ["authorization_url", "token_url", "user_info_url"]
            for url_key in required_urls:
                if not provider_config.get(url_key):
                    errors.append(f"OAuth provider '{provider_name}' missing {url_key}")
        
        # Validate redirect URI
        if not self.redirect_uri:
            errors.append("OAuth redirect_uri must be configured")
        
        # Validate state secret
        if not self.state_secret or len(self.state_secret) < 16:
            errors.append("OAuth state_secret must be at least 16 characters")
        
        return errors