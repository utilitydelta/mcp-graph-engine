# MCP Graph Engine

A graph database and analysis tool that plugs into AI assistants via the Model Context Protocol (MCP). Build relationship graphs, run analysis algorithms, and visualise everything in real-time.

![Graph visualisation demo](docs/assets/placeholder-hero.gif)
<!-- TODO: Record a GIF showing nodes being added and the D3 visualisation updating live -->

## What's This For?

You know how you're debugging something gnarly and you end up with a whiteboard full of boxes and arrows? Or you're trying to understand a codebase and the dependencies are doing your head in? This is that whiteboard, except your AI assistant can build it, query it, and run proper graph algorithms on it.

**Some things it's good for:**

- Mapping code dependencies and finding circular imports
- Building knowledge graphs while researching a topic
- Tracing request flows through a system
- Debugging complex issues (symptoms, causes, evidence)
- Understanding relationships in any domain

The key bit: your AI assistant builds the graph as you work together, then you can both reason about it. The live visualisation means you can see what's being built in real-time.

## Quick Demo

```
You: "Map out the auth system dependencies"

Claude: *adds nodes for AuthService, UserRepository, TokenValidator, Database*
        *adds edges showing what depends on what*

You: "What's the most critical component?"

Claude: *runs PageRank* "Database has the highest centrality -
         everything flows through it eventually"

You: "Any circular dependencies?"

Claude: *runs cycle detection* "Yeah, AuthService and TokenValidator
         have a circular dep through SessionManager"
```

Meanwhile, you're watching the graph build in your browser at `http://localhost:8765`.

![Cycle detection example](docs/assets/placeholder-cycles.png)
<!-- TODO: Screenshot showing a detected cycle highlighted in the visualisation -->

## Installation

### Prerequisites

- Python 3.10+
- An MCP-compatible client (Claude Code, Claude Desktop, Cursor, etc.)

### Install the Package

```bash
# From PyPI (when published)
pip install mcp-graph-engine

# Or from source
git clone https://github.com/utilitydelta/mcp-graph-engine.git
cd mcp-graph-engine
pip install -e .
```

### Configure Your MCP Client

The server runs over stdio, so you need to tell your client how to start it.

**Claude Code** (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "graph-engine": {
      "command": "mcp-graph-engine"
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "graph-engine": {
      "command": "mcp-graph-engine"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "graph-engine": {
      "command": "mcp-graph-engine"
    }
  }
}
```

If you installed in a virtualenv, you might need the full path:

```json
{
  "mcpServers": {
    "graph-engine": {
      "command": "/path/to/venv/bin/mcp-graph-engine"
    }
  }
}
```

### Verify It's Working

Start your MCP client and ask it to list the available tools. You should see a bunch of graph-related tools like `add_facts`, `add_knowledge`, `visualize_graph`, etc.

## Usage

### Adding Data

The easiest way is the knowledge DSL - just plain text relationships:

```
Alice knows Bob
Bob works_at TechCorp
TechCorp located_in Sydney
```

Or with type hints:

```
AuthService:service depends_on UserRepository:repository
UserRepository:repository queries Database:infrastructure
```

You can also use structured facts if you need more control:

```json
{
  "facts": [
    {"from": "AuthService", "to": "Database", "rel": "depends_on", "from_type": "service"}
  ]
}
```

### Querying

**Natural language patterns** (via `ask_graph`):

- "what depends on Database"
- "what does AuthService depend on"
- "path from Frontend to Database"
- "find cycles"
- "most connected nodes"

**Cypher queries** for the fancy stuff:

```cypher
MATCH (s:service)-[r]->(d)
WHERE r.relation = "depends_on"
RETURN s.label, d.label
```

### Analysis Tools

| Tool | What It Does |
|------|--------------|
| `shortest_path` | Find the shortest route between two nodes |
| `all_paths` | Find every possible path (careful with large graphs) |
| `pagerank` | Identify the most important/central nodes |
| `find_cycles` | Detect circular dependencies |
| `connected_components` | Find clusters of related nodes |
| `degree_centrality` | See which nodes have the most connections |
| `transitive_reduction` | Clean up redundant edges |

### Visualisation

```
visualize_graph(graph="my-graph")
```

Opens `http://localhost:8765/graphs/my-graph` in your browser. It's a D3 force-directed graph that updates in real-time as nodes and edges are added.

![Real-time updates demo](docs/assets/placeholder-realtime.gif)
<!-- TODO: GIF showing the graph updating as Claude adds nodes -->

You can filter the visualisation with Cypher:

```
update_visualization_filter(filter='MATCH (n)-[r]->(m) WHERE n.type = "service" RETURN n,r,m')
```

### Import/Export

**Supported formats:** DOT, CSV, GraphML, JSON, Mermaid

```
# Export to Mermaid for documentation
export_graph(format="mermaid")

# Import an existing DOT file
import_graph(format="dot", file_path="/path/to/deps.dot")
```

## Full Tool Reference

### Graph Management
| Tool | Description |
|------|-------------|
| `add_facts` | Add relationships (auto-creates nodes) |
| `add_knowledge` | Add relationships using simple DSL |
| `list_graphs` | List all named graphs |
| `delete_graph` | Delete a graph |
| `get_graph_info` | Get stats (node count, edge count, density, etc.) |

### Querying
| Tool | Description |
|------|-------------|
| `ask_graph` | Natural language queries for common patterns |
| `cypher_query` | Full Cypher query support |
| `dump_context` | Get a complete summary of the graph state |

### Analysis
| Tool | Description |
|------|-------------|
| `shortest_path` | Dijkstra's shortest path |
| `all_paths` | All simple paths between nodes |
| `pagerank` | PageRank centrality scores |
| `find_cycles` | Cycle detection |
| `connected_components` | Find clusters |
| `degree_centrality` | In/out degree analysis |
| `transitive_reduction` | Remove redundant edges |
| `subgraph` | Extract a subset of nodes |

### Node/Edge Operations
| Tool | Description |
|------|-------------|
| `forget` | Remove a node (and its edges) |
| `forget_relationship` | Remove an edge |

### Import/Export
| Tool | Description |
|------|-------------|
| `import_graph` | Import from DOT, CSV, GraphML, JSON |
| `export_graph` | Export to DOT, CSV, GraphML, JSON, Mermaid |
| `create_from_mermaid` | Create graph from Mermaid syntax |

### Visualisation
| Tool | Description |
|------|-------------|
| `visualize_graph` | Open browser visualisation |
| `update_visualization_filter` | Apply Cypher filter to the view |
| `stop_visualization` | Stop the visualisation server |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VIS_ENABLED` | `true` | Enable/disable visualisation server |
| `VIS_PORT` | `8765` | Port for the visualisation server |
| `VIS_HOST` | `localhost` | Host to bind the visualisation server |

## Architecture

```
src/mcp_graph_engine/
├── server.py           # MCP server, tool handlers
├── graph_engine.py     # NetworkX wrapper, algorithms
├── session.py          # Named graph sessions
├── matcher.py          # Fuzzy matching (exact, normalised, embeddings)
├── cypher.py           # Cypher query execution
└── visualization/
    ├── web_server.py   # FastAPI + WebSocket server
    └── broadcast.py    # Real-time update broadcasting
```

**Key dependencies:**
- [NetworkX](https://networkx.org/) - Graph data structure and algorithms
- [grand-cypher](https://github.com/aplbrain/grand-cypher) - Cypher query support
- [sentence-transformers](https://www.sbert.net/) - Embedding-based fuzzy matching
- [FastAPI](https://fastapi.tiangolo.com/) - Visualisation web server
- [D3.js](https://d3js.org/) - Force-directed graph visualisation

## Things to Know

**It's transient.** Graphs live in memory only. When the server stops, they're gone. This is by design - it's a working memory tool, not a database. If you need persistence, export to JSON and import later.

**Fuzzy matching is on by default.** Type "auth service" and it'll match "AuthService". It uses three strategies: exact match, normalised match (case/whitespace), and embedding similarity for semantic matches. Usually this is what you want.

**Multiple graphs are supported.** Each graph is independent. Default graph is called "default". Use the `graph` parameter on any tool to work with a different one.

**Cypher has quirks.** Use double quotes for strings (single quotes don't work). Edge type syntax `[r:type]` doesn't work - use `WHERE r.relation = "type"` instead. The server tries to auto-fix common mistakes but check the error messages if something's off.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run the server directly
python -m mcp_graph_engine.server
```

## Contributing

Issues and PRs welcome. Keep it simple, test your changes, and don't break the existing tools.

## License

MIT. See [LICENSE](LICENSE) for details.

---

Built by [utilitydelta](https://github.com/utilitydelta). If you find this useful, star the repo or let me know what you're using it for.
