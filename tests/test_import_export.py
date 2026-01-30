"""Tests for graph import/export functionality."""

import pytest

from src.mcp_graph_engine.graph_engine import GraphEngine


class TestDOTFormat:
    """Tests for DOT format import/export."""

    def test_export_dot_basic(self):
        """Test basic DOT export."""
        engine = GraphEngine()
        engine.add_node("A", node_type="class")
        engine.add_node("B", node_type="class")
        engine.add_edge("A", "B", "calls")

        dot_content = engine.export_graph("dot")

        assert "digraph" in dot_content
        assert "A" in dot_content
        assert "B" in dot_content
        assert "calls" in dot_content

    def test_import_dot_basic(self):
        """Test basic DOT import."""
        engine = GraphEngine()

        dot_content = """
        digraph test {
            A -> B [label="calls"];
            B -> C [label="uses"];
        }
        """

        result = engine.import_graph("dot", dot_content)

        assert result["nodes_added"] == 3
        assert result["edges_added"] == 2
        assert "A" in engine.graph
        assert "B" in engine.graph
        assert "C" in engine.graph

    def test_import_dot_with_types(self):
        """Test DOT import with node types."""
        engine = GraphEngine()

        dot_content = """
        digraph test {
            A [type="controller"];
            B [type="service"];
            A -> B [label="depends_on"];
        }
        """

        result = engine.import_graph("dot", dot_content)

        assert result["nodes_added"] == 2
        assert engine.graph.nodes["A"]["type"] == "controller"
        assert engine.graph.nodes["B"]["type"] == "service"

    def test_roundtrip_dot(self):
        """Test export then import produces equivalent graph."""
        engine1 = GraphEngine()
        engine1.add_node("AuthController", node_type="controller")
        engine1.add_node("AuthService", node_type="service")
        engine1.add_node("UserRepository", node_type="repository")
        engine1.add_edge("AuthController", "AuthService", "calls")
        engine1.add_edge("AuthService", "UserRepository", "uses")

        # Export
        dot_content = engine1.export_graph("dot")

        # Import into new graph
        engine2 = GraphEngine()
        result = engine2.import_graph("dot", dot_content)

        # Verify
        assert result["nodes_added"] == 3
        assert result["edges_added"] == 2
        assert engine1.graph.number_of_nodes() == engine2.graph.number_of_nodes()
        assert engine1.graph.number_of_edges() == engine2.graph.number_of_edges()


class TestCSVFormat:
    """Tests for CSV format import/export."""

    def test_export_csv_basic(self):
        """Test basic CSV export."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_edge("A", "B", "calls")

        csv_content = engine.export_graph("csv")

        assert "source,target,relation" in csv_content
        assert "A,B,calls" in csv_content

    def test_import_csv_basic(self):
        """Test basic CSV import."""
        engine = GraphEngine()

        csv_content = """source,target,relation
AuthController,AuthService,calls
AuthService,UserRepository,uses
UserRepository,Database,queries"""

        result = engine.import_graph("csv", csv_content)

        assert result["nodes_added"] == 4
        assert result["edges_added"] == 3
        assert "AuthController" in engine.graph
        assert "Database" in engine.graph

    def test_import_csv_missing_relation(self):
        """Test CSV import with missing relation column."""
        engine = GraphEngine()

        csv_content = """source,target
A,B
B,C"""

        result = engine.import_graph("csv", csv_content)

        assert result["nodes_added"] == 3
        assert result["edges_added"] == 2
        # Should default to 'edge' relation
        edge_data = engine.graph.get_edge_data("A", "B")
        assert edge_data["relation"] == "edge"

    def test_roundtrip_csv(self):
        """Test export then import produces equivalent graph."""
        engine1 = GraphEngine()
        engine1.add_node("A")
        engine1.add_node("B")
        engine1.add_node("C")
        engine1.add_edge("A", "B", "depends_on")
        engine1.add_edge("B", "C", "imports")

        # Export
        csv_content = engine1.export_graph("csv")

        # Import into new graph
        engine2 = GraphEngine()
        result = engine2.import_graph("csv", csv_content)

        # Verify
        assert result["nodes_added"] == 3
        assert result["edges_added"] == 2
        assert engine1.graph.number_of_edges() == engine2.graph.number_of_edges()


class TestJSONFormat:
    """Tests for JSON format import/export."""

    def test_export_json_basic(self):
        """Test basic JSON export."""
        engine = GraphEngine()
        engine.add_node("A", node_type="class")
        engine.add_node("B", node_type="function")
        engine.add_edge("A", "B", "calls")

        json_content = engine.export_graph("json")

        assert '"label": "A"' in json_content
        assert '"type": "class"' in json_content
        assert '"relation": "calls"' in json_content

    def test_import_json_basic(self):
        """Test basic JSON import."""
        engine = GraphEngine()

        json_content = """{
            "nodes": [
                {"label": "AuthController", "type": "controller"},
                {"label": "AuthService", "type": "service"}
            ],
            "edges": [
                {"source": "AuthController", "target": "AuthService", "relation": "calls"}
            ]
        }"""

        result = engine.import_graph("json", json_content)

        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert engine.graph.nodes["AuthController"]["type"] == "controller"

    def test_import_json_with_properties(self):
        """Test JSON import with node and edge properties."""
        engine = GraphEngine()

        json_content = """{
            "nodes": [
                {"label": "A", "type": "class", "properties": {"file": "a.py"}},
                {"label": "B", "type": "class", "properties": {"file": "b.py"}}
            ],
            "edges": [
                {"source": "A", "target": "B", "relation": "imports", "properties": {"line": 5}}
            ]
        }"""

        result = engine.import_graph("json", json_content)

        assert result["nodes_added"] == 2
        assert engine.graph.nodes["A"]["file"] == "a.py"
        assert engine.graph.edges["A", "B"]["line"] == 5

    def test_roundtrip_json(self):
        """Test export then import produces equivalent graph."""
        engine1 = GraphEngine()
        engine1.add_node("A", node_type="class", properties={"file": "a.py"})
        engine1.add_node("B", node_type="function", properties={"file": "b.py"})
        engine1.add_edge("A", "B", "calls", properties={"line": 10})

        # Export
        json_content = engine1.export_graph("json")

        # Import into new graph
        engine2 = GraphEngine()
        result = engine2.import_graph("json", json_content)

        # Verify nodes
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert engine2.graph.nodes["A"]["type"] == "class"
        assert engine2.graph.nodes["A"]["file"] == "a.py"
        assert engine2.graph.edges["A", "B"]["line"] == 10


class TestGraphMLFormat:
    """Tests for GraphML format import/export."""

    def test_export_graphml_basic(self):
        """Test basic GraphML export."""
        engine = GraphEngine()
        engine.add_node("A", node_type="class")
        engine.add_node("B", node_type="class")
        engine.add_edge("A", "B", "calls")

        graphml_content = engine.export_graph("graphml")

        assert '<?xml version' in graphml_content
        assert 'graphml' in graphml_content
        assert 'A' in graphml_content
        assert 'B' in graphml_content

    def test_import_graphml_basic(self):
        """Test basic GraphML import."""
        engine = GraphEngine()

        # Create a simple GraphML document
        graphml_content = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B"/>
  </graph>
</graphml>"""

        result = engine.import_graph("graphml", graphml_content)

        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert "A" in engine.graph
        assert "B" in engine.graph

    def test_roundtrip_graphml(self):
        """Test export then import produces equivalent graph."""
        engine1 = GraphEngine()
        engine1.add_node("NodeA", node_type="class")
        engine1.add_node("NodeB", node_type="function")
        engine1.add_edge("NodeA", "NodeB", "calls")

        # Export
        graphml_content = engine1.export_graph("graphml")

        # Import into new graph
        engine2 = GraphEngine()
        result = engine2.import_graph("graphml", graphml_content)

        # Verify
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert engine1.graph.number_of_nodes() == engine2.graph.number_of_nodes()
        assert engine1.graph.number_of_edges() == engine2.graph.number_of_edges()


class TestImportMerging:
    """Tests for import merging behavior."""

    def test_import_merges_into_existing_graph(self):
        """Test that import merges into existing graph rather than replacing."""
        engine = GraphEngine()

        # Add initial nodes
        engine.add_node("Existing1")
        engine.add_node("Existing2")
        engine.add_edge("Existing1", "Existing2", "relates")

        # Import more nodes
        csv_content = """source,target,relation
New1,New2,calls"""

        engine.import_graph("csv", csv_content)

        # Should have 4 nodes total (2 existing + 2 new)
        assert engine.graph.number_of_nodes() == 4
        assert "Existing1" in engine.graph
        assert "New1" in engine.graph

        # Should have 2 edges total
        assert engine.graph.number_of_edges() == 2

    def test_import_creates_graph_if_doesnt_exist(self):
        """Test that import creates a new graph if it doesn't exist."""
        engine = GraphEngine()

        json_content = """{
            "nodes": [{"label": "A"}],
            "edges": []
        }"""

        result = engine.import_graph("json", json_content)

        assert result["nodes_added"] == 1
        assert "A" in engine.graph


class TestErrorHandling:
    """Tests for error handling in import/export."""

    def test_invalid_format_import(self):
        """Test that invalid format raises error."""
        engine = GraphEngine()

        with pytest.raises(ValueError, match="Unsupported import format"):
            engine.import_graph("invalid_format", "content")

    def test_invalid_format_export(self):
        """Test that invalid format raises error."""
        engine = GraphEngine()

        with pytest.raises(ValueError, match="Unsupported export format"):
            engine.export_graph("invalid_format")

    def test_invalid_csv_format(self):
        """Test that CSV without required columns raises error."""
        engine = GraphEngine()

        csv_content = """invalid,headers
A,B"""

        with pytest.raises(ValueError, match="must have 'source' and 'target' columns"):
            engine.import_graph("csv", csv_content)

    def test_malformed_json(self):
        """Test that malformed JSON raises error."""
        engine = GraphEngine()

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            engine.import_graph("json", "not valid json{")

    def test_malformed_dot(self):
        """Test that malformed DOT raises error."""
        engine = GraphEngine()

        with pytest.raises(ValueError, match="Failed to parse DOT"):
            engine.import_graph("dot", "not valid dot syntax {{{")


class TestComplexScenarios:
    """Tests for complex import/export scenarios."""

    def test_large_graph_roundtrip(self):
        """Test roundtrip with a larger graph."""
        engine1 = GraphEngine()

        # Create a graph with many nodes and edges
        for i in range(20):
            engine1.add_node(f"Node{i}", node_type="class")

        for i in range(19):
            engine1.add_edge(f"Node{i}", f"Node{i+1}", "connects")

        # Add some cross-edges
        engine1.add_edge("Node0", "Node10", "shortcut")
        engine1.add_edge("Node5", "Node15", "shortcut")

        # Test with each format
        for format_name in ["json", "csv", "dot", "graphml"]:
            # Export
            content = engine1.export_graph(format_name)

            # Import into new graph
            engine2 = GraphEngine()
            engine2.import_graph(format_name, content)

            # Verify counts
            assert engine1.graph.number_of_nodes() == engine2.graph.number_of_nodes(), \
                f"Node count mismatch for {format_name}"
            assert engine1.graph.number_of_edges() == engine2.graph.number_of_edges(), \
                f"Edge count mismatch for {format_name}"

    def test_import_multiple_formats_sequential(self):
        """Test importing multiple formats into same graph."""
        engine = GraphEngine()

        # Import JSON
        json_content = """{
            "nodes": [{"label": "A"}, {"label": "B"}],
            "edges": [{"source": "A", "target": "B", "relation": "r1"}]
        }"""
        result1 = engine.import_graph("json", json_content)
        assert result1["nodes_added"] == 2
        assert result1["edges_added"] == 1

        # Import CSV (should merge)
        csv_content = """source,target,relation
B,C,r2
C,D,r3"""
        result2 = engine.import_graph("csv", csv_content)
        assert result2["nodes_added"] == 2  # C and D are new
        assert result2["edges_added"] == 2

        # Verify total
        assert engine.graph.number_of_nodes() == 4
        assert engine.graph.number_of_edges() == 3

    def test_export_empty_graph(self):
        """Test exporting an empty graph."""
        engine = GraphEngine()

        for format_name in ["json", "csv", "dot", "graphml"]:
            content = engine.export_graph(format_name)
            assert content is not None

            # Should be able to import back
            engine2 = GraphEngine()
            result = engine2.import_graph(format_name, content)
            assert result["nodes_added"] == 0
            assert result["edges_added"] == 0


class TestMermaidFormat:
    """Tests for Mermaid format export."""

    def test_export_mermaid_basic(self):
        """Test basic Mermaid export."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_node("C")
        engine.add_edge("A", "B", "connects")
        engine.add_edge("B", "C", "links")

        result = engine.export_graph("mermaid")

        assert "graph TD" in result
        assert "A -->|connects| B" in result
        assert "B -->|links| C" in result

    def test_export_mermaid_empty(self):
        """Test Mermaid export of empty graph."""
        engine = GraphEngine()
        result = engine.export_graph("mermaid")
        assert result == "graph TD\n"

    def test_export_mermaid_spaces_in_labels(self):
        """Test Mermaid export with spaces in node labels."""
        engine = GraphEngine()
        engine.add_node("User Service")
        engine.add_node("Auth Service")
        engine.add_edge("User Service", "Auth Service", "calls")

        result = engine.export_graph("mermaid")

        assert "graph TD" in result
        # Should have bracket syntax for labels with spaces
        assert 'User_Service["User Service"]' in result
        assert 'Auth_Service["Auth Service"]' in result
        assert "calls" in result

    def test_export_mermaid_special_chars_in_relation(self):
        """Test Mermaid export with pipe in relation."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_edge("A", "B", "read|write")

        result = engine.export_graph("mermaid")

        # Pipe should be escaped
        assert "&#124;" in result
        assert "read&#124;write" in result

    def test_mermaid_roundtrip(self):
        """Test import then export preserves structure."""
        # Note: This tests the structure is preserved through export
        # We already have create_from_mermaid for import
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_edge("A", "B", "calls")

        # Export
        result = engine.export_graph("mermaid")

        # Should have expected structure
        assert "graph TD" in result
        assert "A" in result
        assert "B" in result
        assert "calls" in result
        assert "-->" in result


class TestFileBasedImport:
    """Tests for file-based import functionality."""

    def test_import_from_file_reads_content(self, tmp_path):
        """Test that importing from a file reads the file content."""
        import asyncio
        import json

        from src.mcp_graph_engine.server import GraphServer

        # Create a test file with graph data
        file_path = tmp_path / "test_import.json"
        test_data = {
            "nodes": [
                {"label": "A", "type": "class"},
                {"label": "B", "type": "function"}
            ],
            "edges": [
                {"source": "A", "target": "B", "relation": "calls"}
            ]
        }
        file_path.write_text(json.dumps(test_data), encoding="utf-8")

        # Import from file
        server = GraphServer()
        result = asyncio.run(server._handle_tool("import_graph", {
            "format": "json",
            "file_path": str(file_path)
        }))

        # Verify import succeeded
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert result["source"] == f"file '{file_path}'"

        # Verify graph was updated
        graph = server.session_manager.get_graph("default")
        assert "A" in graph.graph
        assert "B" in graph.graph
        assert graph.graph.nodes["A"]["type"] == "class"

    def test_import_without_file_path_uses_content(self):
        """Test that import without file_path uses content parameter (existing behavior)."""
        import asyncio
        import json

        from src.mcp_graph_engine.server import GraphServer

        # Import with content parameter
        server = GraphServer()
        test_data = {
            "nodes": [{"label": "X"}, {"label": "Y"}],
            "edges": [{"source": "X", "target": "Y", "relation": "links"}]
        }
        result = asyncio.run(server._handle_tool("import_graph", {
            "format": "json",
            "content": json.dumps(test_data)
        }))

        # Verify import succeeded
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert result["source"] == "inline content"

        # Verify graph was updated
        graph = server.session_manager.get_graph("default")
        assert "X" in graph.graph
        assert "Y" in graph.graph

    def test_import_with_both_file_path_and_content_raises_error(self):
        """Test that providing both file_path and content raises ValueError."""
        import asyncio

        from src.mcp_graph_engine.server import GraphServer

        server = GraphServer()
        with pytest.raises(ValueError, match="Provide either file_path or content, not both"):
            asyncio.run(server._handle_tool("import_graph", {
                "format": "json",
                "file_path": "/some/path.json",
                "content": '{"nodes": [], "edges": []}'
            }))

    def test_import_with_neither_file_path_nor_content_raises_error(self):
        """Test that providing neither file_path nor content raises ValueError."""
        import asyncio

        from src.mcp_graph_engine.server import GraphServer

        server = GraphServer()
        with pytest.raises(ValueError, match="Must provide either file_path or content"):
            asyncio.run(server._handle_tool("import_graph", {
                "format": "json"
            }))

    def test_import_from_nonexistent_file_raises_error(self, tmp_path):
        """Test that importing from a nonexistent file raises FileNotFoundError."""
        import asyncio

        from src.mcp_graph_engine.server import GraphServer

        server = GraphServer()
        nonexistent_path = tmp_path / "does_not_exist.json"

        with pytest.raises(FileNotFoundError, match="File not found"):
            asyncio.run(server._handle_tool("import_graph", {
                "format": "json",
                "file_path": str(nonexistent_path)
            }))

    def test_import_from_directory_raises_error(self, tmp_path):
        """Test that importing from a directory raises ValueError."""
        import asyncio

        from src.mcp_graph_engine.server import GraphServer

        server = GraphServer()

        with pytest.raises(ValueError, match="Path is not a file"):
            asyncio.run(server._handle_tool("import_graph", {
                "format": "json",
                "file_path": str(tmp_path)
            }))

    def test_import_from_file_all_formats(self, tmp_path):
        """Test that import from file works with all supported formats."""
        import asyncio
        import json

        from src.mcp_graph_engine.server import GraphServer

        # Test JSON format
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "nodes": [{"label": "A"}],
            "edges": []
        }), encoding="utf-8")

        server = GraphServer()
        result = asyncio.run(server._handle_tool("import_graph", {
            "format": "json",
            "file_path": str(json_path)
        }))
        assert result["nodes_added"] == 1
        assert result["source"] == f"file '{json_path}'"

        # Test CSV format
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("source,target,relation\nA,B,calls\n", encoding="utf-8")

        server2 = GraphServer()
        result = asyncio.run(server2._handle_tool("import_graph", {
            "format": "csv",
            "file_path": str(csv_path)
        }))
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert result["source"] == f"file '{csv_path}'"

        # Test DOT format
        dot_path = tmp_path / "test.dot"
        dot_path.write_text("digraph test { A -> B; }", encoding="utf-8")

        server3 = GraphServer()
        result = asyncio.run(server3._handle_tool("import_graph", {
            "format": "dot",
            "file_path": str(dot_path)
        }))
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert result["source"] == f"file '{dot_path}'"

        # Test GraphML format
        graphml_path = tmp_path / "test.graphml"
        graphml_path.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B"/>
  </graph>
</graphml>""", encoding="utf-8")

        server4 = GraphServer()
        result = asyncio.run(server4._handle_tool("import_graph", {
            "format": "graphml",
            "file_path": str(graphml_path)
        }))
        assert result["nodes_added"] == 2
        assert result["edges_added"] == 1
        assert result["source"] == f"file '{graphml_path}'"


class TestFileBasedExport:
    """Tests for file-based export functionality."""

    def test_export_to_file_creates_file_with_correct_content(self, tmp_path):
        """Test that exporting to a file creates the file with correct content."""
        import asyncio
        import json

        from src.mcp_graph_engine.server import GraphServer

        # Create a graph with some content
        server = GraphServer()
        graph = server.session_manager.get_graph("default")
        graph.add_node("A", node_type="class")
        graph.add_node("B", node_type="class")
        graph.add_edge("A", "B", "calls")

        # Export to file
        file_path = tmp_path / "test_export.json"
        result = asyncio.run(server._handle_tool("export_graph", {
            "format": "json",
            "file_path": str(file_path)
        }))

        # Verify result contains metadata, not content
        assert "file_path" in result
        assert "format" in result
        assert "bytes_written" in result
        assert "content" not in result
        assert result["format"] == "json"
        assert result["bytes_written"] > 0

        # Verify file was created
        assert file_path.exists()

        # Verify file content is correct
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_export_without_file_path_returns_content_inline(self):
        """Test that export without file_path returns content inline (existing behavior)."""
        import asyncio
        import json

        from src.mcp_graph_engine.server import GraphServer

        # Create a graph with some content
        server = GraphServer()
        graph = server.session_manager.get_graph("default")
        graph.add_node("A", node_type="class")
        graph.add_node("B", node_type="class")
        graph.add_edge("A", "B", "calls")

        # Export without file_path
        result = asyncio.run(server._handle_tool("export_graph", {
            "format": "json"
        }))

        # Verify result contains content, not metadata
        assert "content" in result
        assert "file_path" not in result
        assert "bytes_written" not in result

        # Verify content is correct
        data = json.loads(result["content"])
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_export_to_file_creates_parent_directories(self, tmp_path):
        """Test that export to file creates parent directories if needed."""
        import asyncio

        from src.mcp_graph_engine.server import GraphServer

        # Create a graph
        server = GraphServer()
        graph = server.session_manager.get_graph("default")
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B", "connects")

        # Export to a nested path that doesn't exist yet
        nested_path = tmp_path / "subdir1" / "subdir2" / "export.csv"
        result = asyncio.run(server._handle_tool("export_graph", {
            "format": "csv",
            "file_path": str(nested_path)
        }))

        # Verify directories were created
        assert nested_path.parent.exists()
        assert nested_path.exists()

        # Verify result
        assert result["file_path"] == str(nested_path)
        assert result["format"] == "csv"

    def test_export_to_file_all_formats(self, tmp_path):
        """Test that export to file works with all supported formats."""
        import asyncio

        from src.mcp_graph_engine.server import GraphServer

        formats = ["json", "csv", "dot", "graphml", "mermaid"]

        for fmt in formats:
            # Create a fresh graph for each format
            server = GraphServer()
            graph = server.session_manager.get_graph("default")
            graph.add_node("X")
            graph.add_node("Y")
            graph.add_edge("X", "Y", "links")

            # Export to file
            file_path = tmp_path / f"test_export.{fmt}"
            result = asyncio.run(server._handle_tool("export_graph", {
                "format": fmt,
                "file_path": str(file_path)
            }))

            # Verify file was created
            assert file_path.exists(), f"File not created for format: {fmt}"
            assert result["format"] == fmt
            assert result["bytes_written"] > 0

            # Verify content is not empty
            content = file_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Empty content for format: {fmt}"
