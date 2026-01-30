"""Tests for add_facts tool - the relationship-first API."""

import pytest

from src.mcp_graph_engine.server import GraphServer


class TestAddFactsBasic:
    """Test basic add_facts functionality."""

    @pytest.mark.asyncio
    async def test_add_single_fact_creates_nodes_and_edge(self):
        """Test that a single fact creates both nodes and the edge."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "AuthService", "to": "UserRepository", "rel": "depends_on"}
            ]
        })

        assert result["nodes_created"] == 2  # AuthService + UserRepository
        assert result["nodes_existed"] == 0
        assert result["edges_created"] == 1
        assert result["edges_existed"] == 0

        # Verify nodes and edge exist
        graph = server.session_manager.get_graph("default")
        assert "AuthService" in graph.graph
        assert "UserRepository" in graph.graph
        assert graph.graph.has_edge("AuthService", "UserRepository")

    @pytest.mark.asyncio
    async def test_add_multiple_facts_batch(self):
        """Test adding multiple facts in one call."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "AuthService", "to": "UserRepository", "rel": "depends_on"},
                {"from": "UserRepository", "to": "DatabasePool", "rel": "depends_on"},
                {"from": "ConfigLoader", "to": "DatabasePool", "rel": "configures"}
            ]
        })

        # 4 unique nodes: AuthService, UserRepository, DatabasePool, ConfigLoader
        assert result["nodes_created"] == 4
        assert result["edges_created"] == 3

        # Verify all relationships
        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("AuthService", "UserRepository")
        assert graph.graph.has_edge("UserRepository", "DatabasePool")
        assert graph.graph.has_edge("ConfigLoader", "DatabasePool")

    @pytest.mark.asyncio
    async def test_add_facts_with_type_hints(self):
        """Test adding facts with explicit node types."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {
                    "from": "AuthService",
                    "from_type": "service",
                    "to": "UserRepository",
                    "to_type": "repository",
                    "rel": "depends_on"
                }
            ]
        })

        assert result["nodes_created"] == 2
        assert result["edges_created"] == 1

        # Verify types were set correctly
        graph = server.session_manager.get_graph("default")
        assert graph.graph.nodes["AuthService"]["type"] == "service"
        assert graph.graph.nodes["UserRepository"]["type"] == "repository"

    @pytest.mark.asyncio
    async def test_add_facts_default_entity_type(self):
        """Test that nodes without type hints get 'entity' type."""
        server = GraphServer()
        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "NodeA", "to": "NodeB", "rel": "connects"}
            ]
        })

        graph = server.session_manager.get_graph("default")
        assert graph.graph.nodes["NodeA"]["type"] == "entity"
        assert graph.graph.nodes["NodeB"]["type"] == "entity"


class TestAddFactsIdempotency:
    """Test that add_facts is idempotent."""

    @pytest.mark.asyncio
    async def test_adding_same_fact_twice_is_idempotent(self):
        """Test that adding the same fact twice doesn't duplicate."""
        server = GraphServer()

        # First call
        result1 = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "connects"}
            ]
        })
        assert result1["nodes_created"] == 2
        assert result1["edges_created"] == 1

        # Second call with same fact
        result2 = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "connects"}
            ]
        })
        assert result2["nodes_created"] == 0
        assert result2["nodes_existed"] == 2
        assert result2["edges_created"] == 0
        assert result2["edges_existed"] == 1

        # Verify only one edge exists
        graph = server.session_manager.get_graph("default")
        assert graph.graph.number_of_edges() == 1

    @pytest.mark.asyncio
    async def test_facts_with_shared_nodes(self):
        """Test adding multiple facts that share nodes."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "Hub", "to": "Spoke1", "rel": "connects"},
                {"from": "Hub", "to": "Spoke2", "rel": "connects"},
                {"from": "Hub", "to": "Spoke3", "rel": "connects"}
            ]
        })

        # Hub created once, then existed for next two facts
        # 3 facts, 4 unique nodes (Hub + 3 Spokes)
        assert result["nodes_created"] == 4
        assert result["nodes_existed"] == 2  # Hub existed for 2nd and 3rd facts
        assert result["edges_created"] == 3

        graph = server.session_manager.get_graph("default")
        assert graph.graph.out_degree("Hub") == 3


class TestAddFactsEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_self_referential_fact(self):
        """Test that a node can have a relationship to itself."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "Node", "to": "Node", "rel": "self_reference"}
            ]
        })

        assert result["nodes_created"] == 1  # Only one node
        assert result["nodes_existed"] == 1  # Second reference finds existing
        assert result["edges_created"] == 1

        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("Node", "Node")

    @pytest.mark.asyncio
    async def test_bidirectional_relationships(self):
        """Test creating bidirectional relationships."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "relates_to"},
                {"from": "B", "to": "A", "rel": "relates_to"}
            ]
        })

        assert result["nodes_created"] == 2
        assert result["nodes_existed"] == 2  # Second fact finds both nodes
        assert result["edges_created"] == 2

        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("A", "B")
        assert graph.graph.has_edge("B", "A")

    @pytest.mark.asyncio
    async def test_empty_facts_list(self):
        """Test that empty facts list returns zeros."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": []
        })

        assert result["nodes_created"] == 0
        assert result["nodes_existed"] == 0
        assert result["edges_created"] == 0
        assert result["edges_existed"] == 0

    @pytest.mark.asyncio
    async def test_facts_with_different_relations(self):
        """Test that same nodes can have multiple relations."""
        server = GraphServer()
        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "Service", "to": "Database", "rel": "reads_from"},
                {"from": "Service", "to": "Database", "rel": "writes_to"}
            ]
        })

        # Note: NetworkX DiGraph allows only one edge per (source, target) pair
        # The second edge will overwrite the first
        assert result["nodes_created"] == 2
        assert result["nodes_existed"] == 2
        # Second edge overwrites first (NetworkX behavior)
        assert result["edges_created"] == 1
        assert result["edges_existed"] == 1


class TestAddFactsMultiGraph:
    """Test add_facts with multiple named graphs."""

    @pytest.mark.asyncio
    async def test_facts_in_different_graphs(self):
        """Test that facts are isolated to their named graph."""
        server = GraphServer()

        # Add facts to graph1
        await server._handle_tool("add_facts", {
            "graph": "graph1",
            "facts": [
                {"from": "A", "to": "B", "rel": "connects"}
            ]
        })

        # Add facts to graph2
        await server._handle_tool("add_facts", {
            "graph": "graph2",
            "facts": [
                {"from": "X", "to": "Y", "rel": "links"}
            ]
        })

        # Verify isolation
        graph1 = server.session_manager.get_graph("graph1")
        graph2 = server.session_manager.get_graph("graph2")

        assert "A" in graph1.graph
        assert "A" not in graph2.graph
        assert "X" in graph2.graph
        assert "X" not in graph1.graph

    @pytest.mark.asyncio
    async def test_facts_default_graph(self):
        """Test that facts go to 'default' graph when not specified."""
        server = GraphServer()

        # Don't specify graph name
        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "connects"}
            ]
        })

        # Should be in default graph
        default_graph = server.session_manager.get_graph("default")
        assert "A" in default_graph.graph


class TestAddFactsIntegration:
    """Integration tests combining add_facts with other tools."""

    @pytest.mark.asyncio
    async def test_add_facts_then_query(self):
        """Test adding facts and then querying the graph."""
        server = GraphServer()

        # Add facts
        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "next"},
                {"from": "B", "to": "C", "rel": "next"},
                {"from": "C", "to": "D", "rel": "next"}
            ]
        })

        # Query shortest path
        result = await server._handle_tool("shortest_path", {
            "source": "A",
            "target": "D"
        })

        assert result["path"] == ["A", "B", "C", "D"]
        assert result["length"] == 3

    @pytest.mark.asyncio
    async def test_add_facts_then_get_info(self):
        """Test that get_graph_info reflects added facts."""
        server = GraphServer()

        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "from_type": "service", "to": "B", "to_type": "database", "rel": "uses"},
                {"from": "C", "from_type": "service", "to": "B", "to_type": "database", "rel": "uses"}
            ]
        })

        info = await server._handle_tool("get_graph_info", {})

        assert info["node_count"] == 3
        assert info["edge_count"] == 2
        assert info["node_types"]["service"] == 2
        assert info["node_types"]["database"] == 1
        assert info["relation_types"]["uses"] == 2

    @pytest.mark.asyncio
    async def test_add_facts_creates_cycle(self):
        """Test adding facts that create a cycle."""
        server = GraphServer()

        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "next"},
                {"from": "B", "to": "C", "rel": "next"},
                {"from": "C", "to": "A", "rel": "back"}
            ]
        })

        # Check for cycles
        result = await server._handle_tool("find_cycles", {})
        assert result["has_cycles"] is True
        assert len(result["cycles"]) > 0


class TestAddFactsRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_codebase_dependency_graph(self):
        """Test building a codebase dependency graph."""
        server = GraphServer()

        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "AuthService", "from_type": "service", "to": "UserRepository", "to_type": "repository", "rel": "depends_on"},
                {"from": "AuthService", "from_type": "service", "to": "TokenService", "to_type": "service", "rel": "uses"},
                {"from": "UserRepository", "from_type": "repository", "to": "DatabasePool", "to_type": "infrastructure", "rel": "depends_on"},
                {"from": "TokenService", "from_type": "service", "to": "RedisCache", "to_type": "infrastructure", "rel": "uses"},
                {"from": "ConfigLoader", "from_type": "config", "to": "DatabasePool", "to_type": "infrastructure", "rel": "configures"},
                {"from": "ConfigLoader", "from_type": "config", "to": "RedisCache", "to_type": "infrastructure", "rel": "configures"}
            ]
        })

        assert result["nodes_created"] == 6
        assert result["edges_created"] == 6

        # Verify we can analyze the graph
        info = await server._handle_tool("get_graph_info", {})
        assert info["node_count"] == 6
        assert info["node_types"]["service"] == 2
        assert info["node_types"]["repository"] == 1
        assert info["node_types"]["infrastructure"] == 2
        assert info["node_types"]["config"] == 1

    @pytest.mark.asyncio
    async def test_knowledge_graph_entities(self):
        """Test building a knowledge graph with entities and relationships."""
        server = GraphServer()

        result = await server._handle_tool("add_facts", {
            "facts": [
                {"from": "Paris", "from_type": "city", "to": "France", "to_type": "country", "rel": "capital_of"},
                {"from": "France", "from_type": "country", "to": "Europe", "to_type": "continent", "rel": "located_in"},
                {"from": "London", "from_type": "city", "to": "United Kingdom", "to_type": "country", "rel": "capital_of"},
                {"from": "United Kingdom", "from_type": "country", "to": "Europe", "to_type": "continent", "rel": "located_in"},
                {"from": "Paris", "from_type": "city", "to": "Seine", "to_type": "river", "rel": "located_on"}
            ]
        })

        assert result["nodes_created"] == 6
        assert result["edges_created"] == 5

        # Find all cities
        graph = server.session_manager.get_graph("default")
        nodes = graph.list_nodes(type_filter="city")
        assert len(nodes) == 2
        city_names = [n["label"] for n in nodes]
        assert "Paris" in city_names
        assert "London" in city_names
