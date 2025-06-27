"""
Authentication providers for different authentication mechanisms.

This module contains the various authentication providers that can be used
with the authentication extension.
"""

from beginnings.extensions.auth.providers.base import BaseAuthProvider
from beginnings.extensions.auth.providers.jwt_provider import JWTProvider
from beginnings.extensions.auth.providers.session_provider import SessionProvider

__all__ = ["BaseAuthProvider", "JWTProvider", "SessionProvider"]