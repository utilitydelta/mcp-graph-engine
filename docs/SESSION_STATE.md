# MCP Graph Engine - Session State

## Current Phase
Phase 5: Enhanced Mermaid (next)

## Design Spec
DESIGN-BEST-FRIENDS.md - Making MCP Graph Engine an LLM's Best Friend

## Completed Phases
- Phase 0: Remove Low-Level CRUD Tools ✓ (commit 3524aa5)
- Phase 1: Relationship-First Foundation ✓ (commit 4baa1af)
- Phase 2: Simple DSL Parser ✓ (commit dda858f)
- Phase 3: Query Shortcuts ✓ (commit f68907c)
- Phase 4: Context Dump ✓ (commit 97bf5c1)

## Phase Plan

### Phase 5: Enhanced Mermaid (NEXT)
- Implement `create_from_mermaid` tool
- Edge labels become relation types
- Support node type annotations via Mermaid styling/classes

## Current Tool Surface (19 tools)
**Creation (2)**: add_facts, add_knowledge
**Querying (2)**: ask_graph, dump_context
**Graph Management (3)**: list_graphs, delete_graph, get_graph_info
**Correction (2)**: forget, forget_relationship
**Query & Analysis (8)**: shortest_path, all_paths, pagerank, connected_components, find_cycles, transitive_reduction, degree_centrality, subgraph
**Import/Export (2)**: import_graph, export_graph

## Next Actions
1. Implement create_from_mermaid tool
2. Parse Mermaid flowchart syntax
3. Extract edge labels as relation types
4. Handle node styling/classes for types
5. Write tests

## Key Files
- src/mcp_graph_engine/tools.py - Tool definitions
- src/mcp_graph_engine/server.py - MCP server handlers
