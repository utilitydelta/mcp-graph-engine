# MCP Graph Engine - Session State

## Current Phase
Phase 2: Simple DSL Parser (next)

## Design Spec
DESIGN-BEST-FRIENDS.md - Making MCP Graph Engine an LLM's Best Friend

## Completed Phases
- Phase 0: Remove Low-Level CRUD Tools ✓ (commit 3524aa5)
- Phase 1: Relationship-First Foundation ✓ (commit 4baa1af)

## Phase Plan

### Phase 2: Simple DSL Parser (NEXT)
- Implement `add_knowledge` tool with DSL parser
- Format: `<subject> <relation> <object>`
- Support inline type hints: `AuthService:service depends_on UserRepository:repository`
- Lines starting with # are comments, empty lines ignored

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

## Current Tool Surface (16 tools)
**Creation (1)**: add_facts
**Graph Management (3)**: list_graphs, delete_graph, get_graph_info
**Correction (2)**: forget, forget_relationship
**Query & Analysis (8)**: shortest_path, all_paths, pagerank, connected_components, find_cycles, transitive_reduction, degree_centrality, subgraph
**Import/Export (2)**: import_graph, export_graph

## Next Actions
1. Design DSL parser for add_knowledge
2. Add tool definition to tools.py
3. Add handler in server.py
4. Write tests

## Key Files
- src/mcp_graph_engine/tools.py - Tool definitions
- src/mcp_graph_engine/server.py - MCP server handlers
- src/mcp_graph_engine/graph_engine.py - Core graph operations
- tests/ - Test suite
