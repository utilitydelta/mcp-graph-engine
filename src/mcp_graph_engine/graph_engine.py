"""Graph engine wrapping NetworkX with high-level operations."""

from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
import numpy as np
from .matcher import Matcher, MatchResult


class GraphEngine:
    """Wrapper around NetworkX DiGraph with MCP-friendly operations."""

    def __init__(self, embeddings: Optional[Dict[str, np.ndarray]] = None):
        """
        Initialize the graph engine.

        Args:
            embeddings: Optional dict mapping node labels to embedding vectors
        """
        self.graph = nx.DiGraph()
        self.embeddings = embeddings if embeddings is not None else {}
        self.matcher = Matcher(self.embeddings)
        self._embedding_model = None  # Lazy-loaded

    def add_node(
        self, label: str, node_type: Optional[str] = None, properties: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], bool]:
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

        return node_data, created

    def _compute_embedding(self, label: str):
        """
        Compute and cache the embedding for a node label.

        Args:
            label: Node label to compute embedding for
        """
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            from .matcher import MATCHING_CONFIG
            self._embedding_model = SentenceTransformer(MATCHING_CONFIG["embedding_model"])

        embedding = self._embedding_model.encode(label, convert_to_numpy=True)
        self.embeddings[label] = embedding

    def add_nodes(self, nodes: List[Dict[str, Any]]) -> Tuple[int, int]:
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

    def remove_node(self, label: str) -> Tuple[bool, int]:
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

        return True, edges_removed

    def list_nodes(
        self, type_filter: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
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

    def find_node(self, query: str) -> Dict[str, Any]:
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
        properties: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], bool, str, str]:
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
        source_match = self.matcher.find_match(source, list(self.graph.nodes()))
        if not source_match.matched_label:
            raise ValueError(f"Source node not found: {source}")

        # Match target node
        target_match = self.matcher.find_match(target, list(self.graph.nodes()))
        if not target_match.matched_label:
            raise ValueError(f"Target node not found: {target}")

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

        return edge_data, created, source_matched, target_matched

    def add_edges(self, edges: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
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
        self, source: str, target: str, relation: Optional[str] = None
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

        self.graph.remove_edge(source_matched, target_matched)
        return True

    def find_edges(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
        relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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

    def get_stats(self) -> Dict[str, Any]:
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

    def shortest_path(self, source: str, target: str) -> Dict[str, Any]:
        """
        Find the shortest path between two nodes.

        Args:
            source: Source node label (will be fuzzy matched)
            target: Target node label (will be fuzzy matched)

        Returns:
            Dict with 'path' (list of node labels) and 'length', or 'path': None with 'reason' if no path exists
        """
        # Match source node
        source_match = self.matcher.find_match(source, list(self.graph.nodes()))
        if not source_match.matched_label:
            return {"path": None, "reason": f"Source node not found: {source}"}

        # Match target node
        target_match = self.matcher.find_match(target, list(self.graph.nodes()))
        if not target_match.matched_label:
            return {"path": None, "reason": f"Target node not found: {target}"}

        source_matched = source_match.matched_label
        target_matched = target_match.matched_label

        try:
            path = nx.shortest_path(self.graph, source_matched, target_matched)
            return {"path": path, "length": len(path) - 1}
        except nx.NetworkXNoPath:
            return {"path": None, "reason": f"No path exists between {source_matched} and {target_matched}"}
        except nx.NodeNotFound as e:
            return {"path": None, "reason": f"Node not found in graph: {str(e)}"}

    def all_paths(self, source: str, target: str, max_length: Optional[int] = None) -> Dict[str, Any]:
        """
        Find all simple paths between two nodes.

        Args:
            source: Source node label (will be fuzzy matched)
            target: Target node label (will be fuzzy matched)
            max_length: Maximum path length (cutoff)

        Returns:
            Dict with 'paths' (list of paths) and 'count'
        """
        # Match source node
        source_match = self.matcher.find_match(source, list(self.graph.nodes()))
        if not source_match.matched_label:
            return {"paths": [], "count": 0, "reason": f"Source node not found: {source}"}

        # Match target node
        target_match = self.matcher.find_match(target, list(self.graph.nodes()))
        if not target_match.matched_label:
            return {"paths": [], "count": 0, "reason": f"Target node not found: {target}"}

        source_matched = source_match.matched_label
        target_matched = target_match.matched_label

        try:
            paths = list(nx.all_simple_paths(self.graph, source_matched, target_matched, cutoff=max_length))
            return {"paths": paths, "count": len(paths)}
        except nx.NodeNotFound as e:
            return {"paths": [], "count": 0, "reason": f"Node not found in graph: {str(e)}"}

    def pagerank(self, top_n: Optional[int] = None) -> Dict[str, Any]:
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

    def connected_components(self) -> Dict[str, Any]:
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

    def find_cycles(self) -> Dict[str, Any]:
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

    def transitive_reduction(self, in_place: bool = False) -> Dict[str, Any]:
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

    def degree_centrality(self, top_n: Optional[int] = None) -> Dict[str, Any]:
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

    def subgraph(self, nodes: List[str], include_edges: bool = True) -> Dict[str, Any]:
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
