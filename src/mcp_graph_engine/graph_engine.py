"""Graph engine wrapping NetworkX with high-level operations."""

import csv
import json
import logging
from collections.abc import Callable
from io import StringIO
from typing import Any

import networkx as nx
import numpy as np

from .matcher import Matcher, get_embedding_model

logger = logging.getLogger(__name__)


class GraphEngine:
    """Wrapper around NetworkX DiGraph with MCP-friendly operations."""

    def __init__(
        self,
        embeddings: dict[str, np.ndarray] | None = None,
        on_mutation: Callable[[str], None] | None = None
    ):
        """
        Initialize the graph engine.

        Args:
            embeddings: Optional dict mapping node labels to embedding vectors
            on_mutation: Optional callback invoked on graph mutations.
                         Called with mutation_type and keyword args describing the change.
        """
        self.graph = nx.DiGraph()
        self.embeddings = embeddings if embeddings is not None else {}
        self.matcher = Matcher(self.embeddings)
        self._on_mutation = on_mutation

    def _notify_mutation(self, mutation_type: str, **kwargs) -> None:
        """
        Notify listeners of graph mutation.

        Args:
            mutation_type: Type of mutation (e.g., "node_added", "edge_added", "node_removed", "edge_removed")
            **kwargs: Additional data describing the mutation
        """
        if self._on_mutation:
            try:
                self._on_mutation(mutation_type, **kwargs)
            except Exception as e:
                logger.warning(f"Mutation callback failed for {mutation_type}: {e}")

    def add_node(
        self, label: str, node_type: str | None = None, properties: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], bool]:
        """
        Add a node to the graph.

        Args:
            label: Node label
            node_type: Optional node type
            properties: Optional node properties

        Returns:
            Tuple of (node_data, created) where created is True if node was newly created
        """
        created = label not in self.graph

        # Prepare node attributes
        attrs = {}
        if node_type:
            attrs['type'] = node_type
        if properties:
            attrs.update(properties)

        # Always set label attribute for Cypher queries (n.label access)
        attrs['label'] = label

        self.graph.add_node(label, **attrs)

        # Compute and cache embedding for new nodes
        if created and label not in self.embeddings:
            self._compute_embedding(label)

        # Return node data
        node_data = {
            'label': label,
            'type': node_type,
            'properties': properties or {}
        }

        # Notify of mutation if node was newly created
        if created:
            self._notify_mutation("node_added", node={
                "id": label,
                "label": label,
                "type": node_type,
                **(properties or {})
            })

        return node_data, created

    def _compute_embedding(self, label: str):
        """
        Compute and cache the embedding for a node label.

        Args:
            label: Node label to compute embedding for
        """
        model = get_embedding_model()
        if model is None:
            return
        embedding = model.encode(label, convert_to_numpy=True)
        self.embeddings[label] = embedding

    def add_nodes(self, nodes: list[dict[str, Any]]) -> tuple[int, int]:
        """
        Add multiple nodes to the graph.

        Args:
            nodes: List of node dicts with 'label', optional 'type', optional 'properties'

        Returns:
            Tuple of (added_count, existing_count)
        """
        added = 0
        existing = 0

        for node in nodes:
            label = node['label']
            node_type = node.get('type')
            properties = node.get('properties')

            _, created = self.add_node(label, node_type, properties)

            if created:
                added += 1
            else:
                existing += 1

        return added, existing

    def remove_node(self, label: str) -> tuple[bool, int]:
        """
        Remove a node from the graph.

        Args:
            label: Node label to remove

        Returns:
            Tuple of (success, edges_removed)
        """
        if label not in self.graph:
            return False, 0

        # Count edges that will be removed
        edges_removed = self.graph.in_degree(label) + self.graph.out_degree(label)

        self.graph.remove_node(label)

        # Notify of mutation
        self._notify_mutation("node_removed", node_id=label)

        return True, edges_removed

    def list_nodes(
        self, type_filter: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        List nodes in the graph.

        Args:
            type_filter: Optional type to filter by
            limit: Optional limit on number of nodes returned

        Returns:
            List of node dicts with label, type, and properties
        """
        nodes = []

        for label, attrs in self.graph.nodes(data=True):
            node_type = attrs.get('type')

            # Apply type filter
            if type_filter and node_type != type_filter:
                continue

            # Build properties dict (everything except 'type')
            properties = {k: v for k, v in attrs.items() if k != 'type'}

            nodes.append({
                'label': label,
                'type': node_type,
                'properties': properties
            })

            # Apply limit
            if limit and len(nodes) >= limit:
                break

        return nodes

    def find_node(self, query: str) -> dict[str, Any]:
        """
        Find nodes matching the query using fuzzy matching.

        Args:
            query: Query string to match against node labels

        Returns:
            Dict with 'matches' list containing matching nodes with similarity scores
        """
        existing_labels = list(self.graph.nodes())
        match_result = self.matcher.find_match(query, existing_labels)

        matches = []

        # If we have candidates (ambiguous match), return all of them
        if match_result.candidates:
            for label, similarity in match_result.candidates:
                attrs = self.graph.nodes[label]
                node_type = attrs.get('type')
                properties = {k: v for k, v in attrs.items() if k != 'type'}

                matches.append({
                    'label': label,
                    'similarity': similarity,
                    'type': node_type,
                    'properties': properties
                })

        # If we have a single match, return it
        elif match_result.matched_label:
            label = match_result.matched_label
            attrs = self.graph.nodes[label]
            node_type = attrs.get('type')
            properties = {k: v for k, v in attrs.items() if k != 'type'}

            matches.append({
                'label': label,
                'similarity': match_result.similarity,
                'type': node_type,
                'properties': properties
            })

        return {'matches': matches}

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        properties: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], bool, str, str]:
        """
        Add an edge to the graph with fuzzy matching for source and target.

        Args:
            source: Source node label (will be fuzzy matched)
            target: Target node label (will be fuzzy matched)
            relation: Edge relation type
            properties: Optional edge properties

        Returns:
            Tuple of (edge_data, created, source_matched, target_matched)

        Raises:
            ValueError: If source or target nodes don't exist (no match found)
        """
        # Match source node
        existing_nodes = list(self.graph.nodes())
        if not existing_nodes:
            raise ValueError("Cannot add edge: graph is empty. Add nodes first with add_node or add_nodes.")

        source_match = self.matcher.find_match(source, existing_nodes)
        if not source_match.matched_label:
            available = ", ".join(existing_nodes[:5])
            if len(existing_nodes) > 5:
                available += f", ... ({len(existing_nodes)} total nodes)"
            raise ValueError(f"Source node '{source}' not found. Available nodes: {available}. Use find_node to search.")

        # Match target node
        target_match = self.matcher.find_match(target, existing_nodes)
        if not target_match.matched_label:
            available = ", ".join(existing_nodes[:5])
            if len(existing_nodes) > 5:
                available += f", ... ({len(existing_nodes)} total nodes)"
            raise ValueError(f"Target node '{target}' not found. Available nodes: {available}. Use find_node to search.")

        source_matched = source_match.matched_label
        target_matched = target_match.matched_label

        # Check if edge already exists
        created = not self.graph.has_edge(source_matched, target_matched)

        # Prepare edge attributes
        attrs = {'relation': relation}
        if properties:
            attrs.update(properties)

        self.graph.add_edge(source_matched, target_matched, **attrs)

        edge_data = {
            'source': source_matched,
            'target': target_matched,
            'relation': relation
        }

        # Notify of mutation if edge was newly created
        if created:
            self._notify_mutation("edge_added", edge={
                "source": source_matched,
                "target": target_matched,
                "relation": relation
            })

        return edge_data, created, source_matched, target_matched

    def add_edges(self, edges: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
        """
        Add multiple edges to the graph.

        Args:
            edges: List of edge dicts with 'source', 'target', 'relation', optional 'properties'

        Returns:
            Tuple of (added_count, failed_list)
        """
        added = 0
        failed = []

        for edge in edges:
            source = edge['source']
            target = edge['target']
            relation = edge['relation']
            properties = edge.get('properties')

            try:
                _, created, _, _ = self.add_edge(source, target, relation, properties)
                if created:
                    added += 1
            except ValueError as e:
                failed.append({
                    'edge': edge,
                    'reason': str(e)
                })

        return added, failed

    def remove_edge(
        self, source: str, target: str, relation: str | None = None
    ) -> bool:
        """
        Remove an edge from the graph.

        Args:
            source: Source node label
            target: Target node label
            relation: Optional relation to match (if None, removes all edges between nodes)

        Returns:
            True if edge was removed, False otherwise
        """
        # Match source node
        source_match = self.matcher.find_match(source, list(self.graph.nodes()))
        if not source_match.matched_label:
            return False

        # Match target node
        target_match = self.matcher.find_match(target, list(self.graph.nodes()))
        if not target_match.matched_label:
            return False

        source_matched = source_match.matched_label
        target_matched = target_match.matched_label

        if not self.graph.has_edge(source_matched, target_matched):
            return False

        # If relation is specified, check if it matches
        if relation:
            edge_data = self.graph.get_edge_data(source_matched, target_matched)
            if edge_data.get('relation') != relation:
                return False

        # Get edge relation before removal for notification
        edge_data = self.graph.get_edge_data(source_matched, target_matched)
        edge_relation = edge_data.get('relation') if edge_data else None

        self.graph.remove_edge(source_matched, target_matched)

        # Notify of mutation
        self._notify_mutation("edge_removed", edge={
            "source": source_matched,
            "target": target_matched,
            "relation": edge_relation
        })

        return True

    def find_edges(
        self,
        source: str | None = None,
        target: str | None = None,
        relation: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Find edges matching the given criteria.

        Args:
            source: Optional source node label to filter by
            target: Optional target node label to filter by
            relation: Optional relation type to filter by

        Returns:
            List of edge dicts with source, target, relation, and properties
        """
        # Match source if provided
        source_matched = None
        if source:
            source_match = self.matcher.find_match(source, list(self.graph.nodes()))
            if source_match.matched_label:
                source_matched = source_match.matched_label

        # Match target if provided
        target_matched = None
        if target:
            target_match = self.matcher.find_match(target, list(self.graph.nodes()))
            if target_match.matched_label:
                target_matched = target_match.matched_label

        edges = []

        for src, tgt, attrs in self.graph.edges(data=True):
            # Apply filters
            if source_matched and src != source_matched:
                continue
            if target_matched and tgt != target_matched:
                continue
            if relation and attrs.get('relation') != relation:
                continue

            # Build properties dict (everything except 'relation')
            properties = {k: v for k, v in attrs.items() if k != 'relation'}

            edges.append({
                'source': src,
                'target': tgt,
                'relation': attrs.get('relation'),
                'properties': properties
            })

        return edges

    def get_neighbors(
        self,
        node: str,
        direction: str = "both",
        relation: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get neighbors of a node.

        Args:
            node: Node label
            direction: "in", "out", or "both"
            relation: Optional relation type to filter by

        Returns:
            List of neighbor dicts with label, relation, and direction
        """
        # Match node
        node_match = self.matcher.find_match(node, list(self.graph.nodes()))
        if not node_match.matched_label:
            return []

        node_matched = node_match.matched_label
        neighbors = []

        # Get incoming neighbors
        if direction in ("in", "both"):
            for pred in self.graph.predecessors(node_matched):
                edge_data = self.graph.get_edge_data(pred, node_matched)
                edge_relation = edge_data.get('relation')

                if relation and edge_relation != relation:
                    continue

                neighbors.append({
                    'label': pred,
                    'relation': edge_relation,
                    'direction': 'in'
                })

        # Get outgoing neighbors
        if direction in ("out", "both"):
            for succ in self.graph.successors(node_matched):
                edge_data = self.graph.get_edge_data(node_matched, succ)
                edge_relation = edge_data.get('relation')

                if relation and edge_relation != relation:
                    continue

                neighbors.append({
                    'label': succ,
                    'relation': edge_relation,
                    'direction': 'out'
                })

        return neighbors

    def get_stats(self) -> dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dict with node_count, edge_count, and other stats
        """
        node_count = self.graph.number_of_nodes()
        edge_count = self.graph.number_of_edges()

        # Count node types
        node_types = {}
        for _, attrs in self.graph.nodes(data=True):
            node_type = attrs.get('type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1

        # Count relation types
        relation_types = {}
        for _, _, attrs in self.graph.edges(data=True):
            relation = attrs.get('relation', 'unknown')
            relation_types[relation] = relation_types.get(relation, 0) + 1

        # Calculate density
        if node_count > 1:
            density = edge_count / (node_count * (node_count - 1))
        else:
            density = 0.0

        # Check if DAG
        is_dag = nx.is_directed_acyclic_graph(self.graph)

        # Check if connected (weakly for directed graph)
        is_connected = nx.is_weakly_connected(self.graph) if node_count > 0 else True

        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'is_directed': True,
            'density': density,
            'is_connected': is_connected,
            'is_dag': is_dag,
            'node_types': node_types,
            'relation_types': relation_types
        }

    # Query & Analysis Methods

    def shortest_path(self, source: str, target: str) -> dict[str, Any]:
        """
        Find the shortest path between two nodes.

        Args:
            source: Source node label (will be fuzzy matched)
            target: Target node label (will be fuzzy matched)

        Returns:
            Dict with 'path' (list of node labels) and 'length', or 'path': None with 'reason' if no path exists
        """
        existing_nodes = list(self.graph.nodes())
        if not existing_nodes:
            return {"path": None, "reason": "Cannot find path: graph is empty. Add nodes first."}

        # Match source node
        source_match = self.matcher.find_match(source, existing_nodes)
        if not source_match.matched_label:
            available = ", ".join(existing_nodes[:5])
            if len(existing_nodes) > 5:
                available += f", ... ({len(existing_nodes)} total)"
            return {"path": None, "reason": f"Source node '{source}' not found. Available: {available}. Use find_node to search."}

        # Match target node
        target_match = self.matcher.find_match(target, existing_nodes)
        if not target_match.matched_label:
            available = ", ".join(existing_nodes[:5])
            if len(existing_nodes) > 5:
                available += f", ... ({len(existing_nodes)} total)"
            return {"path": None, "reason": f"Target node '{target}' not found. Available: {available}. Use find_node to search."}

        source_matched = source_match.matched_label
        target_matched = target_match.matched_label

        # Handle self-loops
        if source_matched == target_matched:
            return {"path": [source_matched], "length": 0}

        try:
            path = nx.shortest_path(self.graph, source_matched, target_matched)
            return {"path": path, "length": len(path) - 1}
        except nx.NetworkXNoPath:
            return {"path": None, "reason": f"No path exists from '{source_matched}' to '{target_matched}'. Nodes are in disconnected components. Use connected_components to analyze."}
        except nx.NodeNotFound as e:
            return {"path": None, "reason": f"Internal error: Node not found in graph: {str(e)}"}

    def all_paths(self, source: str, target: str, max_length: int | None = None) -> dict[str, Any]:
        """
        Find all simple paths between two nodes.

        Args:
            source: Source node label (will be fuzzy matched)
            target: Target node label (will be fuzzy matched)
            max_length: Maximum path length (cutoff)

        Returns:
            Dict with 'paths' (list of paths) and 'count'
        """
        existing_nodes = list(self.graph.nodes())
        if not existing_nodes:
            return {"paths": [], "count": 0, "reason": "Cannot find paths: graph is empty. Add nodes first."}

        # Match source node
        source_match = self.matcher.find_match(source, existing_nodes)
        if not source_match.matched_label:
            available = ", ".join(existing_nodes[:5])
            if len(existing_nodes) > 5:
                available += f", ... ({len(existing_nodes)} total)"
            return {"paths": [], "count": 0, "reason": f"Source node '{source}' not found. Available: {available}. Use find_node to search."}

        # Match target node
        target_match = self.matcher.find_match(target, existing_nodes)
        if not target_match.matched_label:
            available = ", ".join(existing_nodes[:5])
            if len(existing_nodes) > 5:
                available += f", ... ({len(existing_nodes)} total)"
            return {"paths": [], "count": 0, "reason": f"Target node '{target}' not found. Available: {available}. Use find_node to search."}

        source_matched = source_match.matched_label
        target_matched = target_match.matched_label

        # Handle self-loops
        if source_matched == target_matched:
            return {"paths": [[source_matched]], "count": 1}

        try:
            paths = list(nx.all_simple_paths(self.graph, source_matched, target_matched, cutoff=max_length))
            if len(paths) == 0:
                return {"paths": [], "count": 0, "reason": f"No paths found from '{source_matched}' to '{target_matched}'. Nodes may be in disconnected components."}
            return {"paths": paths, "count": len(paths)}
        except nx.NodeNotFound as e:
            return {"paths": [], "count": 0, "reason": f"Internal error: Node not found in graph: {str(e)}"}

    def pagerank(self, top_n: int | None = None) -> dict[str, Any]:
        """
        Calculate PageRank scores for all nodes.

        Args:
            top_n: Optional limit to return only top N nodes

        Returns:
            Dict with 'rankings' (list of {label, score})
        """
        if self.graph.number_of_nodes() == 0:
            return {"rankings": []}

        try:
            scores = nx.pagerank(self.graph)
            # Sort by score descending
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            # Apply top_n limit if specified
            if top_n is not None:
                sorted_scores = sorted_scores[:top_n]

            rankings = [{"label": label, "score": score} for label, score in sorted_scores]
            return {"rankings": rankings}
        except Exception as e:
            return {"rankings": [], "error": f"PageRank calculation failed: {str(e)}"}

    def connected_components(self) -> dict[str, Any]:
        """
        Find weakly connected components in the directed graph.

        Returns:
            Dict with 'components' (list of lists of node labels) and 'count'
        """
        if self.graph.number_of_nodes() == 0:
            return {"components": [], "count": 0}

        # Use weakly_connected_components for directed graphs
        components = list(nx.weakly_connected_components(self.graph))
        # Convert sets to sorted lists for consistent output
        components_lists = [sorted(list(comp)) for comp in components]
        # Sort by size descending, then alphabetically by first node
        components_lists.sort(key=lambda x: (-len(x), x[0] if x else ""))

        return {"components": components_lists, "count": len(components_lists)}

    def find_cycles(self) -> dict[str, Any]:
        """
        Detect cycles in the graph.

        Returns:
            Dict with 'cycles' (list of cycles) and 'has_cycles' boolean
        """
        if self.graph.number_of_nodes() == 0:
            return {"cycles": [], "has_cycles": False}

        try:
            # simple_cycles returns an iterator of cycles
            cycles = list(nx.simple_cycles(self.graph))
            return {"cycles": cycles, "has_cycles": len(cycles) > 0}
        except Exception as e:
            return {"cycles": [], "has_cycles": False, "error": f"Cycle detection failed: {str(e)}"}

    def transitive_reduction(self, in_place: bool = False) -> dict[str, Any]:
        """
        Remove redundant edges from the graph (transitive reduction).

        Args:
            in_place: If True, modify the current graph; if False, return count without modifying

        Returns:
            Dict with 'edges_removed' count
        """
        if self.graph.number_of_edges() == 0:
            return {"edges_removed": 0}

        try:
            # Get the transitive reduction
            reduced = nx.transitive_reduction(self.graph)

            # Count edges that would be removed
            original_edges = set(self.graph.edges())
            reduced_edges = set(reduced.edges())
            edges_to_remove = original_edges - reduced_edges
            edges_removed_count = len(edges_to_remove)

            # If in_place, modify the current graph
            if in_place:
                # Remove the redundant edges but preserve edge attributes for remaining edges
                for src, tgt in edges_to_remove:
                    self.graph.remove_edge(src, tgt)

            return {"edges_removed": edges_removed_count}
        except Exception as e:
            return {"edges_removed": 0, "error": f"Transitive reduction failed: {str(e)}"}

    def degree_centrality(self, top_n: int | None = None) -> dict[str, Any]:
        """
        Calculate degree centrality for all nodes.

        Args:
            top_n: Optional limit to return only top N nodes

        Returns:
            Dict with 'rankings' (list of {label, in_degree, out_degree, total})
        """
        if self.graph.number_of_nodes() == 0:
            return {"rankings": []}

        try:
            in_centrality = nx.in_degree_centrality(self.graph)
            out_centrality = nx.out_degree_centrality(self.graph)

            # Combine into rankings with total score
            rankings = []
            for node in self.graph.nodes():
                in_deg = in_centrality[node]
                out_deg = out_centrality[node]
                total = in_deg + out_deg
                rankings.append({
                    "label": node,
                    "in_degree": in_deg,
                    "out_degree": out_deg,
                    "total": total
                })

            # Sort by total centrality descending
            rankings.sort(key=lambda x: x["total"], reverse=True)

            # Apply top_n limit if specified
            if top_n is not None:
                rankings = rankings[:top_n]

            return {"rankings": rankings}
        except Exception as e:
            return {"rankings": [], "error": f"Degree centrality calculation failed: {str(e)}"}

    def subgraph(self, nodes: list[str], include_edges: bool = True) -> dict[str, Any]:
        """
        Extract a subgraph containing specific nodes.

        Args:
            nodes: List of node labels (will be fuzzy matched)
            include_edges: If True, include edges between the nodes; if False, only nodes

        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        # Match all provided nodes
        matched_nodes = []
        not_found = []

        for node_label in nodes:
            node_match = self.matcher.find_match(node_label, list(self.graph.nodes()))
            if node_match.matched_label:
                matched_nodes.append(node_match.matched_label)
            else:
                not_found.append(node_label)

        if not matched_nodes:
            return {"nodes": [], "edges": [], "not_found": not_found}

        # Get subgraph
        try:
            sub = self.graph.subgraph(matched_nodes)

            # Build nodes list with attributes
            nodes_list = []
            for label in sub.nodes():
                attrs = self.graph.nodes[label]
                node_type = attrs.get('type')
                properties = {k: v for k, v in attrs.items() if k != 'type'}
                nodes_list.append({
                    'label': label,
                    'type': node_type,
                    'properties': properties
                })

            # Build edges list if requested
            edges_list = []
            if include_edges:
                for src, tgt, attrs in sub.edges(data=True):
                    relation = attrs.get('relation')
                    properties = {k: v for k, v in attrs.items() if k != 'relation'}
                    edges_list.append({
                        'source': src,
                        'target': tgt,
                        'relation': relation,
                        'properties': properties
                    })

            result = {"nodes": nodes_list, "edges": edges_list}
            if not_found:
                result["not_found"] = not_found

            return result
        except Exception as e:
            return {"nodes": [], "edges": [], "error": f"Subgraph extraction failed: {str(e)}", "not_found": not_found}

    # Import/Export Methods

    def import_graph(self, format: str, content: str) -> dict[str, Any]:
        """
        Import a graph from various formats, merging into the existing graph.

        Args:
            format: Format of the input ("dot", "csv", "graphml", "json")
            content: String content to parse

        Returns:
            Dict with 'nodes_added' and 'edges_added' counts
        """
        if not content or not content.strip():
            raise ValueError(f"Cannot import: content is empty. Provide valid {format} data.")

        initial_node_count = self.graph.number_of_nodes()
        initial_edge_count = self.graph.number_of_edges()

        try:
            if format == "dot":
                self._import_dot(content)
            elif format == "csv":
                self._import_csv(content)
            elif format == "graphml":
                self._import_graphml(content)
            elif format == "json":
                self._import_json(content)
            else:
                raise ValueError(f"Unsupported import format '{format}'. Supported formats: dot, csv, graphml, json.")

            nodes_added = self.graph.number_of_nodes() - initial_node_count
            edges_added = self.graph.number_of_edges() - initial_edge_count

            return {"nodes_added": nodes_added, "edges_added": edges_added}
        except ValueError:
            # Re-raise ValueError with original message
            raise
        except Exception as e:
            # Wrap other exceptions with helpful context
            raise ValueError(f"Import failed ({format} format): {str(e)}. Check that content is valid {format} data.") from e

    def _import_dot(self, content: str):
        """Import from DOT format using pydot."""
        import pydot

        # Parse DOT content
        graphs = pydot.graph_from_dot_data(content)
        if not graphs:
            raise ValueError("Failed to parse DOT content")

        pydot_graph = graphs[0]

        # Import nodes
        for node in pydot_graph.get_nodes():
            node_name = node.get_name().strip('"')
            # Skip special nodes
            if node_name in ('graph', 'node', 'edge'):
                continue

            # Extract node attributes
            node_type = node.get('type')
            if node_type:
                node_type = node_type.strip('"')

            # Add node
            self.add_node(node_name, node_type=node_type)

        # Import edges
        for edge in pydot_graph.get_edges():
            source = edge.get_source().strip('"')
            target = edge.get_destination().strip('"')

            # Get relation from 'label' attribute or default to 'edge'
            relation = edge.get('label')
            if relation:
                relation = relation.strip('"')
            else:
                relation = 'edge'

            # Add edge (nodes should already exist from above)
            try:
                self.add_edge(source, target, relation)
            except ValueError:
                # Node might not exist if it was implicit in DOT
                self.add_node(source)
                self.add_node(target)
                self.add_edge(source, target, relation)

    def _import_csv(self, content: str):
        """Import from CSV edge list format."""
        reader = csv.DictReader(StringIO(content))

        # Validate headers
        if not reader.fieldnames or 'source' not in reader.fieldnames or 'target' not in reader.fieldnames:
            available = ", ".join(reader.fieldnames) if reader.fieldnames else "none"
            raise ValueError(f"CSV must have 'source' and 'target' columns. Found columns: {available}")

        for row in reader:
            source = row['source'].strip()
            target = row['target'].strip()
            relation = row.get('relation', 'edge').strip()

            # Add nodes if they don't exist
            if source not in self.graph:
                self.add_node(source)
            if target not in self.graph:
                self.add_node(target)

            # Add edge
            self.add_edge(source, target, relation)

    def _import_graphml(self, content: str):
        """Import from GraphML format using NetworkX."""
        # Parse GraphML
        imported_graph = nx.read_graphml(StringIO(content))

        # Convert to directed if needed
        if not imported_graph.is_directed():
            imported_graph = imported_graph.to_directed()

        # Import nodes
        for node, attrs in imported_graph.nodes(data=True):
            node_type = attrs.get('type')
            properties = {k: v for k, v in attrs.items() if k != 'type'}
            self.add_node(node, node_type=node_type, properties=properties if properties else None)

        # Import edges
        for source, target, attrs in imported_graph.edges(data=True):
            relation = attrs.get('relation', 'edge')
            properties = {k: v for k, v in attrs.items() if k != 'relation'}
            self.add_edge(source, target, relation, properties=properties if properties else None)

    def _import_json(self, content: str):
        """Import from JSON format."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {str(e)}") from e

        # Import nodes
        if 'nodes' in data:
            for node_data in data['nodes']:
                label = node_data.get('label')
                if not label:
                    continue
                node_type = node_data.get('type')
                properties = node_data.get('properties')
                self.add_node(label, node_type=node_type, properties=properties)

        # Import edges
        if 'edges' in data:
            for edge_data in data['edges']:
                source = edge_data.get('source')
                target = edge_data.get('target')
                if not source or not target:
                    continue

                # Add nodes if they don't exist
                if source not in self.graph:
                    self.add_node(source)
                if target not in self.graph:
                    self.add_node(target)

                relation = edge_data.get('relation', 'edge')
                properties = edge_data.get('properties')
                self.add_edge(source, target, relation, properties=properties)

    def export_graph(self, format: str) -> str:
        """
        Export the graph to various formats.

        Args:
            format: Format to export to ("dot", "csv", "graphml", "json")

        Returns:
            String containing the exported graph
        """
        if self.graph.number_of_nodes() == 0:
            # Allow exporting empty graphs
            if format == "json":
                return '{"nodes": [], "edges": []}'
            elif format == "csv":
                return "source,target,relation\n"
            elif format == "dot":
                return "digraph {\n}\n"
            elif format == "mermaid":
                return "graph TD\n"
            elif format == "graphml":
                # Return minimal GraphML
                pass  # Fall through to normal export

        try:
            if format == "dot":
                return self._export_dot()
            elif format == "csv":
                return self._export_csv()
            elif format == "graphml":
                return self._export_graphml()
            elif format == "json":
                return self._export_json()
            elif format == "mermaid":
                return self._export_mermaid()
            else:
                raise ValueError(f"Unsupported export format '{format}'. Supported formats: dot, csv, graphml, json, mermaid.")
        except ValueError:
            # Re-raise ValueError with original message
            raise
        except Exception as e:
            # Wrap other exceptions with helpful context
            raise ValueError(f"Export failed ({format} format): {str(e)}") from e

    def _export_dot(self) -> str:
        """Export to DOT format using pydot."""
        import pydot

        # Create pydot graph
        pydot_graph = pydot.Dot(graph_type='digraph')

        # Add nodes
        for node, attrs in self.graph.nodes(data=True):
            node_type = attrs.get('type')
            pydot_node = pydot.Node(node)
            if node_type:
                pydot_node.set('type', node_type)
            pydot_graph.add_node(pydot_node)

        # Add edges
        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get('relation', 'edge')
            pydot_edge = pydot.Edge(source, target, label=relation)
            pydot_graph.add_edge(pydot_edge)

        return pydot_graph.to_string()

    def _export_csv(self) -> str:
        """Export to CSV edge list format."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['source', 'target', 'relation'])
        writer.writeheader()

        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get('relation', 'edge')
            writer.writerow({
                'source': source,
                'target': target,
                'relation': relation
            })

        return output.getvalue()

    def _export_graphml(self) -> str:
        """Export to GraphML format using NetworkX."""
        from io import BytesIO
        output = BytesIO()
        nx.write_graphml(self.graph, output)
        return output.getvalue().decode('utf-8')

    def _export_json(self) -> str:
        """Export to JSON format."""
        data = {
            'nodes': [],
            'edges': []
        }

        # Export nodes
        for node, attrs in self.graph.nodes(data=True):
            node_type = attrs.get('type')
            properties = {k: v for k, v in attrs.items() if k != 'type'}
            node_data = {'label': node}
            if node_type:
                node_data['type'] = node_type
            if properties:
                node_data['properties'] = properties
            data['nodes'].append(node_data)

        # Export edges
        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get('relation', 'edge')
            properties = {k: v for k, v in attrs.items() if k != 'relation'}
            edge_data = {
                'source': source,
                'target': target,
                'relation': relation
            }
            if properties:
                edge_data['properties'] = properties
            data['edges'].append(edge_data)

        return json.dumps(data, indent=2)

    def _sanitize_node_id(self, label: str) -> str:
        """Generate valid Mermaid node ID from label."""
        import re
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def _export_mermaid(self) -> str:
        """Export to Mermaid flowchart format."""
        import re
        lines = ["graph TD"]
        node_ids = {}  # Map labels to generated IDs

        # Check which nodes need sanitized IDs
        for node in self.graph.nodes():
            if not re.match(r'^[a-zA-Z0-9_]+$', node):
                node_ids[node] = self._sanitize_node_id(node)

        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get('relation', 'relates_to')
            # Escape pipe characters in relations
            relation_escaped = relation.replace('|', '&#124;')

            src_id = node_ids.get(source, source)
            tgt_id = node_ids.get(target, target)

            # Use bracket syntax if ID differs from original label
            src_str = f'{src_id}["{source}"]' if src_id != source else source
            tgt_str = f'{tgt_id}["{target}"]' if tgt_id != target else target

            lines.append(f"    {src_str} -->|{relation_escaped}| {tgt_str}")

        return "\n".join(lines)
