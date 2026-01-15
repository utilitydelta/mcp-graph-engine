# MCP Graph Engine - Progress Log

## Project Overview
Implementing an MCP server that provides LLMs with a graph-based memory and reasoning tool, as specified in DESIGN.md.

---

## Phase 1 Summary
**Completed**: Session 1 (commit d7fb7a4)

### What was done
- Project structure with pyproject.toml (setuptools build system)
- MCP server implementation with stdio transport
- NetworkX DiGraph wrapper (GraphEngine class)
- Session manager with named graphs and auto-creation
- Exact and normalized matching (Matcher class)
- 13 MCP tool definitions covering all CRUD operations
- Comprehensive test suite (6 tests, all passing)

### Key decisions
- Used DiGraph (single edge per node pair) rather than MultiDiGraph - simpler for typical LLM use cases
- Matcher class uses a two-step strategy: exact match first, then normalized match
- Session manager auto-creates graphs on first access (no explicit creation needed)
- Default graph name is "default" for zero-config usage

### Architecture
```
src/mcp_graph_engine/
├── __init__.py       - Package init
├── server.py         - MCP server with tool routing
├── tools.py          - 13 MCP tool definitions
├── graph_engine.py   - NetworkX wrapper with high-level ops
├── session.py        - Named graph session management
└── matcher.py        - Node label matching (exact + normalized)
```

### Tools implemented
Graph management: list_graphs, delete_graph, get_graph_info
Node operations: add_node, add_nodes, find_node, remove_node, list_nodes
Edge operations: add_edge, add_edges, find_edges, remove_edge, get_neighbors

### Stubs created
None

### Stubs resolved
N/A

### Integration status
- Build: ✓
- Tests: ✓ (6 passing)
- Import: ✓ (all modules importable)

---

## Phase 2 Summary
**Completed**: Session 1 (commit 8aaae65)

### What was done
- Three-tier matching pipeline: exact -> normalized -> embedding
- Integrated sentence-transformers with all-MiniLM-L6-v2 model
- Lazy-loaded model to avoid startup overhead
- Cosine similarity with 0.75 threshold
- Ambiguity detection (0.05 threshold, max 5 candidates)
- Embeddings computed automatically when nodes are added
- Embeddings stored per-graph session for isolation
- 12 new embedding test files

### Key decisions
- Similarity threshold 0.75 is conservative - prevents false positives
- Normalized matching handles most LLM query variations ("auth service" -> "AuthService")
- Embedding matching kicks in for semantic similarity ("database pool" -> "DatabaseConnectionPool")
- Model loaded lazily on first embedding request
- MatchResult extended to include similarity score and candidates list

### Files modified
- matcher.py - Added embedding-based matching with MATCHING_CONFIG
- graph_engine.py - Added _compute_embedding(), find_node() with candidates
- session.py - Embeddings dict shared between GraphEngine and Matcher
- server.py - find_node uses GraphEngine's fuzzy matching

### Integration status
- Build: ✓
- Tests: ✓ (18 passing)
- Import: ✓ (all modules importable)

---

## Phase 3 Summary
**Completed**: Session 1 (commit 1801648)

### What was done
- Implemented 8 graph analysis tools using NetworkX built-in algorithms
- shortest_path (Dijkstra), all_paths, pagerank
- connected_components (weakly connected for DiGraph)
- find_cycles, transitive_reduction
- degree_centrality (in/out/total)
- subgraph extraction
- All tools use fuzzy matching for node parameters
- Comprehensive error handling with LLM-friendly messages

### Key decisions
- Used NetworkX's well-tested built-in algorithms
- All node parameters use fuzzy matching for consistency
- Used weakly_connected_components for directed graphs
- Added top_n parameter to ranking tools
- Subgraph reports not_found nodes when fuzzy matching fails

### Integration status
- Build: ✓
- Tests: ✓ (all original tests passing)
- Total tools: 21

---

## Phase 4 Summary
**Completed**: Session 1 (commit f8cb5e3)

### What was done
- Implemented import_graph and export_graph tools
- DOT format via pydot library
- CSV edge list format
- JSON format with nodes/edges arrays
- GraphML format via NetworkX
- Import merges into existing graph (additive)
- Roundtrip tested for all formats

### Key decisions
- Import auto-creates nodes mentioned in edges
- CSV allows optional relation column (defaults to 'edge')
- JSON preserves node/edge properties
- GraphML uses NetworkX for robust parsing

### Integration status
- Build: ✓
- Tests: ✓ (32 import/export tests passing)
- Total tools: 23

---

## Phase 5 Summary
**Completed**: Session 1 (commit 097fbd7)

### What was done
- Enhanced error messages with LLM-friendly suggestions
- Added edge case handling (self-loops, empty graphs, invalid params)
- Consolidated tests into tests/ directory
- Final validation: 62 tests, all passing

### Key decisions
- Error messages list available options and suggest next actions
- Self-loops properly supported as valid directed graph construct
- Empty graph operations return helpful messages not errors

### Integration status
- Build: ✓
- Tests: ✓ (62 tests, 100% pass rate)
- Total tools: 23
- Full spec conformance: ✓

---

---

## LLM-Friendly API Redesign (DESIGN-BEST-FRIENDS.md)

### Phase 0 Summary
**Completed**: New session (commit 3524aa5)

### What was done
- Removed 8 low-level CRUD tools from MCP API surface:
  - add_node, add_nodes (replaced by add_facts in Phase 1)
  - add_edge, add_edges (replaced by add_facts in Phase 1)
  - find_node, find_edges, get_neighbors (replaced by ask_graph in Phase 3)
  - list_nodes (replaced by dump_context in Phase 4)
- Renamed tools for LLM-native ergonomics:
  - remove_node → forget
  - remove_edge → forget_relationship
- Updated server handlers to match
- Fixed tests to use import_graph for data setup

### Key decisions
- Internal GraphEngine methods preserved (needed for import/export)
- Only removed MCP tool interface, not underlying functionality
- "forget" is more intuitive than "remove_node" for LLMs

### Integration status
- Build: ✓
- Tests: ✓ (62 tests, 100% pass rate)
- Total tools: 15 (down from 23)

### Current tool surface
- **Graph Management (3)**: list_graphs, delete_graph, get_graph_info
- **Correction (2)**: forget, forget_relationship
- **Query & Analysis (8)**: shortest_path, all_paths, pagerank, connected_components, find_cycles, transitive_reduction, degree_centrality, subgraph
- **Import/Export (2)**: import_graph, export_graph

### Next phases
- Phase 1: add_facts (relationship-first bulk creation)
- Phase 2: add_knowledge (DSL parser)
- Phase 3: ask_graph (natural language queries)
- Phase 4: dump_context (LLM memory refresh)
- Phase 5: create_from_mermaid (diagram-based creation)

