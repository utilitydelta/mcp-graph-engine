"""Integration tests for dump_context tool through the server."""

import pytest

from mcp_graph_engine.server import GraphServer


@pytest.fixture
def server():
    """Create a server instance for testing."""
    return GraphServer()


class TestDumpContextIntegration:
    """Test dump_context tool through server interface."""

    def test_dump_context_tool_exists(self):
        """Test that dump_context tool is registered."""
        from mcp_graph_engine.tools import ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert "dump_context" in tool_names

    @pytest.mark.asyncio
    async def test_dump_context_through_server(self, server):
        """Test calling dump_context through the server."""
        # First add some facts
        await server._handle_tool("add_facts", {
            "graph": "test",
            "facts": [
                {"from": "ServiceA", "to": "ServiceB", "rel": "depends_on"},
                {"from": "ServiceB", "to": "DatabasePool", "rel": "depends_on"},
            ]
        })

        # Now dump context
        result = await server._handle_tool("dump_context", {"graph": "test"})

        # Check result structure
        assert "context" in result
        context = result["context"]

        # Check that it's formatted text (not JSON)
        assert isinstance(context, str)
        assert "=== Graph Context: test ===" in context
        assert "## Statistics" in context
        assert "## Nodes by Type" in context
        assert "## Relationships" in context
        assert "## Key Insights" in context

    @pytest.mark.asyncio
    async def test_dump_context_empty_graph(self, server):
        """Test dump_context on empty graph."""
        result = await server._handle_tool("dump_context", {"graph": "empty-test"})

        assert "context" in result
        context = result["context"]
        assert "0 nodes, 0 edges" in context
        assert "(Graph is empty)" in context

    @pytest.mark.asyncio
    async def test_dump_context_default_graph(self, server):
        """Test that dump_context defaults to 'default' graph."""
        # Add to default graph
        await server._handle_tool("add_facts", {
            "facts": [
                {"from": "A", "to": "B", "rel": "relates_to"},
            ]
        })

        # Dump without specifying graph
        result = await server._handle_tool("dump_context", {})

        assert "context" in result
        context = result["context"]
        assert "=== Graph Context: default ===" in context
        assert "A relates_to B" in context
