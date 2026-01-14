"""Session manager for named graphs."""

from typing import Dict, List, Any
from datetime import datetime
from .graph_engine import GraphEngine


class SessionManager:
    """Manages multiple named graph sessions."""

    def __init__(self):
        self.graphs: Dict[str, Dict[str, Any]] = {}

    def get_graph(self, name: str = "default") -> GraphEngine:
        """
        Get or create a graph session by name.

        Args:
            name: Graph name (defaults to "default")

        Returns:
            GraphEngine instance
        """
        if name not in self.graphs:
            # Create embeddings dict that will be shared between GraphEngine and its Matcher
            embeddings = {}

            # Auto-create graph on first access with shared embeddings
            self.graphs[name] = {
                'graph': GraphEngine(embeddings=embeddings),
                'embeddings': embeddings,  # Keep reference for potential future use
                'created_at': datetime.now(),
                'last_accessed': datetime.now()
            }

        # Update last accessed time
        self.graphs[name]['last_accessed'] = datetime.now()

        return self.graphs[name]['graph']

    def list_graphs(self) -> List[Dict[str, Any]]:
        """
        List all graph sessions.

        Returns:
            List of graph info dicts with name, node_count, edge_count, created_at
        """
        result = []

        for name, session in self.graphs.items():
            graph_engine = session['graph']
            stats = graph_engine.get_stats()

            result.append({
                'name': name,
                'node_count': stats['node_count'],
                'edge_count': stats['edge_count'],
                'created_at': session['created_at'].isoformat()
            })

        return result

    def delete_graph(self, name: str = "default") -> bool:
        """
        Delete a graph session.

        Args:
            name: Graph name to delete

        Returns:
            True if graph was deleted, False if it didn't exist
        """
        if name in self.graphs:
            del self.graphs[name]
            return True
        return False

    def get_graph_info(self, name: str = "default") -> Dict[str, Any]:
        """
        Get detailed information about a graph.

        Args:
            name: Graph name

        Returns:
            Dict with graph statistics and metadata

        Raises:
            ValueError: If graph doesn't exist
        """
        if name not in self.graphs:
            raise ValueError(f"Graph '{name}' does not exist")

        session = self.graphs[name]
        graph_engine = session['graph']
        stats = graph_engine.get_stats()

        return {
            'name': name,
            'node_count': stats['node_count'],
            'edge_count': stats['edge_count'],
            'is_directed': stats['is_directed'],
            'density': stats['density'],
            'is_connected': stats['is_connected'],
            'is_dag': stats['is_dag'],
            'node_types': stats['node_types'],
            'relation_types': stats['relation_types'],
            'created_at': session['created_at'].isoformat(),
            'last_accessed': session['last_accessed'].isoformat()
        }
