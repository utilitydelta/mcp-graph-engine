#!/usr/bin/env python3
"""Demo script showing all supported import/export formats."""

import asyncio
from src.mcp_graph_engine.server import GraphServer


async def demo_formats():
    """Demonstrate all import/export formats."""
    server = GraphServer()

    print("=" * 70)
    print("MCP Graph Engine - Import/Export Format Demonstration")
    print("=" * 70)

    # === DOT Format ===
    print("\n1. DOT Format (GraphViz)")
    print("-" * 70)

    dot_content = """digraph codebase {
    AuthController -> AuthService [label="calls"];
    AuthService -> UserRepository [label="uses"];
    UserRepository -> Database [label="queries"];
}"""

    print("Import content:")
    print(dot_content)

    result = await server._handle_tool("import_graph", {
        "graph": "demo",
        "format": "dot",
        "content": dot_content
    })
    print(f"\nImport result: {result['nodes_added']} nodes, {result['edges_added']} edges added")

    export_result = await server._handle_tool("export_graph", {
        "graph": "demo",
        "format": "dot"
    })
    print("\nExport result:")
    print(export_result["content"])

    # === CSV Format ===
    print("\n2. CSV Edge List Format")
    print("-" * 70)

    await server._handle_tool("delete_graph", {"graph": "demo"})

    csv_content = """source,target,relation
AuthController,AuthService,calls
AuthService,UserRepository,uses
UserRepository,Database,queries"""

    print("Import content:")
    print(csv_content)

    result = await server._handle_tool("import_graph", {
        "graph": "demo",
        "format": "csv",
        "content": csv_content
    })
    print(f"\nImport result: {result['nodes_added']} nodes, {result['edges_added']} edges added")

    export_result = await server._handle_tool("export_graph", {
        "graph": "demo",
        "format": "csv"
    })
    print("\nExport result:")
    print(export_result["content"])

    # === JSON Format ===
    print("3. JSON Format")
    print("-" * 70)

    await server._handle_tool("delete_graph", {"graph": "demo"})

    json_content = """{
  "nodes": [
    {"label": "AuthController", "type": "controller"},
    {"label": "AuthService", "type": "service"},
    {"label": "UserRepository", "type": "repository"},
    {"label": "Database", "type": "database"}
  ],
  "edges": [
    {"source": "AuthController", "target": "AuthService", "relation": "calls"},
    {"source": "AuthService", "target": "UserRepository", "relation": "uses"},
    {"source": "UserRepository", "target": "Database", "relation": "queries"}
  ]
}"""

    print("Import content:")
    print(json_content)

    result = await server._handle_tool("import_graph", {
        "graph": "demo",
        "format": "json",
        "content": json_content
    })
    print(f"\nImport result: {result['nodes_added']} nodes, {result['edges_added']} edges added")

    export_result = await server._handle_tool("export_graph", {
        "graph": "demo",
        "format": "json"
    })
    print("\nExport result:")
    print(export_result["content"])

    # === GraphML Format ===
    print("\n4. GraphML Format")
    print("-" * 70)

    print("Exporting to GraphML...")
    export_result = await server._handle_tool("export_graph", {
        "graph": "demo",
        "format": "graphml"
    })
    print("\nExport result (truncated):")
    print(export_result["content"][:500] + "...")

    # Test reimport
    await server._handle_tool("delete_graph", {"graph": "demo"})
    result = await server._handle_tool("import_graph", {
        "graph": "demo",
        "format": "graphml",
        "content": export_result["content"]
    })
    print(f"\nReimport successful: {result['nodes_added']} nodes, {result['edges_added']} edges")

    print("\n" + "=" * 70)
    print("All formats demonstrated successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_formats())
