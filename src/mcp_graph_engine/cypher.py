"""
Cypher query execution for NetworkX graphs using grand-cypher.

This module provides:
1. Query preprocessing to fix common LLM mistakes
2. Cypher query execution against NetworkX graphs
"""

import re
from typing import Any

import networkx as nx
from grandcypher import GrandCypher


def preprocess_cypher(query: str) -> tuple[str, list[str]]:
    """
    Fix common LLM Cypher mistakes before execution.

    Fixes applied:
    1. Single quotes → double quotes (grand-cypher only accepts double quotes)
    2. Edge type syntax [r:type] → WHERE r.relation = "type"

    Args:
        query: Raw Cypher query string

    Returns:
        Tuple of (fixed_query, list_of_fixes_applied)
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


def execute_cypher_query(nx_graph: nx.DiGraph, query: str) -> dict[str, Any]:
    """
    Execute a Cypher query against a NetworkX graph.
    Applies preprocessing to fix common LLM mistakes.

    Args:
        nx_graph: NetworkX DiGraph to query
        query: Cypher query string (may use non-standard syntax)

    Returns:
        Dict with:
        - success: bool - whether query executed successfully
        - query: str - original query
        - query_executed: str | None - query after preprocessing (if different)
        - fixes_applied: list[str] - preprocessing fixes that were applied
        - columns: list[str] - column names (on success)
        - rows: list[dict] - result rows (on success)
        - count: int - number of rows (on success)
        - error: str - error message (on failure)
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

        # Clean column names (remove Token wrapper if present)
        columns = [str(k) if not hasattr(k, 'value') else k.value for k in result.keys()]
        raw_columns = list(result.keys())
        num_rows = len(next(iter(result.values())))

        rows = []
        for i in range(num_rows):
            row = {}
            for col_name, raw_col in zip(columns, raw_columns, strict=True):
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
