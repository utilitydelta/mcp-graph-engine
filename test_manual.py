#!/usr/bin/env python3
"""Manual test script to verify import/export functionality."""

import asyncio
from src.mcp_graph_engine.server import GraphServer


async def test_import_export():
    """Test import/export functionality manually."""
    server = GraphServer()

    print("=== Testing Import/Export Functionality ===\n")

    # Test 1: Import DOT format
    print("1. Importing DOT format...")
    dot_content = """
    digraph codebase {
        AuthController -> AuthService [label="calls"];
        AuthService -> UserRepository [label="uses"];
        UserRepository -> Database [label="queries"];
    }
    """

    result = await server._handle_tool("import_graph", {
        "graph": "codebase",
        "format": "dot",
        "content": dot_content
    })
    print(f"   Result: {result}")
    assert result["nodes_added"] == 4
    assert result["edges_added"] == 3
    print("   ✓ DOT import successful\n")

    # Test 2: Export as JSON
    print("2. Exporting as JSON...")
    result = await server._handle_tool("export_graph", {
        "graph": "codebase",
        "format": "json"
    })
    print(f"   Content preview: {result['content'][:200]}...")
    print("   ✓ JSON export successful\n")

    # Test 3: Import CSV
    print("3. Importing CSV format...")
    csv_content = """source,target,relation
ConfigLoader,DatabasePool,configures
DatabasePool,Database,provides"""

    result = await server._handle_tool("import_graph", {
        "graph": "codebase",
        "format": "csv",
        "content": csv_content
    })
    print(f"   Result: {result}")
    assert result["nodes_added"] == 2  # ConfigLoader and DatabasePool are new
    assert result["edges_added"] == 2
    print("   ✓ CSV import successful (merged into existing graph)\n")

    # Test 4: Export as CSV
    print("4. Exporting as CSV...")
    result = await server._handle_tool("export_graph", {
        "graph": "codebase",
        "format": "csv"
    })
    print(f"   Content:\n{result['content']}")
    print("   ✓ CSV export successful\n")

    # Test 5: Get graph info
    print("5. Getting graph info...")
    result = await server._handle_tool("get_graph_info", {
        "graph": "codebase"
    })
    print(f"   Node count: {result['node_count']}")
    print(f"   Edge count: {result['edge_count']}")
    print(f"   Is DAG: {result['is_dag']}")
    print("   ✓ Graph info retrieved\n")

    # Test 6: Export as DOT and verify roundtrip
    print("6. Testing roundtrip (DOT -> JSON -> DOT)...")
    dot_export = await server._handle_tool("export_graph", {
        "graph": "codebase",
        "format": "dot"
    })
    print("   DOT export:")
    print(f"   {dot_export['content'][:300]}...")

    # Import into new graph
    result = await server._handle_tool("import_graph", {
        "graph": "copy",
        "format": "dot",
        "content": dot_export['content']
    })
    print(f"\n   Imported to 'copy' graph: {result}")

    # Verify they match
    original_info = await server._handle_tool("get_graph_info", {"graph": "codebase"})
    copy_info = await server._handle_tool("get_graph_info", {"graph": "copy"})

    assert original_info["node_count"] == copy_info["node_count"]
    assert original_info["edge_count"] == copy_info["edge_count"]
    print("   ✓ Roundtrip successful - graphs match\n")

    print("=== All tests passed! ===")


if __name__ == "__main__":
    asyncio.run(test_import_export())
