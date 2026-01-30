"""Tests for Cypher query functionality."""

from src.mcp_graph_engine.cypher import execute_cypher_query, preprocess_cypher
from src.mcp_graph_engine.graph_engine import GraphEngine


class TestBasicCypherQueries:
    """Tests for basic Cypher query functionality."""

    def test_basic_match(self):
        """Test basic MATCH query with property matching."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Fellowship", node_type="group")
        engine.add_edge("Frodo", "Fellowship", "member_of")

        result = execute_cypher_query(engine.graph, """
            MATCH (c)-[r]->(f {label: "Fellowship"})
            RETURN c.label
        """)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["rows"][0]["c.label"] == "Frodo"

    def test_filter_by_relation(self):
        """Test filtering edges by relation type using WHERE clause."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Fellowship", node_type="group")
        engine.add_node("Shire", node_type="location")
        engine.add_edge("Frodo", "Fellowship", "member_of")
        engine.add_edge("Frodo", "Shire", "lives_in")

        result = execute_cypher_query(engine.graph, """
            MATCH (c)-[r]->(f)
            WHERE r.relation = "member_of"
            RETURN c.label, f.label
        """)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["rows"][0]["c.label"] == "Frodo"
        assert result["rows"][0]["f.label"] == "Fellowship"

    def test_variable_length_path(self):
        """Test variable-length path queries."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_node("C")
        engine.add_edge("A", "B", "connects")
        engine.add_edge("B", "C", "connects")

        result = execute_cypher_query(engine.graph, """
            MATCH (a {label: "A"})-[*1..2]->(end)
            RETURN end.label
        """)

        assert result["success"] is True
        assert result["count"] == 2
        labels = [r["end.label"] for r in result["rows"]]
        assert "B" in labels
        assert "C" in labels

    def test_empty_result(self):
        """Test query that returns no results."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")

        result = execute_cypher_query(engine.graph, """
            MATCH (n {label: "NonExistent"})
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["rows"] == []

    def test_match_all_nodes(self):
        """Test matching all nodes with no filters."""
        engine = GraphEngine()
        engine.add_node("A", node_type="character")
        engine.add_node("B", node_type="character")
        engine.add_node("C", node_type="location")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["count"] == 3
        labels = [r["n.label"] for r in result["rows"]]
        assert "A" in labels
        assert "B" in labels
        assert "C" in labels

    def test_filter_by_node_type(self):
        """Test filtering nodes by type attribute."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Sam", node_type="character")
        engine.add_node("Shire", node_type="location")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            WHERE n.type = "character"
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["count"] == 2
        labels = [r["n.label"] for r in result["rows"]]
        assert "Frodo" in labels
        assert "Sam" in labels
        assert "Shire" not in labels


class TestCypherPreprocessing:
    """Tests for Cypher query preprocessing (LLM-friendly fixes)."""

    def test_preprocess_single_quotes(self):
        """Test that single quotes are automatically converted to double quotes."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")

        # Use single quotes (common LLM mistake)
        result = execute_cypher_query(engine.graph, """
            MATCH (n {label: 'Frodo'})
            RETURN n.label
        """)

        assert result["success"] is True
        assert "single quotes → double quotes" in result["fixes_applied"]
        assert result["count"] == 1
        assert result["rows"][0]["n.label"] == "Frodo"

    def test_preprocess_edge_type(self):
        """Test that edge type syntax [r:type] is converted to WHERE clause."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Fellowship", node_type="group")
        engine.add_edge("Frodo", "Fellowship", "member_of")

        # Use [r:member_of] syntax (not supported by grand-cypher)
        result = execute_cypher_query(engine.graph, """
            MATCH (c)-[r:member_of]->(f)
            RETURN c.label, f.label
        """)

        assert result["success"] is True
        assert any("WHERE clause" in fix for fix in result["fixes_applied"])
        assert result["count"] == 1
        assert result["rows"][0]["c.label"] == "Frodo"
        assert result["rows"][0]["f.label"] == "Fellowship"

    def test_preprocess_no_changes_needed(self):
        """Test that queries with correct syntax aren't modified."""
        engine = GraphEngine()
        engine.add_node("Frodo")

        result = execute_cypher_query(engine.graph, """
            MATCH (n {label: "Frodo"})
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["fixes_applied"] == []
        assert result["query_executed"] is None

    def test_preprocess_edge_type_without_variable(self):
        """Test edge type syntax without variable name [:type]."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_edge("A", "B", "connects")

        result = execute_cypher_query(engine.graph, """
            MATCH (a)-[:connects]->(b)
            RETURN a.label, b.label
        """)

        assert result["success"] is True
        assert any("WHERE clause" in fix for fix in result["fixes_applied"])
        assert result["count"] == 1


class TestCypherErrorHandling:
    """Tests for Cypher query error handling."""

    def test_syntax_error(self):
        """Test that syntax errors are handled gracefully."""
        engine = GraphEngine()
        engine.add_node("Frodo")

        result = execute_cypher_query(engine.graph, """
            MATCH (n {label: "Frodo"}
            RETURN n
        """)

        assert result["success"] is False
        assert "error" in result

    def test_invalid_property_access(self):
        """Test accessing non-existent property."""
        engine = GraphEngine()
        engine.add_node("Frodo")

        # This should not fail - just return None or handle gracefully
        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            RETURN n.nonexistent
        """)

        # grand-cypher may return empty or None values
        # The query should succeed even if property doesn't exist
        assert result["success"] is True


class TestMultiHopPatterns:
    """Tests for multi-hop path patterns."""

    def test_two_hop_pattern(self):
        """Test finding 2-hop connections."""
        engine = GraphEngine()
        engine.add_node("Frodo")
        engine.add_node("Sam")
        engine.add_node("Fellowship")
        engine.add_edge("Frodo", "Sam", "friends_with")
        engine.add_edge("Sam", "Fellowship", "member_of")

        result = execute_cypher_query(engine.graph, """
            MATCH (a {label: "Frodo"})-[r1]->(b)-[r2]->(c)
            RETURN a.label, b.label, c.label, r1.relation, r2.relation
        """)

        assert result["success"] is True
        assert result["count"] == 1
        row = result["rows"][0]
        assert row["a.label"] == "Frodo"
        assert row["b.label"] == "Sam"
        assert row["c.label"] == "Fellowship"
        assert row["r1.relation"] == "friends_with"
        assert row["r2.relation"] == "member_of"

    def test_variable_length_path_with_distinct(self):
        """Test variable-length paths with DISTINCT."""
        engine = GraphEngine()
        engine.add_node("Sauron")
        engine.add_node("Ring")
        engine.add_node("Frodo")
        engine.add_node("Mount_Doom")
        engine.add_edge("Sauron", "Ring", "created")
        engine.add_edge("Ring", "Frodo", "possessed_by")
        engine.add_edge("Frodo", "Mount_Doom", "traveled_to")

        result = execute_cypher_query(engine.graph, """
            MATCH (s {label: "Sauron"})-[*1..3]->(end)
            RETURN DISTINCT end.label
        """)

        assert result["success"] is True
        assert result["count"] >= 3
        labels = [r["end.label"] for r in result["rows"]]
        assert "Ring" in labels
        assert "Frodo" in labels
        assert "Mount_Doom" in labels


class TestAdvancedFiltering:
    """Tests for advanced WHERE clause filtering."""

    def test_filter_with_in_operator(self):
        """Test filtering with IN operator."""
        engine = GraphEngine()
        engine.add_node("A")
        engine.add_node("B")
        engine.add_node("C")
        engine.add_edge("A", "B", "member_of")
        engine.add_edge("B", "C", "friends_with")

        result = execute_cypher_query(engine.graph, """
            MATCH (a)-[r]->(b)
            WHERE r.relation IN ["member_of", "friends_with"]
            RETURN a.label, r.relation, b.label
        """)

        assert result["success"] is True
        assert result["count"] == 2

    def test_filter_with_and_operator(self):
        """Test filtering with AND operator."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Sam", node_type="character")
        engine.add_node("Fellowship", node_type="group")
        engine.add_edge("Frodo", "Fellowship", "member_of")
        engine.add_edge("Sam", "Fellowship", "member_of")

        result = execute_cypher_query(engine.graph, """
            MATCH (c)-[r]->(g)
            WHERE c.type = "character" AND g.type = "group" AND r.relation = "member_of"
            RETURN c.label
        """)

        assert result["success"] is True
        assert result["count"] == 2
        labels = [r["c.label"] for r in result["rows"]]
        assert "Frodo" in labels
        assert "Sam" in labels

    def test_filter_with_contains(self):
        """Test string matching with CONTAINS."""
        engine = GraphEngine()
        engine.add_node("One_Ring")
        engine.add_node("Ring_of_Power")
        engine.add_node("Sword")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            WHERE n.label CONTAINS "Ring"
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["count"] == 2
        labels = [r["n.label"] for r in result["rows"]]
        assert "One_Ring" in labels
        assert "Ring_of_Power" in labels
        assert "Sword" not in labels

    def test_filter_with_starts_with(self):
        """Test string matching with STARTS WITH."""
        engine = GraphEngine()
        engine.add_node("Sauron")
        engine.add_node("Sam")
        engine.add_node("Frodo")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            WHERE n.label STARTS WITH "S"
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["count"] == 2
        labels = [r["n.label"] for r in result["rows"]]
        assert "Sauron" in labels
        assert "Sam" in labels
        assert "Frodo" not in labels


class TestResultFormatting:
    """Tests for result formatting and structure."""

    def test_result_has_correct_structure(self):
        """Test that result dict has expected structure."""
        engine = GraphEngine()
        engine.add_node("A")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            RETURN n.label
        """)

        assert "success" in result
        assert "query" in result
        assert "query_executed" in result
        assert "fixes_applied" in result
        assert "columns" in result
        assert "rows" in result
        assert "count" in result

    def test_multiple_columns_returned(self):
        """Test returning multiple columns."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Fellowship", node_type="group")
        engine.add_edge("Frodo", "Fellowship", "member_of")

        result = execute_cypher_query(engine.graph, """
            MATCH (a)-[r]->(b)
            RETURN a.label, a.type, r.relation, b.label, b.type
        """)

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["columns"]) == 5
        row = result["rows"][0]
        assert row["a.label"] == "Frodo"
        assert row["a.type"] == "character"
        assert row["r.relation"] == "member_of"
        assert row["b.label"] == "Fellowship"
        assert row["b.type"] == "group"

    def test_empty_graph_query(self):
        """Test querying an empty graph."""
        engine = GraphEngine()

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            RETURN n.label
        """)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["rows"] == []


class TestLabelPropertyAccess:
    """Tests specifically for node label property access."""

    def test_label_property_is_set(self):
        """Test that nodes have a 'label' attribute set."""
        engine = GraphEngine()
        engine.add_node("TestNode", node_type="test")

        # Verify the label attribute is set in NetworkX
        assert "label" in engine.graph.nodes["TestNode"]
        assert engine.graph.nodes["TestNode"]["label"] == "TestNode"

    def test_cypher_can_access_label_property(self):
        """Test that Cypher queries can access n.label."""
        engine = GraphEngine()
        engine.add_node("Frodo")
        engine.add_node("Sam")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            RETURN n.label
            LIMIT 2
        """)

        assert result["success"] is True
        assert result["count"] == 2
        labels = [r["n.label"] for r in result["rows"]]
        assert "Frodo" in labels
        assert "Sam" in labels

    def test_label_property_with_filtering(self):
        """Test filtering by label property."""
        engine = GraphEngine()
        engine.add_node("Frodo", node_type="character")
        engine.add_node("Sam", node_type="character")

        result = execute_cypher_query(engine.graph, """
            MATCH (n)
            WHERE n.label = "Frodo"
            RETURN n.label, n.type
        """)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["rows"][0]["n.label"] == "Frodo"
        assert result["rows"][0]["n.type"] == "character"


class TestPreprocessCypherFunction:
    """Tests for the preprocess_cypher function directly."""

    def test_preprocess_single_quotes_only(self):
        """Test preprocessing only fixes single quotes."""
        query = "MATCH (n {label: 'Frodo'}) RETURN n"
        fixed_query, fixes = preprocess_cypher(query)

        assert 'Frodo"' in fixed_query
        assert "single quotes → double quotes" in fixes

    def test_preprocess_edge_type_only(self):
        """Test preprocessing only fixes edge type syntax."""
        query = "MATCH (a)-[r:member_of]->(b) RETURN a, b"
        fixed_query, fixes = preprocess_cypher(query)

        assert "[r]" in fixed_query
        assert "WHERE" in fixed_query
        assert "r.relation" in fixed_query
        assert any("WHERE clause" in fix for fix in fixes)

    def test_preprocess_both_fixes(self):
        """Test preprocessing applies multiple fixes."""
        query = "MATCH (a {label: 'Frodo'})-[r:member_of]->(b) RETURN a"
        fixed_query, fixes = preprocess_cypher(query)

        assert len(fixes) == 2
        assert "single quotes → double quotes" in fixes
        assert any("WHERE clause" in fix for fix in fixes)

    def test_preprocess_no_fixes_needed(self):
        """Test preprocessing with correct syntax returns unchanged."""
        query = 'MATCH (n {label: "Frodo"}) RETURN n'
        fixed_query, fixes = preprocess_cypher(query)

        assert fixed_query == query
        assert fixes == []

    def test_preprocess_edge_type_with_existing_where(self):
        """Test edge type preprocessing with existing WHERE clause."""
        query = "MATCH (a)-[r:member_of]->(b) WHERE a.type = 'character' RETURN a"
        fixed_query, fixes = preprocess_cypher(query)

        # Should add to existing WHERE with AND
        assert "WHERE r.relation" in fixed_query
        assert "AND" in fixed_query
        assert len(fixes) == 2  # quotes + edge type
