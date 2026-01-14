#!/usr/bin/env python3
"""Test that all analysis tools work through the server handlers."""

import asyncio
import sys


async def test_server_handlers():
    """Test all analysis tool handlers in the server."""
    print("=" * 60)
    print("Testing Server Handlers for Analysis Tools")
    print("=" * 60)

    from src.mcp_graph_engine.server import GraphServer

    server = GraphServer()

    # Setup test graph
    print("\nSetting up test graph...")
    await server._handle_tool("add_nodes", {
        "graph": "test",
        "nodes": [
            {"label": "A"},
            {"label": "B"},
            {"label": "C"},
            {"label": "D"}
        ]
    })

    await server._handle_tool("add_edges", {
        "graph": "test",
        "edges": [
            {"source": "A", "target": "B", "relation": "connects"},
            {"source": "B", "target": "C", "relation": "connects"},
            {"source": "C", "target": "D", "relation": "connects"},
            {"source": "A", "target": "C", "relation": "shortcut"}
        ]
    })
    print("✓ Test graph created")

    # Test shortest_path
    print("\nTesting shortest_path handler...")
    result = await server._handle_tool("shortest_path", {
        "graph": "test",
        "source": "A",
        "target": "D"
    })
    assert "path" in result
    assert result["path"] == ["A", "B", "C", "D"] or result["path"] == ["A", "C", "D"]
    print("✓ shortest_path handler works")

    # Test all_paths
    print("\nTesting all_paths handler...")
    result = await server._handle_tool("all_paths", {
        "graph": "test",
        "source": "A",
        "target": "D"
    })
    assert "paths" in result
    assert result["count"] >= 2
    print(f"✓ all_paths handler works (found {result['count']} paths)")

    # Test pagerank
    print("\nTesting pagerank handler...")
    result = await server._handle_tool("pagerank", {
        "graph": "test",
        "top_n": 2
    })
    assert "rankings" in result
    assert len(result["rankings"]) == 2
    print("✓ pagerank handler works")

    # Test connected_components
    print("\nTesting connected_components handler...")
    result = await server._handle_tool("connected_components", {
        "graph": "test"
    })
    assert "components" in result
    assert result["count"] == 1
    print("✓ connected_components handler works")

    # Test find_cycles
    print("\nTesting find_cycles handler...")
    result = await server._handle_tool("find_cycles", {
        "graph": "test"
    })
    assert "cycles" in result
    assert "has_cycles" in result
    print(f"✓ find_cycles handler works (has_cycles: {result['has_cycles']})")

    # Test transitive_reduction
    print("\nTesting transitive_reduction handler...")
    result = await server._handle_tool("transitive_reduction", {
        "graph": "test",
        "in_place": False
    })
    assert "edges_removed" in result
    print(f"✓ transitive_reduction handler works ({result['edges_removed']} redundant edges)")

    # Test degree_centrality
    print("\nTesting degree_centrality handler...")
    result = await server._handle_tool("degree_centrality", {
        "graph": "test",
        "top_n": 3
    })
    assert "rankings" in result
    assert len(result["rankings"]) <= 3
    print("✓ degree_centrality handler works")

    # Test subgraph
    print("\nTesting subgraph handler...")
    result = await server._handle_tool("subgraph", {
        "graph": "test",
        "nodes": ["A", "B", "C"],
        "include_edges": True
    })
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 3
    print(f"✓ subgraph handler works ({len(result['nodes'])} nodes, {len(result['edges'])} edges)")

    print("\n" + "=" * 60)
    print("✓ All server handlers working correctly!")
    print("=" * 60)


async def test_error_handling():
    """Test error handling in analysis tools."""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    from src.mcp_graph_engine.server import GraphServer

    server = GraphServer()

    # Test shortest_path with non-existent nodes
    print("\nTesting shortest_path with non-existent source...")
    result = await server._handle_tool("shortest_path", {
        "graph": "empty",
        "source": "NonExistent",
        "target": "AlsoNonExistent"
    })
    assert result["path"] is None
    assert "reason" in result
    print("✓ Error handled correctly")

    # Test subgraph with non-existent nodes
    print("\nTesting subgraph with some non-existent nodes...")
    await server._handle_tool("add_node", {
        "graph": "partial",
        "label": "ExistsA"
    })
    result = await server._handle_tool("subgraph", {
        "graph": "partial",
        "nodes": ["ExistsA", "DoesNotExist"]
    })
    assert "not_found" in result
    assert "DoesNotExist" in result["not_found"]
    print("✓ Partial match handled correctly")

    print("\n" + "=" * 60)
    print("✓ All error handling working correctly!")
    print("=" * 60)


def main():
    """Run all async tests."""
    try:
        asyncio.run(test_server_handlers())
        asyncio.run(test_error_handling())
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
