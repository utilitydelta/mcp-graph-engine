#!/usr/bin/env python3
"""Simple test script to verify the MCP Graph Engine server setup."""

import sys
import json


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    from src.mcp_graph_engine.matcher import Matcher, MatchResult
    from src.mcp_graph_engine.graph_engine import GraphEngine
    from src.mcp_graph_engine.session import SessionManager
    from src.mcp_graph_engine.tools import ALL_TOOLS
    from src.mcp_graph_engine.server import GraphServer
    print("✓ All imports successful")


def test_matcher():
    """Test the Matcher class."""
    print("\nTesting Matcher...")
    from src.mcp_graph_engine.matcher import Matcher

    matcher = Matcher()
    labels = ["AuthService", "UserRepository", "DatabasePool"]

    # Test exact match
    result = matcher.find_match("AuthService", labels)
    assert result.matched_label == "AuthService"
    assert result.exact is True
    print("✓ Exact match works")

    # Test normalized match
    result = matcher.find_match("auth service", labels)
    assert result.matched_label == "AuthService"
    assert result.exact is False
    print("✓ Normalized match works")

    # Test no match
    result = matcher.find_match("NonExistent", labels)
    assert result.matched_label is None
    print("✓ No match returns None")


def test_graph_engine():
    """Test the GraphEngine class."""
    print("\nTesting GraphEngine...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Test add_node
    node_data, created = graph.add_node("AuthService", "class", {"file": "auth.py"})
    assert created is True
    assert node_data["label"] == "AuthService"
    print("✓ add_node works")

    # Test add_nodes
    nodes = [
        {"label": "UserRepo", "type": "class"},
        {"label": "Database", "type": "service"}
    ]
    added, existing = graph.add_nodes(nodes)
    assert added == 2
    assert existing == 0
    print("✓ add_nodes works")

    # Test list_nodes
    all_nodes = graph.list_nodes()
    assert len(all_nodes) == 3
    print("✓ list_nodes works")

    # Test add_edge
    edge_data, created, src, tgt = graph.add_edge("AuthService", "UserRepo", "uses")
    assert created is True
    assert src == "AuthService"
    assert tgt == "UserRepo"
    print("✓ add_edge works")

    # Test fuzzy matching in add_edge - updating the edge replaces the relation
    edge_data, created, src, tgt = graph.add_edge("auth service", "user repo", "depends_on")
    assert src == "AuthService"
    assert tgt == "UserRepo"
    assert created is False  # Edge already exists
    assert edge_data["relation"] == "depends_on"  # Relation was updated
    print("✓ Fuzzy matching in add_edge works")

    # Test find_edges - should find 1 edge (second overwrote first)
    edges = graph.find_edges(source="AuthService")
    assert len(edges) == 1
    assert edges[0]["relation"] == "depends_on"  # Latest relation
    print("✓ find_edges works")

    # Test add another edge to a different node
    graph.add_edge("AuthService", "Database", "connects_to")

    # Test get_neighbors - should have 1 incoming edge
    neighbors = graph.get_neighbors("UserRepo", direction="in")
    assert len(neighbors) == 1
    assert neighbors[0]["relation"] == "depends_on"
    print("✓ get_neighbors works")

    # Test get_stats
    stats = graph.get_stats()
    assert stats["node_count"] == 3
    assert stats["edge_count"] == 2  # AuthService->UserRepo, AuthService->Database
    print("✓ get_stats works")

    # Test remove_node
    success, edges_removed = graph.remove_node("UserRepo")
    assert success is True
    assert edges_removed == 1  # Only 1 edge to UserRepo
    print("✓ remove_node works")


def test_session_manager():
    """Test the SessionManager class."""
    print("\nTesting SessionManager...")
    from src.mcp_graph_engine.session import SessionManager

    manager = SessionManager()

    # Test get_graph (auto-create)
    graph = manager.get_graph("test")
    assert graph is not None
    print("✓ get_graph auto-creates graph")

    # Test list_graphs
    graphs = manager.list_graphs()
    assert len(graphs) == 1
    assert graphs[0]["name"] == "test"
    print("✓ list_graphs works")

    # Test default graph
    default_graph = manager.get_graph()
    assert default_graph is not None
    graphs = manager.list_graphs()
    assert len(graphs) == 2
    print("✓ default graph works")

    # Test get_graph_info
    default_graph.add_node("TestNode")
    info = manager.get_graph_info("default")
    assert info["node_count"] == 1
    print("✓ get_graph_info works")

    # Test delete_graph
    success = manager.delete_graph("test")
    assert success is True
    graphs = manager.list_graphs()
    assert len(graphs) == 1
    print("✓ delete_graph works")


def test_tools_definition():
    """Test that tools are properly defined."""
    print("\nTesting tool definitions...")
    from src.mcp_graph_engine.tools import ALL_TOOLS

    assert len(ALL_TOOLS) > 0
    print(f"✓ {len(ALL_TOOLS)} tools defined")

    # Check a few key tools
    tool_names = {tool.name for tool in ALL_TOOLS}
    expected_tools = [
        "list_graphs", "delete_graph", "get_graph_info",
        "add_node", "add_nodes", "list_nodes", "find_node", "remove_node",
        "add_edge", "add_edges", "find_edges", "remove_edge", "get_neighbors",
        "shortest_path", "all_paths", "pagerank", "connected_components",
        "find_cycles", "transitive_reduction", "degree_centrality", "subgraph"
    ]

    for expected in expected_tools:
        assert expected in tool_names, f"Missing tool: {expected}"

    print(f"✓ All expected tools present: {', '.join(sorted(expected_tools))}")


def test_server_initialization():
    """Test that the server can be initialized."""
    print("\nTesting server initialization...")
    from src.mcp_graph_engine.server import GraphServer

    server = GraphServer()
    assert server.app is not None
    assert server.session_manager is not None
    print("✓ Server initialization works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Graph Engine - Core Foundation Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_matcher,
        test_graph_engine,
        test_session_manager,
        test_tools_definition,
        test_server_initialization,
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
        print("✓ All tests passed!")
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
