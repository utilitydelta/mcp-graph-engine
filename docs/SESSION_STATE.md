# MCP Graph Engine - Session State

## Current Phase
Phase 2: Fuzzy Matching with Embeddings

## Completed Phases
- Phase 1: Core Foundation ✓ (commit d7fb7a4)

## Next Actions
1. Integrate sentence-transformers (all-MiniLM-L6-v2)
2. Implement embedding computation and caching per-graph
3. Add similarity search with cosine similarity
4. Handle ambiguity detection (multiple close matches)
5. Update Matcher class to use embeddings as fallback

## Phase Plan
| Phase | Focus | Description |
|-------|-------|-------------|
| 1 | Core Foundation | Project setup, MCP server, NetworkX integration, session manager, basic CRUD ✓ |
| 2 | Fuzzy Matching | sentence-transformers integration, embedding cache, similarity search |
| 3 | Query & Analysis | Path algorithms, PageRank, centrality, components, cycles |
| 4 | Import/Export | DOT, CSV, JSON, GraphML format support |
| 5 | Polish | Error messages, edge cases, comprehensive testing |

## Design Anchors
- Spec: DESIGN.md
- Part 6: Fuzzy Matching Implementation (section 6.1-6.4)
- Embedding model: all-MiniLM-L6-v2 (~80MB, 384-dim, local)
- Similarity threshold: 0.75 for auto-match
- Ambiguity threshold: 0.05 (if top matches within this range, return candidates)

## Active Stubs
(none)

## Key Files for Phase 2
- src/mcp_graph_engine/matcher.py - Add embedding-based matching
- src/mcp_graph_engine/session.py - Store embeddings per graph session
