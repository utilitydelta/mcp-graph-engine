# Design: Cypher Query Support for MCP Graph Engine

## Overview

Add Cypher query language support to enable powerful, expressive graph queries that LLMs can reliably generate. This leverages the `grand-cypher` library which implements Cypher directly on NetworkX graphs.

## Motivation

Current query limitations:
- `ask_graph` is natural language (fuzzy, imprecise)
- No pattern matching (find structural patterns)
- No filtering by relationship type
- No variable-length path queries
- No aggregations or projections

Cypher solves these while being LLM-friendly (well-documented, pattern-based syntax).

## Dependencies

```bash
pip install grand-cypher
```

**grand-cypher** provides:
- Cypher parser and executor for NetworkX
- MATCH, WHERE, RETURN clauses
- Variable-length paths `[*1..3]`
- Node/edge property access
- No external database required

Repository: https://github.com/aplbrain/grand-cypher

## Architecture

### Current State

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ MCP Client  │────▶│ GraphServer  │────▶│  GraphEngine    │
│ (LLM)       │     │ (server.py)  │     │ (nx.DiGraph)    │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  ask_graph   │  ← regex-based NL parsing
                    │  pagerank    │  ← direct NetworkX calls
                    │  paths, etc  │
                    └──────────────┘
```

### Proposed Addition

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ MCP Client  │────▶│ GraphServer  │────▶│  GraphEngine    │
│ (LLM)       │     │ (server.py)  │     │ (nx.DiGraph)    │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ cypher_query │  ← NEW: grand-cypher executor
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ GrandCypher  │  ← Cypher → NetworkX translation
                    └──────────────┘
```

## Implementation

### 1. Tool Definition (`tools.py`)

```python
TOOL_CYPHER_QUERY = Tool(
    name="cypher_query",
    description="""Execute a Cypher query against the graph.

Cypher is a declarative graph query language.

IMPORTANT SYNTAX NOTES:
- Use DOUBLE QUOTES for strings: "value" (single quotes don't work)
- Edge types [r:type] don't work - use WHERE r.relation = "type" instead

Examples:

  # Find all members of the Fellowship
  MATCH (c)-[r]->(f {label: "Fellowship_of_the_Ring"})
  WHERE r.relation = "member_of"
  RETURN c.label

  # Find friends-of-friends
  MATCH (a {label: "Frodo"})-[r1]->(b)-[r2]->(c)
  WHERE r1.relation = "friends_with" AND r2.relation = "friends_with"
  RETURN c.label

  # Variable-length paths (1-3 hops)
  MATCH (a {label: "Sauron"})-[*1..3]->(b)
  RETURN DISTINCT b.label

  # Filter by node type
  MATCH (n)
  WHERE n.type = "character"
  RETURN n.label

  # Find by relationship type
  MATCH (a)-[r]->(b)
  WHERE r.relation = "passed_to"
  RETURN a.label, b.label

  # Multiple conditions
  MATCH (a)-[r]->(b)
  WHERE r.relation IN ["member_of", "friends_with"] AND a.type = "character"
  RETURN a.label, b.label

  # String matching
  MATCH (n)
  WHERE n.label CONTAINS "Ring" OR n.label STARTS WITH "S"
  RETURN n.label

Node properties: label, type
Edge properties: relation
""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Cypher query to execute"
            },
            "graph": {
                "type": "string",
                "description": "Name of the graph (defaults to 'default')"
            }
        },
        "required": ["query"]
    }
)
```

Add to `ALL_TOOLS` list.

### 2. Handler Implementation (`server.py`)

```python
# In _handle_tool method:
elif name == "cypher_query":
    query = args.get("query", "")
    graph_name = args.get("graph", "default")
    graph_engine = self.session_manager.get_graph(graph_name)

    # execute_cypher_query handles preprocessing and error handling
    return execute_cypher_query(graph_engine.graph, query)
```

### 3. Query Preprocessor (LLM-friendly fixes)

```python
import re

def preprocess_cypher(query: str) -> tuple[str, list[str]]:
    """
    Fix common LLM Cypher mistakes before execution.

    Fixes applied:
    1. Single quotes → double quotes (grand-cypher only accepts double quotes)
    2. Edge type syntax [r:type] → WHERE r.relation = "type"

    Returns: (fixed_query, list_of_fixes_applied)
    """
    fixes = []

    # 1. Replace single quotes with double quotes
    if "'" in query:
        query = query.replace("'", '"')
        fixes.append("single quotes → double quotes")

    # 2. Convert edge type syntax [r:type] or [:type] to WHERE clause
    edge_type_pattern = r'\[(\w+)?:(\w+)\]'

    matches = list(re.finditer(edge_type_pattern, query))
    if matches:
        for match in reversed(matches):  # Reverse to preserve indices
            var_name = match.group(1) or f'_r{len(matches)}'  # Generate var if none
            edge_type = match.group(2)

            # Replace [r:type] with [r]
            replacement = f'[{var_name}]'
            query = query[:match.start()] + replacement + query[match.end():]

            # Inject WHERE clause
            where_clause = f'{var_name}.relation = "{edge_type}"'

            if re.search(r'\bWHERE\b', query, re.IGNORECASE):
                # Add to existing WHERE with AND
                query = re.sub(
                    r'\bWHERE\b',
                    f'WHERE {where_clause} AND ',
                    query,
                    count=1,
                    flags=re.IGNORECASE
                )
            else:
                # Insert WHERE before RETURN
                query = re.sub(
                    r'\bRETURN\b',
                    f'WHERE {where_clause} RETURN',
                    query,
                    count=1,
                    flags=re.IGNORECASE
                )

            fixes.append(f"[:{edge_type}] → WHERE clause")

    return query, fixes
```

### 4. Cypher Executor Function (`server.py` or new `cypher.py`)

```python
from grandcypher import GrandCypher

def execute_cypher_query(nx_graph: nx.DiGraph, query: str) -> dict:
    """
    Execute a Cypher query against a NetworkX graph.
    Applies preprocessing to fix common LLM mistakes.

    Returns dict with:
    - success: bool
    - query: original query
    - query_executed: query after preprocessing (if different)
    - fixes_applied: list of preprocessing fixes
    - columns: list of column names
    - rows: list of result dicts
    - count: number of rows
    """
    original_query = query

    # Preprocess to fix common LLM mistakes
    query, fixes = preprocess_cypher(query)

    try:
        gc = GrandCypher(nx_graph)
        result = gc.run(query)

        # Convert result format: {var: [values]} → [{var: value}, ...]
        if not result:
            return {
                "success": True,
                "query": original_query,
                "query_executed": query if fixes else None,
                "fixes_applied": fixes,
                "columns": [],
                "rows": [],
                "count": 0
            }

        # Clean column names (remove Token wrapper)
        columns = [str(k) if not hasattr(k, 'value') else k.value for k in result.keys()]
        raw_columns = list(result.keys())
        num_rows = len(next(iter(result.values())))

        rows = []
        for i in range(num_rows):
            row = {}
            for col_name, raw_col in zip(columns, raw_columns):
                val = result[raw_col][i]
                # Clean up edge relation format {(0,0): 'type'} → 'type'
                if isinstance(val, dict) and len(val) == 1:
                    val = next(iter(val.values()))
                row[col_name] = val
            rows.append(row)

        return {
            "success": True,
            "query": original_query,
            "query_executed": query if fixes else None,
            "fixes_applied": fixes,
            "columns": columns,
            "rows": rows,
            "count": num_rows
        }

    except Exception as e:
        return {
            "success": False,
            "query": original_query,
            "query_executed": query if fixes else None,
            "fixes_applied": fixes,
            "error": str(e)
        }
```

### 5. Property Mapping

NetworkX stores node/edge data as attributes. Map to Cypher properties:

| NetworkX | Cypher Access | Example |
|----------|---------------|---------|
| Node ID | `n.label` or node matching | `{label: 'Frodo'}` |
| `node['type']` | `n.type` | `WHERE n.type = 'character'` |
| `edge['relation']` | `r.relation` or `[r:relation_type]` | `MATCH ()-[r:member_of]->()` |

**Challenge**: grand-cypher uses edge attributes, not edge "types" in the Neo4j sense.

**Solution**: Store relation as both the edge key AND as a `relation` attribute for query flexibility:

```python
# Current storage
graph.add_edge(source, target, relation="member_of")

# Query patterns that should work:
# MATCH ()-[r]->(b) WHERE r.relation = 'member_of'
# MATCH (a)-[r:member_of]->(b)  -- if grand-cypher supports edge type matching
```

Need to verify grand-cypher's edge type matching behavior and potentially adjust.

## Example Queries

### Basic Pattern Matching
```cypher
-- Find all hobbits (nodes that are subtype_of Hobbits)
MATCH (h)-[r]->(hobbits {label: "Hobbits"})
WHERE r.relation = "subtype_of"
RETURN h.label
```

### Variable-Length Paths
```cypher
-- Trace the Ring's journey (all within 1-5 hops of Sauron)
MATCH (s {label: "Sauron"})-[*1..5]->(end)
RETURN DISTINCT end.label
```

### Filtering with ORDER BY
```cypher
-- All characters sorted by label
MATCH (n)
WHERE n.type = "character"
RETURN n.label
ORDER BY n.label
LIMIT 10
```

### Multi-Hop Pattern
```cypher
-- Find 2-hop connections from Frodo
MATCH (a {label: "Frodo"})-[r1]->(b)-[r2]->(c)
RETURN a.label, b.label, c.label, r1.relation, r2.relation
LIMIT 10
```

### Filtering by Type
```cypher
-- All locations in The Shire
MATCH (loc)-[r]->(shire {label: "The_Shire"})
WHERE r.relation = "located_in"
RETURN loc.label
```

### String Matching
```cypher
-- Find all nodes with "Ring" in the name
MATCH (n)
WHERE n.label CONTAINS "Ring"
RETURN n.label, n.type
```

### Multiple Relationship Types
```cypher
-- Find all family or friendship connections
MATCH (a)-[r]->(b)
WHERE r.relation IN ["friends_with", "related_to", "member_of"]
RETURN a.label, r.relation, b.label
LIMIT 20
```

## Testing Strategy

### Unit Tests

```python
def test_basic_match():
    g = nx.DiGraph()
    g.add_node("Frodo", type="character", label="Frodo")
    g.add_node("Fellowship", type="group", label="Fellowship")
    g.add_edge("Frodo", "Fellowship", relation="member_of")

    result = execute_cypher_query(g, """
        MATCH (c)-[r]->(f {label: "Fellowship"})
        RETURN c.label
    """)

    assert result["rows"][0]["c.label"] == "Frodo"

def test_filter_by_relation():
    # Must use WHERE, not [r:type]
    g = nx.DiGraph()
    g.add_node("Frodo", type="character", label="Frodo")
    g.add_node("Fellowship", type="group", label="Fellowship")
    g.add_edge("Frodo", "Fellowship", relation="member_of")

    result = execute_cypher_query(g, """
        MATCH (c)-[r]->(f)
        WHERE r.relation = "member_of"
        RETURN c.label
    """)

    assert "Frodo" in result["rows"][0]["c.label"]

def test_variable_length_path():
    g = nx.DiGraph()
    g.add_node("A", label="A")
    g.add_node("B", label="B")
    g.add_node("C", label="C")
    g.add_edge("A", "B", relation="connects")
    g.add_edge("B", "C", relation="connects")

    result = execute_cypher_query(g, """
        MATCH (a {label: "A"})-[*1..2]->(end)
        RETURN end.label
    """)

    labels = [r["end.label"] for r in result["rows"]]
    assert "B" in labels
    assert "C" in labels

def test_empty_result():
    g = nx.DiGraph()
    g.add_node("Frodo", type="character", label="Frodo")

    result = execute_cypher_query(g, """
        MATCH (n {label: "NonExistent"})
        RETURN n.label
    """)

    assert result["count"] == 0
    assert result["rows"] == []

def test_syntax_error():
    g = nx.DiGraph()

    result = execute_cypher_query(g, """
        MATCH (n {label: 'wrong_quotes'})
        RETURN n
    """)

    assert result["success"] == False
    assert "error" in result
```

### Integration Tests

```python
def test_cypher_with_fellowship_graph():
    # Load fellowship graph
    # Run various Cypher queries
    # Verify results match expected
    pass
```

## LLM Usage Guidelines

Add to tool description or as separate documentation:

```markdown
## Cypher Query Tips for LLMs

AUTOMATIC FIXES (you can use standard Cypher, these are fixed automatically):
- Single quotes 'value' → converted to double quotes "value"
- Edge type syntax [r:member_of] → converted to WHERE r.relation = "member_of"

KNOWN LIMITATIONS (cannot be fixed):
- Multiple MATCH clauses not supported - combine in single MATCH or run separate queries
- OPTIONAL MATCH not supported
- COUNT aggregation not supported - use degree_centrality tool instead

SYNTAX:
1. **Node matching**: `{label: "NodeName"}` or `{label: 'NodeName'}` (quotes auto-fixed)
2. **Edge filtering**: `[r:type]` (auto-fixed) or `WHERE r.relation = "type"`
3. **Variable paths**: `[*1..3]` for 1-3 hops
4. **Return format**: Returns {success, columns, rows, count, fixes_applied}
5. **Case sensitivity**: Node labels are case-sensitive
6. **Available properties**:
   - Nodes: `label`, `type`
   - Edges: `relation`

## Common Patterns

| Intent | Cypher |
|--------|--------|
| Find node by name | `MATCH (n {label: 'Name'}) RETURN n.label` |
| Get neighbors | `MATCH (n {label: 'Name'})-[]->(m) RETURN m.label` |
| Get predecessors | `MATCH (m)-[]->(n {label: 'Name'}) RETURN m.label` |
| Filter by relation | `MATCH (a)-[r:type]->(b) RETURN a.label, b.label` |
| Filter by node type | `MATCH (n) WHERE n.type = 'character' RETURN n.label` |
| Variable path | `MATCH (a {label: 'Start'})-[*1..3]->(b) RETURN b.label` |
| String search | `MATCH (n) WHERE n.label CONTAINS 'Ring' RETURN n.label` |
```

## Rollout Plan

### Phase 1: Basic Integration
- [ ] Add grand-cypher dependency to pyproject.toml
- [ ] Implement `cypher_query` tool with basic execution
- [ ] Add error handling for syntax errors
- [ ] Test with simple queries

### Phase 2: Property Mapping
- [ ] Ensure node `label` property is set (currently just node ID)
- [ ] Verify edge `relation` property works with Cypher edge type syntax
- [ ] Add any necessary property transformations

### Phase 3: Documentation & Testing
- [ ] Add comprehensive examples to tool description
- [ ] Write unit tests for edge cases
- [ ] Integration test with real graphs
- [ ] Document grand-cypher limitations vs full Cypher

### Phase 4: Enhancements (Future)
- [ ] Query result caching for repeated queries
- [ ] Query explanation/plan output
- [ ] Custom functions (e.g., fuzzy matching in WHERE)
- [ ] Query timeout for long-running queries

## Test Results (Verified)

### What Works

| Feature | Status | Example |
|---------|--------|---------|
| Node property matching | ✅ | `MATCH (n {label: "Frodo"})` |
| WHERE with AND/OR | ✅ | `WHERE a.type = "character" AND b.type = "group"` |
| WHERE with NOT | ✅ | `WHERE NOT r.relation = "member_of"` |
| WHERE with IN | ✅ | `WHERE r.relation IN ["member_of", "bearer_of"]` |
| Not equal `<>` | ✅ | `WHERE r.relation <> "member_of"` |
| CONTAINS | ✅ | `WHERE n.label CONTAINS "ring"` |
| STARTS WITH | ✅ | `WHERE n.label STARTS WITH "S"` |
| Variable-length paths | ✅ | `MATCH (a)-[*1..3]->(b)` |
| Multi-hop patterns | ✅ | `MATCH (a)-[r1]->(b)-[r2]->(c)` |
| ORDER BY | ✅ | `ORDER BY n.score DESC` |
| LIMIT | ✅ | `LIMIT 10` |
| SKIP | ✅ | `SKIP 5 LIMIT 10` |
| DISTINCT | ✅ | `RETURN DISTINCT b.type` |

### What Does NOT Work

| Feature | Status | Workaround |
|---------|--------|------------|
| Single quotes | ❌ | Use double quotes: `"value"` not `'value'` |
| Edge type syntax `[r:member_of]` | ❌ | Use `WHERE r.relation = "member_of"` |
| Multiple MATCH clauses | ❌ | Combine patterns in single MATCH or run separate queries |
| OPTIONAL MATCH | ❌ | Run separate queries |
| COUNT aggregation | ❌ | Use degree_centrality tool instead |

### Critical Implementation Notes

1. **Double quotes required**: grand-cypher only accepts double quotes for strings
   ```cypher
   -- WRONG: MATCH (n {label: 'Frodo'})
   -- RIGHT: MATCH (n {label: "Frodo"})
   ```

2. **Edge type syntax broken**: `[r:member_of]` returns empty results
   ```cypher
   -- WRONG: MATCH (a)-[r:member_of]->(b)
   -- RIGHT: MATCH (a)-[r]->(b) WHERE r.relation = "member_of"
   ```

3. **Node label property required**: Returning a node variable gives attributes dict, not ID
   ```python
   # Must add label property to nodes for easy querying
   for node in g.graph.nodes():
       g.graph.nodes[node]['label'] = node
   ```

4. **Edge relation format in results**: Raw edge returns `{(0, 0): 'relation'}` dict
   - Best to filter edges in WHERE, don't return raw edge variables
   - Or post-process to extract the relation string

## Open Questions (Resolved)

1. ~~**grand-cypher edge type syntax**: Does `[r:member_of]` work?~~
   - **ANSWER**: NO. Must use `WHERE r.relation = "member_of"`

2. ~~**Node ID vs label property**: Should we duplicate as a `label` property?~~
   - **ANSWER**: YES. Required for `n.label` access in queries

3. **Result size limits**: Should we add pagination or limits for large result sets?
   - Recommend: Add default LIMIT if none specified, or warn on large results

4. **Fuzzy matching**: Should Cypher queries support the existing fuzzy matcher?
   - Recommend: Keep Cypher strict, use `ask_graph` for fuzzy queries

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| grand-cypher | Pure Python, NetworkX native | Subset of Cypher |
| Custom DSL | Tailored to our needs | LLMs won't know it |
| SPARQL + rdflib | Standard, powerful | Different paradigm, RDF overhead |
| Raw NetworkX API | Full power | Not LLM-friendly |
| Gremlin | Industry standard | Needs Tinkerpop, heavier |

**Decision**: grand-cypher offers the best balance of capability, simplicity, and LLM familiarity.

## References

- [grand-cypher GitHub](https://github.com/aplbrain/grand-cypher)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)
