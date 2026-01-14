#!/usr/bin/env python3
"""Test script for query and analysis tools."""

import sys


def test_shortest_path():
    """Test shortest path algorithm."""
    print("\nTesting shortest_path...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a simple graph: A -> B -> C -> D
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_edge("A", "B", "connects")
    graph.add_edge("B", "C", "connects")
    graph.add_edge("C", "D", "connects")

    # Test path exists
    result = graph.shortest_path("A", "D")
    assert result["path"] == ["A", "B", "C", "D"]
    assert result["length"] == 3
    print("✓ Shortest path found correctly")

    # Test fuzzy matching
    result = graph.shortest_path("a", "d")
    assert result["path"] == ["A", "B", "C", "D"]
    print("✓ Fuzzy matching works in shortest_path")

    # Test no path exists
    graph.add_node("E")  # Isolated node
    result = graph.shortest_path("A", "E")
    assert result["path"] is None
    assert "reason" in result
    print("✓ No path case handled correctly")

    # Test node not found
    result = graph.shortest_path("X", "Y")
    assert result["path"] is None
    assert "not found" in result["reason"].lower()
    print("✓ Node not found case handled correctly")


def test_all_paths():
    """Test all paths algorithm."""
    print("\nTesting all_paths...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a graph with multiple paths: A -> B -> D, A -> C -> D
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_edge("A", "B", "path1")
    graph.add_edge("A", "C", "path2")
    graph.add_edge("B", "D", "path1")
    graph.add_edge("C", "D", "path2")

    # Test multiple paths exist
    result = graph.all_paths("A", "D")
    assert result["count"] == 2
    assert len(result["paths"]) == 2
    print(f"✓ Found {result['count']} paths correctly")

    # Test with max_length
    result = graph.all_paths("A", "D", max_length=2)
    assert result["count"] == 2  # Both paths are length 2
    print("✓ max_length filter works")

    # Test no paths
    graph.add_node("E")
    result = graph.all_paths("A", "E")
    assert result["count"] == 0
    assert result["paths"] == []
    print("✓ No paths case handled correctly")


def test_pagerank():
    """Test PageRank algorithm."""
    print("\nTesting pagerank...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a graph where B is more central (has more incoming edges)
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_edge("A", "B", "links")
    graph.add_edge("C", "B", "links")
    graph.add_edge("D", "B", "links")
    graph.add_edge("B", "A", "links")

    result = graph.pagerank()
    assert len(result["rankings"]) == 4
    # B should have highest PageRank
    assert result["rankings"][0]["label"] == "B"
    print(f"✓ PageRank calculated, top node: {result['rankings'][0]['label']}")

    # Test top_n
    result = graph.pagerank(top_n=2)
    assert len(result["rankings"]) == 2
    print("✓ top_n filter works")

    # Test empty graph
    empty_graph = GraphEngine()
    result = empty_graph.pagerank()
    assert result["rankings"] == []
    print("✓ Empty graph handled correctly")


def test_connected_components():
    """Test connected components algorithm."""
    print("\nTesting connected_components...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create two separate components
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_edge("A", "B", "connects")
    graph.add_edge("C", "D", "connects")

    result = graph.connected_components()
    assert result["count"] == 2
    assert len(result["components"]) == 2
    print(f"✓ Found {result['count']} components correctly")

    # Test single component
    graph.add_edge("B", "C", "connects")
    result = graph.connected_components()
    assert result["count"] == 1
    assert len(result["components"][0]) == 4
    print("✓ Single connected component works")

    # Test empty graph
    empty_graph = GraphEngine()
    result = empty_graph.connected_components()
    assert result["count"] == 0
    print("✓ Empty graph handled correctly")


def test_find_cycles():
    """Test cycle detection."""
    print("\nTesting find_cycles...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a graph with a cycle: A -> B -> C -> A
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B", "next")
    graph.add_edge("B", "C", "next")
    graph.add_edge("C", "A", "next")

    result = graph.find_cycles()
    assert result["has_cycles"] is True
    assert len(result["cycles"]) > 0
    print(f"✓ Found {len(result['cycles'])} cycle(s)")

    # Test acyclic graph
    acyclic_graph = GraphEngine()
    acyclic_graph.add_node("A")
    acyclic_graph.add_node("B")
    acyclic_graph.add_node("C")
    acyclic_graph.add_edge("A", "B", "next")
    acyclic_graph.add_edge("B", "C", "next")

    result = acyclic_graph.find_cycles()
    assert result["has_cycles"] is False
    assert len(result["cycles"]) == 0
    print("✓ No cycles in acyclic graph")


def test_transitive_reduction():
    """Test transitive reduction."""
    print("\nTesting transitive_reduction...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a graph with transitive edges: A -> B -> C and A -> C (redundant)
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B", "next")
    graph.add_edge("B", "C", "next")
    graph.add_edge("A", "C", "redundant")  # This should be removed

    # Test without modifying
    result = graph.transitive_reduction(in_place=False)
    assert result["edges_removed"] == 1
    assert graph.graph.number_of_edges() == 3  # Graph unchanged
    print("✓ Transitive reduction counted correctly without modifying")

    # Test with modification
    result = graph.transitive_reduction(in_place=True)
    assert result["edges_removed"] == 1
    assert graph.graph.number_of_edges() == 2  # Redundant edge removed
    print("✓ Transitive reduction modified graph correctly")

    # Test graph with no transitive edges
    simple_graph = GraphEngine()
    simple_graph.add_node("A")
    simple_graph.add_node("B")
    simple_graph.add_edge("A", "B", "connects")

    result = simple_graph.transitive_reduction()
    assert result["edges_removed"] == 0
    print("✓ No transitive edges to remove handled correctly")


def test_degree_centrality():
    """Test degree centrality."""
    print("\nTesting degree_centrality...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a graph where B is most connected
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_edge("A", "B", "connects")
    graph.add_edge("B", "C", "connects")
    graph.add_edge("B", "D", "connects")

    result = graph.degree_centrality()
    assert len(result["rankings"]) == 4
    # B should have highest total centrality
    assert result["rankings"][0]["label"] == "B"
    assert "in_degree" in result["rankings"][0]
    assert "out_degree" in result["rankings"][0]
    assert "total" in result["rankings"][0]
    print(f"✓ Degree centrality calculated, top node: {result['rankings'][0]['label']}")

    # Test top_n
    result = graph.degree_centrality(top_n=2)
    assert len(result["rankings"]) == 2
    print("✓ top_n filter works")

    # Test empty graph
    empty_graph = GraphEngine()
    result = empty_graph.degree_centrality()
    assert result["rankings"] == []
    print("✓ Empty graph handled correctly")


def test_subgraph():
    """Test subgraph extraction."""
    print("\nTesting subgraph...")
    from src.mcp_graph_engine.graph_engine import GraphEngine

    graph = GraphEngine()

    # Create a larger graph
    graph.add_node("A", "type1")
    graph.add_node("B", "type1")
    graph.add_node("C", "type2")
    graph.add_node("D", "type2")
    graph.add_edge("A", "B", "connects")
    graph.add_edge("B", "C", "connects")
    graph.add_edge("C", "D", "connects")

    # Test subgraph with edges
    result = graph.subgraph(["A", "B", "C"], include_edges=True)
    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 2  # A->B and B->C
    print(f"✓ Subgraph extracted with {len(result['nodes'])} nodes and {len(result['edges'])} edges")

    # Test subgraph without edges
    result = graph.subgraph(["A", "B"], include_edges=False)
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 0
    print("✓ Subgraph without edges works")

    # Test fuzzy matching
    result = graph.subgraph(["a", "b"], include_edges=True)
    assert len(result["nodes"]) == 2
    assert result["nodes"][0]["label"] in ["A", "B"]
    print("✓ Fuzzy matching works in subgraph")

    # Test with non-existent node
    result = graph.subgraph(["A", "X"], include_edges=True)
    assert len(result["nodes"]) == 1
    assert "not_found" in result
    assert "X" in result["not_found"]
    print("✓ Non-existent nodes handled correctly")


def test_integration_with_session_manager():
    """Test that all tools work with SessionManager."""
    print("\nTesting integration with SessionManager...")
    from src.mcp_graph_engine.session import SessionManager

    manager = SessionManager()
    graph = manager.get_graph("test")

    # Add some test data
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B", "connects")
    graph.add_edge("B", "C", "connects")

    # Test each analysis tool
    result = graph.shortest_path("A", "C")
    assert result["path"] == ["A", "B", "C"]

    result = graph.all_paths("A", "C")
    assert result["count"] == 1

    result = graph.pagerank()
    assert len(result["rankings"]) == 3

    result = graph.connected_components()
    assert result["count"] == 1

    result = graph.find_cycles()
    assert result["has_cycles"] is False

    result = graph.degree_centrality()
    assert len(result["rankings"]) == 3

    result = graph.subgraph(["A", "B"])
    assert len(result["nodes"]) == 2

    print("✓ All tools work with SessionManager")


def test_tool_definitions():
    """Test that all new tools are properly defined."""
    print("\nTesting new tool definitions...")
    from src.mcp_graph_engine.tools import ALL_TOOLS

    tool_names = {tool.name for tool in ALL_TOOLS}
    expected_new_tools = [
        "shortest_path",
        "all_paths",
        "pagerank",
        "connected_components",
        "find_cycles",
        "transitive_reduction",
        "degree_centrality",
        "subgraph"
    ]

    for expected in expected_new_tools:
        assert expected in tool_names, f"Missing tool: {expected}"

    print(f"✓ All {len(expected_new_tools)} new tools defined correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Graph Engine - Query & Analysis Tools Tests")
    print("=" * 60)

    tests = [
        test_shortest_path,
        test_all_paths,
        test_pagerank,
        test_connected_components,
        test_find_cycles,
        test_transitive_reduction,
        test_degree_centrality,
        test_subgraph,
        test_integration_with_session_manager,
        test_tool_definitions,
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
        print("✓ All analysis tools tests passed!")
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
