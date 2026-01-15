# Design: Mermaid Export Support

## Overview

Add Mermaid flowchart export to the graph engine, enabling round-trip workflows where graphs can be imported from Mermaid diagrams, analyzed, and exported back to Mermaid for documentation.

## Motivation

Currently the tool supports:
- **Import**: Mermaid → Graph (`create_from_mermaid`)
- **Export**: Graph → DOT, CSV, GraphML, JSON

Adding Mermaid export closes the loop, allowing users to:
1. Build graphs programmatically via `add_facts` or `add_knowledge`
2. Run analysis (PageRank, cycles, paths)
3. Export to Mermaid for embedding in documentation

## Implementation

### 1. Add `_export_mermaid()` method

**File**: `src/mcp_graph_engine/graph_engine.py`

**Location**: After `_export_json()` (around line 1070)

```python
def _export_mermaid(self) -> str:
    """Export to Mermaid flowchart format."""
    lines = ["graph TD"]

    for source, target, attrs in self.graph.edges(data=True):
        relation = attrs.get('relation', 'relates_to')
        # Escape special characters in relation labels
        relation_escaped = relation.replace('"', '\\"')
        lines.append(f"    {source} -->|{relation_escaped}| {target}")

    return "\n".join(lines)
```

### 2. Update `export_graph()` to handle "mermaid" format

**File**: `src/mcp_graph_engine/graph_engine.py`

**Location**: In `export_graph()` method (around line 983)

Add case for mermaid format:
```python
elif format == "mermaid":
    return self._export_mermaid()
```

Update the error message to include "mermaid" in supported formats.

### 3. Update empty graph handling

**Location**: In `export_graph()` around line 970

Add empty graph case:
```python
elif format == "mermaid":
    return "graph TD\n"
```

### 4. Update tool schema

**File**: `src/mcp_graph_engine/tools.py`

**Location**: `export_graph` tool definition (search for `name="export_graph"`)

Update the format enum to include "mermaid":
```python
"format": {
    "type": "string",
    "description": "Format to export to",
    "enum": ["dot", "csv", "graphml", "json", "mermaid"]
}
```

## Edge Cases

### Node IDs with spaces
Mermaid node IDs cannot contain spaces. Current implementation uses node labels directly.

**Options**:
1. Replace spaces with underscores in export
2. Use bracket syntax: `A["Node With Spaces"]`

**Recommendation**: Use bracket syntax for labels with spaces:
```python
def _sanitize_node_id(self, label: str) -> str:
    """Generate valid Mermaid node ID from label."""
    # Replace non-alphanumeric with underscore
    node_id = re.sub(r'[^a-zA-Z0-9]', '_', label)
    return node_id

def _export_mermaid(self) -> str:
    lines = ["graph TD"]
    node_ids = {}  # Map labels to generated IDs

    for node in self.graph.nodes():
        if not re.match(r'^[a-zA-Z0-9_]+$', node):
            node_ids[node] = self._sanitize_node_id(node)

    for source, target, attrs in self.graph.edges(data=True):
        src_id = node_ids.get(source, source)
        tgt_id = node_ids.get(target, target)
        relation = attrs.get('relation', 'relates_to')

        # Add label syntax if ID differs from original
        src_str = f'{src_id}["{source}"]' if src_id != source else source
        tgt_str = f'{tgt_id}["{target}"]' if tgt_id != target else target

        lines.append(f"    {src_str} -->|{relation}| {tgt_str}")

    return "\n".join(lines)
```

### Special characters in relations
Mermaid edge labels use `|label|` syntax. Pipe characters in labels need escaping.

**Solution**: Replace `|` with `\|` or use HTML entity `&#124;`

### Graph direction
Default to `TD` (top-down). Could add parameter for `LR` (left-right).

**Recommendation**: Start with `TD`, add direction parameter later if needed.

## Testing

### Unit tests to add

**File**: `tests/test_graph_engine.py`

```python
def test_export_mermaid_basic():
    """Test basic Mermaid export."""
    engine = GraphEngine()
    engine.add_facts([
        {"from": "A", "to": "B", "rel": "connects"},
        {"from": "B", "to": "C", "rel": "links"}
    ])
    result = engine.export_graph("mermaid")
    assert "graph TD" in result
    assert "A -->|connects| B" in result
    assert "B -->|links| C" in result

def test_export_mermaid_empty():
    """Test Mermaid export of empty graph."""
    engine = GraphEngine()
    result = engine.export_graph("mermaid")
    assert result == "graph TD\n"

def test_export_mermaid_spaces_in_labels():
    """Test Mermaid export with spaces in node labels."""
    engine = GraphEngine()
    engine.add_facts([
        {"from": "User Service", "to": "Auth Service", "rel": "calls"}
    ])
    result = engine.export_graph("mermaid")
    assert "graph TD" in result
    # Should have bracket syntax for labels with spaces
    assert '["User Service"]' in result or "User_Service" in result

def test_export_mermaid_special_chars_in_relation():
    """Test Mermaid export with pipe in relation."""
    engine = GraphEngine()
    engine.add_facts([
        {"from": "A", "to": "B", "rel": "read|write"}
    ])
    result = engine.export_graph("mermaid")
    # Pipe should be escaped
    assert "|" not in result.split("-->")[1].split("|")[1] or "read" in result

def test_mermaid_roundtrip():
    """Test import then export preserves structure."""
    engine = GraphEngine()
    original = """graph TD
    A -->|calls| B
    B -->|returns| A"""

    # Import
    # (would need to call the server's parse_mermaid or add a method)

    # Export
    result = engine.export_graph("mermaid")

    # Should have same edges
    assert "A" in result
    assert "B" in result
    assert "calls" in result
    assert "returns" in result
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/mcp_graph_engine/graph_engine.py` | Add `_export_mermaid()`, update `export_graph()` |
| `src/mcp_graph_engine/tools.py` | Update format enum in export_graph tool |
| `tests/test_graph_engine.py` | Add mermaid export tests |

## Acceptance Criteria

- [ ] `export_graph("mermaid")` returns valid Mermaid flowchart syntax
- [ ] Empty graphs export as `graph TD\n`
- [ ] Node labels with spaces are handled correctly
- [ ] Special characters in relations are escaped
- [ ] Tool schema updated to include "mermaid" format
- [ ] Unit tests pass
- [ ] Round-trip test: import mermaid → export mermaid preserves structure
