"""Integration tests for server import/export handlers."""

import json

import pytest

from src.mcp_graph_engine.server import GraphServer


class TestServerImportExport:
    """Integration tests for import/export through the server."""

    @pytest.fixture
    def server(self):
        """Create a GraphServer instance."""
        return GraphServer()

    @pytest.mark.asyncio
    async def test_import_export_json_integration(self, server):
        """Test JSON import and export through server handlers."""

        # Import graph
        json_content = """{
            "nodes": [
                {"label": "A", "type": "class"},
                {"label": "B", "type": "function"}
            ],
            "edges": [
                {"source": "A", "target": "B", "relation": "calls"}
            ]
        }"""

        import_result = await server._handle_tool("import_graph", {
            "graph": "test",
            "format": "json",
            "content": json_content
        })

        assert import_result["nodes_added"] == 2
        assert import_result["edges_added"] == 1

        # Export graph
        export_result = await server._handle_tool("export_graph", {
            "graph": "test",
            "format": "json"
        })

        assert "content" in export_result
        exported_data = json.loads(export_result["content"])
        assert len(exported_data["nodes"]) == 2
        assert len(exported_data["edges"]) == 1

    @pytest.mark.asyncio
    async def test_import_csv_integration(self, server):
        """Test CSV import through server handlers."""

        csv_content = """source,target,relation
Node1,Node2,depends_on
Node2,Node3,uses"""

        result = await server._handle_tool("import_graph", {
            "format": "csv",
            "content": csv_content
        })

        assert result["nodes_added"] == 3
        assert result["edges_added"] == 2

        # Verify nodes were created via graph info
        info_result = await server._handle_tool("get_graph_info", {})
        assert info_result["node_count"] == 3

    @pytest.mark.asyncio
    async def test_import_dot_integration(self, server):
        """Test DOT import through server handlers."""

        dot_content = """
        digraph test {
            X -> Y [label="connects"];
            Y -> Z [label="links"];
        }
        """

        result = await server._handle_tool("import_graph", {
            "graph": "dot_test",
            "format": "dot",
            "content": dot_content
        })

        assert result["nodes_added"] == 3
        assert result["edges_added"] == 2

    @pytest.mark.asyncio
    async def test_export_csv_integration(self, server):
        """Test CSV export through server handlers."""

        # Add some nodes and edges using import
        json_content = """{
            "nodes": [
                {"label": "A"},
                {"label": "B"}
            ],
            "edges": [
                {"source": "A", "target": "B", "relation": "connects"}
            ]
        }"""
        await server._handle_tool("import_graph", {
            "format": "json",
            "content": json_content
        })

        # Export as CSV
        result = await server._handle_tool("export_graph", {
            "format": "csv"
        })

        assert "content" in result
        assert "source,target,relation" in result["content"]
        assert "A,B,connects" in result["content"]

    @pytest.mark.asyncio
    async def test_export_dot_integration(self, server):
        """Test DOT export through server handlers."""

        # Add some nodes and edges using import
        json_content = """{
            "nodes": [
                {"label": "NodeA", "type": "class"},
                {"label": "NodeB", "type": "function"}
            ],
            "edges": [
                {"source": "NodeA", "target": "NodeB", "relation": "calls"}
            ]
        }"""
        await server._handle_tool("import_graph", {
            "format": "json",
            "content": json_content
        })

        # Export as DOT
        result = await server._handle_tool("export_graph", {
            "format": "dot"
        })

        assert "content" in result
        assert "digraph" in result["content"]
        assert "NodeA" in result["content"]
        assert "NodeB" in result["content"]
        assert "calls" in result["content"]

    @pytest.mark.asyncio
    async def test_roundtrip_through_server(self, server):
        """Test full roundtrip: import graph, export, import to new graph."""

        # Create initial graph using import
        initial_json = """{
            "nodes": [
                {"label": "A", "type": "class"},
                {"label": "B", "type": "function"},
                {"label": "C", "type": "module"}
            ],
            "edges": [
                {"source": "A", "target": "B", "relation": "calls"},
                {"source": "B", "target": "C", "relation": "imports"}
            ]
        }"""
        await server._handle_tool("import_graph", {
            "graph": "original",
            "format": "json",
            "content": initial_json
        })

        # Export
        export_result = await server._handle_tool("export_graph", {
            "graph": "original",
            "format": "json"
        })

        # Import to new graph
        import_result = await server._handle_tool("import_graph", {
            "graph": "copy",
            "format": "json",
            "content": export_result["content"]
        })

        assert import_result["nodes_added"] == 3
        assert import_result["edges_added"] == 2

        # Verify both graphs have same structure
        original_info = await server._handle_tool("get_graph_info", {"graph": "original"})
        copy_info = await server._handle_tool("get_graph_info", {"graph": "copy"})

        assert original_info["node_count"] == copy_info["node_count"]
        assert original_info["edge_count"] == copy_info["edge_count"]

    @pytest.mark.asyncio
    async def test_invalid_format_error(self, server):
        """Test that invalid format raises proper error."""

        with pytest.raises(ValueError, match="Unsupported import format"):
            await server._handle_tool("import_graph", {
                "format": "invalid",
                "content": "data"
            })

        with pytest.raises(ValueError, match="Unsupported export format"):
            await server._handle_tool("export_graph", {
                "format": "invalid"
            })
