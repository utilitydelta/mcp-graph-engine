"""MCP Graph Engine server with stdio transport."""

import json
import sys
import re
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


def parse_ask_query(query: str, graph) -> Dict[str, Any]:
    """
    Parse natural language queries and map them to graph operations.

    Args:
        query: Natural language query string
        graph: GraphEngine instance

    Returns:
        Dict with query results or error/help message
    """
    query_lower = query.lower().strip()

    # Pattern 1: "what depends on X" / "what depends on X" → incoming edges
    match = re.match(r'^what\s+depends\s+on\s+(.+)$', query_lower, re.IGNORECASE)
    if match:
        node_name = match.group(1).strip()
        # Find nodes that point to this node (predecessors)
        neighbors = graph.get_neighbors(node_name, direction="in")
        if not neighbors:
            return {
                "query": query,
                "interpretation": f"Find what depends on '{node_name}'",
                "result": f"No incoming dependencies found for '{node_name}'"
            }

        dependents = [n['label'] for n in neighbors]
        return {
            "query": query,
            "interpretation": f"Find what depends on '{node_name}'",
            "result": f"Nodes that depend on '{node_name}': {', '.join(dependents)}",
            "dependents": dependents
        }

    # Pattern 2: "what does X depend on" / "dependencies of X" → outgoing edges
    match = re.match(r'^what\s+(?:does\s+)?(.+?)\s+depend(?:s)?\s+on$', query_lower, re.IGNORECASE)
    if match:
        node_name = match.group(1).strip()
        # Find nodes this node points to (successors)
        neighbors = graph.get_neighbors(node_name, direction="out")
        if not neighbors:
            return {
                "query": query,
                "interpretation": f"Find what '{node_name}' depends on",
                "result": f"'{node_name}' has no outgoing dependencies"
            }
        dependencies = [n['label'] for n in neighbors]
        return {
            "query": query,
            "interpretation": f"Find what '{node_name}' depends on",
            "result": f"'{node_name}' depends on: {', '.join(dependencies)}",
            "dependencies": dependencies
        }

    # Pattern 3: "dependencies of X" → outgoing edges (alternative phrasing)
    match = re.match(r'^dependencies\s+(?:of\s+)?(.+)$', query_lower, re.IGNORECASE)
    if match:
        node_name = match.group(1).strip()
        # Find nodes this node points to (successors)
        neighbors = graph.get_neighbors(node_name, direction="out")
        if not neighbors:
            return {
                "query": query,
                "interpretation": f"Find what '{node_name}' depends on",
                "result": f"'{node_name}' has no outgoing dependencies"
            }
        dependencies = [n['label'] for n in neighbors]
        return {
            "query": query,
            "interpretation": f"Find what '{node_name}' depends on",
            "result": f"'{node_name}' depends on: {', '.join(dependencies)}",
            "dependencies": dependencies
        }

    # Pattern 4: "dependents of X" → incoming edges
    match = re.match(r'^dependents\s+(?:of\s+)?(.+)$', query_lower, re.IGNORECASE)
    if match:
        node_name = match.group(1).strip()
        neighbors = graph.get_neighbors(node_name, direction="in")
        if not neighbors:
            return {
                "query": query,
                "interpretation": f"Find dependents of '{node_name}'",
                "result": f"No nodes depend on '{node_name}'"
            }
        dependents = [n['label'] for n in neighbors]
        return {
            "query": query,
            "interpretation": f"Find dependents of '{node_name}'",
            "result": f"Nodes that depend on '{node_name}': {', '.join(dependents)}",
            "dependents": dependents
        }

    # Pattern 5: Path queries - "path from X to Y" / "shortest path X to Y" / "how to get from X to Y"
    match = re.match(r'^(?:shortest\s+)?path\s+from\s+(.+?)\s+to\s+(.+)$', query_lower, re.IGNORECASE)
    if not match:
        match = re.match(r'^how\s+(?:to\s+)?(?:get\s+)?from\s+(.+?)\s+to\s+(.+)$', query_lower, re.IGNORECASE)
    if match:
        source = match.group(1).strip()
        target = match.group(2).strip()
        result = graph.shortest_path(source, target)
        if result.get('path'):
            path_str = ' -> '.join(result['path'])
            return {
                "query": query,
                "interpretation": f"Find shortest path from '{source}' to '{target}'",
                "result": f"Path found (length {result['length']}): {path_str}",
                "path": result['path'],
                "length": result['length']
            }
        else:
            return {
                "query": query,
                "interpretation": f"Find shortest path from '{source}' to '{target}'",
                "result": result.get('reason', 'No path found'),
                "path": None
            }

    # Pattern 6: All paths query - "all paths from X to Y"
    match = re.match(r'^all\s+paths?\s+from\s+(.+?)\s+to\s+(.+)$', query_lower, re.IGNORECASE)
    if match:
        source = match.group(1).strip()
        target = match.group(2).strip()
        result = graph.all_paths(source, target)
        if result.get('count', 0) > 0:
            paths_strs = [' -> '.join(path) for path in result['paths']]
            return {
                "query": query,
                "interpretation": f"Find all paths from '{source}' to '{target}'",
                "result": f"Found {result['count']} path(s):\n" + '\n'.join(f"  {i+1}. {p}" for i, p in enumerate(paths_strs)),
                "paths": result['paths'],
                "count": result['count']
            }
        else:
            return {
                "query": query,
                "interpretation": f"Find all paths from '{source}' to '{target}'",
                "result": result.get('reason', 'No paths found'),
                "paths": [],
                "count": 0
            }

    # Pattern 7: Cycles queries - "cycles" / "find cycles" / "what are the cycles"
    if re.match(r'^(?:find\s+)?(?:what\s+are\s+(?:the\s+)?)?cycles?$', query_lower, re.IGNORECASE):
        result = graph.find_cycles()
        if result['has_cycles']:
            cycles_strs = [' -> '.join(cycle + [cycle[0]]) for cycle in result['cycles']]
            return {
                "query": query,
                "interpretation": "Find cycles in the graph",
                "result": f"Found {len(result['cycles'])} cycle(s):\n" + '\n'.join(f"  {i+1}. {c}" for i, c in enumerate(cycles_strs)),
                "cycles": result['cycles'],
                "has_cycles": True
            }
        else:
            return {
                "query": query,
                "interpretation": "Find cycles in the graph",
                "result": "No cycles found - graph is acyclic",
                "cycles": [],
                "has_cycles": False
            }

    # Pattern 8: Most connected / important nodes / central nodes
    if re.match(r'^(?:most\s+)?(?:connected|important|central)\s*(?:nodes?)?$', query_lower, re.IGNORECASE):
        # Use degree centrality for "most connected"
        result = graph.degree_centrality(top_n=10)
        if result['rankings']:
            rankings_str = '\n'.join(
                f"  {i+1}. {r['label']} (in: {r['in_degree']:.2f}, out: {r['out_degree']:.2f}, total: {r['total']:.2f})"
                for i, r in enumerate(result['rankings'])
            )
            return {
                "query": query,
                "interpretation": "Find most connected nodes",
                "result": f"Top {len(result['rankings'])} most connected nodes:\n{rankings_str}",
                "rankings": result['rankings']
            }
        else:
            return {
                "query": query,
                "interpretation": "Find most connected nodes",
                "result": "No nodes in graph",
                "rankings": []
            }

    # Pattern 9: Orphans / isolated nodes / disconnected
    if re.match(r'^(?:orphans?|isolated|disconnected)(?:\s+nodes?)?$', query_lower, re.IGNORECASE):
        # Find nodes with no edges
        nodes = graph.list_nodes()
        orphans = []
        for node in nodes:
            neighbors = graph.get_neighbors(node['label'], direction="both")
            if not neighbors:
                orphans.append(node['label'])

        if orphans:
            return {
                "query": query,
                "interpretation": "Find nodes with no connections",
                "result": f"Found {len(orphans)} isolated node(s): {', '.join(orphans)}",
                "orphans": orphans
            }
        else:
            return {
                "query": query,
                "interpretation": "Find nodes with no connections",
                "result": "No isolated nodes found - all nodes have at least one connection",
                "orphans": []
            }

    # Pattern 10: Components / clusters
    if re.match(r'^(?:connected\s+)?(?:components?|clusters?)$', query_lower, re.IGNORECASE):
        result = graph.connected_components()
        if result['count'] > 0:
            components_str = '\n'.join(
                f"  Component {i+1} ({len(comp)} nodes): {', '.join(comp)}"
                for i, comp in enumerate(result['components'])
            )
            return {
                "query": query,
                "interpretation": "Find connected components",
                "result": f"Found {result['count']} connected component(s):\n{components_str}",
                "components": result['components'],
                "count": result['count']
            }
        else:
            return {
                "query": query,
                "interpretation": "Find connected components",
                "result": "No nodes in graph",
                "components": [],
                "count": 0
            }

    # Fallback: unrecognized query
    return {
        "query": query,
        "error": "Query pattern not recognized",
        "help": (
            "Supported query patterns:\n"
            "  - 'what depends on X' - find nodes that depend on X\n"
            "  - 'what does X depend on' - find X's dependencies\n"
            "  - 'dependencies of X' - find X's dependencies\n"
            "  - 'dependents of X' - find what depends on X\n"
            "  - 'path from X to Y' - find shortest path\n"
            "  - 'all paths from X to Y' - find all paths\n"
            "  - 'cycles' - find circular dependencies\n"
            "  - 'most connected' - find highly connected nodes\n"
            "  - 'orphans' - find isolated nodes\n"
            "  - 'components' - find connected components"
        )
    }


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

        elif name == "ask_graph":
            graph = self.session_manager.get_graph(graph_name)
            query = args["query"]
            return parse_ask_query(query, graph)

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
