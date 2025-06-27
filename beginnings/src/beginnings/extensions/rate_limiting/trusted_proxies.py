"""
Trusted proxy management for rate limiting extension.

This module provides IP address validation and trusted proxy management
to prevent IP spoofing in rate limiting scenarios.
"""

from __future__ import annotations

import ipaddress
import pathlib
from typing import Any


class TrustedProxyManager:
    """
    Trusted proxy manager for IP validation.
    
    Manages trusted proxy lists and validates forwarded IP addresses
    to prevent IP spoofing attacks in rate limiting.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize trusted proxy manager.
        
        Args:
            config: Trusted proxy configuration dictionary
        """
        self.enabled = config.get("enabled", True)
        self.trusted_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        
        # Validation settings
        self.allow_localhost = config.get("allow_localhost", True)
        self.allow_private_networks = config.get("allow_private_networks", True)
        self.strict_validation = config.get("strict_validation", False)
        
        # Load trusted proxies from configuration
        self._load_trusted_proxies(config)
    
    def _load_trusted_proxies(self, config: dict[str, Any]) -> None:
        """Load trusted proxy networks from configuration."""
        # Load from list in config
        trusted_proxies = config.get("trusted_proxies", [])
        for proxy in trusted_proxies:
            try:
                network = ipaddress.ip_network(proxy, strict=False)
                self.trusted_networks.append(network)
            except ValueError as e:
                raise ValueError(f"Invalid trusted proxy network '{proxy}': {e}")
        
        # Load from file if specified
        proxy_file = config.get("trusted_proxies_file")
        if proxy_file:
            self._load_from_file(proxy_file)
        
        # Add default trusted networks if enabled
        if self.allow_localhost:
            self.trusted_networks.extend([
                ipaddress.ip_network("127.0.0.0/8"),
                ipaddress.ip_network("::1/128")
            ])
        
        if self.allow_private_networks:
            self.trusted_networks.extend([
                ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("172.16.0.0/12"),
                ipaddress.ip_network("192.168.0.0/16"),
                ipaddress.ip_network("fc00::/7")
            ])
    
    def _load_from_file(self, file_path: str) -> None:
        """Load trusted proxy networks from a file."""
        try:
            path = pathlib.Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Trusted proxies file not found: {file_path}")
            
            with path.open("r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue
                    
                    try:
                        network = ipaddress.ip_network(line, strict=False)
                        self.trusted_networks.append(network)
                    except ValueError as e:
                        raise ValueError(f"Invalid network at line {line_num} in {file_path}: {e}")
        
        except Exception as e:
            raise ValueError(f"Failed to load trusted proxies file '{file_path}': {e}")
    
    def is_trusted_proxy(self, ip_address: str) -> bool:
        """
        Check if an IP address is a trusted proxy.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if the IP is a trusted proxy
        """
        if not self.enabled:
            return False
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            for network in self.trusted_networks:
                if ip in network:
                    return True
            
            return False
        
        except ValueError:
            # Invalid IP address
            return False
    
    def extract_real_ip(self, remote_addr: str, forwarded_for: str | None = None, real_ip: str | None = None) -> str:
        """
        Extract the real client IP address with proxy validation.
        
        Args:
            remote_addr: Direct connection IP address
            forwarded_for: X-Forwarded-For header value
            real_ip: X-Real-IP header value
            
        Returns:
            Validated real IP address
        """
        if not self.enabled or not self.is_trusted_proxy(remote_addr):
            # No trusted proxy or proxy not trusted, use remote address
            return self._normalize_ip(remote_addr)
        
        # Check X-Real-IP first (simpler, single IP)
        if real_ip:
            normalized_ip = self._normalize_ip(real_ip.strip())
            if self._validate_forwarded_ip(normalized_ip):
                return normalized_ip
        
        # Check X-Forwarded-For (may contain multiple IPs)
        if forwarded_for:
            # Get the leftmost (original client) IP
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            if ips:
                normalized_ip = self._normalize_ip(ips[0])
                if self._validate_forwarded_ip(normalized_ip):
                    return normalized_ip
        
        # Fall back to remote address if forwarded headers are invalid
        return self._normalize_ip(remote_addr)
    
    def _normalize_ip(self, ip_string: str) -> str:
        """Normalize IP address string."""
        try:
            # Parse and normalize the IP address
            ip = ipaddress.ip_address(ip_string.strip())
            return str(ip)
        except ValueError:
            # Invalid IP, return original string
            return ip_string.strip()
    
    def _validate_forwarded_ip(self, ip_string: str) -> bool:
        """Validate a forwarded IP address."""
        try:
            ip = ipaddress.ip_address(ip_string)
            
            if self.strict_validation:
                # In strict mode, reject private IPs in forwarded headers
                return not ip.is_private and not ip.is_loopback
            else:
                # In non-strict mode, accept all valid IPs
                return True
        
        except ValueError:
            # Invalid IP address
            return False
    
    def get_trusted_networks(self) -> list[str]:
        """
        Get list of trusted network strings.
        
        Returns:
            List of trusted network CIDR strings
        """
        return [str(network) for network in self.trusted_networks]
    
    def validate_config(self) -> list[str]:
        """
        Validate trusted proxy configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if self.enabled and not self.trusted_networks:
            errors.append("No trusted proxy networks configured")
        
        return errors