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

        result = engine.import_graph("csv", csv_content)

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
            result = engine2.import_graph(format_name, content)

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
