#!/usr/bin/env python3
"""Demonstration of query and analysis tools with a realistic example."""

import json


def demo_codebase_analysis():
    """Demonstrate analysis tools on a simulated codebase dependency graph."""
    print("=" * 70)
    print("MCP Graph Engine - Query & Analysis Tools Demonstration")
    print("Scenario: Analyzing a microservices architecture")
    print("=" * 70)

    from src.mcp_graph_engine.graph_engine import GraphEngine

    # Create a graph representing a microservices architecture
    graph = GraphEngine()

    print("\n1. Building the dependency graph...")
    print("-" * 70)

    # Add service nodes
    services = [
        ("ApiGateway", "service"),
        ("AuthService", "service"),
        ("UserService", "service"),
        ("OrderService", "service"),
        ("PaymentService", "service"),
        ("InventoryService", "service"),
        ("NotificationService", "service"),
        ("Database", "database"),
        ("Cache", "cache"),
        ("MessageQueue", "infrastructure")
    ]

    for label, node_type in services:
        graph.add_node(label, node_type)
        print(f"  Added: {label} ({node_type})")

    # Add dependencies
    dependencies = [
        ("ApiGateway", "AuthService", "authenticates_via"),
        ("ApiGateway", "UserService", "routes_to"),
        ("ApiGateway", "OrderService", "routes_to"),
        ("AuthService", "Database", "queries"),
        ("AuthService", "Cache", "caches_in"),
        ("UserService", "Database", "queries"),
        ("UserService", "Cache", "caches_in"),
        ("OrderService", "UserService", "validates_with"),
        ("OrderService", "PaymentService", "processes_payment_via"),
        ("OrderService", "InventoryService", "checks_stock_in"),
        ("OrderService", "Database", "queries"),
        ("PaymentService", "Database", "queries"),
        ("PaymentService", "NotificationService", "notifies_via"),
        ("InventoryService", "Database", "queries"),
        ("InventoryService", "MessageQueue", "publishes_to"),
        ("NotificationService", "MessageQueue", "subscribes_to"),
    ]

    print("\n  Adding dependencies...")
    for source, target, relation in dependencies:
        graph.add_edge(source, target, relation)

    stats = graph.get_stats()
    print(f"\n  Graph created: {stats['node_count']} nodes, {stats['edge_count']} edges")

    # Demonstrate each analysis tool

    print("\n2. Finding shortest path (API Gateway → Database)")
    print("-" * 70)
    result = graph.shortest_path("ApiGateway", "Database")
    if result["path"]:
        print(f"  Path: {' → '.join(result['path'])}")
        print(f"  Length: {result['length']} hops")
    else:
        print(f"  {result['reason']}")

    print("\n3. Finding all paths (OrderService → Database)")
    print("-" * 70)
    result = graph.all_paths("OrderService", "Database", max_length=3)
    print(f"  Found {result['count']} path(s):")
    for i, path in enumerate(result["paths"], 1):
        print(f"    {i}. {' → '.join(path)}")

    print("\n4. PageRank - Most important services")
    print("-" * 70)
    result = graph.pagerank(top_n=5)
    print("  Top 5 most central services:")
    for i, item in enumerate(result["rankings"], 1):
        print(f"    {i}. {item['label']}: {item['score']:.4f}")

    print("\n5. Degree Centrality - Most connected services")
    print("-" * 70)
    result = graph.degree_centrality(top_n=5)
    print("  Top 5 most connected services:")
    for i, item in enumerate(result["rankings"], 1):
        print(f"    {i}. {item['label']}")
        print(f"       In-degree:  {item['in_degree']:.3f}")
        print(f"       Out-degree: {item['out_degree']:.3f}")
        print(f"       Total:      {item['total']:.3f}")

    print("\n6. Connected Components")
    print("-" * 70)
    result = graph.connected_components()
    print(f"  Number of components: {result['count']}")
    if result['count'] == 1:
        print("  ✓ All services are connected (good architecture!)")
    else:
        print("  Components:")
        for i, component in enumerate(result["components"], 1):
            print(f"    {i}. {', '.join(component)}")

    print("\n7. Cycle Detection")
    print("-" * 70)
    result = graph.find_cycles()
    if result["has_cycles"]:
        print(f"  ⚠ Found {len(result['cycles'])} cycle(s) (circular dependencies):")
        for i, cycle in enumerate(result["cycles"], 1):
            print(f"    {i}. {' → '.join(cycle + [cycle[0]])}")
    else:
        print("  ✓ No cycles detected (clean dependency graph)")

    print("\n8. Subgraph - Core payment flow")
    print("-" * 70)
    result = graph.subgraph(
        ["OrderService", "PaymentService", "NotificationService", "Database"],
        include_edges=True
    )
    print(f"  Nodes in subgraph: {len(result['nodes'])}")
    print("  Nodes:")
    for node in result["nodes"]:
        print(f"    - {node['label']} ({node['type']})")
    print(f"\n  Edges in subgraph: {len(result['edges'])}")
    for edge in result["edges"]:
        print(f"    - {edge['source']} → {edge['target']} ({edge['relation']})")

    print("\n9. Transitive Reduction - Remove redundant edges")
    print("-" * 70)
    # First check without modifying
    result = graph.transitive_reduction(in_place=False)
    print(f"  Redundant edges that could be removed: {result['edges_removed']}")
    if result['edges_removed'] > 0:
        print("  (These are edges implied by transitive relationships)")

    print("\n" + "=" * 70)
    print("Demonstration complete!")
    print("=" * 70)


def demo_cycle_detection():
    """Demonstrate cycle detection with a graph that has cycles."""
    print("\n\n" + "=" * 70)
    print("Bonus Demo: Detecting Circular Dependencies")
    print("=" * 70)

    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    print("\nCreating a graph with circular dependencies...")
    # Module A depends on B, B depends on C, C depends back to A
    graph.add_node("ModuleA")
    graph.add_node("ModuleB")
    graph.add_node("ModuleC")
    graph.add_node("ModuleD")

    graph.add_edge("ModuleA", "ModuleB", "imports")
    graph.add_edge("ModuleB", "ModuleC", "imports")
    graph.add_edge("ModuleC", "ModuleA", "imports")  # Creates a cycle
    graph.add_edge("ModuleD", "ModuleA", "imports")  # Not part of cycle

    result = graph.find_cycles()
    print(f"\nCycles detected: {result['has_cycles']}")
    print(f"Number of cycles: {len(result['cycles'])}")
    for i, cycle in enumerate(result["cycles"], 1):
        print(f"  Cycle {i}: {' → '.join(cycle + [cycle[0]])}")


if __name__ == "__main__":
    demo_codebase_analysis()
    demo_cycle_detection()
