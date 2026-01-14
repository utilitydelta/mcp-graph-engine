"""Node matching logic with exact and normalized matching."""

import re
from typing import Optional, List, Tuple


class MatchResult:
    """Result of a node matching operation."""

    def __init__(self, matched_label: Optional[str], exact: bool = False):
        self.matched_label = matched_label
        self.exact = exact


class Matcher:
    """Handles node matching with exact and normalized strategies."""

    def __init__(self):
        pass

    def find_match(self, query: str, existing_labels: List[str]) -> MatchResult:
        """
        Find a matching node label using exact and normalized matching.

        Args:
            query: The query string to match
            existing_labels: List of existing node labels in the graph

        Returns:
            MatchResult with matched_label (or None if no match)
        """
        # Step 1: Exact match
        if query in existing_labels:
            return MatchResult(matched_label=query, exact=True)

        # Step 2: Normalized match
        normalized_query = self._normalize(query)

        for label in existing_labels:
            normalized_label = self._normalize(label)
            if normalized_query == normalized_label:
                return MatchResult(matched_label=label, exact=False)

        # No match found
        return MatchResult(matched_label=None)

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
