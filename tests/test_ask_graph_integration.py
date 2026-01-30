"""Integration tests for ask_graph tool with MCP server."""

import pytest

from mcp_graph_engine.server import GraphServer


@pytest.mark.asyncio
class TestAskGraphIntegration:
    """Test ask_graph tool through the server interface."""

    @pytest.fixture
    async def server_with_graph(self):
        """Create a server with a sample graph."""
        server = GraphServer()

        # Add some test data
        knowledge = """
A depends_on B
B depends_on C
D depends_on B
"""
        await server._handle_tool("add_knowledge", {"knowledge": knowledge})

        return server

    async def test_ask_graph_tool_exists(self):
        """Test that ask_graph tool is registered."""
        server = GraphServer()

        # Get list of tools
        handler = server.app.request_handlers.get("tools/list")
        if handler:
            tools = await handler()
            tool_names = [tool.name for tool in tools]
            assert "ask_graph" in tool_names

    async def test_ask_graph_what_depends_on(self, server_with_graph):
        """Test 'what depends on' query through server."""
        result = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "what depends on B"}
        )

        assert "dependents" in result
        assert set(result["dependents"]) == {"A", "D"}

    async def test_ask_graph_dependencies_of(self, server_with_graph):
        """Test 'dependencies of' query through server."""
        result = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "dependencies of A"}
        )

        assert "dependencies" in result
        assert result["dependencies"] == ["B"]

    async def test_ask_graph_path(self, server_with_graph):
        """Test path query through server."""
        result = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "path from A to C"}
        )

        assert result["path"] is not None
        assert result["path"] == ["A", "B", "C"]
        assert result["length"] == 2

    async def test_ask_graph_cycles(self, server_with_graph):
        """Test cycles query through server."""
        # Add a cycle
        await server_with_graph._handle_tool(
            "add_facts",
            {"facts": [{"from": "C", "to": "A", "rel": "depends_on"}]}
        )

        result = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "cycles"}
        )

        assert result["has_cycles"] is True
        assert len(result["cycles"]) > 0

    async def test_ask_graph_unrecognized_query(self, server_with_graph):
        """Test unrecognized query through server."""
        result = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "invalid query"}
        )

        assert "error" in result
        assert "help" in result

    async def test_ask_graph_with_different_graph_names(self):
        """Test ask_graph with non-default graph name."""
        server = GraphServer()

        # Create graph in custom session
        await server._handle_tool(
            "add_knowledge",
            {
                "graph": "test_graph",
                "knowledge": "X depends_on Y"
            }
        )

        result = await server._handle_tool(
            "ask_graph",
            {
                "graph": "test_graph",
                "query": "what depends on Y"
            }
        )

        assert "dependents" in result
        assert "X" in result["dependents"]

    async def test_ask_graph_case_insensitive(self, server_with_graph):
        """Test that queries are case insensitive."""
        result1 = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "what depends on B"}
        )

        result2 = await server_with_graph._handle_tool(
            "ask_graph",
            {"query": "WHAT DEPENDS ON B"}
        )

        # Both should work
        assert "dependents" in result1
        assert "dependents" in result2
        assert result1["dependents"] == result2["dependents"]
