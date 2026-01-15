# MCP Graph Engine - Session State

## Current Phase
Phase 0: Remove Low-Level CRUD Tools (starting)

## Design Spec
DESIGN-BEST-FRIENDS.md - Making MCP Graph Engine an LLM's Best Friend

## Completed Phases
(none - new session)

## Phase Plan

### Phase 0: Remove Low-Level CRUD Tools
- Remove `add_node` / `add_nodes` tools
- Remove `add_edge` / `add_edges` tools
- Remove `find_node` tool
- Remove `find_edges` tool
- Remove `list_nodes` tool
- Remove `get_neighbors` tool
- Rename `remove_node` → `forget`
- Rename `remove_edge` → `forget_relationship`
- Update handlers and tests

### Phase 1: Relationship-First Foundation
- Implement `add_facts` tool (bulk relationships, auto-create nodes)
- Node type inference with optional type parameter

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

## Next Actions
1. Remove low-level CRUD tool definitions from tools.py
2. Remove corresponding handlers from server.py
3. Update ALL_TOOLS list
4. Rename remove_node → forget, remove_edge → forget_relationship

## Key Files
- src/mcp_graph_engine/tools.py - Tool definitions
- src/mcp_graph_engine/server.py - MCP server handlers
- src/mcp_graph_engine/graph_engine.py - Core graph operations
- tests/ - Test suite
