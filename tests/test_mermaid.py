"""Tests for create_from_mermaid tool - Mermaid flowchart parsing."""

import pytest

from src.mcp_graph_engine.server import GraphServer, parse_mermaid


class TestMermaidParser:
    """Test the Mermaid parser function."""

    def test_parse_simple_edge(self):
        """Test parsing a simple edge without labels."""
        mermaid = """
graph TD
    A --> B
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "A",
            "to": "B",
            "rel": "relates_to"  # Default relation
        }

    def test_parse_edge_with_label(self):
        """Test parsing an edge with a label."""
        mermaid = """
graph TD
    A -->|depends_on| B
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "A",
            "to": "B",
            "rel": "depends_on"
        }

    def test_parse_node_with_brackets(self):
        """Test parsing nodes with display labels in brackets."""
        mermaid = """
graph TD
    A[AuthService] --> B[UserRepository]
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "AuthService",
            "to": "UserRepository",
            "rel": "relates_to"
        }

    def test_parse_node_with_brackets_and_edge_label(self):
        """Test parsing nodes with display labels and edge label."""
        mermaid = """
graph TD
    A[AuthService] -->|depends_on| B[UserRepository]
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "AuthService",
            "to": "UserRepository",
            "rel": "depends_on"
        }

    def test_parse_node_with_parentheses(self):
        """Test parsing nodes with rounded brackets (parentheses)."""
        mermaid = """
graph TD
    A(Start) --> B(End)
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "Start",
            "to": "End",
            "rel": "relates_to"
        }

    def test_parse_node_with_braces(self):
        """Test parsing nodes with diamond shape (braces)."""
        mermaid = """
graph TD
    A{Decision} --> B[Action]
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "Decision",
            "to": "Action",
            "rel": "relates_to"
        }

    def test_parse_multiple_edges(self):
        """Test parsing multiple edges."""
        mermaid = """
graph TD
    A --> B
    B --> C
    C --> D
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 3
        assert facts[0]["from"] == "A"
        assert facts[0]["to"] == "B"
        assert facts[1]["from"] == "B"
        assert facts[1]["to"] == "C"
        assert facts[2]["from"] == "C"
        assert facts[2]["to"] == "D"

    def test_parse_complex_diagram(self):
        """Test parsing a complex diagram with mixed syntax."""
        mermaid = """
graph TD
    A[AuthService] -->|depends_on| B[UserRepository]
    B -->|depends_on| C[DatabasePool]
    D(ConfigLoader) -->|configures| C
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 3
        assert facts[0] == {
            "from": "AuthService",
            "to": "UserRepository",
            "rel": "depends_on"
        }
        assert facts[1] == {
            "from": "UserRepository",
            "to": "DatabasePool",
            "rel": "depends_on"
        }
        assert facts[2] == {
            "from": "ConfigLoader",
            "to": "DatabasePool",
            "rel": "configures"
        }

    def test_parse_direction_lr(self):
        """Test that different direction markers work."""
        mermaid = """
graph LR
    A --> B
    B --> C
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 2
        assert facts[0]["from"] == "A"
        assert facts[1]["from"] == "B"

    def test_parse_flowchart_keyword(self):
        """Test using 'flowchart' instead of 'graph'."""
        mermaid = """
flowchart TD
    A --> B
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 1
        assert facts[0]["from"] == "A"

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        mermaid = ""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 0

    def test_parse_only_graph_declaration(self):
        """Test parsing with only graph declaration."""
        mermaid = """
graph TD
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 0

    def test_parse_ignores_comments(self):
        """Test that Mermaid comments are ignored."""
        mermaid = """
graph TD
    %% This is a comment
    A --> B
    %% Another comment
    B --> C
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 2
        assert facts[0]["from"] == "A"
        assert facts[1]["from"] == "B"

    def test_parse_ignores_empty_lines(self):
        """Test that empty lines are ignored."""
        mermaid = """
graph TD

    A --> B


    B --> C

"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 2

    def test_parse_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        mermaid = """
graph TD
  A --> B
    B --> C
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 2

    def test_parse_different_arrow_styles(self):
        """Test different arrow styles (-->, ---, etc.)."""
        mermaid = """
graph TD
    A --> B
    C --- D
"""
        facts = parse_mermaid(mermaid)

        # Both should be parsed as edges
        assert len(facts) == 2
        assert facts[0]["from"] == "A"
        assert facts[1]["from"] == "C"

    def test_parse_preserves_label_across_edges(self):
        """Test that node labels are preserved across multiple edges."""
        mermaid = """
graph TD
    A[Service]
    A --> B
    A --> C
"""
        facts = parse_mermaid(mermaid)

        # The standalone node declaration should be parsed
        # and the label should be used in subsequent edges
        assert len(facts) == 2
        assert facts[0]["from"] == "Service"
        assert facts[1]["from"] == "Service"

    def test_parse_reuses_node_labels(self):
        """Test that node labels defined once are reused."""
        mermaid = """
graph TD
    A[ServiceA] --> B
    C --> A
"""
        facts = parse_mermaid(mermaid)

        assert len(facts) == 2
        # First edge defines A as ServiceA
        assert facts[0]["from"] == "ServiceA"
        # Second edge should reuse ServiceA for A
        assert facts[1]["to"] == "ServiceA"


class TestCreateFromMermaidBasic:
    """Test basic create_from_mermaid functionality."""

    @pytest.mark.asyncio
    async def test_create_from_simple_mermaid(self):
        """Test creating graph from simple Mermaid diagram."""
        server = GraphServer()
        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> B
    B --> C
"""
        })

        assert result["nodes_created"] == 3
        assert result["edges_created"] == 2

        graph = server.session_manager.get_graph("default")
        assert "A" in graph.graph
        assert "B" in graph.graph
        assert "C" in graph.graph
        assert graph.graph.has_edge("A", "B")
        assert graph.graph.has_edge("B", "C")

    @pytest.mark.asyncio
    async def test_create_from_mermaid_with_labels(self):
        """Test creating graph from Mermaid with node labels."""
        server = GraphServer()
        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A[AuthService] -->|depends_on| B[UserRepository]
"""
        })

        assert result["nodes_created"] == 2
        assert result["edges_created"] == 1

        graph = server.session_manager.get_graph("default")
        assert "AuthService" in graph.graph
        assert "UserRepository" in graph.graph
        assert graph.graph.has_edge("AuthService", "UserRepository")

        # Check edge has correct relation type
        edge_data = graph.graph.get_edge_data("AuthService", "UserRepository")
        assert edge_data["relation"] == "depends_on"

    @pytest.mark.asyncio
    async def test_create_from_mermaid_default_relation(self):
        """Test that edges without labels get default relation."""
        server = GraphServer()
        await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> B
"""
        })

        graph = server.session_manager.get_graph("default")
        edge_data = graph.graph.get_edge_data("A", "B")
        assert edge_data["relation"] == "relates_to"

    @pytest.mark.asyncio
    async def test_create_from_mermaid_complex(self):
        """Test creating a complex dependency graph from Mermaid."""
        server = GraphServer()
        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    AuthService -->|depends_on| UserRepository
    UserRepository -->|depends_on| DatabasePool
    ConfigLoader -->|configures| DatabasePool
"""
        })

        assert result["nodes_created"] == 4
        assert result["edges_created"] == 3

        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("AuthService", "UserRepository")
        assert graph.graph.has_edge("UserRepository", "DatabasePool")
        assert graph.graph.has_edge("ConfigLoader", "DatabasePool")

    @pytest.mark.asyncio
    async def test_create_from_mermaid_empty(self):
        """Test creating from empty Mermaid diagram."""
        server = GraphServer()
        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
"""
        })

        assert result["nodes_created"] == 0
        assert result["edges_created"] == 0


class TestCreateFromMermaidIdempotency:
    """Test that create_from_mermaid is idempotent."""

    @pytest.mark.asyncio
    async def test_creating_same_mermaid_twice(self):
        """Test that creating the same diagram twice is idempotent."""
        server = GraphServer()

        mermaid = """
graph TD
    A --> B
    B --> C
"""

        # First call
        result1 = await server._handle_tool("create_from_mermaid", {
            "mermaid": mermaid
        })
        assert result1["nodes_created"] == 3
        assert result1["edges_created"] == 2

        # Second call with same Mermaid
        result2 = await server._handle_tool("create_from_mermaid", {
            "mermaid": mermaid
        })
        assert result2["nodes_created"] == 0
        # nodes_existed counts per-fact: A+B from first fact, B+C from second fact = 4
        assert result2["nodes_existed"] == 4
        assert result2["edges_created"] == 0
        assert result2["edges_existed"] == 2


class TestCreateFromMermaidEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_mermaid_with_self_loop(self):
        """Test that a node can reference itself."""
        server = GraphServer()
        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> A
"""
        })

        assert result["nodes_created"] == 1
        assert result["edges_created"] == 1

        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("A", "A")

    @pytest.mark.asyncio
    async def test_mermaid_multiple_edges_same_nodes(self):
        """Test multiple edges between same nodes - second one overwrites first."""
        server = GraphServer()
        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A -->|depends_on| B
    A -->|uses| B
"""
        })

        # Only one edge created - second overwrites first
        assert result["nodes_created"] == 2
        assert result["edges_created"] == 1
        assert result["edges_existed"] == 1

        graph = server.session_manager.get_graph("default")
        # The last edge should be the one that remains
        edge_data = graph.graph.get_edge_data("A", "B")
        assert edge_data["relation"] == "uses"


class TestCreateFromMermaidMultiGraph:
    """Test create_from_mermaid with multiple named graphs."""

    @pytest.mark.asyncio
    async def test_mermaid_in_different_graphs(self):
        """Test that Mermaid diagrams are isolated to named graphs."""
        server = GraphServer()

        # Add to graph1
        await server._handle_tool("create_from_mermaid", {
            "graph": "graph1",
            "mermaid": """
graph TD
    A --> B
"""
        })

        # Add to graph2
        await server._handle_tool("create_from_mermaid", {
            "graph": "graph2",
            "mermaid": """
graph TD
    X --> Y
"""
        })

        # Verify isolation
        graph1 = server.session_manager.get_graph("graph1")
        graph2 = server.session_manager.get_graph("graph2")

        assert "A" in graph1.graph
        assert "A" not in graph2.graph
        assert "X" in graph2.graph
        assert "X" not in graph1.graph

    @pytest.mark.asyncio
    async def test_mermaid_default_graph(self):
        """Test that Mermaid goes to 'default' graph when not specified."""
        server = GraphServer()

        await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> B
"""
        })

        default_graph = server.session_manager.get_graph("default")
        assert "A" in default_graph.graph


class TestCreateFromMermaidIntegration:
    """Integration tests combining create_from_mermaid with other tools."""

    @pytest.mark.asyncio
    async def test_mermaid_then_query(self):
        """Test creating from Mermaid and then querying the graph."""
        server = GraphServer()

        await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> B
    B --> C
    C --> D
"""
        })

        result = await server._handle_tool("shortest_path", {
            "source": "A",
            "target": "D"
        })

        assert result["path"] == ["A", "B", "C", "D"]
        assert result["length"] == 3

    @pytest.mark.asyncio
    async def test_mermaid_then_get_info(self):
        """Test that get_graph_info reflects Mermaid-created graph."""
        server = GraphServer()

        await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A[Service1] -->|depends_on| B[Service2]
    C[Service3] -->|depends_on| B[Service2]
"""
        })

        info = await server._handle_tool("get_graph_info", {})

        assert info["node_count"] == 3
        assert info["edge_count"] == 2

    @pytest.mark.asyncio
    async def test_mermaid_creates_cycle(self):
        """Test creating a cycle via Mermaid."""
        server = GraphServer()

        await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> B
    B --> C
    C --> A
"""
        })

        result = await server._handle_tool("find_cycles", {})
        assert result["has_cycles"] is True
        assert len(result["cycles"]) > 0

    @pytest.mark.asyncio
    async def test_mixed_add_facts_and_mermaid(self):
        """Test that add_facts and create_from_mermaid work together."""
        server = GraphServer()

        # Add via Mermaid
        await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    A --> B
"""
        })

        # Add via add_facts
        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "B", "to": "C", "rel": "connects"}
            ]
        })

        # Verify both are in the graph
        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("A", "B")
        assert graph.graph.has_edge("B", "C")

        # Verify path works
        result = await server._handle_tool("shortest_path", {
            "source": "A",
            "target": "C"
        })
        assert result["path"] == ["A", "B", "C"]


class TestCreateFromMermaidRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_mermaid_service_architecture(self):
        """Test creating a service architecture diagram from Mermaid."""
        server = GraphServer()

        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    API[API Gateway] -->|routes_to| Auth[Auth Service]
    API -->|routes_to| User[User Service]
    Auth -->|depends_on| DB[(Database)]
    User -->|depends_on| DB
    Auth -->|uses| Cache[Redis Cache]
"""
        })

        assert result["nodes_created"] == 5
        assert result["edges_created"] == 5

        info = await server._handle_tool("get_graph_info", {})
        assert info["node_count"] == 5
        assert info["edge_count"] == 5

    @pytest.mark.asyncio
    async def test_mermaid_decision_flow(self):
        """Test creating a decision flow diagram from Mermaid."""
        server = GraphServer()

        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph TD
    Start{Check Auth} -->|authenticated| Dashboard[Show Dashboard]
    Start -->|not_authenticated| Login[Show Login]
    Login -->|success| Dashboard
"""
        })

        assert result["nodes_created"] == 3
        assert result["edges_created"] == 3

        graph = server.session_manager.get_graph("default")
        # Check that edge labels became relation types
        edge_data1 = graph.graph.get_edge_data("Check Auth", "Show Dashboard")
        assert edge_data1["relation"] == "authenticated"

        edge_data2 = graph.graph.get_edge_data("Check Auth", "Show Login")
        assert edge_data2["relation"] == "not_authenticated"

    @pytest.mark.asyncio
    async def test_mermaid_data_pipeline(self):
        """Test creating a data pipeline diagram from Mermaid."""
        server = GraphServer()

        result = await server._handle_tool("create_from_mermaid", {
            "mermaid": """
graph LR
    Source[Data Source] -->|extracts| ETL[ETL Process]
    ETL -->|transforms| Clean[Clean Data]
    Clean -->|loads| Warehouse[Data Warehouse]
    Warehouse -->|feeds| Analytics[Analytics Dashboard]
"""
        })

        assert result["nodes_created"] == 5
        assert result["edges_created"] == 4

        # Verify the pipeline path
        result = await server._handle_tool("shortest_path", {
            "source": "Data Source",
            "target": "Analytics Dashboard"
        })
        assert result["length"] == 4
        assert len(result["path"]) == 5
