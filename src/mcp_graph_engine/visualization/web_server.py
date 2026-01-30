"""FastAPI-based web server for D3 graph visualization."""

import asyncio
import logging
import socket
import threading
from pathlib import Path

import networkx as nx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..cypher import execute_cypher_query
from .broadcast import BroadcastManager

logger = logging.getLogger(__name__)


class VisualizationServer:
    """Web server for serving D3 visualization and handling WebSocket connections.

    Provides:
    - Static file serving for D3 visualization frontend
    - WebSocket endpoint for real-time graph updates
    - Filter management for Cypher-based graph filtering
    """

    def __init__(self, session_manager):
        """Initialize the visualization server.

        Args:
            session_manager: SessionManager instance for accessing graphs
        """
        self.session_manager = session_manager
        self.app = FastAPI(title="Graph Visualization Server")
        self.broadcast_manager = BroadcastManager()
        self.filters: dict[str, str] = {}  # graph_name -> cypher_filter
        self._filters_lock = asyncio.Lock()
        self._server_thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None
        self.host: str | None = None
        self.port: int | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register FastAPI routes for static files and WebSocket."""
        # Serve static files (D3, JS, CSS)
        static_dir = Path(__file__).parent / "static"
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @self.app.get("/graphs/{graph_name}")
        async def serve_visualization(graph_name: str) -> HTMLResponse:
            """Serve the visualization HTML page for a specific graph."""
            html_path = static_dir / "index.html"
            return HTMLResponse(html_path.read_text())

        @self.app.websocket("/ws/{graph_name}")
        async def websocket_endpoint(websocket: WebSocket, graph_name: str) -> None:
            """Handle WebSocket connections for real-time graph updates."""
            await websocket.accept()

            # Register connection with broadcast manager
            await self.broadcast_manager.add_connection(graph_name, websocket)
            logger.info(f"WebSocket connected for graph '{graph_name}'")

            try:
                # Send initial state to new connection
                await self._send_initial_state(websocket, graph_name)

                # Keep connection alive, handle incoming messages
                while True:
                    data = await websocket.receive_text()
                    # Future: Handle client messages (e.g., subscribe/unsubscribe)
                    logger.debug(f"Received from client: {data}")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for graph '{graph_name}'")
            finally:
                await self.broadcast_manager.remove_connection(graph_name, websocket)

    async def _send_initial_state(self, websocket: WebSocket, graph_name: str) -> None:
        """Send current graph state to a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to send to
            graph_name: Name of the graph to send
        """
        try:
            graph = self.session_manager.get_graph(graph_name)
            async with self._filters_lock:
                filter_query = self.filters.get(graph_name)

            nodes, edges = self._get_filtered_data(graph, filter_query)

            # Compute critical path
            critical_path = self._compute_critical_path(graph.graph)

            await websocket.send_json({
                "type": "initial_state",
                "graph": graph_name,
                "filter": filter_query,
                "nodes": nodes,
                "edges": edges,
                "criticalPath": critical_path
            })
        except Exception as e:
            logger.error(f"Failed to send initial state for graph '{graph_name}': {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to load graph: {e}"
            })

    def _get_filtered_data(self, graph, filter_query: str | None) -> tuple[list, list]:
        """Get graph data, optionally filtered by Cypher query.

        Args:
            graph: GraphEngine instance
            filter_query: Optional Cypher query to filter the graph

        Returns:
            Tuple of (nodes, edges) lists in D3 format
        """
        if not filter_query:
            return self._export_for_d3(graph)

        result = execute_cypher_query(graph.graph, filter_query)
        logger.debug(f"Cypher filter query: {filter_query}")
        logger.debug(f"Cypher result: success={result.get('success')}, count={result.get('count')}, rows={result.get('rows', [])[:3]}")

        if not result.get("success") or not result.get("rows"):
            logger.warning(f"Cypher filter failed or empty: {result.get('error', 'no results')}")
            return [], []

        node_ids: set[str] = set()
        edges: set[tuple[str, str, str]] = set()  # (source, target, relation)

        # Get all node keys for comparison
        graph_node_keys = set(graph.graph.nodes)
        logger.debug(f"Graph has {len(graph_node_keys)} nodes: {list(graph_node_keys)[:5]}...")

        # Extract nodes and edges from query results
        # GrandCypher returns dicts for nodes: {"type": "...", "label": "..."}
        # and dicts for edges: {"relation": "..."}
        for row in result["rows"]:
            values = list(row.values())
            row_nodes = []
            row_relation = None

            for val in values:
                if isinstance(val, dict):
                    # Node dict has 'label' key, edge dict has 'relation' key
                    if "label" in val:
                        node_label = val["label"]
                        if node_label in graph_node_keys:
                            row_nodes.append(node_label)
                            node_ids.add(node_label)
                    elif "relation" in val:
                        row_relation = val["relation"]
                elif isinstance(val, str):
                    # Fallback for string values (e.g., RETURN n.label)
                    if val in graph_node_keys:
                        row_nodes.append(val)
                        node_ids.add(val)

            # If we have exactly 2 nodes and a relation, record the edge
            if len(row_nodes) == 2 and row_relation:
                edges.add((row_nodes[0], row_nodes[1], row_relation))

        logger.debug(f"Extracted {len(node_ids)} nodes and {len(edges)} edges from filter")

        # Build D3 format from collected nodes and edges
        nodes = []
        for node_id in node_ids:
            attrs = graph.graph.nodes.get(node_id, {})
            nodes.append({
                "id": node_id,
                "label": attrs.get("label", node_id),
                "type": attrs.get("type"),
                "inDegree": graph.graph.in_degree(node_id),
                "outDegree": graph.graph.out_degree(node_id),
                **{k: v for k, v in attrs.items() if k not in ("label", "type")}
            })

        edges_list = []
        for src, tgt, rel in edges:
            edges_list.append({"source": src, "target": tgt, "relation": rel})

        return nodes, edges_list

    def _export_for_d3(self, graph) -> tuple[list, list]:
        """Convert NetworkX graph to D3-compatible format.

        Args:
            graph: GraphEngine instance with .graph attribute (NetworkX DiGraph)

        Returns:
            Tuple of (nodes, edges) where:
            - nodes: List of dicts with id, label, type, and other attributes
            - edges: List of dicts with source, target, relation, and other attributes
        """
        nodes = []
        for node, attrs in graph.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "label": attrs.get("label", node),
                "type": attrs.get("type"),
                "inDegree": graph.graph.in_degree(node),
                "outDegree": graph.graph.out_degree(node),
                **{k: v for k, v in attrs.items() if k not in ("label", "type")}
            })

        edges = []
        for source, target, attrs in graph.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "relation": attrs.get("relation", "relates_to"),
                **{k: v for k, v in attrs.items() if k != "relation"}
            })

        return nodes, edges

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

    async def set_filter(self, graph_name: str, filter_query: str | None) -> None:
        """Set or clear a Cypher filter for a graph.

        Args:
            graph_name: Name of the graph to filter
            filter_query: Cypher query string, or None to clear the filter
        """
        async with self._filters_lock:
            if filter_query:
                self.filters[graph_name] = filter_query
                logger.info(f"Set filter for graph '{graph_name}': {filter_query}")
            elif graph_name in self.filters:
                del self.filters[graph_name]
                logger.info(f"Cleared filter for graph '{graph_name}'")

        # Broadcast filtered data to all connected clients
        try:
            graph = self.session_manager.get_graph(graph_name)
            nodes, edges = self._get_filtered_data(graph, filter_query)
            await self.broadcast_manager.broadcast_update(graph_name, {
                "type": "filter_update",
                "graph": graph_name,
                "filter": filter_query,
                "nodes": nodes,
                "edges": edges
            })
        except Exception as e:
            logger.error(f"Failed to broadcast filter update for '{graph_name}': {e}")

    @staticmethod
    def _is_port_available(host: str, port: int) -> bool:
        """Check if a port is available to bind on the given host."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return True
        except OSError:
            return False

    def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start the server in a background thread.

        If the requested port is already in use (e.g. by another instance),
        automatically tries subsequent ports until an available one is found.

        Args:
            host: Host address to bind to
            port: Port number to start trying from
        """
        # Check if server is already running
        if self._server_thread is not None and self._server_thread.is_alive():
            logger.warning("Server is already running, ignoring start request")
            return

        # Find an available port, starting from the requested one
        max_attempts = 20
        actual_port = port
        for _attempt in range(max_attempts):
            if self._is_port_available(host, actual_port):
                break
            logger.info(f"Port {actual_port} is in use, trying {actual_port + 1}")
            actual_port += 1
        else:
            logger.error(f"Could not find an available port after {max_attempts} attempts (tried {port}-{actual_port})")
            return

        self.host = host
        self.port = actual_port

        config = uvicorn.Config(self.app, host=host, port=actual_port, log_level="warning")
        self._server = uvicorn.Server(config)

        def run_server():
            self._server.run()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        if actual_port != port:
            logger.info(f"Visualization server started at http://{host}:{actual_port} (default port {port} was in use)")
        else:
            logger.info(f"Visualization server started at http://{host}:{actual_port}")

    def stop(self) -> None:
        """Stop the server gracefully.

        Signals the uvicorn server to shut down and waits for the thread to finish.
        """
        if self._server is not None:
            logger.info("Stopping visualization server...")
            self._server.should_exit = True
            if self._server_thread is not None and self._server_thread.is_alive():
                self._server_thread.join(timeout=5.0)
                if self._server_thread.is_alive():
                    logger.warning("Server thread did not stop within timeout")
            self._server = None
            self._server_thread = None
            logger.info("Visualization server stopped")

    async def broadcast_update(self, graph_name: str, update: dict) -> None:
        """Broadcast an update to all clients viewing a graph.

        This is a convenience method that delegates to the BroadcastManager.

        Args:
            graph_name: Name of the graph that was updated
            update: Update payload to broadcast
        """
        await self.broadcast_manager.broadcast_update(graph_name, update)
