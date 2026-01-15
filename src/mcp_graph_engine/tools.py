"""MCP tool definitions for graph operations."""

from typing import Any, Dict
from mcp.types import Tool, TextContent


# Graph Management Tools

TOOL_ADD_FACTS = Tool(
    name="add_facts",
    description="Add facts (relationships) to the graph. Nodes are auto-created if they don't exist. This is the primary way to add knowledge to the graph.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "facts": {
                "type": "array",
                "description": "Array of relationship facts to add",
                "items": {
                    "type": "object",
                    "properties": {
                        "from": {
                            "type": "string",
                            "description": "Source node label (will be created if doesn't exist)"
                        },
                        "to": {
                            "type": "string",
                            "description": "Target node label (will be created if doesn't exist)"
                        },
                        "rel": {
                            "type": "string",
                            "description": "Relationship type"
                        },
                        "from_type": {
                            "type": "string",
                            "description": "Optional type for source node (defaults to 'entity')"
                        },
                        "to_type": {
                            "type": "string",
                            "description": "Optional type for target node (defaults to 'entity')"
                        }
                    },
                    "required": ["from", "to", "rel"]
                }
            }
        },
        "required": ["facts"]
    }
)

TOOL_ADD_KNOWLEDGE = Tool(
    name="add_knowledge",
    description="Add knowledge using a simple text format. One relationship per line: 'Subject relation Object'. Supports optional type hints: 'Subject:type relation Object:type'. Lines starting with # are comments, empty lines are ignored.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "knowledge": {
                "type": "string",
                "description": "Text-based DSL for relationships. Format: 'Subject relation Object' (one per line). Optional type hints: 'Subject:type relation Object:type'. Comments start with #."
            }
        },
        "required": ["knowledge"]
    }
)

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

TOOL_FORGET = Tool(
    name="forget",
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

# Edge Operation Tools

TOOL_FORGET_RELATIONSHIP = Tool(
    name="forget_relationship",
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

TOOL_ASK_GRAPH = Tool(
    name="ask_graph",
    description="Ask natural questions about the graph without needing to remember specific tool names. Examples: 'what depends on X', 'what does X depend on', 'path from A to B', 'cycles', 'most connected', 'orphans'",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "query": {
                "type": "string",
                "description": "Natural language query about the graph"
            }
        },
        "required": ["query"]
    }
)

TOOL_DUMP_CONTEXT = Tool(
    name="dump_context",
    description="Get a complete readable summary of the graph state. Returns nodes by type, all relationships, and key insights (hubs, cycles, orphans). This is perfect for LLMs to refresh their memory of the entire graph with one call.",
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

# Import/Export Tools

TOOL_IMPORT_GRAPH = Tool(
    name="import_graph",
    description="Import a graph from various formats (DOT, CSV, GraphML, JSON), merging into existing graph",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "format": {
                "type": "string",
                "enum": ["dot", "csv", "graphml", "json"],
                "description": "Format of the input data"
            },
            "content": {
                "type": "string",
                "description": "String content to import"
            }
        },
        "required": ["format", "content"]
    }
)

TOOL_EXPORT_GRAPH = Tool(
    name="export_graph",
    description="Export the graph to various formats (DOT, CSV, GraphML, JSON, Mermaid)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "format": {
                "type": "string",
                "enum": ["dot", "csv", "graphml", "json", "mermaid"],
                "description": "Format to export to"
            }
        },
        "required": ["format"]
    }
)

TOOL_CREATE_FROM_MERMAID = Tool(
    name="create_from_mermaid",
    description="Create graph from Mermaid flowchart syntax. Edge labels become relation types. Default relation is 'relates_to' if no label is specified.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            },
            "mermaid": {
                "type": "string",
                "description": "Mermaid flowchart diagram text"
            }
        },
        "required": ["mermaid"]
    }
)

# All tools list
ALL_TOOLS = [
    TOOL_ADD_FACTS,
    TOOL_ADD_KNOWLEDGE,
    TOOL_LIST_GRAPHS,
    TOOL_DELETE_GRAPH,
    TOOL_GET_GRAPH_INFO,
    TOOL_FORGET,
    TOOL_FORGET_RELATIONSHIP,
    TOOL_SHORTEST_PATH,
    TOOL_ALL_PATHS,
    TOOL_PAGERANK,
    TOOL_CONNECTED_COMPONENTS,
    TOOL_FIND_CYCLES,
    TOOL_TRANSITIVE_REDUCTION,
    TOOL_DEGREE_CENTRALITY,
    TOOL_SUBGRAPH,
    TOOL_ASK_GRAPH,
    TOOL_DUMP_CONTEXT,
    TOOL_IMPORT_GRAPH,
    TOOL_EXPORT_GRAPH,
    TOOL_CREATE_FROM_MERMAID,
]
