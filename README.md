# MCP Graph Engine

A graph-based memory and reasoning tool for LLMs, built with the Model Context Protocol (MCP).

## Quick Start

### Installation

```bash
# Install in editable mode
pip install -e .
```

### Run the Server

```bash
# Start the MCP server with stdio transport
mcp-graph-engine
```

### Run Tests

```bash
# Run the test script to verify setup
python test_server.py
```

## Features

This is the **Core Foundation** implementation with:

- **Session Management**: Named graphs with automatic creation
- **Node Operations**: Add, remove, list, and find nodes
- **Edge Operations**: Add, remove, find edges with fuzzy matching
- **Graph Management**: List, delete, and get info about graphs
- **Fuzzy Matching**: Exact and normalized matching for node labels

## Tool Reference

### Graph Management
- `list_graphs` - List all graph sessions
- `delete_graph` - Delete a graph session
- `get_graph_info` - Get detailed graph statistics

### Node Operations
- `add_node` - Add a single node
- `add_nodes` - Batch add multiple nodes
- `find_node` - Find nodes by query
- `remove_node` - Remove a node
- `list_nodes` - List all nodes (with optional type filter)

### Edge Operations
- `add_edge` - Add an edge (with fuzzy node matching)
- `add_edges` - Batch add multiple edges
- `find_edges` - Find edges by source, target, or relation
- `remove_edge` - Remove an edge
- `get_neighbors` - Get neighbors of a node

## Architecture

```
src/
  mcp_graph_engine/
    __init__.py        # Package initialization
    server.py          # MCP server with stdio transport
    graph_engine.py    # NetworkX wrapper
    session.py         # Session manager with named graphs
    matcher.py         # Node matching (exact + normalized)
    tools.py           # MCP tool definitions
```

## Design

See [DESIGN.md](DESIGN.md) for the complete design specification.

Key design decisions:
- Named graphs instead of opaque session IDs
- Fuzzy matching for LLM-friendly node references
- Directed graphs (DiGraph) as default
- Transient in-memory storage (no persistence)
- Default "default" graph for simple use cases

## What's Not Implemented (Yet)

The Core Foundation focuses on basic CRUD operations. Future phases will add:

- **Phase 2**: Embedding-based fuzzy matching with semantic similarity
- **Phase 3**: Graph query algorithms (shortest_path, pagerank, cycles, etc.)
- **Phase 4**: Import/export (DOT, CSV, JSON, GraphML)

## Example Usage

```python
# Add nodes
add_nodes({
  "nodes": [
    {"label": "AuthService", "type": "class"},
    {"label": "UserRepository", "type": "class"}
  ]
})

# Add edge with fuzzy matching
add_edge({
  "source": "auth service",      # Matches "AuthService"
  "target": "user repository",   # Matches "UserRepository"
  "relation": "depends_on"
})

# Query neighbors
get_neighbors({
  "node": "AuthService",
  "direction": "out"
})

# List all graphs
list_graphs()
```
