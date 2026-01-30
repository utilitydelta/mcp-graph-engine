"""Tests for the ask_graph natural language query tool."""

import pytest

from mcp_graph_engine.graph_engine import GraphEngine
from mcp_graph_engine.server import parse_ask_query


@pytest.fixture
def sample_graph():
    """Create a sample graph for testing."""
    graph = GraphEngine()

    # Create a simple dependency graph
    # AuthService -> UserRepository -> DatabasePool
    # LoginController -> AuthService
    # ConfigLoader -> DatabasePool
    # OrphanNode (isolated)
    # CycleA -> CycleB -> CycleC -> CycleA

    graph.add_node("AuthService", node_type="service")
    graph.add_node("UserRepository", node_type="repository")
    graph.add_node("DatabasePool", node_type="pool")
    graph.add_node("LoginController", node_type="controller")
    graph.add_node("ConfigLoader", node_type="loader")
    graph.add_node("OrphanNode", node_type="orphan")
    graph.add_node("CycleA")
    graph.add_node("CycleB")
    graph.add_node("CycleC")

    # Add edges
    graph.add_edge("AuthService", "UserRepository", "depends_on")
    graph.add_edge("UserRepository", "DatabasePool", "depends_on")
    graph.add_edge("LoginController", "AuthService", "uses")
    graph.add_edge("ConfigLoader", "DatabasePool", "configures")

    # Add cycle
    graph.add_edge("CycleA", "CycleB", "depends_on")
    graph.add_edge("CycleB", "CycleC", "depends_on")
    graph.add_edge("CycleC", "CycleA", "depends_on")

    return graph


class TestDependencyQueries:
    """Test dependency-related queries."""

    def test_what_depends_on(self, sample_graph):
        """Test 'what depends on X' query."""
        result = parse_ask_query("what depends on DatabasePool", sample_graph)
        assert "dependents" in result
        assert set(result["dependents"]) == {"UserRepository", "ConfigLoader"}
        assert "No incoming dependencies" not in result["result"]

    def test_what_depends_on_nothing(self, sample_graph):
        """Test 'what depends on X' when nothing depends on X."""
        result = parse_ask_query("what depends on LoginController", sample_graph)
        assert "No incoming dependencies" in result["result"]

    def test_what_depends_on_case_insensitive(self, sample_graph):
        """Test case insensitivity."""
        result = parse_ask_query("WHAT DEPENDS ON DatabasePool", sample_graph)
        assert "dependents" in result
        # Query is lowercased for matching, but should still work
        assert "databasepool" in result["interpretation"].lower()

    def test_what_does_x_depend_on(self, sample_graph):
        """Test 'what does X depend on' query."""
        result = parse_ask_query("what does AuthService depend on", sample_graph)
        assert "dependencies" in result
        assert result["dependencies"] == ["UserRepository"]

    def test_what_x_depends_on(self, sample_graph):
        """Test 'what X depends on' variation."""
        result = parse_ask_query("what AuthService depends on", sample_graph)
        assert "dependencies" in result
        assert result["dependencies"] == ["UserRepository"]

    def test_dependencies_of(self, sample_graph):
        """Test 'dependencies of X' query."""
        result = parse_ask_query("dependencies of AuthService", sample_graph)
        assert "dependencies" in result
        assert result["dependencies"] == ["UserRepository"]

    def test_dependents_of(self, sample_graph):
        """Test 'dependents of X' query (incoming edges)."""
        result = parse_ask_query("dependents of DatabasePool", sample_graph)
        assert "dependents" in result
        assert set(result["dependents"]) == {"UserRepository", "ConfigLoader"}

    def test_dependencies_of_leaf_node(self, sample_graph):
        """Test dependencies of a leaf node."""
        result = parse_ask_query("dependencies of DatabasePool", sample_graph)
        assert "has no outgoing dependencies" in result["result"]


class TestPathQueries:
    """Test path-finding queries."""

    def test_path_from_to(self, sample_graph):
        """Test 'path from X to Y' query."""
        result = parse_ask_query("path from LoginController to DatabasePool", sample_graph)
        assert result["path"] is not None
        assert result["path"] == ["LoginController", "AuthService", "UserRepository", "DatabasePool"]
        assert result["length"] == 3

    def test_shortest_path_from_to(self, sample_graph):
        """Test 'shortest path from X to Y' query."""
        result = parse_ask_query("shortest path from LoginController to DatabasePool", sample_graph)
        assert result["path"] is not None
        assert result["length"] == 3

    def test_how_to_get_from_to(self, sample_graph):
        """Test 'how to get from X to Y' query."""
        result = parse_ask_query("how to get from LoginController to DatabasePool", sample_graph)
        assert result["path"] is not None
        assert result["length"] == 3

    def test_path_not_found(self, sample_graph):
        """Test path query when no path exists."""
        result = parse_ask_query("path from DatabasePool to LoginController", sample_graph)
        assert result["path"] is None
        assert "reason" in result["result"].lower() or "no path" in result["result"].lower()

    def test_all_paths_from_to(self, sample_graph):
        """Test 'all paths from X to Y' query."""
        result = parse_ask_query("all paths from LoginController to DatabasePool", sample_graph)
        assert result["count"] > 0
        assert result["paths"] is not None
        # Should have exactly one path in this case
        assert result["count"] == 1

    def test_all_paths_no_paths(self, sample_graph):
        """Test 'all paths' when no paths exist."""
        result = parse_ask_query("all paths from DatabasePool to LoginController", sample_graph)
        assert result["count"] == 0
        assert result["paths"] == []


class TestAnalysisQueries:
    """Test analysis queries."""

    def test_cycles(self, sample_graph):
        """Test 'cycles' query."""
        result = parse_ask_query("cycles", sample_graph)
        assert result["has_cycles"] is True
        assert len(result["cycles"]) > 0
        # Should find the cycle we created
        assert any("CycleA" in str(cycle) for cycle in result["cycles"])

    def test_find_cycles(self, sample_graph):
        """Test 'find cycles' query variation."""
        result = parse_ask_query("find cycles", sample_graph)
        assert result["has_cycles"] is True

    def test_what_are_the_cycles(self, sample_graph):
        """Test 'what are the cycles' query variation."""
        result = parse_ask_query("what are the cycles", sample_graph)
        assert result["has_cycles"] is True

    def test_most_connected(self, sample_graph):
        """Test 'most connected' query."""
        result = parse_ask_query("most connected", sample_graph)
        assert "rankings" in result
        assert len(result["rankings"]) > 0
        # DatabasePool should be highly connected (2 incoming edges)
        labels = [r["label"] for r in result["rankings"]]
        assert "DatabasePool" in labels

    def test_most_connected_nodes(self, sample_graph):
        """Test 'most connected nodes' variation."""
        result = parse_ask_query("most connected nodes", sample_graph)
        assert "rankings" in result

    def test_important_nodes(self, sample_graph):
        """Test 'important nodes' variation."""
        result = parse_ask_query("important nodes", sample_graph)
        assert "rankings" in result

    def test_central_nodes(self, sample_graph):
        """Test 'central nodes' variation."""
        result = parse_ask_query("central nodes", sample_graph)
        assert "rankings" in result

    def test_orphans(self, sample_graph):
        """Test 'orphans' query."""
        result = parse_ask_query("orphans", sample_graph)
        assert "orphans" in result
        assert "OrphanNode" in result["orphans"]

    def test_isolated(self, sample_graph):
        """Test 'isolated' query variation."""
        result = parse_ask_query("isolated", sample_graph)
        assert "orphans" in result
        assert "OrphanNode" in result["orphans"]

    def test_disconnected_nodes(self, sample_graph):
        """Test 'disconnected nodes' variation."""
        result = parse_ask_query("disconnected nodes", sample_graph)
        assert "orphans" in result

    def test_components(self, sample_graph):
        """Test 'components' query."""
        result = parse_ask_query("components", sample_graph)
        assert result["count"] > 0
        assert len(result["components"]) > 0
        # Should have at least 2 components (main graph + orphan)
        assert result["count"] >= 2

    def test_clusters(self, sample_graph):
        """Test 'clusters' query variation."""
        result = parse_ask_query("clusters", sample_graph)
        assert result["count"] > 0

    def test_connected_components(self, sample_graph):
        """Test 'connected components' query variation."""
        result = parse_ask_query("connected components", sample_graph)
        assert result["count"] > 0


class TestFuzzyMatching:
    """Test fuzzy matching in queries."""

    def test_fuzzy_node_name_in_depends_query(self, sample_graph):
        """Test fuzzy matching for node names."""
        # "DatabasePool" should match even with typo
        result = parse_ask_query("what depends on databasepool", sample_graph)
        assert "dependents" in result or "dependencies" in result

    def test_fuzzy_node_name_in_path_query(self, sample_graph):
        """Test fuzzy matching in path queries."""
        result = parse_ask_query("path from logincontroller to databasepool", sample_graph)
        # Should work despite case differences
        assert result["path"] is not None or "reason" in result


class TestEmptyGraph:
    """Test queries on empty graph."""

    def test_cycles_empty_graph(self):
        """Test cycles query on empty graph."""
        graph = GraphEngine()
        result = parse_ask_query("cycles", graph)
        assert result["has_cycles"] is False
        assert result["cycles"] == []

    def test_orphans_empty_graph(self):
        """Test orphans query on empty graph."""
        graph = GraphEngine()
        result = parse_ask_query("orphans", graph)
        assert result["orphans"] == []

    def test_components_empty_graph(self):
        """Test components query on empty graph."""
        graph = GraphEngine()
        result = parse_ask_query("components", graph)
        assert result["count"] == 0


class TestUnrecognizedQueries:
    """Test fallback for unrecognized queries."""

    def test_unrecognized_query(self, sample_graph):
        """Test that unrecognized queries return helpful message."""
        result = parse_ask_query("show me everything", sample_graph)
        assert "error" in result
        assert "help" in result
        assert "Supported query patterns" in result["help"]

    def test_empty_query(self, sample_graph):
        """Test empty query."""
        result = parse_ask_query("", sample_graph)
        assert "error" in result
        assert "help" in result

    def test_gibberish_query(self, sample_graph):
        """Test gibberish query."""
        result = parse_ask_query("asdfghjkl qwertyuiop", sample_graph)
        assert "error" in result
        assert "help" in result


class TestQueryInterpretation:
    """Test that queries include interpretation field."""

    def test_interpretation_included(self, sample_graph):
        """Test that all queries include interpretation."""
        queries = [
            "what depends on DatabasePool",
            "dependencies of AuthService",
            "path from LoginController to DatabasePool",
            "cycles",
            "most connected",
            "orphans",
            "components"
        ]

        for query in queries:
            result = parse_ask_query(query, sample_graph)
            assert "interpretation" in result or "error" in result
            if "interpretation" in result:
                assert len(result["interpretation"]) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_node_graph(self):
        """Test queries on a graph with single node."""
        graph = GraphEngine()
        graph.add_node("SingleNode")

        result = parse_ask_query("what depends on SingleNode", graph)
        assert "No incoming dependencies" in result["result"]

        result = parse_ask_query("dependencies of SingleNode", graph)
        assert "no outgoing dependencies" in result["result"]

        result = parse_ask_query("orphans", graph)
        assert "SingleNode" in result["orphans"]

    def test_self_loop(self):
        """Test queries with self-loops."""
        graph = GraphEngine()
        graph.add_node("SelfLoop")
        graph.add_edge("SelfLoop", "SelfLoop", "self_reference")

        result = parse_ask_query("what depends on SelfLoop", graph)
        assert "SelfLoop" in result["dependents"]

        result = parse_ask_query("dependencies of SelfLoop", graph)
        assert "SelfLoop" in result["dependencies"]

    def test_multiple_edges_same_nodes(self):
        """Test with multiple edges between same nodes."""
        graph = GraphEngine()
        graph.add_node("A")
        graph.add_node("B")
        # NetworkX DiGraph doesn't support multi-edges by default,
        # but the last edge overwrites, so this should still work
        graph.add_edge("A", "B", "depends_on")

        result = parse_ask_query("what depends on B", graph)
        assert "A" in result["dependents"]
