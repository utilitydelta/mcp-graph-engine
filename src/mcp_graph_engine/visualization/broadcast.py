"""WebSocket broadcast manager for graph visualization."""

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class BroadcastManager:
    """Manages WebSocket connections and broadcasts updates to connected clients.

    Thread-safe: All connection mutations are protected by an asyncio.Lock.
    """

    def __init__(self):
        # Map of graph_name -> set of WebSocket connections
        self.connections: dict[str, set[WebSocket]] = {}
        # Lock for thread-safe access to connections
        self._lock = asyncio.Lock()

    async def add_connection(self, graph_name: str, websocket: WebSocket) -> None:
        """Register a WebSocket connection for a graph."""
        async with self._lock:
            if graph_name not in self.connections:
                self.connections[graph_name] = set()
            self.connections[graph_name].add(websocket)
            logger.debug(
                f"Added connection for graph '{graph_name}', "
                f"total: {len(self.connections[graph_name])}"
            )

    async def remove_connection(self, graph_name: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        async with self._lock:
            if graph_name in self.connections:
                self.connections[graph_name].discard(websocket)
                logger.debug(
                    f"Removed connection for graph '{graph_name}', "
                    f"remaining: {len(self.connections[graph_name])}"
                )
                if not self.connections[graph_name]:
                    del self.connections[graph_name]

    def get_connection_count(self, graph_name: str) -> int:
        """Get number of active connections for a graph.

        Note: This is a point-in-time snapshot and may be stale by the time
        the caller uses the result. For informational purposes only.
        """
        return len(self.connections.get(graph_name, set()))

    async def broadcast_update(self, graph_name: str, update: dict) -> None:
        """Broadcast update to all clients viewing this graph.

        Handles disconnected clients gracefully by removing them from the set.
        Uses asyncio.gather for parallel sends to prevent slow clients from
        blocking others.
        """
        async with self._lock:
            if graph_name not in self.connections:
                return

            # Snapshot the connections to send to
            connections = list(self.connections[graph_name])

        if not connections:
            return

        async def send_to_client(ws: WebSocket) -> tuple[WebSocket, bool]:
            """Send update to a single client, returning (websocket, success)."""
            try:
                await ws.send_json(update)
                return (ws, True)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                return (ws, False)

        # Send to all clients in parallel
        results = await asyncio.gather(
            *[send_to_client(ws) for ws in connections],
            return_exceptions=True
        )

        # Collect disconnected clients
        disconnected = set()
        for result in results:
            if isinstance(result, Exception):
                # Unexpected exception from gather itself
                logger.warning(f"Unexpected broadcast error: {result}")
                continue
            ws, success = result
            if not success:
                disconnected.add(ws)

        # Clean up disconnected clients under lock
        if disconnected:
            async with self._lock:
                if graph_name in self.connections:
                    self.connections[graph_name] -= disconnected
                    if not self.connections[graph_name]:
                        del self.connections[graph_name]

    async def broadcast_to_all(self, update: dict) -> None:
        """Broadcast update to all connected clients across all graphs."""
        async with self._lock:
            graph_names = list(self.connections.keys())

        for graph_name in graph_names:
            await self.broadcast_update(graph_name, update)
