"""Tests for the dump_context tool."""

import pytest

from mcp_graph_engine.graph_engine import GraphEngine
from mcp_graph_engine.server import GraphServer


@pytest.fixture
def empty_graph():
    """Create an empty graph for testing."""
    return GraphEngine()


@pytest.fixture
def simple_graph():
    """Create a simple graph with a few nodes and edges."""
    graph = GraphEngine()

    # Add nodes with types
    graph.add_node("ServiceA", node_type="service")
    graph.add_node("ServiceB", node_type="service")
    graph.add_node("DatabasePool", node_type="infrastructure")

    # Add edges
    graph.add_edge("ServiceA", "DatabasePool", "depends_on")
    graph.add_edge("ServiceB", "DatabasePool", "depends_on")

    return graph


@pytest.fixture
def complex_graph():
    """Create a complex graph with multiple node types, cycles, and orphans."""
    graph = GraphEngine()

    # Services
    graph.add_node("AuthService", node_type="service")
    graph.add_node("UserService", node_type="service")
    graph.add_node("PaymentService", node_type="service")
    graph.add_node("LoginService", node_type="service")

    # Repositories
    graph.add_node("UserRepository", node_type="repository")
    graph.add_node("PaymentRepository", node_type="repository")
    graph.add_node("SessionRepository", node_type="repository")

    # Infrastructure
    graph.add_node("DatabasePool", node_type="infrastructure")
    graph.add_node("CacheLayer", node_type="infrastructure")
    graph.add_node("MessageQueue", node_type="infrastructure")

    # Orphan node
    graph.add_node("UnusedService", node_type="service")

    # Add edges to create a complex structure
    graph.add_edge("AuthService", "UserRepository", "depends_on")
    graph.add_edge("AuthService", "SessionRepository", "depends_on")
    graph.add_edge("LoginService", "AuthService", "uses")
    graph.add_edge("UserService", "UserRepository", "depends_on")
    graph.add_edge("UserService", "CacheLayer", "depends_on")
    graph.add_edge("PaymentService", "PaymentRepository", "depends_on")
    graph.add_edge("UserRepository", "DatabasePool", "depends_on")
    graph.add_edge("PaymentRepository", "DatabasePool", "depends_on")
    graph.add_edge("SessionRepository", "DatabasePool", "depends_on")
    graph.add_edge("SessionRepository", "CacheLayer", "depends_on")
    graph.add_edge("CacheLayer", "MessageQueue", "depends_on")

    # Create a cycle: AuthService -> UserService -> AuthService
    graph.add_edge("AuthService", "UserService", "notifies")
    graph.add_edge("UserService", "AuthService", "uses")

    return graph


class TestDumpContextEmpty:
    """Test dump_context with empty graph."""

    def test_empty_graph(self, empty_graph):
        """Test dump_context on an empty graph."""
        server = GraphServer()
        result = server._dump_context(empty_graph, "default")

        assert "context" in result
        context = result["context"]

        # Should have header
        assert "=== Graph Context: default ===" in context

        # Should have statistics
        assert "## Statistics" in context
        assert "0 nodes, 0 edges" in context

        # Should indicate empty
        assert "(Graph is empty)" in context


class TestDumpContextSimple:
    """Test dump_context with simple graph."""

    def test_simple_graph_structure(self, simple_graph):
        """Test that all major sections are present."""
        server = GraphServer()
        result = server._dump_context(simple_graph, "default")

        context = result["context"]

        # Check all major sections exist
        assert "=== Graph Context: default ===" in context
        assert "## Statistics" in context
        assert "## Nodes by Type" in context
        assert "## Relationships" in context
        assert "## Key Insights" in context

    def test_simple_graph_statistics(self, simple_graph):
        """Test statistics section."""
        server = GraphServer()
        result = server._dump_context(simple_graph, "default")

        context = result["context"]

        # Check statistics
        assert "3 nodes, 2 edges" in context
        assert "2 node types" in context
        assert "infrastructure" in context
        assert "service" in context
        assert "Cycles detected: No" in context

    def test_simple_graph_nodes_by_type(self, simple_graph):
        """Test nodes grouped by type."""
        server = GraphServer()
        result = server._dump_context(simple_graph, "default")

        context = result["context"]

        # Should have node type sections
        assert "### infrastructure (1 nodes)" in context
        assert "- DatabasePool" in context
        assert "### service (2 nodes)" in context
        assert "- ServiceA" in context
        assert "- ServiceB" in context

    def test_simple_graph_relationships(self, simple_graph):
        """Test relationships listing."""
        server = GraphServer()
        result = server._dump_context(simple_graph, "default")

        context = result["context"]

        # Should list relationships
        assert "## Relationships (2 total)" in context
        assert "ServiceA depends_on DatabasePool" in context
        assert "ServiceB depends_on DatabasePool" in context

    def test_simple_graph_insights(self, simple_graph):
        """Test key insights section."""
        server = GraphServer()
        result = server._dump_context(simple_graph, "default")

        context = result["context"]

        # DatabasePool should be most connected (2 incoming edges)
        assert "- Most connected: DatabasePool" in context
        assert "- Isolated nodes: None" in context


class TestDumpContextComplex:
    """Test dump_context with complex graph."""

    def test_complex_graph_statistics(self, complex_graph):
        """Test statistics with more complex graph."""
        server = GraphServer()
        result = server._dump_context(complex_graph, "default")

        context = result["context"]

        # Check node and edge counts
        assert "11 nodes, 13 edges" in context  # 11 nodes, 13 edges

        # Check node types
        assert "3 node types" in context
        assert "infrastructure" in context
        assert "repository" in context
        assert "service" in context

        # Should detect cycle
        assert "Cycles detected: Yes" in context

    def test_complex_graph_all_types_present(self, complex_graph):
        """Test that all node types are listed."""
        server = GraphServer()
        result = server._dump_context(complex_graph, "default")

        context = result["context"]

        # Check that sections for all types exist
        assert "### infrastructure (3 nodes)" in context
        assert "### repository (3 nodes)" in context
        assert "### service (5 nodes)" in context

    def test_complex_graph_hubs_detected(self, complex_graph):
        """Test that hub nodes are identified."""
        server = GraphServer()
        result = server._dump_context(complex_graph, "default")

        context = result["context"]

        # DatabasePool should be most connected (3 incoming edges)
        assert "Most connected:" in context

        # Should have hubs section
        assert "- Hubs:" in context

    def test_complex_graph_orphans_detected(self, complex_graph):
        """Test that isolated nodes are identified."""
        server = GraphServer()
        result = server._dump_context(complex_graph, "default")

        context = result["context"]

        # UnusedService has no connections
        assert "UnusedService" in context
        # Note: It will be listed in nodes, and in isolated nodes
        assert "- Isolated nodes:" in context
        assert "UnusedService" in context

    def test_complex_graph_cycles_listed(self, complex_graph):
        """Test that cycles are listed in insights."""
        server = GraphServer()
        result = server._dump_context(complex_graph, "default")

        context = result["context"]

        # Should list cycles
        assert "- Cycles:" in context
        # The cycle should include AuthService and UserService
        assert "AuthService" in context
        assert "UserService" in context


class TestDumpContextMultiGraph:
    """Test dump_context with multiple graphs."""

    def test_graph_name_in_header(self):
        """Test that graph name appears in the output."""
        server = GraphServer()
        graph = GraphEngine()

        result = server._dump_context(graph, "my-custom-graph")
        context = result["context"]

        assert "=== Graph Context: my-custom-graph ===" in context


class TestDumpContextEdgeCases:
    """Test edge cases."""

    def test_graph_with_only_orphans(self):
        """Test graph with nodes but no edges."""
        graph = GraphEngine()
        graph.add_node("Node1", node_type="type1")
        graph.add_node("Node2", node_type="type2")
        graph.add_node("Node3", node_type="type1")

        server = GraphServer()
        result = server._dump_context(graph, "default")
        context = result["context"]

        # Should have nodes
        assert "3 nodes, 0 edges" in context

        # Should have no relationships
        assert "(No relationships)" in context

        # All nodes should be orphans
        assert "- Isolated nodes: Node1, Node2, Node3" in context

    def test_graph_with_many_cycles(self):
        """Test graph with multiple cycles."""
        graph = GraphEngine()

        # Create multiple small cycles
        # Cycle 1: A -> B -> A
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B", "rel")
        graph.add_edge("B", "A", "rel")

        # Cycle 2: C -> D -> C
        graph.add_node("C")
        graph.add_node("D")
        graph.add_edge("C", "D", "rel")
        graph.add_edge("D", "C", "rel")

        # Cycle 3: E -> F -> E
        graph.add_node("E")
        graph.add_node("F")
        graph.add_edge("E", "F", "rel")
        graph.add_edge("F", "E", "rel")

        # Cycle 4: G -> H -> G
        graph.add_node("G")
        graph.add_node("H")
        graph.add_edge("G", "H", "rel")
        graph.add_edge("H", "G", "rel")

        server = GraphServer()
        result = server._dump_context(graph, "default")
        context = result["context"]

        # Should detect cycles
        assert "Cycles detected: Yes" in context

        # Should show up to 3 cycles
        assert "- Cycles:" in context

    def test_graph_with_unknown_type_nodes(self):
        """Test graph with nodes that have no type."""
        graph = GraphEngine()

        # Add nodes with explicit types
        graph.add_node("TypedNode1", node_type="service")
        graph.add_node("TypedNode2", node_type="service")

        # Add nodes without type (will be 'unknown')
        graph.add_node("UntypedNode1")
        graph.add_node("UntypedNode2")

        server = GraphServer()
        result = server._dump_context(graph, "default")
        context = result["context"]

        # Should have service type section
        assert "### service (2 nodes)" in context

        # Unknown type should appear last
        assert "### unknown (2 nodes)" in context
        assert "- UntypedNode1" in context
        assert "- UntypedNode2" in context

    def test_relationships_are_sorted(self):
        """Test that relationships are listed in consistent order."""
        graph = GraphEngine()

        # Add edges in random order
        graph.add_node("Z")
        graph.add_node("A")
        graph.add_node("M")

        graph.add_edge("Z", "A", "rel1")
        graph.add_edge("A", "M", "rel2")
        graph.add_edge("M", "Z", "rel3")

        server = GraphServer()
        result = server._dump_context(graph, "default")
        context = result["context"]

        # Find the relationships section
        lines = context.split('\n')
        rel_start = None
        for i, line in enumerate(lines):
            if "## Relationships" in line:
                rel_start = i
                break

        assert rel_start is not None

        # Get relationship lines (skip header and blank line)
        rel_lines = []
        for line in lines[rel_start+2:]:
            if line.startswith("- "):
                rel_lines.append(line)
            elif line.startswith("##"):
                break

        # Should be in alphabetical order by source
        assert rel_lines[0] == "- A rel2 M"
        assert rel_lines[1] == "- M rel3 Z"
        assert rel_lines[2] == "- Z rel1 A"
