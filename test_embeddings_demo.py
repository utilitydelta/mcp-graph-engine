#!/usr/bin/env python3
"""Demonstration of embedding-based fuzzy matching capabilities."""

import sys


def test_realistic_scenarios():
    """Test realistic scenarios where embedding-based matching should work."""
    print("=" * 60)
    print("Embedding-Based Fuzzy Matching - Real-World Examples")
    print("=" * 60)

    from src.mcp_graph_engine.graph_engine import GraphEngine

    # Scenario 1: Software Architecture Components
    print("\nScenario 1: Software Architecture")
    print("-" * 60)

    graph = GraphEngine()

    # Add common software components
    components = [
        ("AuthenticationService", "service"),
        ("UserRepository", "repository"),
        ("DatabaseConnectionPool", "infrastructure"),
        ("PaymentProcessor", "service"),
        ("EmailNotificationService", "service"),
    ]

    for label, node_type in components:
        graph.add_node(label, node_type)

    # Test fuzzy queries
    test_queries = [
        "authentication",
        "user data store",
        "database",
        "payment",
        "email notifications",
    ]

    for query in test_queries:
        result = graph.find_node(query)
        matches = result['matches']
        if matches:
            top_match = matches[0]
            print(f"  '{query}' -> '{top_match['label']}' (similarity: {top_match['similarity']:.3f})")
        else:
            print(f"  '{query}' -> No match found")

    # Scenario 2: Check exact and normalized still work
    print("\nScenario 2: Exact and Normalized Matching Still Work")
    print("-" * 60)

    result = graph.find_node("AuthenticationService")
    if result['matches']:
        print(f"  Exact match: 'AuthenticationService' -> '{result['matches'][0]['label']}'")

    result = graph.find_node("authentication service")
    if result['matches']:
        print(f"  Normalized match: 'authentication service' -> '{result['matches'][0]['label']}'")

    result = graph.find_node("AUTHENTICATION_SERVICE")
    if result['matches']:
        print(f"  Normalized match: 'AUTHENTICATION_SERVICE' -> '{result['matches'][0]['label']}'")

    # Scenario 3: Adding edges with fuzzy matching
    print("\nScenario 3: Adding Edges with Fuzzy Matching")
    print("-" * 60)

    try:
        # This should work if "authentication" matches AuthenticationService well enough
        edge_data, created, src, tgt = graph.add_edge(
            "AuthenticationService",  # Use exact match to ensure it works
            "UserRepository",
            "queries"
        )
        print(f"  Edge created: '{src}' -> '{tgt}' (relation: queries)")
    except ValueError as e:
        print(f"  Failed to create edge: {e}")

    # Scenario 4: Demonstrate threshold behavior
    print("\nScenario 4: Similarity Threshold Behavior")
    print("-" * 60)
    from src.mcp_graph_engine.matcher import MATCHING_CONFIG

    print(f"  Similarity threshold: {MATCHING_CONFIG['similarity_threshold']}")
    print(f"  Ambiguity threshold: {MATCHING_CONFIG['ambiguity_threshold']}")
    print(f"  Max candidates: {MATCHING_CONFIG['max_candidates']}")

    # Test with varying similarity
    varied_queries = [
        "auth",           # Partial match
        "authenticate",   # Related word
        "login service",  # Conceptually related
        "xyz123",        # Should definitely not match
    ]

    for query in varied_queries:
        result = graph.find_node(query)
        matches = result['matches']
        if matches:
            top_match = matches[0]
            print(f"  '{query}' -> '{top_match['label']}' (similarity: {top_match['similarity']:.3f})")
        else:
            print(f"  '{query}' -> No match (below threshold)")

    # Scenario 5: Ambiguous matches
    print("\nScenario 5: Ambiguous Match Detection")
    print("-" * 60)

    graph2 = GraphEngine()

    # Add similar services that could be ambiguous
    similar_services = [
        "AuthenticationService",
        "AuthorizationService",
        "AccountService",
    ]

    for service in similar_services:
        graph2.add_node(service, "service")

    # This query might match multiple services
    result = graph2.find_node("auth")
    matches = result['matches']

    if len(matches) > 1:
        print(f"  Ambiguous query 'auth' returned {len(matches)} candidates:")
        for match in matches:
            print(f"    - {match['label']} (similarity: {match['similarity']:.3f})")
    elif len(matches) == 1:
        print(f"  Clear match: 'auth' -> '{matches[0]['label']}' (similarity: {matches[0]['similarity']:.3f})")
    else:
        print(f"  No matches for 'auth'")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_realistic_scenarios()
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
