"""MCP Graph Engine server with stdio transport."""

import atexit
import json
import logging
import os
import re
import shlex
import signal
from collections.abc import Sequence
from typing import Any

import networkx as nx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .cypher import execute_cypher_query
from .session import SessionManager
from .tools import ALL_TOOLS
from .visualization.web_server import VisualizationServer

logger = logging.getLogger(__name__)

# Global reference for cleanup handlers
_active_server: "GraphServer | None" = None


def remove_comments(line: str) -> str:
    """Remove # comments, but not # inside quoted strings."""
    in_quotes = False
    quote_char = None
    for i, char in enumerate(line):
        if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
        elif char == '#' and not in_quotes:
            return line[:i]
    return line


def parse_knowledge_dsl(knowledge: str) -> list[dict[str, str]]:
    """Parse the simple DSL format into facts.

    Format:
        Subject relation Object
        Subject:type relation Object:type
        "Subject With Spaces" relation "Object With Spaces"
        "Subject":type "relation with spaces" "Object":type
        # Comments are ignored (but not # inside quotes)
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
        # Remove comments (but preserve # inside quotes)
        line = remove_comments(line)

        # Strip whitespace
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Split into parts using shlex to handle quoted strings
        try:
            parts = shlex.split(line)
        except ValueError as e:
            raise ValueError(
                f"Line {line_num}: Invalid syntax - {e}"
            ) from e

        if len(parts) != 3:
            raise ValueError(
                f"Line {line_num}: Expected 3 parts (subject relation object), got {len(parts)}: '{line}'"
            )

        subject_part, relation, object_part = parts

        # Parse subject (handle optional type hint)
        if ':' in subject_part:
            subject, subject_type = subject_part.rsplit(':', 1)
        else:
            subject = subject_part
            subject_type = None

        # Parse object (handle optional type hint)
        if ':' in object_part:
            obj, object_type = object_part.rsplit(':', 1)
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


def parse_mermaid(mermaid: str) -> list[dict[str, str]]:
    """Parse Mermaid flowchart syntax into facts.

    Supports:
        - graph TD / graph LR (direction markers)
        - A --> B (simple edge, relation defaults to 'relates_to')
        - A -->|label| B (edge with label as relation)
        - A -- text --> B (alternative label syntax)
        - A ---|text| B (another label variant)
        - A[Label] (node with display label)
        - A(Label), A{Label} (other node shapes - label extracted)

    Args:
        mermaid: Multi-line string with Mermaid flowchart syntax

    Returns:
        List of fact dictionaries suitable for add_facts

    Raises:
        ValueError: If the Mermaid syntax is malformed
    """
    facts = []
    node_labels = {}  # Map node IDs to their display labels

    for _line_num, line in enumerate(mermaid.split('\n'), start=1):
        # Strip whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('%%'):
            continue

        # Skip graph direction declarations
        if line.startswith('graph ') or line.startswith('flowchart '):
            continue

        # Pattern for edges with various syntax variants
        # Captures: source_id, source_label, edge_type, edge_label, target_id, target_label

        # Try to match edge patterns (handles multiple arrow styles and labels)
        # Pattern breakdown:
        # (\w+) - source node ID
        # (?:\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\})? - optional source label in [], (), or {}
        # \s* - whitespace
        # (?:-->|---|-\.-|==>|~~>|--) - arrow type
        # (?:\|([^|]+)\||--\s*([^-]+?)\s*-->)? - optional edge label (|label| or -- label -->)
        # \s* - whitespace
        # (\w+) - target node ID
        # (?:\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\})? - optional target label in [], (), or {}

        # Simplified pattern for basic support
        # Support different arrow types: -->, ---, -.-, -.->, ==>, ~~>
        edge_pattern = r'(\w+)(?:\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\})?\s*(?:-->|---|\.->|-\.\->|==>|~~>)\s*(?:\|([^|]+)\|)?\s*(\w+)(?:\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\})?'

        match = re.match(edge_pattern, line)
        if match:
            groups = match.groups()
            source_id = groups[0]
            # Source label can be in [], (), or {}
            source_label = groups[1] or groups[2] or groups[3]
            edge_label = groups[4]
            target_id = groups[5]
            # Target label can be in [], (), or {}
            target_label = groups[6] or groups[7] or groups[8]

            # Store node labels if provided
            if source_label:
                node_labels[source_id] = source_label
            if target_label:
                node_labels[target_id] = target_label

            # Determine source and target names (use label if available, else ID)
            source_name = node_labels.get(source_id, source_id)
            target_name = node_labels.get(target_id, target_id)

            # Determine relation (use edge label if available, else default)
            relation = edge_label.strip() if edge_label else "relates_to"

            # Create fact
            fact = {
                "from": source_name,
                "to": target_name,
                "rel": relation
            }

            facts.append(fact)
        else:
            # Try to match node-only declarations (for storing labels)
            node_pattern = r'(\w+)(?:\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\})'
            node_match = re.match(node_pattern, line)
            if node_match:
                node_id = node_match.group(1)
                node_label = node_match.group(2) or node_match.group(3) or node_match.group(4)
                if node_label:
                    node_labels[node_id] = node_label
            # Otherwise, skip lines that don't match (could be style declarations, etc.)

    return facts


def parse_ask_query(query: str, graph) -> dict[str, Any]:
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
        global _active_server
        self.app = Server("mcp-graph-engine")
        self.session_manager = SessionManager(on_mutation=self._handle_graph_mutation)

        # Visualization server
        self.vis_server = None
        if os.environ.get('VIS_ENABLED', 'true').lower() == 'true':
            self._start_visualization_server()

        self._setup_handlers()
        self._register_cleanup()
        _active_server = self

    def _register_cleanup(self):
        """Register cleanup handlers for graceful shutdown."""
        atexit.register(self.cleanup)

        # Register signal handlers (SIGTERM, SIGINT)
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self._signal_handler)
            except (ValueError, OSError):
                # Signal handling may not work in all contexts (e.g., non-main thread)
                pass

    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, cleaning up...")
        self.cleanup()

    def cleanup(self):
        """Clean up resources (stop visualization server, etc.)."""
        if self.vis_server is not None:
            self.vis_server.stop()
            self.vis_server = None

    def _start_visualization_server(self):
        """Start the embedded visualization server."""
        port = int(os.environ.get('VIS_PORT', '8765'))
        host = os.environ.get('VIS_HOST', 'localhost')

        self.vis_server = VisualizationServer(self.session_manager)
        self.vis_server.start(host=host, port=port)

    def _compute_critical_path(self, graph: nx.DiGraph) -> list[dict]:
        """Compute critical path for a DAG.

        Args:
            graph: NetworkX DiGraph to analyze

        Returns:
            List of edge dicts with 'source' and 'target' keys representing
            the critical path, or empty list if graph is not a DAG or has no edges
        """
        # Check if graph is empty or has no edges
        if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
            return []

        # Check if graph is a DAG
        if not nx.is_directed_acyclic_graph(graph):
            return []

        # Compute longest path in the DAG
        try:
            path = nx.dag_longest_path(graph)
            # Convert node path to edge list
            critical_edges = [
                {"source": path[i], "target": path[i + 1]}
                for i in range(len(path) - 1)
            ]
            return critical_edges
        except Exception as e:
            logger.warning(f"Failed to compute critical path: {e}")
            return []

    def _handle_graph_mutation(self, graph_name: str, mutation_type: str, **kwargs):
        """Handle graph mutation by broadcasting to visualization clients."""
        if not self.vis_server:
            return

        # Build update message for WebSocket broadcast
        update = {"type": "graph_update", "graph": graph_name}
        if mutation_type == "node_added":
            update["added_nodes"] = [kwargs.get("node")]
            update["removed_nodes"] = []
            update["added_edges"] = []
            update["removed_edges"] = []
        elif mutation_type == "edge_added":
            update["added_nodes"] = []
            update["removed_nodes"] = []
            update["added_edges"] = [kwargs.get("edge")]
            update["removed_edges"] = []
        elif mutation_type == "node_removed":
            update["added_nodes"] = []
            update["removed_nodes"] = [kwargs.get("node_id")]
            update["added_edges"] = []
            update["removed_edges"] = []
        elif mutation_type == "edge_removed":
            update["added_nodes"] = []
            update["removed_nodes"] = []
            update["added_edges"] = []
            update["removed_edges"] = [kwargs.get("edge")]
        else:
            return  # Unknown mutation type

        # Compute critical path for the updated graph
        try:
            graph = self.session_manager.get_graph(graph_name)
            update["criticalPath"] = self._compute_critical_path(graph.graph)
        except Exception as e:
            logger.warning(f"Failed to compute critical path for graph '{graph_name}': {e}")
            update["criticalPath"] = []

        # Schedule async broadcast - use thread-safe approach
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.vis_server.broadcast_update(graph_name, update))
        except RuntimeError:
            # No running event loop - try to get any event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.vis_server.broadcast_update(graph_name, update),
                        loop
                    )
                else:
                    # Loop exists but not running - queue for later or skip
                    logger.debug(f"No running event loop for graph update broadcast: {mutation_type}")
            except RuntimeError as e:
                logger.debug(f"Could not schedule graph update broadcast: {e}")

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

        elif name == "dump_context":
            graph = self.session_manager.get_graph(graph_name)
            return self._dump_context(graph, graph_name)

        # Import/Export tools
        elif name == "import_graph":
            from pathlib import Path

            graph = self.session_manager.get_graph(graph_name)
            file_path = args.get("file_path")
            content = args.get("content")

            # Validation
            if file_path and content:
                raise ValueError("Provide either file_path or content, not both")
            if not file_path and not content:
                raise ValueError("Must provide either file_path or content")

            # Get content from file if path provided
            if file_path:
                path = Path(file_path).expanduser().resolve()
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                if not path.is_file():
                    raise ValueError(f"Path is not a file: {path}")
                content = path.read_text(encoding="utf-8")

            result = graph.import_graph(
                format=args["format"],
                content=content
            )

            # Include source info in response
            source = f"file '{file_path}'" if file_path else "inline content"
            return {
                **result,
                "source": source
            }

        elif name == "export_graph":
            graph = self.session_manager.get_graph(graph_name)
            format_type = args["format"]
            file_path = args.get("file_path")

            # Export the graph
            content = graph.export_graph(format=format_type)

            # If file_path provided, write to file and return metadata
            if file_path:
                from pathlib import Path
                path = Path(file_path).expanduser().resolve()
                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return {
                    "file_path": str(path),
                    "format": format_type,
                    "bytes_written": len(content.encode("utf-8"))
                }
            else:
                # Return inline (existing behavior)
                return {"content": content}

        elif name == "create_from_mermaid":
            # Parse Mermaid content into facts
            mermaid = args["mermaid"]
            facts = parse_mermaid(mermaid)

            # Reuse add_facts logic by calling it with parsed facts
            return await self._handle_tool("add_facts", {"graph": graph_name, "facts": facts})

        elif name == "cypher_query":
            query = args["query"]
            graph = self.session_manager.get_graph(graph_name)
            return execute_cypher_query(graph.graph, query)

        elif name == "visualize_graph":
            filter_query = args.get("filter")

            if not self.vis_server:
                self._start_visualization_server()

            if filter_query:
                await self.vis_server.set_filter(graph_name, filter_query)

            graph = self.session_manager.get_graph(graph_name)
            nodes, edges = self.vis_server._export_for_d3(graph)

            host = self.vis_server.host
            port = self.vis_server.port
            url = f"http://{host}:{port}/graphs/{graph_name}"

            return {
                "url": url,
                "graph": graph_name,
                "filter": filter_query,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "message": f"Visualization ready at {url}"
            }

        elif name == "update_visualization_filter":
            filter_query = args.get("filter", "")

            if not self.vis_server:
                return {"error": "Visualization server not running"}

            await self.vis_server.set_filter(graph_name, filter_query if filter_query else None)

            # set_filter already broadcasts the filtered data to connected clients

            return {
                "success": True,
                "graph": graph_name,
                "filter": filter_query if filter_query else None,
                "message": f"Filter {'updated' if filter_query else 'cleared'} for graph '{graph_name}'"
            }

        elif name == "stop_visualization":
            if self.vis_server:
                self.vis_server.stop()
                self.vis_server = None
                return {"success": True, "message": "Visualization server stopped"}
            else:
                return {"success": True, "message": "Visualization server was not running"}

        else:
            raise ValueError(f"Unknown tool: {name}")

    def _dump_context(self, graph, graph_name: str) -> dict[str, str]:
        """
        Generate a complete readable summary of the graph state.

        Args:
            graph: GraphEngine instance
            graph_name: Name of the graph

        Returns:
            Dict with 'context' key containing formatted text summary
        """
        lines = []
        lines.append(f"=== Graph Context: {graph_name} ===")
        lines.append("")

        # Get basic stats
        stats = graph.get_stats()
        node_count = stats['node_count']
        edge_count = stats['edge_count']
        node_types = stats.get('node_types', {})

        # Statistics section
        lines.append("## Statistics")
        lines.append(f"- {node_count} nodes, {edge_count} edges")

        if node_types:
            type_count = len([t for t in node_types if t != 'unknown'])
            lines.append(f"- {type_count} node types: {', '.join(sorted([t for t in node_types if t != 'unknown']))}")

        # Check for cycles
        cycles_result = graph.find_cycles()
        has_cycles = cycles_result.get('has_cycles', False)
        cycle_count = len(cycles_result.get('cycles', []))
        if has_cycles:
            lines.append(f"- Cycles detected: Yes ({cycle_count} cycles)")
        else:
            lines.append("- Cycles detected: No")

        lines.append("")

        # Handle empty graph
        if node_count == 0:
            lines.append("(Graph is empty)")
            return {"context": "\n".join(lines)}

        # Nodes by Type section
        lines.append("## Nodes by Type")
        lines.append("")

        nodes = graph.list_nodes()
        nodes_by_type = {}
        for node in nodes:
            node_type = node.get('type') or 'unknown'
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append(node['label'])

        # Sort types (put 'unknown' last)
        sorted_types = sorted([t for t in nodes_by_type.keys() if t != 'unknown'])
        if 'unknown' in nodes_by_type:
            sorted_types.append('unknown')

        for node_type in sorted_types:
            type_nodes = sorted(nodes_by_type[node_type])
            lines.append(f"### {node_type} ({len(type_nodes)} nodes)")
            for node_label in type_nodes:
                lines.append(f"- {node_label}")
            lines.append("")

        # Relationships section
        lines.append(f"## Relationships ({edge_count} total)")
        lines.append("")

        if edge_count > 0:
            edges = graph.find_edges()
            # Sort edges for consistency
            sorted_edges = sorted(edges, key=lambda e: (e['source'], e['target']))

            for edge in sorted_edges:
                relation = edge.get('relation', 'related_to')
                lines.append(f"- {edge['source']} {relation} {edge['target']}")
        else:
            lines.append("(No relationships)")

        lines.append("")

        # Key Insights section
        lines.append("## Key Insights")
        lines.append("")

        # Find most connected nodes using actual degree counts
        # Calculate actual degrees (not normalized centrality)
        degree_counts = []
        for node in nodes:
            in_degree = graph.graph.in_degree(node['label'])
            out_degree = graph.graph.out_degree(node['label'])
            total_degree = in_degree + out_degree
            if total_degree > 0:  # Only include connected nodes
                degree_counts.append({
                    'label': node['label'],
                    'in_degree': in_degree,
                    'out_degree': out_degree,
                    'total': total_degree
                })

        # Sort by total degree
        degree_counts.sort(key=lambda x: x['total'], reverse=True)

        if degree_counts:
            top_node = degree_counts[0]
            lines.append(f"- Most connected: {top_node['label']} ({top_node['total']} connections)")

            # List hubs (nodes with >= 2 total connections)
            hubs = [r['label'] for r in degree_counts[:3] if r['total'] >= 2]
            if len(hubs) > 1:
                lines.append(f"- Hubs: {', '.join(hubs)}")

        # Find isolated nodes (orphans)
        orphans = []
        for node in nodes:
            neighbors = graph.get_neighbors(node['label'], direction="both")
            if not neighbors:
                orphans.append(node['label'])

        if orphans:
            lines.append(f"- Isolated nodes: {', '.join(sorted(orphans))}")
        else:
            lines.append("- Isolated nodes: None")

        # List cycles if they exist
        if has_cycles:
            cycles = cycles_result.get('cycles', [])
            lines.append("- Cycles:")
            for cycle in cycles[:3]:  # Show first 3 cycles
                cycle_str = ' -> '.join(cycle + [cycle[0]])
                lines.append(f"  - {cycle_str}")
            if len(cycles) > 3:
                lines.append(f"  - ... and {len(cycles) - 3} more")

        return {"context": "\n".join(lines)}

    async def run(self):
        """Run the server with stdio transport."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options()
                )
        finally:
            self.cleanup()


def main():
    """Entry point for the MCP Graph Engine server."""
    import asyncio

    server = GraphServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
