"""MCP tool definitions for graph operations."""

from typing import Any, Dict
from mcp.types import Tool, TextContent


# Graph Management Tools

TOOL_LIST_GRAPHS = Tool(
    name="list_graphs",
    description="List all graph sessions with their basic statistics",
    inputSchema={
        "type": "object",
        "properties": {},
        "required": []
    }
)

TOOL_DELETE_GRAPH = Tool(
    name="delete_graph",
    description="Delete a graph session",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph to delete (defaults to 'default')"
            }
        },
        "required": []
    }
)

TOOL_GET_GRAPH_INFO = Tool(
    name="get_graph_info",
    description="Get detailed information and statistics about a graph",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            }
        },
        "required": []
    }
)

# Node Operation Tools

TOOL_ADD_NODE = Tool(
    name="add_node",
    description="Add a node to the graph. Returns created=false if node already exists.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "label": {
                "type": "string",
                "description": "Node label (unique identifier)"
            },
            "type": {
                "type": "string",
                "description": "Node type (optional, e.g., 'class', 'function', 'concept')"
            },
            "properties": {
                "type": "object",
                "description": "Additional node properties (optional)"
            }
        },
        "required": ["label"]
    }
)

TOOL_ADD_NODES = Tool(
    name="add_nodes",
    description="Add multiple nodes to the graph in a batch operation",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "nodes": {
                "type": "array",
                "description": "List of nodes to add",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "type": {"type": "string"},
                        "properties": {"type": "object"}
                    },
                    "required": ["label"]
                }
            }
        },
        "required": ["nodes"]
    }
)

TOOL_FIND_NODE = Tool(
    name="find_node",
    description="Find nodes matching a query using exact and normalized matching",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "query": {
                "type": "string",
                "description": "Query string to match against node labels"
            }
        },
        "required": ["query"]
    }
)

TOOL_REMOVE_NODE = Tool(
    name="remove_node",
    description="Remove a node from the graph (also removes all connected edges)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "label": {
                "type": "string",
                "description": "Node label to remove"
            }
        },
        "required": ["label"]
    }
)

TOOL_LIST_NODES = Tool(
    name="list_nodes",
    description="List nodes in the graph, optionally filtered by type",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "type": {
                "type": "string",
                "description": "Filter by node type (optional)"
            },
            "limit": {
                "type": "number",
                "description": "Maximum number of nodes to return (optional)"
            }
        },
        "required": []
    }
)

# Edge Operation Tools

TOOL_ADD_EDGE = Tool(
    name="add_edge",
    description="Add an edge between two nodes. Source and target are fuzzy matched against existing nodes.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "source": {
                "type": "string",
                "description": "Source node label (will be fuzzy matched)"
            },
            "target": {
                "type": "string",
                "description": "Target node label (will be fuzzy matched)"
            },
            "relation": {
                "type": "string",
                "description": "Relation type (e.g., 'depends_on', 'calls', 'relates_to')"
            },
            "properties": {
                "type": "object",
                "description": "Additional edge properties (optional)"
            }
        },
        "required": ["source", "target", "relation"]
    }
)

TOOL_ADD_EDGES = Tool(
    name="add_edges",
    description="Add multiple edges to the graph in a batch operation",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "edges": {
                "type": "array",
                "description": "List of edges to add",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "relation": {"type": "string"},
                        "properties": {"type": "object"}
                    },
                    "required": ["source", "target", "relation"]
                }
            }
        },
        "required": ["edges"]
    }
)

TOOL_FIND_EDGES = Tool(
    name="find_edges",
    description="Find edges matching the given criteria (all parameters are optional filters)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "source": {
                "type": "string",
                "description": "Source node label to filter by (optional)"
            },
            "target": {
                "type": "string",
                "description": "Target node label to filter by (optional)"
            },
            "relation": {
                "type": "string",
                "description": "Relation type to filter by (optional)"
            }
        },
        "required": []
    }
)

TOOL_REMOVE_EDGE = Tool(
    name="remove_edge",
    description="Remove an edge from the graph",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "source": {
                "type": "string",
                "description": "Source node label"
            },
            "target": {
                "type": "string",
                "description": "Target node label"
            },
            "relation": {
                "type": "string",
                "description": "Relation type to match (optional, removes all edges if omitted)"
            }
        },
        "required": ["source", "target"]
    }
)

TOOL_GET_NEIGHBORS = Tool(
    name="get_neighbors",
    description="Get neighbors of a node with optional direction and relation filtering",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "node": {
                "type": "string",
                "description": "Node label to get neighbors for"
            },
            "direction": {
                "type": "string",
                "enum": ["in", "out", "both"],
                "description": "Direction of edges to follow (defaults to 'both')"
            },
            "relation": {
                "type": "string",
                "description": "Relation type to filter by (optional)"
            }
        },
        "required": ["node"]
    }
)

# Query & Analysis Tools

TOOL_SHORTEST_PATH = Tool(
    name="shortest_path",
    description="Find the shortest path between two nodes using Dijkstra's algorithm",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "source": {
                "type": "string",
                "description": "Source node label (will be fuzzy matched)"
            },
            "target": {
                "type": "string",
                "description": "Target node label (will be fuzzy matched)"
            }
        },
        "required": ["source", "target"]
    }
)

TOOL_ALL_PATHS = Tool(
    name="all_paths",
    description="Find all simple paths between two nodes (no repeated nodes)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "source": {
                "type": "string",
                "description": "Source node label (will be fuzzy matched)"
            },
            "target": {
                "type": "string",
                "description": "Target node label (will be fuzzy matched)"
            },
            "max_length": {
                "type": "number",
                "description": "Maximum path length to consider (optional)"
            }
        },
        "required": ["source", "target"]
    }
)

TOOL_PAGERANK = Tool(
    name="pagerank",
    description="Calculate PageRank scores to identify important/central nodes in the graph",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "top_n": {
                "type": "number",
                "description": "Return only the top N nodes by score (optional, returns all if omitted)"
            }
        },
        "required": []
    }
)

TOOL_CONNECTED_COMPONENTS = Tool(
    name="connected_components",
    description="Find weakly connected components (groups of nodes connected by paths, ignoring edge direction)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            }
        },
        "required": []
    }
)

TOOL_FIND_CYCLES = Tool(
    name="find_cycles",
    description="Detect cycles in the graph (circular dependency paths)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            }
        },
        "required": []
    }
)

TOOL_TRANSITIVE_REDUCTION = Tool(
    name="transitive_reduction",
    description="Remove redundant transitive edges (e.g., if A->B->C and A->C exist, remove A->C)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "in_place": {
                "type": "boolean",
                "description": "If true, modify the graph; if false, only return count (defaults to false)"
            }
        },
        "required": []
    }
)

TOOL_DEGREE_CENTRALITY = Tool(
    name="degree_centrality",
    description="Calculate degree centrality (in-degree, out-degree) to identify highly connected nodes",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "top_n": {
                "type": "number",
                "description": "Return only the top N nodes by total centrality (optional, returns all if omitted)"
            }
        },
        "required": []
    }
)

TOOL_SUBGRAPH = Tool(
    name="subgraph",
    description="Extract a subgraph containing only the specified nodes and their interconnections",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "nodes": {
                "type": "array",
                "description": "List of node labels to include (will be fuzzy matched)",
                "items": {"type": "string"}
            },
            "include_edges": {
                "type": "boolean",
                "description": "If true, include edges between nodes; if false, only nodes (defaults to true)"
            }
        },
        "required": ["nodes"]
    }
)

# All tools list
ALL_TOOLS = [
    TOOL_LIST_GRAPHS,
    TOOL_DELETE_GRAPH,
    TOOL_GET_GRAPH_INFO,
    TOOL_ADD_NODE,
    TOOL_ADD_NODES,
    TOOL_FIND_NODE,
    TOOL_REMOVE_NODE,
    TOOL_LIST_NODES,
    TOOL_ADD_EDGE,
    TOOL_ADD_EDGES,
    TOOL_FIND_EDGES,
    TOOL_REMOVE_EDGE,
    TOOL_GET_NEIGHBORS,
    TOOL_SHORTEST_PATH,
    TOOL_ALL_PATHS,
    TOOL_PAGERANK,
    TOOL_CONNECTED_COMPONENTS,
    TOOL_FIND_CYCLES,
    TOOL_TRANSITIVE_REDUCTION,
    TOOL_DEGREE_CENTRALITY,
    TOOL_SUBGRAPH,
]
