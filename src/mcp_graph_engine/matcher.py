"""Node matching logic with exact, normalized, and embedding-based matching."""

import re

import numpy as np

# Check if sentence-transformers is available (optional dependency)
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# Matching configuration constants
MATCHING_CONFIG = {
    "similarity_threshold": 0.75,    # Minimum similarity for auto-match
    "ambiguity_threshold": 0.05,     # If top matches within this range, return candidates
    "max_candidates": 5,             # Max candidates to return when ambiguous
    "embedding_model": "all-MiniLM-L6-v2",
}

# Module-level singleton for the embedding model (loaded lazily, shared across all instances)
_embedding_model = None


def get_embedding_model():
    """Get the shared embedding model (lazy-loaded singleton). Returns None if not available."""
    global _embedding_model
    if not EMBEDDINGS_AVAILABLE:
        return None
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])
    return _embedding_model


class MatchResult:
    """Result of a node matching operation."""

    def __init__(
        self,
        matched_label: str | None,
        exact: bool = False,
        similarity: float = 1.0,
        candidates: list[tuple[str, float]] | None = None
    ):
        self.matched_label = matched_label
        self.exact = exact
        self.similarity = similarity
        self.candidates = candidates or []


class Matcher:
    """Handles node matching with exact, normalized, and embedding-based strategies."""

    def __init__(self, embeddings: dict[str, np.ndarray] | None = None):
        """
        Initialize the matcher.

        Args:
            embeddings: Optional dict mapping node labels to embedding vectors
        """
        self.embeddings = embeddings or {}

    def find_match(self, query: str, existing_labels: list[str]) -> MatchResult:
        """
        Find a matching node label using exact, normalized, and embedding-based matching.

        Args:
            query: The query string to match
            existing_labels: List of existing node labels in the graph

        Returns:
            MatchResult with matched_label (or None if no match)
        """
        # Step 1: Exact match
        if query in existing_labels:
            return MatchResult(matched_label=query, exact=True, similarity=1.0)

        # Step 2: Normalized match
        normalized_query = self._normalize(query)

        for label in existing_labels:
            normalized_label = self._normalize(label)
            if normalized_query == normalized_label:
                return MatchResult(matched_label=label, exact=False, similarity=1.0)

        # Step 3: Embedding-based similarity matching
        if self.embeddings:
            embedding_result = self._embedding_match(query, existing_labels)
            if embedding_result:
                return embedding_result

        # No match found
        return MatchResult(matched_label=None, similarity=0.0)

    def _embedding_match(self, query: str, existing_labels: list[str]) -> MatchResult | None:
        """
        Find matches using embedding-based similarity.

        Args:
            query: The query string to match
            existing_labels: List of existing node labels

        Returns:
            MatchResult with best match, candidates if ambiguous, or None if no match
        """
        # Compute query embedding
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return None

        # Calculate similarities for all labels with embeddings
        similarities = []
        for label in existing_labels:
            if label in self.embeddings:
                label_embedding = self.embeddings[label]
                similarity = self._cosine_similarity(query_embedding, label_embedding)
                similarities.append((label, similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Filter by threshold
        above_threshold = [
            (label, sim) for label, sim in similarities
            if sim >= MATCHING_CONFIG["similarity_threshold"]
        ]

        if not above_threshold:
            return None

        # Check for ambiguity - if top matches are within ambiguity_threshold
        top_label, top_similarity = above_threshold[0]

        # Find all candidates within ambiguity threshold of the top match
        ambiguous_candidates = []
        for label, sim in above_threshold[:MATCHING_CONFIG["max_candidates"]]:
            if top_similarity - sim <= MATCHING_CONFIG["ambiguity_threshold"]:
                ambiguous_candidates.append((label, sim))

        # If multiple candidates are ambiguous, return them all
        if len(ambiguous_candidates) > 1:
            return MatchResult(
                matched_label=None,
                exact=False,
                similarity=top_similarity,
                candidates=ambiguous_candidates
            )

        # Single clear match
        return MatchResult(
            matched_label=top_label,
            exact=False,
            similarity=top_similarity
        )

    def _get_embedding(self, text: str) -> np.ndarray | None:
        """
        Get embedding for a text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array, or None if embeddings not available
        """
        model = get_embedding_model()
        if model is None:
            return None
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0 to 1)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _normalize(self, text: str) -> str:
        """
        Normalize text for matching: lowercase, strip whitespace, remove punctuation.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()
        # Strip leading/trailing whitespace
        text = text.strip()
        # Remove punctuation (keep only alphanumeric and spaces)
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Collapse multiple spaces to single space
        text = re.sub(r'\s+', ' ', text)
        # Remove remaining spaces for final comparison
        text = text.replace(' ', '')

        return text
