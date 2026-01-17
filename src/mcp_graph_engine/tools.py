"""MCP tool definitions for graph operations."""

from mcp.types import Tool

# Graph Management Tools

TOOL_ADD_FACTS = Tool(
    name="add_facts",
    description="Add facts (relationships) to the graph. Nodes are auto-created if they don't exist.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "facts": {
                "type": "array",
                "description": "Relationship facts to add",
                "items": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string", "description": "Source node"},
                        "to": {"type": "string", "description": "Target node"},
                        "rel": {"type": "string", "description": "Relationship type"},
                        "from_type": {"type": "string", "description": "Source node type"},
                        "to_type": {"type": "string", "description": "Target node type"}
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
    description="Add knowledge using text DSL. Format: 'Subject relation Object' per line. Quote spaces: '\"Auth Service\" \"depends on\" \"User DB\"'. Type hints: 'Node:type rel Target:type'. Lines with # are comments.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "knowledge": {"type": "string", "description": "DSL text"}
        },
        "required": ["knowledge"]
    }
)

TOOL_LIST_GRAPHS = Tool(
    name="list_graphs",
    description="List all graph sessions with statistics",
    inputSchema={"type": "object", "properties": {}, "required": []}
)

TOOL_DELETE_GRAPH = Tool(
    name="delete_graph",
    description="Delete a graph session",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph to delete"}
        },
        "required": []
    }
)

TOOL_GET_GRAPH_INFO = Tool(
    name="get_graph_info",
    description="Get graph statistics and info",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"}
        },
        "required": []
    }
)

# Node Operation Tools

TOOL_FORGET = Tool(
    name="forget",
    description="Remove a node and its connected edges",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "label": {"type": "string", "description": "Node to remove"}
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
            "graph": {"type": "string", "description": "Graph name"},
            "source": {"type": "string", "description": "Source node"},
            "target": {"type": "string", "description": "Target node"},
            "relation": {"type": "string", "description": "Relation type (optional, omit to remove all)"}
        },
        "required": ["source", "target"]
    }
)

# Query & Analysis Tools

TOOL_SHORTEST_PATH = Tool(
    name="shortest_path",
    description="Find shortest path between two nodes (Dijkstra). Fuzzy matches node labels.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "source": {"type": "string", "description": "Start node"},
            "target": {"type": "string", "description": "End node"}
        },
        "required": ["source", "target"]
    }
)

TOOL_ALL_PATHS = Tool(
    name="all_paths",
    description="Find all simple paths between two nodes. Fuzzy matches labels.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "source": {"type": "string", "description": "Start node"},
            "target": {"type": "string", "description": "End node"},
            "max_length": {"type": "number", "description": "Max path length"}
        },
        "required": ["source", "target"]
    }
)

TOOL_PAGERANK = Tool(
    name="pagerank",
    description="Calculate PageRank scores for node importance",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "top_n": {"type": "number", "description": "Limit to top N results"}
        },
        "required": []
    }
)

TOOL_CONNECTED_COMPONENTS = Tool(
    name="connected_components",
    description="Find weakly connected components (node groups connected by paths)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"}
        },
        "required": []
    }
)

TOOL_FIND_CYCLES = Tool(
    name="find_cycles",
    description="Detect cycles (circular dependencies) in the graph",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"}
        },
        "required": []
    }
)

TOOL_TRANSITIVE_REDUCTION = Tool(
    name="transitive_reduction",
    description="Remove redundant transitive edges (if A->B->C and A->C exist, remove A->C)",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "in_place": {"type": "boolean", "description": "Modify graph if true, else just count"}
        },
        "required": []
    }
)

TOOL_DEGREE_CENTRALITY = Tool(
    name="degree_centrality",
    description="Calculate in/out degree centrality to find highly connected nodes",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "top_n": {"type": "number", "description": "Limit to top N results"}
        },
        "required": []
    }
)

TOOL_SUBGRAPH = Tool(
    name="subgraph",
    description="Extract subgraph with specified nodes and their interconnections. Fuzzy matches labels.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "nodes": {"type": "array", "items": {"type": "string"}, "description": "Nodes to include"},
            "include_edges": {"type": "boolean", "description": "Include edges between nodes"}
        },
        "required": ["nodes"]
    }
)

TOOL_ASK_GRAPH = Tool(
    name="ask_graph",
    description="Pattern-matching queries: 'what depends on X', 'what does X depend on', 'path from X to Y', 'all paths from X to Y', 'cycles', 'most connected', 'orphans', 'components'. Use cypher_query for complex queries.",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Query matching a supported pattern"},
            "graph": {"type": "string", "description": "Graph name"}
        },
        "required": ["query"]
    }
)

TOOL_DUMP_CONTEXT = Tool(
    name="dump_context",
    description="Get complete graph summary: nodes by type, relationships, and insights (hubs, cycles, orphans).",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"}
        },
        "required": []
    }
)

# Import/Export Tools

TOOL_IMPORT_GRAPH = Tool(
    name="import_graph",
    description="Import graph from DOT, CSV, GraphML, or JSON. Merges into existing graph.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "format": {"type": "string", "enum": ["dot", "csv", "graphml", "json"], "description": "Input format"},
            "content": {"type": "string", "description": "Inline content"},
            "file_path": {"type": "string", "description": "File path (alternative to content)"}
        },
        "required": ["format"]
    }
)

TOOL_EXPORT_GRAPH = Tool(
    name="export_graph",
    description="Export graph to DOT, CSV, GraphML, JSON, or Mermaid format.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "format": {"type": "string", "enum": ["dot", "csv", "graphml", "json", "mermaid"], "description": "Output format"},
            "file_path": {"type": "string", "description": "File path (omit for inline return)"}
        },
        "required": ["format"]
    }
)

TOOL_CREATE_FROM_MERMAID = Tool(
    name="create_from_mermaid",
    description="Create graph from Mermaid flowchart. Edge labels become relation types.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "mermaid": {"type": "string", "description": "Mermaid diagram text"}
        },
        "required": ["mermaid"]
    }
)

TOOL_CYPHER_QUERY = Tool(
    name="cypher_query",
    description="""Execute Cypher query. Use DOUBLE QUOTES for strings. Edge types via WHERE r.relation = "type".

Examples:
  MATCH (a)-[r]->(b) WHERE r.relation = "depends_on" RETURN a.label, b.label
  MATCH (n) WHERE n.type = "service" RETURN n.label
  MATCH (a)-[*1..3]->(b) RETURN DISTINCT b.label

Node props: label, type. Edge props: relation.""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Cypher query"},
            "graph": {"type": "string", "description": "Graph name"}
        },
        "required": ["query"]
    }
)

# Visualization Tools

TOOL_VISUALIZE_GRAPH = Tool(
    name="visualize_graph",
    description="Open browser visualization at localhost URL. Updates in real-time.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "filter": {"type": "string", "description": "Cypher filter query"}
        }
    }
)

TOOL_UPDATE_VIS_FILTER = Tool(
    name="update_visualization_filter",
    description="Update Cypher filter for visualization. Empty string clears filter.",
    inputSchema={
        "type": "object",
        "properties": {
            "graph": {"type": "string", "description": "Graph name"},
            "filter": {"type": "string", "description": "Cypher filter (empty to clear)"}
        },
        "required": ["filter"]
    }
)

TOOL_STOP_VISUALIZATION = Tool(
    name="stop_visualization",
    description="Stop the visualization server.",
    inputSchema={"type": "object", "properties": {}}
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
    TOOL_CYPHER_QUERY,
    TOOL_VISUALIZE_GRAPH,
    TOOL_UPDATE_VIS_FILTER,
    TOOL_STOP_VISUALIZATION,
]
