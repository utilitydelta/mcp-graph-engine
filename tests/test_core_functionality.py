"""Core functionality tests covering graph operations, analysis tools, and edge cases."""

import pytest

from src.mcp_graph_engine.graph_engine import GraphEngine
from src.mcp_graph_engine.session import SessionManager


class TestBasicGraphOperations:
    """Test basic node and edge operations."""

    def test_add_node_creates_new(self):
        """Test that adding a new node returns created=True."""
        engine = GraphEngine()
        node_data, created = engine.add_node("TestNode", "class")
        assert created is True
        assert node_data["label"] == "TestNode"
        assert node_data["type"] == "class"

    def test_add_node_idempotent(self):
        """Test that adding existing node returns created=False."""
        engine = GraphEngine()
        engine.add_node("TestNode")
        node_data, created = engine.add_node("TestNode")
        assert created is False

    def test_add_nodes_batch(self):
        """Test batch node addition."""
        engine = GraphEngine()
        nodes = [
            {"label": "A", "type": "class"},
            {"label": "B", "type": "function"},
            {"label": "A", "type": "class"}  # Duplicate
        ]
        added, existing = engine.add_nodes(nodes)
        assert added == 2
        assert existing == 1

    def test_remove_node_with_edges(self):
        """Test that removing a node also removes its edges."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_node("C")
        engine.add_edge("A", "B", "connects")
        engine.add_edge("B", "C", "links")

        success, edges_removed = engine.remove_node("B")
        assert success is True
        assert edges_removed == 2  # One in, one out

    def test_list_nodes_with_filter(self):
        """Test listing nodes with type filter."""
        engine = GraphEngine()
        engine.add_node("A", "class")
        engine.add_node("B", "function")
        engine.add_node("C", "class")

        classes = engine.list_nodes(type_filter="class")
        assert len(classes) == 2
        assert all(n["type"] == "class" for n in classes)


class TestEdgeOperations:
    """Test edge operations and fuzzy matching."""

    def test_add_edge_to_empty_graph_fails(self):
        """Test that adding edge to empty graph gives helpful error."""
        engine = GraphEngine()
        with pytest.raises(ValueError, match="graph is empty"):
            engine.add_edge("A", "B", "connects")

    def test_add_edge_with_fuzzy_matching(self):
        """Test that fuzzy matching works for edges."""
        engine = GraphEngine()
        engine.add_node("AuthService")
        engine.add_node("UserRepo")

        # Fuzzy match should find the nodes
        edge_data, created, src, tgt = engine.add_edge("auth service", "user repo", "uses")
        assert src == "AuthService"
        assert tgt == "UserRepo"
        assert created is True

    def test_add_edge_missing_node_error(self):
        """Test that missing nodes give helpful error message."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")

        with pytest.raises(ValueError, match="not found.*Available.*Use find_node"):
            engine.add_edge("A", "NonExistent", "connects")

    def test_self_loop_allowed(self):
        """Test that self-loops are allowed."""
        engine = GraphEngine()
        engine.add_node("A")
        edge_data, created, src, tgt = engine.add_edge("A", "A", "self_reference")
        assert created is True
        assert src == tgt == "A"


class TestPathFinding:
    """Test path-finding algorithms."""

    def test_shortest_path_basic(self):
        """Test shortest path between nodes."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_node("C")
        engine.add_edge("A", "B", "connects")
        engine.add_edge("B", "C", "connects")

        result = engine.shortest_path("A", "C")
        assert result["path"] == ["A", "B", "C"]
        assert result["length"] == 2

    def test_shortest_path_self_loop(self):
        """Test shortest path from node to itself."""
        engine = GraphEngine()
        engine.add_node("A")

        result = engine.shortest_path("A", "A")
        assert result["path"] == ["A"]
        assert result["length"] == 0

    def test_shortest_path_no_path_exists(self):
        """Test shortest path when nodes are disconnected."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")

        result = engine.shortest_path("A", "B")
        assert result["path"] is None
        assert "disconnected" in result["reason"].lower()

    def test_shortest_path_empty_graph(self):
        """Test shortest path on empty graph."""
        engine = GraphEngine()
        result = engine.shortest_path("A", "B")
        assert result["path"] is None
        assert "empty" in result["reason"].lower()

    def test_all_paths_multiple(self):
        """Test finding all paths between nodes."""
        engine = GraphEngine()
        # Create diamond: A -> B -> D, A -> C -> D
        engine.add_nodes([
            {"label": "A"},
            {"label": "B"},
            {"label": "C"},
            {"label": "D"}
        ])
        engine.add_edge("A", "B", "path1")
        engine.add_edge("A", "C", "path2")
        engine.add_edge("B", "D", "path1")
        engine.add_edge("C", "D", "path2")

        result = engine.all_paths("A", "D")
        assert result["count"] == 2
        assert ["A", "B", "D"] in result["paths"]
        assert ["A", "C", "D"] in result["paths"]


class TestAnalysisTools:
    """Test graph analysis algorithms."""

    def test_pagerank_basic(self):
        """Test PageRank calculation."""
        engine = GraphEngine()
        engine.add_nodes([{"label": "A"}, {"label": "B"}, {"label": "C"}])
        engine.add_edge("A", "C", "links")
        engine.add_edge("B", "C", "links")

        result = engine.pagerank(top_n=3)
        # Check for errors first to aid debugging
        assert "error" not in result, f"PageRank failed: {result.get('error')}"
        assert len(result["rankings"]) == 3, f"Expected 3 rankings, got {result}"
        # C should have highest PageRank (most incoming links)
        assert result["rankings"][0]["label"] == "C"

    def test_pagerank_empty_graph(self):
        """Test PageRank on empty graph."""
        engine = GraphEngine()
        result = engine.pagerank()
        assert result["rankings"] == []

    def test_connected_components(self):
        """Test connected components detection."""
        engine = GraphEngine()
        # Two disconnected components
        engine.add_nodes([{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}])
        engine.add_edge("A", "B", "connects")
        engine.add_edge("C", "D", "connects")

        result = engine.connected_components()
        assert result["count"] == 2
        assert ["A", "B"] in result["components"]
        assert ["C", "D"] in result["components"]

    def test_find_cycles(self):
        """Test cycle detection."""
        engine = GraphEngine()
        engine.add_nodes([{"label": "A"}, {"label": "B"}, {"label": "C"}])
        engine.add_edge("A", "B", "next")
        engine.add_edge("B", "C", "next")
        engine.add_edge("C", "A", "back")  # Creates cycle

        result = engine.find_cycles()
        assert result["has_cycles"] is True
        assert len(result["cycles"]) > 0

    def test_degree_centrality(self):
        """Test degree centrality calculation."""
        engine = GraphEngine()
        engine.add_nodes([{"label": "Hub"}, {"label": "A"}, {"label": "B"}])
        engine.add_edge("Hub", "A", "connects")
        engine.add_edge("Hub", "B", "connects")

        result = engine.degree_centrality(top_n=1)
        assert len(result["rankings"]) == 1
        # Hub should have highest out-degree
        assert result["rankings"][0]["label"] == "Hub"

    def test_subgraph_extraction(self):
        """Test subgraph extraction."""
        engine = GraphEngine()
        engine.add_nodes([{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}])
        engine.add_edge("A", "B", "connects")
        engine.add_edge("B", "C", "connects")
        engine.add_edge("C", "D", "connects")

        result = engine.subgraph(["A", "B", "C"])
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2  # A->B, B->C


class TestSessionManager:
    """Test multi-graph session management."""

    def test_default_graph_auto_created(self):
        """Test that default graph is auto-created."""
        manager = SessionManager()
        graph = manager.get_graph()
        assert graph is not None

    def test_named_graphs(self):
        """Test creating and managing named graphs."""
        manager = SessionManager()
        graph1 = manager.get_graph("graph1")
        graph2 = manager.get_graph("graph2")

        # Add different nodes to each
        graph1.add_node("A")
        graph2.add_node("B")

        # Verify isolation
        assert "A" in graph1.graph
        assert "A" not in graph2.graph

    def test_list_graphs(self):
        """Test listing all graphs."""
        manager = SessionManager()
        manager.get_graph("test1")
        manager.get_graph("test2")

        graphs = manager.list_graphs()
        assert len(graphs) >= 2
        names = [g["name"] for g in graphs]
        assert "test1" in names
        assert "test2" in names

    def test_delete_graph(self):
        """Test graph deletion."""
        manager = SessionManager()
        manager.get_graph("temp")

        success = manager.delete_graph("temp")
        assert success is True

        # Verify deleted
        graphs = manager.list_graphs()
        names = [g["name"] for g in graphs]
        assert "temp" not in names

    def test_get_graph_info_nonexistent(self):
        """Test that getting info for nonexistent graph gives helpful error."""
        manager = SessionManager()
        manager.get_graph("existing")

        with pytest.raises(ValueError, match="does not exist.*Available"):
            manager.get_graph_info("nonexistent")


class TestErrorMessages:
    """Test that error messages are LLM-friendly and actionable."""

    def test_add_edge_empty_graph_error(self):
        """Test error message for adding edge to empty graph."""
        engine = GraphEngine()
        try:
            engine.add_edge("A", "B", "connects")
        except ValueError as e:
            assert "empty" in str(e).lower()
            assert "add nodes first" in str(e).lower()

    def test_add_edge_node_not_found_suggests_alternatives(self):
        """Test that node not found error lists available nodes."""
        engine = GraphEngine()
        engine.add_node("Available1")
        engine.add_node("Available2")

        try:
            engine.add_edge("Available1", "Missing", "connects")
        except ValueError as e:
            assert "not found" in str(e)
            assert "Available1" in str(e) or "Available2" in str(e)
            assert "find_node" in str(e)

    def test_shortest_path_suggests_connected_components(self):
        """Test that no path error suggests using connected_components."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")

        result = engine.shortest_path("A", "B")
        assert "connected_components" in result.get("reason", "").lower()

    def test_import_empty_content_error(self):
        """Test that importing empty content gives clear error."""
        engine = GraphEngine()

        with pytest.raises(ValueError, match="content is empty"):
            engine.import_graph("json", "")

    def test_import_invalid_format_lists_supported(self):
        """Test that invalid format error lists supported formats."""
        engine = GraphEngine()

        with pytest.raises(ValueError, match="Supported formats"):
            engine.import_graph("invalid", "data")
