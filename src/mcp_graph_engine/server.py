"""MCP Graph Engine server with stdio transport."""

import json
import sys
from typing import Any, Sequence, Dict, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from .session import SessionManager
from .tools import ALL_TOOLS


def parse_knowledge_dsl(knowledge: str) -> List[Dict[str, str]]:
    """Parse the simple DSL format into facts.

    Format:
        Subject relation Object
        Subject:type relation Object:type
        # Comments are ignored
        Empty lines are ignored

    Args:
        knowledge: Multi-line string with DSL format

    Returns:
        List of fact dictionaries suitable for add_facts

    Raises:
        ValueError: If a line is malformed
    """
    facts = []

    for line_num, line in enumerate(knowledge.split('\n'), start=1):
        # Strip whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Split into parts
        parts = line.split()

        if len(parts) != 3:
            raise ValueError(
                f"Line {line_num}: Expected 3 parts (subject relation object), got {len(parts)}: '{line}'"
            )

        subject_part, relation, object_part = parts

        # Parse subject (handle optional type hint)
        if ':' in subject_part:
            subject, subject_type = subject_part.split(':', 1)
        else:
            subject = subject_part
            subject_type = None

        # Parse object (handle optional type hint)
        if ':' in object_part:
            obj, object_type = object_part.split(':', 1)
        else:
            obj = object_part
            object_type = None

        # Build fact dictionary
        fact = {
            "from": subject,
            "to": obj,
            "rel": relation
        }

        if subject_type:
            fact["from_type"] = subject_type
        if object_type:
            fact["to_type"] = object_type

        facts.append(fact)

    return facts


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

        # Creation tools
        if name == "add_facts":
            graph = self.session_manager.get_graph(graph_name)
            facts = args["facts"]

            nodes_created = 0
            nodes_existed = 0
            edges_created = 0
            edges_existed = 0

            for fact in facts:
                from_label = fact["from"]
                to_label = fact["to"]
                relation = fact["rel"]
                from_type = fact.get("from_type", "entity")
                to_type = fact.get("to_type", "entity")

                # Auto-create "from" node if it doesn't exist
                _, from_created = graph.add_node(from_label, node_type=from_type)
                if from_created:
                    nodes_created += 1
                else:
                    nodes_existed += 1

                # Auto-create "to" node if it doesn't exist
                _, to_created = graph.add_node(to_label, node_type=to_type)
                if to_created:
                    nodes_created += 1
                else:
                    nodes_existed += 1

                # Add the edge
                _, edge_created, _, _ = graph.add_edge(from_label, to_label, relation)
                if edge_created:
                    edges_created += 1
                else:
                    edges_existed += 1

            return {
                "nodes_created": nodes_created,
                "nodes_existed": nodes_existed,
                "edges_created": edges_created,
                "edges_existed": edges_existed
            }

        elif name == "add_knowledge":
            # Parse DSL into facts
            knowledge = args["knowledge"]
            facts = parse_knowledge_dsl(knowledge)

            # Reuse add_facts logic by calling it with parsed facts
            return await self._handle_tool("add_facts", {"graph": graph_name, "facts": facts})

        # Graph management tools
        elif name == "list_graphs":
            return {"graphs": self.session_manager.list_graphs()}

        elif name == "delete_graph":
            success = self.session_manager.delete_graph(graph_name)
            return {"success": success}

        elif name == "get_graph_info":
            return self.session_manager.get_graph_info(graph_name)

        # Node operation tools
        elif name == "forget":
            graph = self.session_manager.get_graph(graph_name)
            success, edges_removed = graph.remove_node(args["label"])
            return {"success": success, "edges_removed": edges_removed}

        # Edge operation tools
        elif name == "forget_relationship":
            graph = self.session_manager.get_graph(graph_name)
            success = graph.remove_edge(
                source=args["source"],
                target=args["target"],
                relation=args.get("relation")
            )
            return {"success": success}

        # Query & Analysis tools
        elif name == "shortest_path":
            graph = self.session_manager.get_graph(graph_name)
            return graph.shortest_path(
                source=args["source"],
                target=args["target"]
            )

        elif name == "all_paths":
            graph = self.session_manager.get_graph(graph_name)
            return graph.all_paths(
                source=args["source"],
                target=args["target"],
                max_length=args.get("max_length")
            )

        elif name == "pagerank":
            graph = self.session_manager.get_graph(graph_name)
            return graph.pagerank(top_n=args.get("top_n"))

        elif name == "connected_components":
            graph = self.session_manager.get_graph(graph_name)
            return graph.connected_components()

        elif name == "find_cycles":
            graph = self.session_manager.get_graph(graph_name)
            return graph.find_cycles()

        elif name == "transitive_reduction":
            graph = self.session_manager.get_graph(graph_name)
            return graph.transitive_reduction(in_place=args.get("in_place", False))

        elif name == "degree_centrality":
            graph = self.session_manager.get_graph(graph_name)
            return graph.degree_centrality(top_n=args.get("top_n"))

        elif name == "subgraph":
            graph = self.session_manager.get_graph(graph_name)
            return graph.subgraph(
                nodes=args["nodes"],
                include_edges=args.get("include_edges", True)
            )

        # Import/Export tools
        elif name == "import_graph":
            graph = self.session_manager.get_graph(graph_name)
            result = graph.import_graph(
                format=args["format"],
                content=args["content"]
            )
            return result

        elif name == "export_graph":
            graph = self.session_manager.get_graph(graph_name)
            content = graph.export_graph(format=args["format"])
            return {"content": content}

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
