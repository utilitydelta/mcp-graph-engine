# Query & Analysis Tools - Usage Guide

This document provides examples of how to use each of the 8 new analysis tools in the MCP Graph Engine.

## 1. shortest_path

Find the shortest path between two nodes.

**MCP Tool Call:**
```json
{
  "tool": "shortest_path",
  "arguments": {
    "graph": "codebase",
    "source": "ApiController",
    "target": "Database"
  }
}
```

**Response:**
```json
{
  "path": ["ApiController", "Service", "Repository", "Database"],
  "length": 3
}
```

**Use Cases:**
- Finding dependency chains
- Understanding data flow paths
- Identifying shortest route between components

---

## 2. all_paths

Find all simple paths between two nodes (no repeated nodes).

**MCP Tool Call:**
```json
{
  "tool": "all_paths",
  "arguments": {
    "graph": "codebase",
    "source": "Frontend",
    "target": "Backend",
    "max_length": 5
  }
}
```

**Response:**
```json
{
  "paths": [
    ["Frontend", "API", "Backend"],
    ["Frontend", "Router", "Controller", "Backend"]
  ],
  "count": 2
}
```

**Use Cases:**
- Finding alternative paths
- Understanding all possible routes
- Analyzing redundancy in architecture

---

## 3. pagerank

Calculate PageRank scores to identify important/central nodes.

**MCP Tool Call:**
```json
{
  "tool": "pagerank",
  "arguments": {
    "graph": "codebase",
    "top_n": 5
  }
}
```

**Response:**
```json
{
  "rankings": [
    {"label": "Database", "score": 0.2341},
    {"label": "AuthService", "score": 0.1892},
    {"label": "ApiGateway", "score": 0.1654},
    {"label": "UserService", "score": 0.1234},
    {"label": "Cache", "score": 0.1021}
  ]
}
```

**Use Cases:**
- Identifying the most important nodes
- Finding bottlenecks
- Prioritizing refactoring targets

---

## 4. connected_components

Find weakly connected components (groups of interconnected nodes).

**MCP Tool Call:**
```json
{
  "tool": "connected_components",
  "arguments": {
    "graph": "codebase"
  }
}
```

**Response:**
```json
{
  "components": [
    ["ServiceA", "ServiceB", "Database"],
    ["UtilityModule", "HelperClass"]
  ],
  "count": 2
}
```

**Use Cases:**
- Finding isolated modules
- Identifying architectural boundaries
- Detecting disconnected systems

---

## 5. find_cycles

Detect cycles in the graph (circular dependencies).

**MCP Tool Call:**
```json
{
  "tool": "find_cycles",
  "arguments": {
    "graph": "codebase"
  }
}
```

**Response:**
```json
{
  "cycles": [
    ["ModuleA", "ModuleB", "ModuleC"]
  ],
  "has_cycles": true
}
```

**Use Cases:**
- Detecting circular dependencies
- Finding problematic import cycles
- Identifying areas needing refactoring

---

## 6. transitive_reduction

Remove redundant transitive edges (e.g., if A→B→C and A→C exist, A→C is redundant).

**MCP Tool Call:**
```json
{
  "tool": "transitive_reduction",
  "arguments": {
    "graph": "codebase",
    "in_place": false
  }
}
```

**Response:**
```json
{
  "edges_removed": 3
}
```

**Use Cases:**
- Simplifying dependency graphs
- Finding direct vs indirect dependencies
- Cleaning up architecture diagrams

---

## 7. degree_centrality

Calculate degree centrality (in-degree, out-degree) to identify highly connected nodes.

**MCP Tool Call:**
```json
{
  "tool": "degree_centrality",
  "arguments": {
    "graph": "codebase",
    "top_n": 5
  }
}
```

**Response:**
```json
{
  "rankings": [
    {
      "label": "Database",
      "in_degree": 0.667,
      "out_degree": 0.000,
      "total": 0.667
    },
    {
      "label": "ApiGateway",
      "in_degree": 0.000,
      "out_degree": 0.556,
      "total": 0.556
    }
  ]
}
```

**Use Cases:**
- Finding hubs (high in-degree)
- Finding sources (high out-degree)
- Identifying communication patterns

---

## 8. subgraph

Extract a subgraph containing only specified nodes and their interconnections.

**MCP Tool Call:**
```json
{
  "tool": "subgraph",
  "arguments": {
    "graph": "codebase",
    "nodes": ["ServiceA", "ServiceB", "Database"],
    "include_edges": true
  }
}
```

**Response:**
```json
{
  "nodes": [
    {"label": "ServiceA", "type": "service", "properties": {}},
    {"label": "ServiceB", "type": "service", "properties": {}},
    {"label": "Database", "type": "database", "properties": {}}
  ],
  "edges": [
    {"source": "ServiceA", "target": "Database", "relation": "queries"},
    {"source": "ServiceB", "target": "Database", "relation": "queries"}
  ]
}
```

**Use Cases:**
- Extracting a portion of a large graph
- Focusing on specific subsystems
- Creating views for specific analyses

---

## Common Patterns

### Fuzzy Matching
All tools that accept node names support fuzzy matching:
```json
{
  "tool": "shortest_path",
  "arguments": {
    "source": "auth service",     // Matches "AuthService"
    "target": "database pool"     // Matches "DatabasePool"
  }
}
```

### Default Graph
If you omit the `graph` parameter, the "default" graph is used:
```json
{
  "tool": "pagerank",
  "arguments": {
    "top_n": 10
  }
}
```

### Error Handling
When nodes aren't found, tools return helpful error messages:
```json
{
  "path": null,
  "reason": "Source node not found: NonExistentNode"
}
```

## Workflow Examples

### Analyzing a Codebase
1. Add nodes and edges as you explore
2. Use `pagerank` to find most important modules
3. Use `degree_centrality` to find hubs
4. Use `find_cycles` to detect circular dependencies
5. Use `shortest_path` to understand dependency chains

### Refactoring Planning
1. Use `connected_components` to find isolated modules
2. Use `transitive_reduction` to simplify dependencies
3. Use `subgraph` to focus on specific areas
4. Use `all_paths` to understand alternative routes

### Architecture Review
1. Use `pagerank` to identify critical components
2. Use `degree_centrality` to find coupling issues
3. Use `find_cycles` to find design problems
4. Use `shortest_path` to trace request flows
