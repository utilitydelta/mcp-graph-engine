# MCP Graph Engine - Session State

## Current Phase
Phase 4: Context Dump (next)

## Design Spec
DESIGN-BEST-FRIENDS.md - Making MCP Graph Engine an LLM's Best Friend

## Completed Phases
- Phase 0: Remove Low-Level CRUD Tools ✓ (commit 3524aa5)
- Phase 1: Relationship-First Foundation ✓ (commit 4baa1af)
- Phase 2: Simple DSL Parser ✓ (commit dda858f)
- Phase 3: Query Shortcuts ✓ (commit f68907c)

## Phase Plan

### Phase 4: Context Dump (NEXT)
- Implement `dump_context` tool
- Format output for LLM readability (not JSON blobs)
- Include relationship summary in natural format
- Include key insights (cycles, hubs, isolated nodes)

### Phase 5: Enhanced Mermaid
- Implement `create_from_mermaid` tool
- Edge labels become relation types
- Support node type annotations

## Current Tool Surface (18 tools)
**Creation (2)**: add_facts, add_knowledge
**Querying (1)**: ask_graph
**Graph Management (3)**: list_graphs, delete_graph, get_graph_info
**Correction (2)**: forget, forget_relationship
**Query & Analysis (8)**: shortest_path, all_paths, pagerank, connected_components, find_cycles, transitive_reduction, degree_centrality, subgraph
**Import/Export (2)**: import_graph, export_graph

## Next Actions
1. Design dump_context output format
2. Add tool definition and handler
3. Include nodes grouped by type, relationships, key insights
4. Write tests

## Key Files
- src/mcp_graph_engine/tools.py - Tool definitions
- src/mcp_graph_engine/server.py - MCP server handlers
