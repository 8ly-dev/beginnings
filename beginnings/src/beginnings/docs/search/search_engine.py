"""Documentation search engine with indexing and retrieval.

This module provides fast search functionality for documentation content
with ranking, filtering, and faceted search. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import json
import re
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum
from collections import defaultdict, Counter


class SearchResultType(Enum):
    """Types of search results."""
    PAGE = "page"
    SECTION = "section"
    CODE_EXAMPLE = "code_example"
    API_REFERENCE = "api_reference"


@dataclass
class SearchDocument:
    """Document for search indexing."""
    
    id: str
    title: str
    content: str
    url: str
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    result_type: SearchResultType = SearchResultType.PAGE
    sections: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    last_modified: Optional[str] = None


@dataclass
class SearchResult:
    """Individual search result."""
    
    document_id: str
    title: str
    url: str
    snippet: str
    score: float
    result_type: SearchResultType
    category: str = ""
    tags: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchQuery:
    """Search query configuration."""
    
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    facets: List[str] = field(default_factory=list)
    page: int = 1
    per_page: int = 20
    highlight: bool = True
    include_sections: bool = True
    boost_title: float = 2.0
    boost_recent: bool = True


@dataclass
class SearchResponse:
    """Search response with results and metadata."""
    
    results: List[SearchResult]
    total_results: int
    page: int
    per_page: int
    total_pages: int
    query_time_ms: float
    facets: Dict[str, List[Tuple[str, int]]] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    query: str = ""


class TextProcessor:
    """Processes text for search indexing.
    
    Follows Single Responsibility Principle - only handles text processing.
    """
    
    def __init__(self):
        """Initialize text processor."""
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'said', 'each', 'which', 'their', 'time', 'if',
            'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her',
            'would', 'make', 'like', 'into', 'him', 'has', 'two', 'more',
            'very', 'after', 'words', 'not', 'way', 'could', 'my', 'than',
            'first', 'been', 'call', 'who', 'its', 'now', 'find', 'long',
            'down', 'day', 'did', 'get', 'come', 'made', 'may', 'part'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        tokens = [word for word in words if len(word) > 2 and word not in self.stop_words]
        
        return tokens
    
    def extract_phrases(self, text: str, min_length: int = 2, max_length: int = 4) -> List[str]:
        """Extract meaningful phrases from text.
        
        Args:
            text: Text to process
            min_length: Minimum phrase length
            max_length: Maximum phrase length
            
        Returns:
            List of phrases
        """
        tokens = self.tokenize(text)
        phrases = []
        
        for length in range(min_length, max_length + 1):
            for i in range(len(tokens) - length + 1):
                phrase = ' '.join(tokens[i:i + length])
                phrases.append(phrase)
        
        return phrases
    
    def stem_word(self, word: str) -> str:
        """Simple word stemming.
        
        Args:
            word: Word to stem
            
        Returns:
            Stemmed word
        """
        # Very basic stemming - remove common suffixes
        suffixes = ['ing', 'ed', 'er', 'est', 'ly', 's']
        
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        
        return word
    
    def calculate_tf_idf(self, documents: List[SearchDocument]) -> Dict[str, Dict[str, float]]:
        """Calculate TF-IDF scores for documents.
        
        Args:
            documents: List of documents
            
        Returns:
            TF-IDF scores by document and term
        """
        # Calculate term frequencies
        tf_scores = {}
        df_counts = defaultdict(int)
        
        for doc in documents:
            tokens = self.tokenize(doc.content + ' ' + doc.title)
            token_counts = Counter(tokens)
            total_tokens = len(tokens)
            
            tf_scores[doc.id] = {}
            for token, count in token_counts.items():
                tf_scores[doc.id][token] = count / total_tokens
                df_counts[token] += 1
        
        # Calculate TF-IDF
        total_docs = len(documents)
        tfidf_scores = {}
        
        for doc_id, tf_dict in tf_scores.items():
            tfidf_scores[doc_id] = {}
            for term, tf in tf_dict.items():
                idf = math.log(total_docs / df_counts[term])
                tfidf_scores[doc_id][term] = tf * idf
        
        return tfidf_scores


class SearchIndex:
    """In-memory search index.
    
    Follows Single Responsibility Principle - only handles index operations.
    """
    
    def __init__(self):
        """Initialize search index."""
        self.documents = {}
        self.inverted_index = defaultdict(set)
        self.phrase_index = defaultdict(set)
        self.tfidf_scores = {}
        self.text_processor = TextProcessor()
    
    def add_document(self, document: SearchDocument) -> None:
        """Add document to search index.
        
        Args:
            document: Document to index
        """
        self.documents[document.id] = document
        
        # Index content
        content_tokens = self.text_processor.tokenize(document.content)
        title_tokens = self.text_processor.tokenize(document.title)
        
        # Add to inverted index
        for token in content_tokens + title_tokens:
            self.inverted_index[token].add(document.id)
        
        # Index phrases
        phrases = self.text_processor.extract_phrases(document.content)
        for phrase in phrases:
            self.phrase_index[phrase].add(document.id)
        
        # Index metadata
        for tag in document.tags:
            tag_tokens = self.text_processor.tokenize(tag)
            for token in tag_tokens:
                self.inverted_index[token].add(document.id)
    
    def remove_document(self, document_id: str) -> bool:
        """Remove document from index.
        
        Args:
            document_id: ID of document to remove
            
        Returns:
            True if document was removed
        """
        if document_id not in self.documents:
            return False
        
        # Remove from inverted index
        for token_set in self.inverted_index.values():
            token_set.discard(document_id)
        
        # Remove from phrase index
        for phrase_set in self.phrase_index.values():
            phrase_set.discard(document_id)
        
        # Remove document
        del self.documents[document_id]
        
        # Remove from TF-IDF scores
        if document_id in self.tfidf_scores:
            del self.tfidf_scores[document_id]
        
        return True
    
    def update_tfidf_scores(self) -> None:
        """Update TF-IDF scores for all documents."""
        documents = list(self.documents.values())
        self.tfidf_scores = self.text_processor.calculate_tf_idf(documents)
    
    def search_tokens(self, tokens: List[str]) -> Set[str]:
        """Search for documents containing tokens.
        
        Args:
            tokens: List of search tokens
            
        Returns:
            Set of matching document IDs
        """
        if not tokens:
            return set()
        
        # Find documents containing all tokens (AND search)
        result_sets = []
        for token in tokens:
            token_docs = set()
            
            # Exact match
            if token in self.inverted_index:
                token_docs.update(self.inverted_index[token])
            
            # Stemmed match
            stemmed = self.text_processor.stem_word(token)
            if stemmed != token and stemmed in self.inverted_index:
                token_docs.update(self.inverted_index[stemmed])
            
            # Partial match for longer tokens
            if len(token) > 4:
                for indexed_token in self.inverted_index:
                    if token in indexed_token or indexed_token in token:
                        token_docs.update(self.inverted_index[indexed_token])
            
            result_sets.append(token_docs)
        
        # Intersection of all sets
        if result_sets:
            return set.intersection(*result_sets)
        
        return set()
    
    def search_phrases(self, query: str) -> Set[str]:
        """Search for documents containing phrases.
        
        Args:
            query: Search query
            
        Returns:
            Set of matching document IDs
        """
        # Extract phrases from query
        phrases = self.text_processor.extract_phrases(query)
        
        matching_docs = set()
        for phrase in phrases:
            if phrase in self.phrase_index:
                matching_docs.update(self.phrase_index[phrase])
        
        return matching_docs
    
    def get_document_count(self) -> int:
        """Get total number of indexed documents.
        
        Returns:
            Number of documents
        """
        return len(self.documents)


class DocumentationSearchEngine:
    """Search engine for documentation content.
    
    Follows Single Responsibility Principle - orchestrates search operations.
    Uses Dependency Inversion - depends on index and processor abstractions.
    """
    
    def __init__(self):
        """Initialize search engine."""
        self.index = SearchIndex()
        self.text_processor = TextProcessor()
    
    def index_documents(self, documents: List[SearchDocument]) -> int:
        """Index multiple documents.
        
        Args:
            documents: List of documents to index
            
        Returns:
            Number of documents indexed
        """
        indexed_count = 0
        
        for document in documents:
            self.index.add_document(document)
            indexed_count += 1
        
        # Update TF-IDF scores after indexing
        self.index.update_tfidf_scores()
        
        return indexed_count
    
    def search(self, search_query: SearchQuery) -> SearchResponse:
        """Perform search query.
        
        Args:
            search_query: Search query configuration
            
        Returns:
            Search response with results
        """
        import time
        start_time = time.time()
        
        # Tokenize query
        query_tokens = self.text_processor.tokenize(search_query.query)
        
        if not query_tokens:
            return SearchResponse(
                results=[],
                total_results=0,
                page=search_query.page,
                per_page=search_query.per_page,
                total_pages=0,
                query_time_ms=0,
                query=search_query.query
            )
        
        # Find matching documents
        token_matches = self.index.search_tokens(query_tokens)
        phrase_matches = self.index.search_phrases(search_query.query)
        
        # Combine matches (union for broader results)
        all_matches = token_matches.union(phrase_matches)
        
        # Apply filters
        filtered_matches = self._apply_filters(all_matches, search_query.filters)
        
        # Score and rank results
        scored_results = self._score_results(filtered_matches, query_tokens, search_query)
        
        # Sort by score
        scored_results.sort(key=lambda x: x.score, reverse=True)
        
        # Pagination
        total_results = len(scored_results)
        start_idx = (search_query.page - 1) * search_query.per_page
        end_idx = start_idx + search_query.per_page
        paginated_results = scored_results[start_idx:end_idx]
        
        # Generate facets
        facets = self._generate_facets(all_matches, search_query.facets) if search_query.facets else {}
        
        # Generate suggestions
        suggestions = self._generate_suggestions(search_query.query, query_tokens)
        
        query_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=paginated_results,
            total_results=total_results,
            page=search_query.page,
            per_page=search_query.per_page,
            total_pages=math.ceil(total_results / search_query.per_page),
            query_time_ms=query_time,
            facets=facets,
            suggestions=suggestions,
            query=search_query.query
        )
    
    def _apply_filters(self, document_ids: Set[str], filters: Dict[str, Any]) -> Set[str]:
        """Apply filters to search results."""
        if not filters:
            return document_ids
        
        filtered_ids = set()
        
        for doc_id in document_ids:
            document = self.index.documents.get(doc_id)
            if not document:
                continue
            
            matches_filters = True
            
            # Category filter
            if 'category' in filters:
                allowed_categories = filters['category']
                if isinstance(allowed_categories, str):
                    allowed_categories = [allowed_categories]
                if document.category not in allowed_categories:
                    matches_filters = False
            
            # Type filter
            if 'type' in filters:
                allowed_types = filters['type']
                if isinstance(allowed_types, str):
                    allowed_types = [allowed_types]
                if document.result_type.value not in allowed_types:
                    matches_filters = False
            
            # Tags filter
            if 'tags' in filters:
                required_tags = filters['tags']
                if isinstance(required_tags, str):
                    required_tags = [required_tags]
                if not any(tag in document.tags for tag in required_tags):
                    matches_filters = False
            
            if matches_filters:
                filtered_ids.add(doc_id)
        
        return filtered_ids
    
    def _score_results(self, document_ids: Set[str], query_tokens: List[str], search_query: SearchQuery) -> List[SearchResult]:
        """Score and create search results."""
        results = []
        
        for doc_id in document_ids:
            document = self.index.documents.get(doc_id)
            if not document:
                continue
            
            score = self._calculate_score(document, query_tokens, search_query)
            snippet = self._generate_snippet(document, query_tokens)
            highlights = self._generate_highlights(document, query_tokens) if search_query.highlight else []
            
            result = SearchResult(
                document_id=doc_id,
                title=document.title,
                url=document.url,
                snippet=snippet,
                score=score,
                result_type=document.result_type,
                category=document.category,
                tags=document.tags,
                highlights=highlights,
                metadata=document.metadata
            )
            
            results.append(result)
        
        return results
    
    def _calculate_score(self, document: SearchDocument, query_tokens: List[str], search_query: SearchQuery) -> float:
        """Calculate relevance score for document."""
        score = 0.0
        
        # TF-IDF score
        if document.id in self.index.tfidf_scores:
            tfidf_dict = self.index.tfidf_scores[document.id]
            for token in query_tokens:
                if token in tfidf_dict:
                    score += tfidf_dict[token]
        
        # Title boost
        title_tokens = self.text_processor.tokenize(document.title)
        title_matches = sum(1 for token in query_tokens if token in title_tokens)
        if title_matches > 0:
            score *= search_query.boost_title
        
        # Length normalization (shorter documents get slight boost)
        if document.word_count > 0:
            length_factor = 1.0 / (1.0 + document.word_count / 1000.0)
            score *= (1.0 + length_factor * 0.1)
        
        # Exact phrase bonus
        query_lower = search_query.query.lower()
        if query_lower in document.content.lower() or query_lower in document.title.lower():
            score *= 1.5
        
        # Category boost (API references and examples get higher scores)
        if document.result_type in [SearchResultType.API_REFERENCE, SearchResultType.CODE_EXAMPLE]:
            score *= 1.2
        
        return score
    
    def _generate_snippet(self, document: SearchDocument, query_tokens: List[str], max_length: int = 150) -> str:
        """Generate search result snippet."""
        content = document.content
        
        # Find best snippet containing query terms
        sentences = re.split(r'[.!?]+', content)
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Count query token matches in sentence
            sentence_lower = sentence.lower()
            score = sum(1 for token in query_tokens if token in sentence_lower)
            
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        # Fallback to beginning of content
        if not best_sentence:
            best_sentence = content[:max_length]
        
        # Truncate if too long
        if len(best_sentence) > max_length:
            best_sentence = best_sentence[:max_length - 3] + "..."
        
        return best_sentence
    
    def _generate_highlights(self, document: SearchDocument, query_tokens: List[str]) -> List[str]:
        """Generate highlight snippets for query tokens."""
        highlights = []
        content_lower = document.content.lower()
        title_lower = document.title.lower()
        
        for token in query_tokens:
            # Find in title
            if token in title_lower:
                highlights.append(f"Title: {document.title}")
            
            # Find in content
            token_pos = content_lower.find(token)
            if token_pos >= 0:
                start = max(0, token_pos - 30)
                end = min(len(document.content), token_pos + len(token) + 30)
                snippet = document.content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(document.content):
                    snippet = snippet + "..."
                highlights.append(snippet)
        
        return highlights[:3]  # Limit to 3 highlights
    
    def _generate_facets(self, document_ids: Set[str], facet_fields: List[str]) -> Dict[str, List[Tuple[str, int]]]:
        """Generate facets for search results."""
        facets = {}
        
        for field in facet_fields:
            facet_counts = defaultdict(int)
            
            for doc_id in document_ids:
                document = self.index.documents.get(doc_id)
                if not document:
                    continue
                
                if field == 'category' and document.category:
                    facet_counts[document.category] += 1
                elif field == 'type':
                    facet_counts[document.result_type.value] += 1
                elif field == 'tags':
                    for tag in document.tags:
                        facet_counts[tag] += 1
            
            # Sort by count descending
            sorted_facets = sorted(facet_counts.items(), key=lambda x: x[1], reverse=True)
            facets[field] = sorted_facets[:10]  # Limit to top 10
        
        return facets
    
    def _generate_suggestions(self, original_query: str, query_tokens: List[str]) -> List[str]:
        """Generate search suggestions."""
        suggestions = []
        
        # Find similar tokens in index
        for token in query_tokens:
            similar_tokens = []
            for indexed_token in self.index.inverted_index:
                if len(indexed_token) > 3 and token != indexed_token:
                    # Simple similarity based on common characters
                    common_chars = set(token) & set(indexed_token)
                    similarity = len(common_chars) / max(len(token), len(indexed_token))
                    if similarity > 0.6:
                        similar_tokens.append(indexed_token)
            
            # Add most relevant similar tokens as suggestions
            for similar_token in similar_tokens[:2]:
                suggested_query = original_query.replace(token, similar_token)
                if suggested_query != original_query:
                    suggestions.append(suggested_query)
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_docs = self.index.get_document_count()
        total_terms = len(self.index.inverted_index)
        total_phrases = len(self.index.phrase_index)
        
        # Document type distribution
        type_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for document in self.index.documents.values():
            type_counts[document.result_type.value] += 1
            if document.category:
                category_counts[document.category] += 1
        
        return {
            "total_documents": total_docs,
            "total_terms": total_terms,
            "total_phrases": total_phrases,
            "document_types": dict(type_counts),
            "categories": dict(category_counts),
            "average_document_size": sum(doc.word_count for doc in self.index.documents.values()) / max(total_docs, 1)
        }
    
    def save_index(self, file_path: Path) -> bool:
        """Save search index to file.
        
        Args:
            file_path: Path to save index
            
        Returns:
            True if saved successfully
        """
        try:
            index_data = {
                "documents": {
                    doc_id: {
                        "id": doc.id,
                        "title": doc.title,
                        "content": doc.content,
                        "url": doc.url,
                        "description": doc.description,
                        "category": doc.category,
                        "tags": doc.tags,
                        "result_type": doc.result_type.value,
                        "metadata": doc.metadata,
                        "word_count": doc.word_count,
                        "last_modified": doc.last_modified
                    }
                    for doc_id, doc in self.index.documents.items()
                },
                "inverted_index": {
                    term: list(doc_ids) for term, doc_ids in self.index.inverted_index.items()
                },
                "phrase_index": {
                    phrase: list(doc_ids) for phrase, doc_ids in self.index.phrase_index.items()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def load_index(self, file_path: Path) -> bool:
        """Load search index from file.
        
        Args:
            file_path: Path to load index from
            
        Returns:
            True if loaded successfully
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Restore documents
            self.index.documents = {}
            for doc_id, doc_data in index_data["documents"].items():
                document = SearchDocument(
                    id=doc_data["id"],
                    title=doc_data["title"],
                    content=doc_data["content"],
                    url=doc_data["url"],
                    description=doc_data["description"],
                    category=doc_data["category"],
                    tags=doc_data["tags"],
                    result_type=SearchResultType(doc_data["result_type"]),
                    metadata=doc_data["metadata"],
                    word_count=doc_data["word_count"],
                    last_modified=doc_data["last_modified"]
                )
                self.index.documents[doc_id] = document
            
            # Restore inverted index
            self.index.inverted_index = defaultdict(set)
            for term, doc_ids in index_data["inverted_index"].items():
                self.index.inverted_index[term] = set(doc_ids)
            
            # Restore phrase index
            self.index.phrase_index = defaultdict(set)
            for phrase, doc_ids in index_data["phrase_index"].items():
                self.index.phrase_index[phrase] = set(doc_ids)
            
            # Update TF-IDF scores
            self.index.update_tfidf_scores()
            
            return True
        except Exception:
            return False