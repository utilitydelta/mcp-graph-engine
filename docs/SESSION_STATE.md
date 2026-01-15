# MCP Graph Engine - Session State

## Current Phase
Phase 1: Relationship-First Foundation (next)

## Design Spec
DESIGN-BEST-FRIENDS.md - Making MCP Graph Engine an LLM's Best Friend

## Completed Phases
- Phase 0: Remove Low-Level CRUD Tools ✓ (commit 3524aa5)

## Phase Plan

### Phase 1: Relationship-First Foundation (NEXT)
- Implement `add_facts` tool (bulk relationships, auto-create nodes)
- Node type inference with optional type parameter
- Return clear summary of created/existing entities

### Phase 2: Simple DSL Parser
- Implement `add_knowledge` tool with DSL parser
- Format: `<subject> <relation> <object>`
- Support inline type hints: `AuthService:service depends_on UserRepository:repository`

### Phase 3: Query Shortcuts
- Implement `ask_graph` with pattern matching for common queries
- Support: "what depends on X", "path from X to Y", "cycles", etc.

### Phase 4: Context Dump
- Implement `dump_context` tool
- Format output for LLM readability
- Include relationship summary and key insights

### Phase 5: Enhanced Mermaid
- Implement `create_from_mermaid` tool
- Edge labels become relation types
- Support node type annotations

## Current Tool Surface (15 tools)
**Graph Management (3)**: list_graphs, delete_graph, get_graph_info
**Correction (2)**: forget, forget_relationship
**Query & Analysis (8)**: shortest_path, all_paths, pagerank, connected_components, find_cycles, transitive_reduction, degree_centrality, subgraph
**Import/Export (2)**: import_graph, export_graph

## Next Actions
1. Implement add_facts tool in tools.py
2. Add handler in server.py
3. Auto-create nodes when adding facts
4. Return summary of what was created

## Key Files
- src/mcp_graph_engine/tools.py - Tool definitions
- src/mcp_graph_engine/server.py - MCP server handlers
- src/mcp_graph_engine/graph_engine.py - Core graph operations
- tests/ - Test suite
