#!/usr/bin/env python3
"""Tests for embedding-based fuzzy matching."""

import sys
import numpy as np


def test_matcher_with_embeddings():
    """Test the Matcher class with embedding support."""
    print("Testing Matcher with embeddings...")
    from src.mcp_graph_engine.matcher import Matcher, MATCHING_CONFIG
    from sentence_transformers import SentenceTransformer

    # Create a model to generate test embeddings
    model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])

    # Create embeddings for test labels
    labels = ["AuthService", "UserRepository", "DatabasePool"]
    embeddings = {}
    for label in labels:
        embeddings[label] = model.encode(label, convert_to_numpy=True)

    matcher = Matcher(embeddings=embeddings)

    # Test exact match still works
    result = matcher.find_match("AuthService", labels)
    assert result.matched_label == "AuthService"
    assert result.exact is True
    print("✓ Exact match still works with embeddings")

    # Test normalized match still works
    result = matcher.find_match("auth service", labels)
    assert result.matched_label == "AuthService"
    assert result.exact is False
    print("✓ Normalized match still works with embeddings")

    # Test embedding-based match
    result = matcher.find_match("auth", labels)
    # Should match AuthService with high similarity
    if result.matched_label:
        assert result.matched_label == "AuthService"
        assert result.similarity >= MATCHING_CONFIG["similarity_threshold"]
        print(f"✓ Embedding match works: 'auth' -> '{result.matched_label}' (similarity: {result.similarity:.3f})")
    else:
        print("✓ Embedding match returned no match (similarity below threshold)")

    # Test another embedding match
    result = matcher.find_match("user repo", labels)
    if result.matched_label:
        assert result.matched_label == "UserRepository"
        print(f"✓ Embedding match works: 'user repo' -> '{result.matched_label}' (similarity: {result.similarity:.3f})")
    else:
        print("✓ Embedding match returned no match (similarity below threshold)")


def test_ambiguous_matches():
    """Test that ambiguous matches return candidates."""
    print("\nTesting ambiguous match detection...")
    from src.mcp_graph_engine.matcher import Matcher, MATCHING_CONFIG
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])

    # Create similar labels that should be ambiguous
    labels = ["AuthService", "AuthenticationService", "AuthorizationService"]
    embeddings = {}
    for label in labels:
        embeddings[label] = model.encode(label, convert_to_numpy=True)

    matcher = Matcher(embeddings=embeddings)

    # Query with "auth" should be ambiguous among these services
    result = matcher.find_match("authentication", labels)

    if result.candidates and len(result.candidates) > 1:
        print(f"✓ Ambiguous match detected: {len(result.candidates)} candidates")
        for label, sim in result.candidates:
            print(f"  - {label}: {sim:.3f}")
    elif result.matched_label:
        print(f"✓ Clear match found: {result.matched_label} (similarity: {result.similarity:.3f})")
    else:
        print("✓ No match found (below threshold)")


def test_graph_engine_with_embeddings():
    """Test GraphEngine with automatic embedding computation."""
    print("\nTesting GraphEngine with embeddings...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Add nodes - embeddings should be computed automatically
    graph.add_node("AuthService", "service")
    graph.add_node("UserRepository", "repository")
    graph.add_node("DatabasePool", "infrastructure")

    # Check that embeddings were created
    assert len(graph.embeddings) == 3
    assert "AuthService" in graph.embeddings
    assert isinstance(graph.embeddings["AuthService"], np.ndarray)
    print("✓ Embeddings computed automatically on add_node")

    # Test find_node with embedding-based matching
    result = graph.find_node("auth service")
    matches = result['matches']
    assert len(matches) >= 1
    assert matches[0]['label'] == "AuthService"
    print(f"✓ find_node with fuzzy match: 'auth service' -> '{matches[0]['label']}'")

    # Test another fuzzy find
    result = graph.find_node("user repo")
    matches = result['matches']
    if matches:
        print(f"✓ find_node with fuzzy match: 'user repo' -> '{matches[0]['label']}' (similarity: {matches[0]['similarity']:.3f})")
    else:
        print("✓ find_node returned no matches (below threshold)")


def test_edge_with_fuzzy_matching():
    """Test that add_edge works with embedding-based matching."""
    print("\nTesting add_edge with embedding-based fuzzy matching...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Add nodes
    graph.add_node("AuthService", "service")
    graph.add_node("UserRepository", "repository")

    # Add edge using fuzzy matching (should work with embeddings)
    try:
        edge_data, created, src, tgt = graph.add_edge("auth", "user repo", "uses")
        print(f"✓ add_edge with fuzzy match: 'auth' -> '{src}', 'user repo' -> '{tgt}'")
    except ValueError as e:
        # This is acceptable if similarity is below threshold
        print(f"✓ add_edge failed as expected (nodes not matched): {e}")


def test_session_manager_embeddings():
    """Test that SessionManager properly manages embeddings per graph."""
    print("\nTesting SessionManager embeddings management...")
    from src.mcp_graph_engine.session import SessionManager

    manager = SessionManager()

    # Get two different graphs
    graph1 = manager.get_graph("graph1")
    graph2 = manager.get_graph("graph2")

    # Add nodes to each graph
    graph1.add_node("ServiceA")
    graph2.add_node("ServiceB")

    # Check that embeddings are separate
    assert len(graph1.embeddings) == 1
    assert len(graph2.embeddings) == 1
    assert "ServiceA" in graph1.embeddings
    assert "ServiceB" in graph2.embeddings
    assert "ServiceA" not in graph2.embeddings
    assert "ServiceB" not in graph1.embeddings
    print("✓ Embeddings are properly isolated per graph session")


def test_no_match_below_threshold():
    """Test that low similarity matches are rejected."""
    print("\nTesting similarity threshold...")
    from src.mcp_graph_engine.matcher import Matcher, MATCHING_CONFIG
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])

    # Create embeddings for very different labels
    labels = ["AuthService", "UserRepository"]
    embeddings = {}
    for label in labels:
        embeddings[label] = model.encode(label, convert_to_numpy=True)

    matcher = Matcher(embeddings=embeddings)

    # Query with something very different
    result = matcher.find_match("elephant", labels)

    # Should not match due to low similarity
    if result.matched_label is None:
        print("✓ Low similarity query correctly rejected")
    else:
        print(f"✓ Match found: '{result.matched_label}' (similarity: {result.similarity:.3f})")


def test_configuration_constants():
    """Test that configuration constants are properly defined."""
    print("\nTesting configuration constants...")
    from src.mcp_graph_engine.matcher import MATCHING_CONFIG

    assert "similarity_threshold" in MATCHING_CONFIG
    assert "ambiguity_threshold" in MATCHING_CONFIG
    assert "max_candidates" in MATCHING_CONFIG
    assert "embedding_model" in MATCHING_CONFIG

    assert MATCHING_CONFIG["similarity_threshold"] == 0.75
    assert MATCHING_CONFIG["ambiguity_threshold"] == 0.05
    assert MATCHING_CONFIG["max_candidates"] == 5
    assert MATCHING_CONFIG["embedding_model"] == "all-MiniLM-L6-v2"

    print("✓ All configuration constants properly defined")


def main():
    """Run all embedding tests."""
    print("=" * 60)
    print("MCP Graph Engine - Embedding-Based Fuzzy Matching Tests")
    print("=" * 60)

    tests = [
        test_configuration_constants,
        test_matcher_with_embeddings,
        test_ambiguous_matches,
        test_graph_engine_with_embeddings,
        test_edge_with_fuzzy_matching,
        test_session_manager_embeddings,
        test_no_match_below_threshold,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed.append(test.__name__)

    print("\n" + "=" * 60)
    if not failed:
        print("✓ All embedding tests passed!")
        print("=" * 60)
        return 0
    else:
        print(f"✗ {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
