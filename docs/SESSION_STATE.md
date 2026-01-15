# MCP Graph Engine - Session State

## Current Phase
Phase 1: Dependencies & Core Infrastructure

## Design Spec
DESIGN-CYPHER.md - Add Cypher query language support using grand-cypher

## Completed Phases
- (none for this feature)

## Phase Plan
1. **Phase 1: Dependencies & Core Infrastructure**
   - Add grand-cypher to pyproject.toml
   - Create cypher.py with preprocess_cypher() and execute_cypher_query()

2. **Phase 2: Tool & Handler Integration**
   - Add TOOL_CYPHER_QUERY to tools.py with comprehensive description
   - Wire up handler in server.py

3. **Phase 3: Node Label Property Mapping**
   - Ensure nodes have `label` property for n.label access
   - Update add_node/add_edge to set label property

4. **Phase 4: Test Suite**
   - Unit tests for preprocessor fixes
   - Unit tests for executor edge cases
   - Integration tests with graph operations

## Current Focus
- Design spec section: "Implementation" subsections 3 & 4
- Key files: pyproject.toml, src/mcp_graph_engine/cypher.py (new)

## Design Anchors
- grand-cypher only accepts double quotes (preprocessor must fix single quotes)
- Edge type syntax [r:type] doesn't work - must convert to WHERE clause
- Node label property must be explicitly set for Cypher access
