# Design: Making MCP Graph Engine an LLM's Best Friend

## The Problem

### LLMs Have a Memory Problem

When AI assistants work on complex tasks, they discover relationships piece by piece. An AI exploring a codebase might learn:
- Authentication service depends on user repository
- User repository talks to database pool
- Database pool is configured by config loader

Each discovery happens at different times. The AI has to hold all these relationships in its context window, competing with everything else. There's no structured place to query this knowledge.

### The Graph Engine Exists But Doesn't Get Used

We built an MCP Graph Engine to solve this. It works. But here's the brutal truth:

**LLMs don't organically reach for it.**

Why not?

1. **Cognitive overhead**: By the time an LLM recognizes it needs the tool, it's already forgotten the tool exists
2. **High-friction API**: The current interface is database-y, not LLM-native
3. **Diffuse benefit**: The payoff is better reasoning over time, but the cost (tool calls) is immediate

### The Current API is Too Granular

To capture "AuthService depends on UserRepository":

```
add_node("AuthService", type="service")
add_node("UserRepository", type="repository")
add_edge("AuthService", "UserRepository", "depends_on")
```

That's 3 tool calls for ONE relationship. For 20 relationships, that's potentially 60 tool calls. This is:
- Exhausting for the LLM
- Error-prone
- Context-consuming (each tool call takes space)
- Unnatural (LLMs think in chunks, not atoms)

## The Goal

Make the graph engine so frictionless that LLMs **actually use it** without being told.

## API Simplification: Remove the Database-y Tools

### The Problem with Too Many Tools

The current API exposes ~25 tools:
```
add_node, add_nodes, find_node, remove_node, list_nodes
add_edge, add_edges, find_edges, remove_edge
get_neighbors, shortest_path, all_paths
pagerank, connected_components, find_cycles
transitive_reduction, degree_centrality, subgraph
import_graph, export_graph, create_from_mermaid
list_graphs, delete_graph, get_graph_info
```

When an LLM sees that many options, there's decision paralysis. Worse, the LLM might pick `add_node` (because it exists) when `add_facts` would be 10x better.

### Decision: Remove Low-Level CRUD Tools

**Remove these tools entirely:**
- `add_node` / `add_nodes` - replaced by auto-creation in `add_facts`
- `add_edge` / `add_edges` - replaced by `add_facts`
- `find_node` - replaced by `ask_graph`
- `find_edges` - replaced by `ask_graph`
- `list_nodes` - replaced by `dump_context`
- `get_neighbors` - replaced by `ask_graph`

**Keep these tools (they provide query/analysis value):**
- `shortest_path` - core graph value
- `all_paths` - core graph value
- `find_cycles` - core graph value
- `pagerank` - useful for "what's important"
- `connected_components` - useful for finding clusters
- `degree_centrality` - useful for finding hubs
- `export_graph` - needed for visualization/backup
- `import_graph` - useful for restoring state
- `create_from_mermaid` - already LLM-friendly

**Keep for graph management:**
- `list_graphs` - multi-graph support
- `delete_graph` - cleanup
- `get_graph_info` - statistics

**Keep for surgical fixes (but maybe rename):**
- `remove_node` → `forget` - remove a concept
- `remove_edge` → `forget_relationship` - remove a specific relationship

### Final Tool Surface (~15 tools)

**Creation (LLM-friendly):**
- `add_facts` - bulk relationship creation with auto-node creation
- `add_knowledge` - DSL parser for natural text
- `create_from_mermaid` - diagram-based creation

**Querying (natural language-ish):**
- `ask_graph` - natural queries ("what depends on X", "path from A to B")
- `dump_context` - full state refresh for LLM

**Analysis (keep as-is, these are the payoff):**
- `shortest_path`
- `all_paths`
- `find_cycles`
- `pagerank`
- `connected_components`
- `degree_centrality`

**Correction:**
- `forget` - remove a node and its edges
- `forget_relationship` - remove specific edge

**Management:**
- `list_graphs`
- `delete_graph`
- `get_graph_info`
- `export_graph`
- `import_graph`

### Why This Works

1. **Fewer choices**: 15 tools instead of 25
2. **Clear purpose**: Creation vs Query vs Analysis vs Management
3. **No wrong path**: Can't accidentally use the slow granular approach
4. **LLM-native names**: `forget` instead of `remove_node`, `ask_graph` instead of `find_edges`

### Design Principles

1. **Relationship-first**: Declare relationships, not entities. Nodes are auto-created.
2. **Chunk-friendly**: Accept batches of knowledge in one call, not individual atoms.
3. **LLM-native formats**: Support formats LLMs naturally generate (Mermaid, simple DSL, JSON).
4. **Forgiveness over precision**: Fuzzy matching, auto-creation, sensible defaults.
5. **Low ceremony**: No schema design, no setup, just start adding facts.

## Proposed Solutions

### 1. Auto-Creating Relationship API

**New tool: `add_facts`**

```
add_facts([
  {"from": "AuthService", "rel": "depends_on", "to": "UserRepository"},
  {"from": "UserRepository", "rel": "depends_on", "to": "DatabasePool"},
  {"from": "ConfigLoader", "rel": "configures", "to": "DatabasePool"}
])
```

Works for single facts too:
```
add_facts([{"from": "AuthService", "rel": "depends_on", "to": "UserRepository"}])
```

Behavior:
- Nodes are auto-created if they don't exist
- Node types can be optionally provided: `{"from": "AuthService", "from_type": "service", ...}`
- Returns summary of what was created/already existed

### 2. Simple DSL Format

**New tool: `add_knowledge`**

Accept a simple, LLM-friendly text format:

```
add_knowledge("""
AuthService depends_on UserRepository
UserRepository depends_on DatabasePool
ConfigLoader configures DatabasePool
LoginController uses AuthService
""")
```

Format rules:
- One relationship per line
- Format: `<subject> <relation> <object>`
- Relation uses snake_case
- Lines starting with # are comments
- Empty lines ignored

### 3. Enhanced Mermaid Support

The existing `create_from_mermaid` is good but could be enhanced:

```
create_from_mermaid("""
graph TD
    AuthService -->|depends_on| UserRepository
    UserRepository -->|depends_on| DatabasePool
    ConfigLoader -->|configures| DatabasePool
""")
```

Ensure edge labels become relation types.

### 4. Query Shortcuts

**New tool: `ask_graph`**

Natural-ish queries without knowing the exact API:

```
ask_graph("what depends on DatabasePool")
ask_graph("path from LoginController to DatabasePool")
ask_graph("what are the cycles")
ask_graph("most connected nodes")
```

Maps to underlying operations but doesn't require the LLM to remember specific tool names.

### 5. Context Dump

**New tool: `dump_context`**

One-call export of everything relevant:

```
dump_context()
```

Returns:
- All nodes grouped by type
- All relationships in readable format
- Key statistics (most connected, cycles detected, etc.)

This lets an LLM "refresh" its memory with one call.

## Task Breakdown

### Phase 0: Remove Low-Level CRUD Tools
- [ ] Remove `add_node` / `add_nodes` tools
- [ ] Remove `add_edge` / `add_edges` tools
- [ ] Remove `find_node` tool
- [ ] Remove `find_edges` tool
- [ ] Remove `list_nodes` tool
- [ ] Remove `get_neighbors` tool
- [ ] Rename `remove_node` → `forget`
- [ ] Rename `remove_edge` → `forget_relationship`
- [ ] Update any internal code that depends on removed tools
- [ ] Remove corresponding tests (or adapt for new tools)

### Phase 1: Relationship-First Foundation
- [ ] Implement `add_facts` tool (bulk relationships, auto-create nodes)
- [ ] Add node type inference (optional type parameter, defaults to "entity")
- [ ] Return clear summary of created/existing entities
- [ ] Write tests for auto-creation behavior

### Phase 2: Simple DSL Parser
- [ ] Design and document the simple DSL format
- [ ] Implement `add_knowledge` tool with DSL parser
- [ ] Handle edge cases (quoted strings with spaces, special chars)
- [ ] Support inline type hints: `AuthService:service depends_on UserRepository:repository`
- [ ] Write tests for parser

### Phase 3: Query Shortcuts
- [ ] Implement `ask_graph` with pattern matching for common queries
- [ ] Support: "what depends on X", "what does X depend on"
- [ ] Support: "path from X to Y", "shortest path X to Y"
- [ ] Support: "cycles", "most connected", "orphans"
- [ ] Graceful fallback for unrecognized queries
- [ ] Write tests for query patterns

### Phase 4: Context Dump
- [ ] Implement `dump_context` tool
- [ ] Format output for LLM readability (not JSON blobs)
- [ ] Include relationship summary in natural format
- [ ] Include key insights (cycles, hubs, isolated nodes)
- [ ] Write tests

### Phase 5: Enhanced Mermaid
- [ ] Ensure edge labels in Mermaid become relation types
- [ ] Support node type annotations via Mermaid styling/classes
- [ ] Document Mermaid best practices for graph building
- [ ] Write tests for label extraction

### Phase 6: Documentation & Examples
- [ ] Update README with new LLM-friendly tools
- [ ] Add "Quick Start for LLMs" section
- [ ] Provide example workflows (codebase exploration, research, planning)
- [ ] Add example prompts that demonstrate organic usage

## Success Criteria

1. **Friction reduction**: Capturing 10 relationships takes 1-2 tool calls, not 30
2. **Organic adoption**: In testing, LLMs choose to use the graph without explicit instruction
3. **Memory recovery**: An LLM can "refresh" its understanding with a single `dump_context` call
4. **Error tolerance**: Typos, fuzzy references, and incomplete info don't cause failures

## Non-Goals

- Complex query language (we're not building GraphQL)
- Schema enforcement (flexibility over correctness)
- Persistence across sessions (this is thinking scratchpad, not database)
- Visualization (leave that to Mermaid export)

## Open Questions

1. Should `add_facts` support bidirectional relationships? (`A relates_to B` creates both directions?)
2. Should we auto-detect relation types from verbs? ("A uses B" → relation: "uses")
3. How much fuzzy matching is too much? (typo tolerance vs. accidental merges)
4. Should `ask_graph` use an LLM to parse queries, or stick to pattern matching?
5. Should `subgraph` and `transitive_reduction` be kept? (Useful but niche)

---

*This document is ready for vibe coding. Each phase is independent enough to tackle in a session. Start with Phase 1 - it provides the most value with the least complexity.*
