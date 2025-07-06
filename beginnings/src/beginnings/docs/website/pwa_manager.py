"""Progressive Web App manager for documentation.

This module provides PWA functionality including service workers,
offline support, and app manifests. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum


class CacheStrategy(Enum):
    """Caching strategies for different resource types."""
    CACHE_FIRST = "cache_first"
    NETWORK_FIRST = "network_first"
    STALE_WHILE_REVALIDATE = "stale_while_revalidate"
    NETWORK_ONLY = "network_only"
    CACHE_ONLY = "cache_only"


@dataclass
class PWAConfig:
    """Configuration for Progressive Web App features."""
    
    name: str
    short_name: str
    description: str = ""
    theme_color: str = "#2563eb"
    background_color: str = "#ffffff"
    display: str = "standalone"
    orientation: str = "portrait-primary"
    start_url: str = "/"
    scope: str = "/"
    icons: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[str] = field(default_factory=lambda: ["productivity", "education"])
    lang: str = "en"
    dir: str = "ltr"
    offline_fallback: str = "/offline.html"
    cache_strategy: CacheStrategy = CacheStrategy.STALE_WHILE_REVALIDATE
    

@dataclass
class ServiceWorkerConfig:
    """Configuration for service worker."""
    
    cache_name: str = "docs-cache-v1"
    precache_urls: List[str] = field(default_factory=list)
    runtime_cache_patterns: List[Dict[str, Any]] = field(default_factory=list)
    offline_fallbacks: Dict[str, str] = field(default_factory=dict)
    update_strategy: str = "immediate"
    max_cache_size: int = 50  # MB
    cache_expiry_hours: int = 24


@dataclass
class PWAGenerationResult:
    """Result of PWA generation."""
    
    success: bool
    manifest_generated: bool = False
    service_worker_generated: bool = False
    offline_page_generated: bool = False
    icons_generated: int = 0
    cache_urls: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ManifestGenerator:
    """Generates web app manifest.
    
    Follows Single Responsibility Principle - only handles manifest generation.
    """
    
    def __init__(self, config: PWAConfig):
        """Initialize manifest generator.
        
        Args:
            config: PWA configuration
        """
        self.config = config
    
    def generate_manifest(self, output_dir: Path) -> bool:
        """Generate web app manifest file.
        
        Args:
            output_dir: Directory to save manifest
            
        Returns:
            True if generated successfully
        """
        try:
            manifest = {
                "name": self.config.name,
                "short_name": self.config.short_name,
                "description": self.config.description,
                "start_url": self.config.start_url,
                "scope": self.config.scope,
                "display": self.config.display,
                "orientation": self.config.orientation,
                "theme_color": self.config.theme_color,
                "background_color": self.config.background_color,
                "lang": self.config.lang,
                "dir": self.config.dir,
                "categories": self.config.categories,
                "icons": self.config.icons
            }
            
            manifest_path = output_dir / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def generate_default_icons(self, output_dir: Path) -> int:
        """Generate default PWA icons.
        
        Args:
            output_dir: Directory to save icons
            
        Returns:
            Number of icons generated
        """
        # In a real implementation, this would generate actual icon files
        # For now, we'll create placeholder icon configurations
        
        icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
        icons_generated = 0
        
        icons_dir = output_dir / "icons"
        icons_dir.mkdir(exist_ok=True)
        
        for size in icon_sizes:
            icon_config = {
                "src": f"/icons/icon-{size}x{size}.png",
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "any maskable"
            }
            
            self.config.icons.append(icon_config)
            
            # Create placeholder icon file (1x1 PNG)
            icon_path = icons_dir / f"icon-{size}x{size}.png"
            if not icon_path.exists():
                # Minimal PNG header for 1x1 transparent pixel
                png_data = bytes.fromhex(
                    '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4'
                    '890000000a4944415478da6364f8006201000007000208e737003d000000004945'
                    '4e44ae426082'
                )
                icon_path.write_bytes(png_data)
                icons_generated += 1
        
        return icons_generated


class ServiceWorkerGenerator:
    """Generates service worker for offline functionality.
    
    Follows Single Responsibility Principle - only handles service worker generation.
    """
    
    def __init__(self, config: ServiceWorkerConfig):
        """Initialize service worker generator.
        
        Args:
            config: Service worker configuration
        """
        self.config = config
    
    def generate_service_worker(self, output_dir: Path, site_urls: List[str]) -> bool:
        """Generate service worker file.
        
        Args:
            output_dir: Directory to save service worker
            site_urls: List of URLs to precache
            
        Returns:
            True if generated successfully
        """
        try:
            # Generate cache version hash based on URLs
            cache_hash = hashlib.md5(''.join(sorted(site_urls)).encode()).hexdigest()[:8]
            cache_name = f"{self.config.cache_name}-{cache_hash}"
            
            sw_content = self._generate_sw_content(cache_name, site_urls)
            
            sw_path = output_dir / "sw.js"
            sw_path.write_text(sw_content, encoding='utf-8')
            
            return True
        except Exception:
            return False
    
    def _generate_sw_content(self, cache_name: str, urls: List[str]) -> str:
        """Generate service worker JavaScript content."""
        precache_urls = json.dumps(urls)
        
        return f"""
// Documentation Site Service Worker
// Generated automatically - do not edit manually

const CACHE_NAME = '{cache_name}';
const OFFLINE_FALLBACK = '{self.config.offline_fallbacks.get("document", "/offline.html")}';
const MAX_CACHE_SIZE = {self.config.max_cache_size} * 1024 * 1024; // {self.config.max_cache_size}MB
const CACHE_EXPIRY_MS = {self.config.cache_expiry_hours} * 60 * 60 * 1000; // {self.config.cache_expiry_hours} hours

// URLs to precache
const PRECACHE_URLS = {precache_urls};

// Install event - precache resources
self.addEventListener('install', event => {{
    console.log('[SW] Installing service worker');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {{
                console.log('[SW] Precaching', PRECACHE_URLS.length, 'resources');
                return cache.addAll(PRECACHE_URLS);
            }})
            .then(() => {{
                console.log('[SW] Installation complete');
                {'self.skipWaiting();' if self.config.update_strategy == 'immediate' else ''}
            }})
            .catch(error => {{
                console.error('[SW] Installation failed:', error);
            }})
    );
}});

// Activate event - clean up old caches
self.addEventListener('activate', event => {{
    console.log('[SW] Activating service worker');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {{
                return Promise.all(
                    cacheNames
                        .filter(name => name.startsWith('{self.config.cache_name.split('-')[0]}') && name !== CACHE_NAME)
                        .map(name => {{
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        }})
                );
            }})
            .then(() => {{
                console.log('[SW] Activation complete');
                {'return self.clients.claim();' if self.config.update_strategy == 'immediate' else ''}
            }})
            .catch(error => {{
                console.error('[SW] Activation failed:', error);
            }})
    );
}});

// Fetch event - serve from cache with fallbacks
self.addEventListener('fetch', event => {{
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests and external URLs
    if (request.method !== 'GET' || !url.origin.includes(self.location.origin)) {{
        return;
    }}
    
    // Handle navigation requests (documents)
    if (request.mode === 'navigate') {{
        event.respondWith(
            fetch(request)
                .then(response => {{
                    // Cache successful navigation responses
                    if (response.ok) {{
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => cache.put(request, responseClone));
                    }}
                    return response;
                }})
                .catch(() => {{
                    // Serve from cache or offline fallback
                    return caches.match(request)
                        .then(response => response || caches.match(OFFLINE_FALLBACK))
                        .then(response => response || new Response('Offline', {{
                            status: 503,
                            statusText: 'Service Unavailable'
                        }}));
                }})
        );
        return;
    }}
    
    // Handle other requests with stale-while-revalidate strategy
    event.respondWith(
        caches.match(request)
            .then(cachedResponse => {{
                const fetchPromise = fetch(request)
                    .then(networkResponse => {{
                        // Cache successful responses
                        if (networkResponse.ok) {{
                            const responseClone = networkResponse.clone();
                            caches.open(CACHE_NAME)
                                .then(cache => {{
                                    cache.put(request, responseClone);
                                    // Clean up cache if it gets too large
                                    cleanupCache(cache);
                                }});
                        }}
                        return networkResponse;
                    }})
                    .catch(() => {{
                        // Return cached version on network failure
                        return cachedResponse;
                    }});
                
                // Return cached version immediately if available
                return cachedResponse || fetchPromise;
            }})
    );
}});

// Cleanup cache to maintain size limits
async function cleanupCache(cache) {{
    try {{
        const requests = await cache.keys();
        let totalSize = 0;
        const sizePromises = requests.map(async request => {{
            const response = await cache.match(request);
            const size = response ? (await response.blob()).size : 0;
            return {{ request, size }};
        }});
        
        const requestSizes = await Promise.all(sizePromises);
        totalSize = requestSizes.reduce((sum, item) => sum + item.size, 0);
        
        if (totalSize > MAX_CACHE_SIZE) {{
            console.log('[SW] Cache cleanup needed, current size:', totalSize);
            
            // Sort by last access time (simplified - just remove oldest entries)
            const toDelete = requestSizes
                .slice(0, Math.floor(requestSizes.length * 0.1)) // Remove 10% of entries
                .map(item => item.request);
            
            await Promise.all(toDelete.map(request => cache.delete(request)));
            console.log('[SW] Cleaned up', toDelete.length, 'cache entries');
        }}
    }} catch (error) {{
        console.error('[SW] Cache cleanup failed:', error);
    }}
}}

// Background sync for analytics and updates
self.addEventListener('sync', event => {{
    if (event.tag === 'docs-analytics') {{
        event.waitUntil(syncAnalytics());
    }}
}});

async function syncAnalytics() {{
    try {{
        // Sync any pending analytics data
        console.log('[SW] Syncing analytics data');
    }} catch (error) {{
        console.error('[SW] Analytics sync failed:', error);
    }}
}}

// Message handling for cache updates
self.addEventListener('message', event => {{
    if (event.data && event.data.type === 'CACHE_UPDATE') {{
        event.waitUntil(updateCache(event.data.urls));
    }}
}});

async function updateCache(urls) {{
    try {{
        const cache = await caches.open(CACHE_NAME);
        await cache.addAll(urls);
        console.log('[SW] Cache updated with', urls.length, 'new URLs');
    }} catch (error) {{
        console.error('[SW] Cache update failed:', error);
    }}
}}

console.log('[SW] Service worker loaded');
"""


class OfflinePageGenerator:
    """Generates offline fallback page.
    
    Follows Single Responsibility Principle - only handles offline page generation.
    """
    
    def __init__(self, pwa_config: PWAConfig):
        """Initialize offline page generator.
        
        Args:
            pwa_config: PWA configuration
        """
        self.config = pwa_config
    
    def generate_offline_page(self, output_dir: Path) -> bool:
        """Generate offline fallback page.
        
        Args:
            output_dir: Directory to save offline page
            
        Returns:
            True if generated successfully
        """
        try:
            offline_html = self._generate_offline_html()
            
            offline_path = output_dir / "offline.html"
            offline_path.write_text(offline_html, encoding='utf-8')
            
            return True
        except Exception:
            return False
    
    def _generate_offline_html(self) -> str:
        """Generate offline page HTML content."""
        return f"""
        <!DOCTYPE html>
        <html lang="{self.config.lang}" dir="{self.config.dir}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - {self.config.name}</title>
            <meta name="description" content="You are currently offline">
            <meta name="theme-color" content="{self.config.theme_color}">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: {self.config.background_color};
                    color: #374151;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    text-align: center;
                }}
                
                .offline-container {{
                    max-width: 400px;
                    padding: 2rem;
                }}
                
                .offline-icon {{
                    width: 64px;
                    height: 64px;
                    margin: 0 auto 1.5rem;
                    background: {self.config.theme_color};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 2rem;
                }}
                
                h1 {{
                    margin: 0 0 1rem;
                    font-size: 1.5rem;
                    color: #1f2937;
                }}
                
                p {{
                    margin: 0 0 1.5rem;
                    line-height: 1.5;
                    color: #6b7280;
                }}
                
                .retry-btn {{
                    background: {self.config.theme_color};
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 6px;
                    font-size: 1rem;
                    cursor: pointer;
                    transition: background-color 0.2s;
                }}
                
                .retry-btn:hover {{
                    opacity: 0.9;
                }}
                
                .cache-status {{
                    margin-top: 2rem;
                    padding: 1rem;
                    background: #f9fafb;
                    border-radius: 6px;
                    font-size: 0.875rem;
                    color: #6b7280;
                }}
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="offline-icon">📱</div>
                <h1>You're offline</h1>
                <p>It looks like you've lost your internet connection. Some content may not be available, but you can still browse cached pages.</p>
                
                <button class="retry-btn" onclick="window.location.reload()">Try Again</button>
                
                <div class="cache-status">
                    <p><strong>Cached content available:</strong></p>
                    <ul id="cached-pages" style="text-align: left; padding-left: 1rem;"></ul>
                </div>
            </div>
            
            <script>
                // List available cached pages
                if ('caches' in window) {{
                    caches.keys().then(cacheNames => {{
                        return Promise.all(
                            cacheNames.map(name => caches.open(name).then(cache => cache.keys()))
                        );
                    }}).then(allRequests => {{
                        const cachedUrls = allRequests
                            .flat()
                            .map(request => request.url)
                            .filter(url => url.includes(location.origin) && !url.includes('sw.js'))
                            .slice(0, 10); // Show first 10
                        
                        const pagesList = document.getElementById('cached-pages');
                        if (cachedUrls.length > 0) {{
                            pagesList.innerHTML = cachedUrls
                                .map(url => {{
                                    const path = new URL(url).pathname;
                                    return `<li><a href="${{url}}" style="color: {self.config.theme_color};">${{path}}</a></li>`;
                                }})
                                .join('');
                        }} else {{
                            pagesList.innerHTML = '<li>No cached pages available</li>';
                        }}
                    }}).catch(() => {{
                        document.getElementById('cached-pages').innerHTML = '<li>Cache not available</li>';
                    }});
                }}
                
                // Check for connection restoration
                window.addEventListener('online', () => {{
                    document.querySelector('.offline-container').innerHTML = `
                        <div class="offline-icon">✅</div>
                        <h1>Back online!</h1>
                        <p>Your connection has been restored.</p>
                        <button class="retry-btn" onclick="window.location.reload()">Reload Page</button>
                    `;
                }});
            </script>
        </body>
        </html>
        """


class PWAManager:
    """Manages Progressive Web App features for documentation site.
    
    Follows Single Responsibility Principle - orchestrates PWA generation.
    Uses Dependency Inversion - depends on generator abstractions.
    """
    
    def __init__(self, pwa_config: PWAConfig, sw_config: Optional[ServiceWorkerConfig] = None):
        """Initialize PWA manager.
        
        Args:
            pwa_config: PWA configuration
            sw_config: Service worker configuration
        """
        self.pwa_config = pwa_config
        self.sw_config = sw_config or ServiceWorkerConfig()
        
        self.manifest_generator = ManifestGenerator(pwa_config)
        self.sw_generator = ServiceWorkerGenerator(self.sw_config)
        self.offline_generator = OfflinePageGenerator(pwa_config)
    
    def generate_pwa_files(self, output_dir: Path, site_urls: List[str]) -> PWAGenerationResult:
        """Generate all PWA files.
        
        Args:
            output_dir: Directory to save PWA files
            site_urls: List of site URLs for caching
            
        Returns:
            Generation result with statistics
        """
        result = PWAGenerationResult(success=True)
        
        try:
            # Generate web app manifest
            if self.manifest_generator.generate_manifest(output_dir):
                result.manifest_generated = True
            else:
                result.errors.append("Failed to generate web app manifest")
            
            # Generate default icons if none provided
            if not self.pwa_config.icons:
                icons_generated = self.manifest_generator.generate_default_icons(output_dir)
                result.icons_generated = icons_generated
                if icons_generated == 0:
                    result.warnings.append("No icons generated")
            
            # Generate service worker
            if self.sw_generator.generate_service_worker(output_dir, site_urls):
                result.service_worker_generated = True
                result.cache_urls = len(site_urls)
            else:
                result.errors.append("Failed to generate service worker")
            
            # Generate offline fallback page
            if self.offline_generator.generate_offline_page(output_dir):
                result.offline_page_generated = True
            else:
                result.errors.append("Failed to generate offline page")
            
            # Generate PWA registration script
            self._generate_pwa_registration(output_dir)
            
            if result.errors:
                result.success = len(result.errors) < 3  # Allow some failures
            
        except Exception as e:
            result.success = False
            result.errors.append(f"PWA generation failed: {str(e)}")
        
        return result
    
    def _generate_pwa_registration(self, output_dir: Path) -> None:
        """Generate PWA registration JavaScript."""
        registration_js = f"""
        // PWA Registration Script
        // Registers service worker and handles PWA installation
        
        class PWAManager {{
            constructor() {{
                this.deferredPrompt = null;
                this.init();
            }}
            
            async init() {{
                // Register service worker
                if ('serviceWorker' in navigator) {{
                    try {{
                        const registration = await navigator.serviceWorker.register('/sw.js');
                        console.log('SW registered:', registration);
                        
                        // Handle updates
                        registration.addEventListener('updatefound', () => {{
                            this.handleServiceWorkerUpdate(registration);
                        }});
                    }} catch (error) {{
                        console.error('SW registration failed:', error);
                    }}
                }}
                
                // Handle install prompt
                window.addEventListener('beforeinstallprompt', (e) => {{
                    e.preventDefault();
                    this.deferredPrompt = e;
                    this.showInstallButton();
                }});
                
                // Handle successful installation
                window.addEventListener('appinstalled', () => {{
                    console.log('PWA installed successfully');
                    this.hideInstallButton();
                }});
                
                // Handle online/offline status
                window.addEventListener('online', () => this.handleOnlineStatus(true));
                window.addEventListener('offline', () => this.handleOnlineStatus(false));
            }}
            
            handleServiceWorkerUpdate(registration) {{
                const newWorker = registration.installing;
                if (newWorker) {{
                    newWorker.addEventListener('statechange', () => {{
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {{
                            this.showUpdateAvailable();
                        }}
                    }});
                }}
            }}
            
            showInstallButton() {{
                const installBtn = document.getElementById('pwa-install-btn');
                if (installBtn) {{
                    installBtn.style.display = 'block';
                    installBtn.addEventListener('click', () => this.installPWA());
                }}
            }}
            
            hideInstallButton() {{
                const installBtn = document.getElementById('pwa-install-btn');
                if (installBtn) {{
                    installBtn.style.display = 'none';
                }}
            }}
            
            async installPWA() {{
                if (this.deferredPrompt) {{
                    this.deferredPrompt.prompt();
                    const result = await this.deferredPrompt.userChoice;
                    console.log('Install prompt result:', result.outcome);
                    this.deferredPrompt = null;
                    this.hideInstallButton();
                }}
            }}
            
            showUpdateAvailable() {{
                const updateNotification = document.createElement('div');
                updateNotification.id = 'update-notification';
                updateNotification.innerHTML = `
                    <div style="position: fixed; top: 20px; right: 20px; background: {self.pwa_config.theme_color}; color: white; padding: 1rem; border-radius: 6px; z-index: 1000; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <p style="margin: 0 0 0.5rem;">New version available!</p>
                        <button onclick="location.reload()" style="background: white; color: {self.pwa_config.theme_color}; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer;">Update</button>
                        <button onclick="this.parentElement.remove()" style="background: transparent; color: white; border: 1px solid white; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin-left: 0.5rem;">Later</button>
                    </div>
                `;
                document.body.appendChild(updateNotification);
                
                // Auto-remove after 10 seconds
                setTimeout(() => {{
                    if (updateNotification.parentElement) {{
                        updateNotification.remove();
                    }}
                }}, 10000);
            }}
            
            handleOnlineStatus(isOnline) {{
                const statusIndicator = document.getElementById('connection-status');
                if (statusIndicator) {{
                    statusIndicator.textContent = isOnline ? 'Online' : 'Offline';
                    statusIndicator.className = isOnline ? 'status-online' : 'status-offline';
                }}
                
                if (isOnline) {{
                    // Sync any pending data when back online
                    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {{
                        navigator.serviceWorker.controller.postMessage({{
                            type: 'SYNC_PENDING_DATA'
                        }});
                    }}
                }}
            }}
        }}
        
        // Initialize PWA manager when DOM is ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', () => new PWAManager());
        }} else {{
            new PWAManager();
        }}
        """
        
        registration_path = output_dir / "pwa.js"
        registration_path.write_text(registration_js, encoding='utf-8')
    
    def update_html_for_pwa(self, html_content: str) -> str:
        """Update HTML content to include PWA features.
        
        Args:
            html_content: Original HTML content
            
        Returns:
            Updated HTML with PWA features
        """
        # Add PWA meta tags and links
        pwa_tags = f"""
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="{self.pwa_config.theme_color}">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="default">
        <meta name="apple-mobile-web-app-title" content="{self.pwa_config.short_name}">
        <script src="/pwa.js" defer></script>
        """
        
        # Insert PWA tags before closing head tag
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', f'{pwa_tags}\n</head>')
        
        return html_content