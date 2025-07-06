"""Documentation search functionality.

This module provides fast search indexing and retrieval for documentation
content with ranking, filtering, and faceted search capabilities.
"""

from .search_engine import (
    DocumentationSearchEngine,
    SearchDocument,
    SearchResult,
    SearchQuery,
    SearchResponse,
    SearchResultType
)

__all__ = [
    'DocumentationSearchEngine',
    'SearchDocument',
    'SearchResult',
    'SearchQuery',
    'SearchResponse',
    'SearchResultType',
]