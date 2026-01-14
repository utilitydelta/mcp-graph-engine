#!/usr/bin/env python3
"""Test pure embedding-based matching (not exact or normalized)."""

import sys


def test_pure_embedding_matching():
    """Test cases where only embedding matching can work."""
    print("=" * 60)
    print("Pure Embedding-Based Matching (No Exact/Normalized Match)")
    print("=" * 60)

    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Add nodes with very specific names
    print("\nAdding nodes to graph...")
    nodes = [
        ("AuthenticationController", "controller"),
        ("DatabaseConnectionPool", "infrastructure"),
        ("EmailNotificationHandler", "handler"),
    ]

    for label, node_type in nodes:
        graph.add_node(label, node_type)
        print(f"  Added: {label}")

    print("\nTesting queries that require embedding matching:")
    print("-" * 60)

    # These queries should NOT match via normalized matching,
    # but SHOULD match via embeddings (if similarity > 0.75)
    test_cases = [
        # Query that is semantically similar but structurally different
        ("login controller", "AuthenticationController"),  # Different words but similar meaning
        ("db pool", "DatabaseConnectionPool"),  # Abbreviation + different structure
        ("connection pool", "DatabaseConnectionPool"),  # Partial semantic match
    ]

    from src.mcp_graph_engine.matcher import Matcher

    # First verify these DON'T match via normalized matching
    print("\n1. Verifying these queries DON'T match via normalized matching:")
    matcher_no_embeddings = Matcher(embeddings={})  # No embeddings

    for query, expected in test_cases:
        result = matcher_no_embeddings.find_match(query, [expected])
        if result.matched_label:
            print(f"  ✗ UNEXPECTED: '{query}' matched '{result.matched_label}' without embeddings")
        else:
            print(f"  ✓ '{query}' does not match '{expected}' via exact/normalized")

    # Now test with embeddings
    print("\n2. Testing with embedding-based matching:")
    for query, expected in test_cases:
        result = graph.find_node(query)
        matches = result['matches']

        if matches and matches[0]['label'] == expected:
            print(f"  ✓ '{query}' -> '{matches[0]['label']}'")
            print(f"    Similarity: {matches[0]['similarity']:.4f}")
        else:
            print(f"  ✗ '{query}' did not match '{expected}'")
            if matches:
                print(f"    Got: '{matches[0]['label']}' (similarity: {matches[0]['similarity']:.4f})")
            else:
                print(f"    Got: No matches (similarity below threshold)")

    # Calculate actual similarity scores for reference
    print("\n3. Actual similarity scores:")
    print("-" * 60)
    from sentence_transformers import SentenceTransformer
    from src.mcp_graph_engine.matcher import MATCHING_CONFIG
    import numpy as np

    model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])

    for query, label in test_cases:
        query_emb = model.encode(query, convert_to_numpy=True)
        label_emb = model.encode(label, convert_to_numpy=True)

        dot_product = np.dot(query_emb, label_emb)
        norm_a = np.linalg.norm(query_emb)
        norm_b = np.linalg.norm(label_emb)
        similarity = float(dot_product / (norm_a * norm_b))

        threshold = MATCHING_CONFIG['similarity_threshold']
        status = "✓ Above threshold" if similarity >= threshold else "✗ Below threshold"

        print(f"  '{query}' vs '{label}':")
        print(f"    Similarity: {similarity:.4f} (threshold: {threshold}) {status}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        test_pure_embedding_matching()
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
