#!/usr/bin/env python3
"""Check actual similarity scores to verify embedding system is working."""

import sys
import numpy as np


def test_similarity_scores():
    """Test to see actual similarity scores between queries and labels."""
    print("=" * 60)
    print("Similarity Score Analysis")
    print("=" * 60)

    from sentence_transformers import SentenceTransformer
    from src.mcp_graph_engine.matcher import MATCHING_CONFIG

    # Load the model
    print(f"\nLoading model: {MATCHING_CONFIG['embedding_model']}")
    model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])

    # Test various query-label pairs
    test_cases = [
        ("auth service", "AuthService"),
        ("authentication", "AuthenticationService"),
        ("user repo", "UserRepository"),
        ("database pool", "DatabaseConnectionPool"),
        ("payment", "PaymentProcessor"),
        ("auth", "AuthenticationService"),
        ("auth", "AuthorizationService"),
        ("email", "EmailNotificationService"),
    ]

    print("\nSimilarity Scores:")
    print("-" * 60)

    for query, label in test_cases:
        query_emb = model.encode(query, convert_to_numpy=True)
        label_emb = model.encode(label, convert_to_numpy=True)

        # Compute cosine similarity
        dot_product = np.dot(query_emb, label_emb)
        norm_a = np.linalg.norm(query_emb)
        norm_b = np.linalg.norm(label_emb)
        similarity = float(dot_product / (norm_a * norm_b))

        threshold = MATCHING_CONFIG['similarity_threshold']
        status = "✓ MATCH" if similarity >= threshold else "✗ BELOW THRESHOLD"

        print(f"  '{query}' vs '{label}':")
        print(f"    Similarity: {similarity:.4f} {status}")

    print("\n" + "=" * 60)
    print(f"Threshold: {MATCHING_CONFIG['similarity_threshold']}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_similarity_scores()
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
