"""MCP Graph Engine server with stdio transport."""

import json
import sys
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from .session import SessionManager
from .tools import ALL_TOOLS


class GraphServer:
    """MCP server for graph operations."""

    def __init__(self):
        self.app = Server("mcp-graph-engine")
        self.session_manager = SessionManager()
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return ALL_TOOLS

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._handle_tool(name, arguments or {})
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                error_result = {"error": str(e), "tool": name}
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    async def _handle_tool(self, name: str, args: dict) -> Any:
        """Route tool calls to appropriate handlers."""

        # Extract graph name (defaults to "default")
        graph_name = args.get("graph", "default")

        # Graph management tools
        if name == "list_graphs":
            return {"graphs": self.session_manager.list_graphs()}

        elif name == "delete_graph":
            success = self.session_manager.delete_graph(graph_name)
            return {"success": success}

        elif name == "get_graph_info":
            return self.session_manager.get_graph_info(graph_name)

        # Node operation tools
        elif name == "add_node":
            graph = self.session_manager.get_graph(graph_name)
            node_data, created = graph.add_node(
                label=args["label"],
                node_type=args.get("type"),
                properties=args.get("properties")
            )
            return {"node": node_data, "created": created}

        elif name == "add_nodes":
            graph = self.session_manager.get_graph(graph_name)
            added, existing = graph.add_nodes(args["nodes"])
            return {"added": added, "existing": existing}

        elif name == "find_node":
            graph = self.session_manager.get_graph(graph_name)
            query = args["query"]
            # Use matcher to find nodes
            from .matcher import Matcher
            matcher = Matcher()
            match = matcher.find_match(query, list(graph.graph.nodes()))

            if match.matched_label:
                # Get node data
                node_attrs = graph.graph.nodes[match.matched_label]
                node_type = node_attrs.get('type')
                properties = {k: v for k, v in node_attrs.items() if k != 'type'}

                return {
                    "matches": [{
                        "label": match.matched_label,
                        "similarity": 1.0 if match.exact else 0.9,
                        "type": node_type,
                        "properties": properties
                    }]
                }
            else:
                return {"matches": []}

        elif name == "remove_node":
            graph = self.session_manager.get_graph(graph_name)
            success, edges_removed = graph.remove_node(args["label"])
            return {"success": success, "edges_removed": edges_removed}

        elif name == "list_nodes":
            graph = self.session_manager.get_graph(graph_name)
            nodes = graph.list_nodes(
                type_filter=args.get("type"),
                limit=args.get("limit")
            )
            return {"nodes": nodes}

        # Edge operation tools
        elif name == "add_edge":
            graph = self.session_manager.get_graph(graph_name)
            edge_data, created, source_matched, target_matched = graph.add_edge(
                source=args["source"],
                target=args["target"],
                relation=args["relation"],
                properties=args.get("properties")
            )
            return {
                "edge": edge_data,
                "created": created,
                "source_matched": source_matched,
                "target_matched": target_matched
            }

        elif name == "add_edges":
            graph = self.session_manager.get_graph(graph_name)
            added, failed = graph.add_edges(args["edges"])
            return {"added": added, "failed": failed}

        elif name == "find_edges":
            graph = self.session_manager.get_graph(graph_name)
            edges = graph.find_edges(
                source=args.get("source"),
                target=args.get("target"),
                relation=args.get("relation")
            )
            return {"edges": edges}

        elif name == "remove_edge":
            graph = self.session_manager.get_graph(graph_name)
            success = graph.remove_edge(
                source=args["source"],
                target=args["target"],
                relation=args.get("relation")
            )
            return {"success": success}

        elif name == "get_neighbors":
            graph = self.session_manager.get_graph(graph_name)
            neighbors = graph.get_neighbors(
                node=args["node"],
                direction=args.get("direction", "both"),
                relation=args.get("relation")
            )
            return {"neighbors": neighbors}

        else:
            raise ValueError(f"Unknown tool: {name}")

    async def run(self):
        """Run the server with stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(
                read_stream,
                write_stream,
                self.app.create_initialization_options()
            )


def main():
    """Entry point for the MCP Graph Engine server."""
    import asyncio

    server = GraphServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
