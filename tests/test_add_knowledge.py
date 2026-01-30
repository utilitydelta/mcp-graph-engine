"""Tests for add_knowledge tool - the text-based DSL API."""

import pytest

from src.mcp_graph_engine.server import GraphServer, parse_knowledge_dsl


class TestDSLParser:
    """Test the DSL parser function."""

    def test_parse_single_relationship(self):
        """Test parsing a single relationship."""
        dsl = "AuthService depends_on UserRepository"
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "AuthService",
            "to": "UserRepository",
            "rel": "depends_on"
        }

    def test_parse_multiple_relationships(self):
        """Test parsing multiple relationships."""
        dsl = """
AuthService depends_on UserRepository
UserRepository depends_on DatabasePool
ConfigLoader configures DatabasePool
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 3
        assert facts[0]["from"] == "AuthService"
        assert facts[1]["from"] == "UserRepository"
        assert facts[2]["from"] == "ConfigLoader"

    def test_parse_with_type_hints(self):
        """Test parsing with type hints."""
        dsl = "AuthService:service depends_on UserRepository:repository"
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "AuthService",
            "from_type": "service",
            "to": "UserRepository",
            "to_type": "repository",
            "rel": "depends_on"
        }

    def test_parse_mixed_type_hints(self):
        """Test parsing with type hints on only one side."""
        dsl1 = "AuthService:service depends_on UserRepository"
        facts1 = parse_knowledge_dsl(dsl1)

        assert facts1[0]["from"] == "AuthService"
        assert facts1[0]["from_type"] == "service"
        assert facts1[0]["to"] == "UserRepository"
        assert "to_type" not in facts1[0]

        dsl2 = "AuthService depends_on UserRepository:repository"
        facts2 = parse_knowledge_dsl(dsl2)

        assert facts2[0]["from"] == "AuthService"
        assert "from_type" not in facts2[0]
        assert facts2[0]["to"] == "UserRepository"
        assert facts2[0]["to_type"] == "repository"

    def test_parse_ignores_comments(self):
        """Test that comments are ignored."""
        dsl = """
# This is a comment
AuthService depends_on UserRepository
# Another comment
UserRepository depends_on DatabasePool
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 2
        assert facts[0]["from"] == "AuthService"
        assert facts[1]["from"] == "UserRepository"

    def test_parse_ignores_empty_lines(self):
        """Test that empty lines are ignored."""
        dsl = """

AuthService depends_on UserRepository


UserRepository depends_on DatabasePool

"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 2

    def test_parse_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        dsl = """
  AuthService depends_on UserRepository
    UserRepository depends_on DatabasePool
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 2
        assert facts[0]["from"] == "AuthService"

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        dsl = ""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 0

    def test_parse_only_comments(self):
        """Test parsing string with only comments."""
        dsl = """
# Comment 1
# Comment 2
# Comment 3
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 0

    def test_parse_malformed_line_too_few_parts(self):
        """Test that malformed lines raise errors."""
        dsl = "AuthService depends_on"

        with pytest.raises(ValueError) as exc_info:
            parse_knowledge_dsl(dsl)

        assert "Line 1" in str(exc_info.value)
        assert "Expected 3 parts" in str(exc_info.value)

    def test_parse_malformed_line_too_many_parts(self):
        """Test that lines with too many parts raise errors."""
        dsl = "AuthService depends_on UserRepository extra"

        with pytest.raises(ValueError) as exc_info:
            parse_knowledge_dsl(dsl)

        assert "Line 1" in str(exc_info.value)
        assert "Expected 3 parts" in str(exc_info.value)

    def test_parse_error_line_number_correct(self):
        """Test that error messages show correct line number."""
        dsl = """
AuthService depends_on UserRepository
UserRepository depends_on DatabasePool
ConfigLoader configures
"""

        with pytest.raises(ValueError) as exc_info:
            parse_knowledge_dsl(dsl)

        # Should be line 4 (counting the leading newline)
        assert "Line 4" in str(exc_info.value)


class TestDSLParserSpacesInLabels:
    """Test DSL parser with spaces in labels using quoted strings."""

    def test_spaces_in_node_labels(self):
        """Node labels with spaces using quotes."""
        dsl = '"Auth Service" depends_on "User Repository"'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "Auth Service",
            "to": "User Repository",
            "rel": "depends_on"
        }

    def test_spaces_in_relation_labels(self):
        """Relation labels with spaces using quotes."""
        dsl = 'AuthService "depends on" UserRepository'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0]["from"] == "AuthService"
        assert facts[0]["to"] == "UserRepository"
        assert facts[0]["rel"] == "depends on"

    def test_spaces_in_all_labels(self):
        """All labels with spaces."""
        dsl = '"Auth Service" "depends on" "User Repository"'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "Auth Service",
            "to": "User Repository",
            "rel": "depends on"
        }

    def test_mixed_quoted_unquoted(self):
        """Mix of quoted and unquoted labels."""
        dsl = '"Auth Service" depends_on UserRepository'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0]["from"] == "Auth Service"
        assert facts[0]["to"] == "UserRepository"
        assert facts[0]["rel"] == "depends_on"

    def test_spaces_with_type_hints(self):
        """Spaces in labels with type hints."""
        dsl = '"Auth Service":service depends_on "User Repo":repository'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0] == {
            "from": "Auth Service",
            "from_type": "service",
            "to": "User Repo",
            "to_type": "repository",
            "rel": "depends_on"
        }

    def test_backward_compatibility(self):
        """Existing syntax without quotes still works."""
        dsl = """
AuthService depends_on UserRepository
AuthService:service depends_on UserRepository:repository
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 2
        assert facts[0]["from"] == "AuthService"
        assert facts[1]["from_type"] == "service"

    def test_comments_with_quotes(self):
        """Comments work correctly with quoted strings."""
        dsl = '''
"Auth Service" depends_on "User Repo"  # This is a comment
'''
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0]["from"] == "Auth Service"
        assert facts[0]["to"] == "User Repo"

    def test_hash_inside_quotes(self):
        """Hash character inside quoted strings is preserved."""
        dsl = '"Hash#Tag" depends_on Something'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0]["from"] == "Hash#Tag"
        assert facts[0]["to"] == "Something"

    def test_multiline_with_spaces(self):
        """Multiple lines with spaces in labels."""
        dsl = """
"Auth Service" "depends on" "User Repository"
"User Repository" "stores data in" Database
Database "runs on" "Cloud Provider"
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 3
        assert facts[0]["from"] == "Auth Service"
        assert facts[0]["rel"] == "depends on"
        assert facts[1]["from"] == "User Repository"
        assert facts[1]["rel"] == "stores data in"
        assert facts[2]["to"] == "Cloud Provider"

    def test_single_quotes(self):
        """Single quotes also work for spaces."""
        dsl = "'Auth Service' depends_on 'User Repository'"
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0]["from"] == "Auth Service"
        assert facts[0]["to"] == "User Repository"

    def test_unclosed_quote_error(self):
        """Unclosed quotes raise clear error."""
        dsl = '"Auth Service depends_on UserRepository'

        with pytest.raises(ValueError) as exc_info:
            parse_knowledge_dsl(dsl)

        assert "Line 1" in str(exc_info.value)
        assert "Invalid syntax" in str(exc_info.value)

    def test_escaped_quotes_inside_strings(self):
        """Escaped quotes inside strings are handled."""
        dsl = r'"Node \"Quoted\"" relates_to Another'
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 1
        assert facts[0]["from"] == 'Node "Quoted"'

    def test_mixed_quotes_and_type_hints(self):
        """Complex: quoted labels with type hints and mixed syntax."""
        dsl = """
"Auth Service":service "depends on" UserRepository:repository
"Config Loader":config configures "Database Pool":infrastructure
"""
        facts = parse_knowledge_dsl(dsl)

        assert len(facts) == 2
        assert facts[0]["from"] == "Auth Service"
        assert facts[0]["from_type"] == "service"
        assert facts[0]["rel"] == "depends on"
        assert facts[0]["to"] == "UserRepository"
        assert facts[0]["to_type"] == "repository"

        assert facts[1]["from"] == "Config Loader"
        assert facts[1]["from_type"] == "config"
        assert facts[1]["to"] == "Database Pool"
        assert facts[1]["to_type"] == "infrastructure"

    def test_colons_in_quoted_labels_with_type_hints(self):
        """Labels with colons work correctly with type hints."""
        knowledge = '''
        "http://example.com":url relates_to "Service:v2":service
        '''
        facts = parse_knowledge_dsl(knowledge)
        assert len(facts) == 1
        assert facts[0]['from'] == 'http://example.com'
        assert facts[0]['from_type'] == 'url'
        assert facts[0]['to'] == 'Service:v2'
        assert facts[0]['to_type'] == 'service'

    def test_unicode_labels(self):
        """Unicode characters including Chinese work in labels."""
        knowledge = '''
        "用户服务" "依赖于" "数据库"
        "Ключевой сервис" relates_to "База данных"
        "サービス":service depends_on "データベース":database
        Ümläut connects_to Çafé
        '''
        facts = parse_knowledge_dsl(knowledge)
        assert len(facts) == 4

        # Chinese
        assert facts[0]['from'] == '用户服务'
        assert facts[0]['rel'] == '依赖于'
        assert facts[0]['to'] == '数据库'

        # Russian
        assert facts[1]['from'] == 'Ключевой сервис'
        assert facts[1]['to'] == 'База данных'

        # Japanese with type hints
        assert facts[2]['from'] == 'サービス'
        assert facts[2]['from_type'] == 'service'
        assert facts[2]['to'] == 'データベース'
        assert facts[2]['to_type'] == 'database'

        # Unquoted Unicode (Latin extended)
        assert facts[3]['from'] == 'Ümläut'
        assert facts[3]['to'] == 'Çafé'


class TestAddKnowledgeBasic:
    """Test basic add_knowledge functionality."""

    @pytest.mark.asyncio
    async def test_add_knowledge_single_relationship(self):
        """Test adding a single relationship via DSL."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": "AuthService depends_on UserRepository"
        })

        assert result["nodes_created"] == 2
        assert result["edges_created"] == 1

        graph = server.session_manager.get_graph("default")
        assert "AuthService" in graph.graph
        assert "UserRepository" in graph.graph
        assert graph.graph.has_edge("AuthService", "UserRepository")

    @pytest.mark.asyncio
    async def test_add_knowledge_multiple_relationships(self):
        """Test adding multiple relationships via DSL."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": """
AuthService depends_on UserRepository
UserRepository depends_on DatabasePool
ConfigLoader configures DatabasePool
"""
        })

        assert result["nodes_created"] == 4
        assert result["edges_created"] == 3

        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("AuthService", "UserRepository")
        assert graph.graph.has_edge("UserRepository", "DatabasePool")
        assert graph.graph.has_edge("ConfigLoader", "DatabasePool")

    @pytest.mark.asyncio
    async def test_add_knowledge_with_type_hints(self):
        """Test adding knowledge with type hints."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": "AuthService:service depends_on UserRepository:repository"
        })

        assert result["nodes_created"] == 2
        assert result["edges_created"] == 1

        graph = server.session_manager.get_graph("default")
        assert graph.graph.nodes["AuthService"]["type"] == "service"
        assert graph.graph.nodes["UserRepository"]["type"] == "repository"

    @pytest.mark.asyncio
    async def test_add_knowledge_default_entity_type(self):
        """Test that nodes without type hints get 'entity' type."""
        server = GraphServer()
        await server._handle_tool("add_knowledge", {
            "knowledge": "NodeA connects NodeB"
        })

        graph = server.session_manager.get_graph("default")
        assert graph.graph.nodes["NodeA"]["type"] == "entity"
        assert graph.graph.nodes["NodeB"]["type"] == "entity"

    @pytest.mark.asyncio
    async def test_add_knowledge_with_comments(self):
        """Test that comments are ignored."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": """
# This defines service dependencies
AuthService depends_on UserRepository
# Database layer
UserRepository depends_on DatabasePool
"""
        })

        assert result["nodes_created"] == 3
        assert result["edges_created"] == 2

    @pytest.mark.asyncio
    async def test_add_knowledge_empty_lines_ignored(self):
        """Test that empty lines are ignored."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": """

AuthService depends_on UserRepository


UserRepository depends_on DatabasePool

"""
        })

        assert result["nodes_created"] == 3
        assert result["edges_created"] == 2


class TestAddKnowledgeIdempotency:
    """Test that add_knowledge is idempotent."""

    @pytest.mark.asyncio
    async def test_adding_same_knowledge_twice(self):
        """Test that adding the same knowledge twice is idempotent."""
        server = GraphServer()

        # First call
        result1 = await server._handle_tool("add_knowledge", {
            "knowledge": "A connects B"
        })
        assert result1["nodes_created"] == 2
        assert result1["edges_created"] == 1

        # Second call with same knowledge
        result2 = await server._handle_tool("add_knowledge", {
            "knowledge": "A connects B"
        })
        assert result2["nodes_created"] == 0
        assert result2["nodes_existed"] == 2
        assert result2["edges_created"] == 0
        assert result2["edges_existed"] == 1


class TestAddKnowledgeEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_add_knowledge_empty_string(self):
        """Test that empty knowledge string is handled gracefully."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": ""
        })

        assert result["nodes_created"] == 0
        assert result["edges_created"] == 0

    @pytest.mark.asyncio
    async def test_add_knowledge_only_comments(self):
        """Test that only comments doesn't create anything."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": """
# Comment 1
# Comment 2
"""
        })

        assert result["nodes_created"] == 0
        assert result["edges_created"] == 0

    @pytest.mark.asyncio
    async def test_add_knowledge_malformed_line_raises_error(self):
        """Test that malformed lines raise errors."""
        server = GraphServer()

        # Test with try/catch since error handling happens in call_tool
        try:
            await server._handle_tool("add_knowledge", {
                "knowledge": "AuthService depends_on"
            })
            # If no error was raised, the test should fail
            raise AssertionError("Expected ValueError to be raised")
        except ValueError as e:
            assert "Expected 3 parts" in str(e)

    @pytest.mark.asyncio
    async def test_add_knowledge_self_referential(self):
        """Test that a node can have a relationship to itself."""
        server = GraphServer()
        result = await server._handle_tool("add_knowledge", {
            "knowledge": "Node self_reference Node"
        })

        assert result["nodes_created"] == 1
        assert result["nodes_existed"] == 1
        assert result["edges_created"] == 1

        graph = server.session_manager.get_graph("default")
        assert graph.graph.has_edge("Node", "Node")


class TestAddKnowledgeMultiGraph:
    """Test add_knowledge with multiple named graphs."""

    @pytest.mark.asyncio
    async def test_knowledge_in_different_graphs(self):
        """Test that knowledge is isolated to named graphs."""
        server = GraphServer()

        # Add to graph1
        await server._handle_tool("add_knowledge", {
            "graph": "graph1",
            "knowledge": "A connects B"
        })

        # Add to graph2
        await server._handle_tool("add_knowledge", {
            "graph": "graph2",
            "knowledge": "X links Y"
        })

        # Verify isolation
        graph1 = server.session_manager.get_graph("graph1")
        graph2 = server.session_manager.get_graph("graph2")

        assert "A" in graph1.graph
        assert "A" not in graph2.graph
        assert "X" in graph2.graph
        assert "X" not in graph1.graph

    @pytest.mark.asyncio
    async def test_knowledge_default_graph(self):
        """Test that knowledge goes to 'default' graph when not specified."""
        server = GraphServer()

        await server._handle_tool("add_knowledge", {
            "knowledge": "A connects B"
        })

        default_graph = server.session_manager.get_graph("default")
        assert "A" in default_graph.graph


class TestAddKnowledgeIntegration:
    """Integration tests combining add_knowledge with other tools."""

    @pytest.mark.asyncio
    async def test_add_knowledge_then_query(self):
        """Test adding knowledge and then querying the graph."""
        server = GraphServer()

        await server._handle_tool("add_knowledge", {
            "knowledge": """
A next B
B next C
C next D
"""
        })

        result = await server._handle_tool("shortest_path", {
            "source": "A",
            "target": "D"
        })

        assert result["path"] == ["A", "B", "C", "D"]
        assert result["length"] == 3

    @pytest.mark.asyncio
    async def test_add_knowledge_then_get_info(self):
        """Test that get_graph_info reflects added knowledge."""
        server = GraphServer()

        await server._handle_tool("add_knowledge", {
            "knowledge": """
A:service uses B:database
C:service uses B:database
"""
        })

        info = await server._handle_tool("get_graph_info", {})

        assert info["node_count"] == 3
        assert info["edge_count"] == 2
        assert info["node_types"]["service"] == 2
        assert info["node_types"]["database"] == 1
        assert info["relation_types"]["uses"] == 2

    @pytest.mark.asyncio
    async def test_add_knowledge_creates_cycle(self):
        """Test adding knowledge that creates a cycle."""
        server = GraphServer()

        await server._handle_tool("add_knowledge", {
            "knowledge": """
A next B
B next C
C back A
"""
        })

        result = await server._handle_tool("find_cycles", {})
        assert result["has_cycles"] is True
        assert len(result["cycles"]) > 0

    @pytest.mark.asyncio
    async def test_mixed_add_facts_and_add_knowledge(self):
        """Test that add_facts and add_knowledge work together."""
        server = GraphServer()

        # Add via add_knowledge
        await server._handle_tool("add_knowledge", {
            "knowledge": "A connects B"
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


class TestAddKnowledgeRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_codebase_dependency_graph(self):
        """Test building a codebase dependency graph via DSL."""
        server = GraphServer()

        result = await server._handle_tool("add_knowledge", {
            "knowledge": """
# Service layer
AuthService:service depends_on UserRepository:repository
AuthService:service uses TokenService:service

# Repository layer
UserRepository:repository depends_on DatabasePool:infrastructure

# Infrastructure
TokenService:service uses RedisCache:infrastructure
ConfigLoader:config configures DatabasePool:infrastructure
ConfigLoader:config configures RedisCache:infrastructure
"""
        })

        assert result["nodes_created"] == 6
        assert result["edges_created"] == 6

        info = await server._handle_tool("get_graph_info", {})
        assert info["node_count"] == 6
        assert info["node_types"]["service"] == 2
        assert info["node_types"]["repository"] == 1
        assert info["node_types"]["infrastructure"] == 2
        assert info["node_types"]["config"] == 1

    @pytest.mark.asyncio
    async def test_knowledge_graph_entities(self):
        """Test building a knowledge graph via DSL."""
        server = GraphServer()

        result = await server._handle_tool("add_knowledge", {
            "knowledge": """
# European capitals
Paris:city capital_of France:country
London:city capital_of UnitedKingdom:country

# Geography
France:country located_in Europe:continent
UnitedKingdom:country located_in Europe:continent
Paris:city located_on Seine:river
"""
        })

        assert result["nodes_created"] == 6
        assert result["edges_created"] == 5

        graph = server.session_manager.get_graph("default")
        nodes = graph.list_nodes(type_filter="city")
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_large_knowledge_block(self):
        """Test adding a large block of knowledge at once."""
        server = GraphServer()

        # Build a large dependency chain
        knowledge_lines = []
        for i in range(20):
            knowledge_lines.append(f"Node{i} connects Node{i+1}")

        result = await server._handle_tool("add_knowledge", {
            "knowledge": "\n".join(knowledge_lines)
        })

        assert result["nodes_created"] == 21  # Node0 through Node20
        assert result["edges_created"] == 20

        # Verify path from start to end
        path_result = await server._handle_tool("shortest_path", {
            "source": "Node0",
            "target": "Node20"
        })
        assert path_result["length"] == 20
