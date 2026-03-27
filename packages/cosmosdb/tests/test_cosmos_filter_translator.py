"""
Unit tests for CosmosFilterTranslator.

Covers:
- All 10 operators: eq, ne, gt, gte, lt, lte, contains, in, nin, exists
- and-node with 1 condition unwraps (no wrapping parens)
- and-node with 2 conditions → "(expr1) AND (expr2)"
- or-node with 1 condition unwraps
- or-node with 2 conditions → "(expr1) OR (expr2)"
- not-node → "NOT (expr)"
- None ast → (None, [])
- empty dict ast → (None, [])
- empty and/or conditions → (None, [])
- in_ multi-value expansion with real SQL IN
- nin multi-value expansion with NOT (...IN...)
- in_ with empty list → "1=0"
- nin with empty list → "1=1"
- exists(True) / exists(False) add no parameter entry
- unknown op raises ValueError
- unknown node type raises ValueError
- compound filter uses distinct @vN aliases with no collisions
- bracket notation c["field"] is used for all field paths
"""

import pytest

from pynosqlc.cosmosdb.cosmos_filter_translator import CosmosFilterTranslator

translate = CosmosFilterTranslator.translate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cond(field, op, value=None):
    """Convenience factory for condition AST nodes."""
    node = {"type": "condition", "field": field, "op": op}
    if value is not None:
        node["value"] = value
    return node


def param(name: str, value) -> dict:
    """Convenience factory for a Cosmos parameter dict."""
    return {"name": name, "value": value}


# ---------------------------------------------------------------------------
# None / empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_none_returns_none_empty(self):
        assert translate(None) == (None, [])

    def test_empty_dict_returns_none_empty(self):
        assert translate({}) == (None, [])

    def test_empty_and_conditions_returns_none_empty(self):
        assert translate({"type": "and", "conditions": []}) == (None, [])

    def test_empty_or_conditions_returns_none_empty(self):
        assert translate({"type": "or", "conditions": []}) == (None, [])


# ---------------------------------------------------------------------------
# All 10 operators on a regular field
# ---------------------------------------------------------------------------

class TestOperators:
    def test_eq(self):
        expr, params = translate(cond("name", "eq", "Alice"))
        assert expr == 'c["name"] = @v0'
        assert params == [param("@v0", "Alice")]

    def test_ne(self):
        expr, params = translate(cond("status", "ne", "inactive"))
        assert expr == 'c["status"] != @v0'
        assert params == [param("@v0", "inactive")]

    def test_gt(self):
        expr, params = translate(cond("age", "gt", 18))
        assert expr == 'c["age"] > @v0'
        assert params == [param("@v0", 18)]

    def test_gte(self):
        expr, params = translate(cond("score", "gte", 90))
        assert expr == 'c["score"] >= @v0'
        assert params == [param("@v0", 90)]

    def test_lt(self):
        expr, params = translate(cond("price", "lt", 100))
        assert expr == 'c["price"] < @v0'
        assert params == [param("@v0", 100)]

    def test_lte(self):
        expr, params = translate(cond("rank", "lte", 5))
        assert expr == 'c["rank"] <= @v0'
        assert params == [param("@v0", 5)]

    def test_contains(self):
        expr, params = translate(cond("tags", "contains", "python"))
        assert expr == 'ARRAY_CONTAINS(c["tags"], @v0)'
        assert params == [param("@v0", "python")]

    def test_exists_true(self):
        expr, params = translate(cond("email", "exists", True))
        assert expr == 'IS_DEFINED(c["email"])'
        assert params == []

    def test_exists_false(self):
        expr, params = translate(cond("deleted_at", "exists", False))
        assert expr == 'NOT IS_DEFINED(c["deleted_at"])'
        assert params == []

    def test_in(self):
        expr, params = translate(cond("category", "in", ["a", "b", "c"]))
        assert expr == 'c["category"] IN (@v0, @v1, @v2)'
        assert params == [
            param("@v0", "a"),
            param("@v1", "b"),
            param("@v2", "c"),
        ]

    def test_nin(self):
        expr, params = translate(cond("role", "nin", ["admin", "root"]))
        assert expr == 'NOT (c["role"] IN (@v0, @v1))'
        assert params == [
            param("@v0", "admin"),
            param("@v1", "root"),
        ]


# ---------------------------------------------------------------------------
# in / nin expansion and edge cases
# ---------------------------------------------------------------------------

class TestInNinExpansion:
    def test_in_single_value(self):
        expr, params = translate(cond("x", "in", ["only"]))
        assert expr == 'c["x"] IN (@v0)'
        assert params == [param("@v0", "only")]

    def test_in_multi_value_aliases_present(self):
        expr, params = translate(cond("x", "in", [1, 2, 3, 4]))
        assert expr == 'c["x"] IN (@v0, @v1, @v2, @v3)'
        assert [p["name"] for p in params] == ["@v0", "@v1", "@v2", "@v3"]
        assert [p["value"] for p in params] == [1, 2, 3, 4]

    def test_nin_produces_not_in(self):
        expr, params = translate(cond("status", "nin", ["a", "b"]))
        assert expr == 'NOT (c["status"] IN (@v0, @v1))'
        assert params == [param("@v0", "a"), param("@v1", "b")]

    def test_nin_multi_value(self):
        expr, params = translate(cond("x", "nin", [10, 20, 30]))
        assert expr == 'NOT (c["x"] IN (@v0, @v1, @v2))'
        assert params == [
            param("@v0", 10),
            param("@v1", 20),
            param("@v2", 30),
        ]

    def test_in_empty_list_never_matches(self):
        expr, params = translate(cond("x", "in", []))
        assert expr == "1=0"
        assert params == []

    def test_nin_empty_list_always_matches(self):
        expr, params = translate(cond("x", "nin", []))
        assert expr == "1=1"
        assert params == []


# ---------------------------------------------------------------------------
# exists does not add to parameters
# ---------------------------------------------------------------------------

class TestExistsNoValue:
    def test_exists_true_no_parameter(self):
        _, params = translate(cond("field", "exists", True))
        assert params == []

    def test_exists_false_no_parameter(self):
        _, params = translate(cond("field", "exists", False))
        assert params == []


# ---------------------------------------------------------------------------
# and-node
# ---------------------------------------------------------------------------

class TestAndNode:
    def test_single_condition_unwraps(self):
        node = {"type": "and", "conditions": [cond("x", "eq", 1)]}
        expr, params = translate(node)
        assert expr == 'c["x"] = @v0'
        assert params == [param("@v0", 1)]

    def test_two_conditions_produces_and(self):
        node = {
            "type": "and",
            "conditions": [cond("x", "eq", 1), cond("y", "gt", 0)],
        }
        expr, params = translate(node)
        assert expr == '(c["x"] = @v0) AND (c["y"] > @v1)'
        assert params == [param("@v0", 1), param("@v1", 0)]

    def test_three_conditions(self):
        node = {
            "type": "and",
            "conditions": [
                cond("a", "eq", 1),
                cond("b", "ne", 2),
                cond("c", "gt", 3),
            ],
        }
        expr, params = translate(node)
        assert expr == '(c["a"] = @v0) AND (c["b"] != @v1) AND (c["c"] > @v2)'
        assert len(params) == 3

    def test_empty_conditions_returns_none(self):
        node = {"type": "and", "conditions": []}
        assert translate(node) == (None, [])


# ---------------------------------------------------------------------------
# or-node
# ---------------------------------------------------------------------------

class TestOrNode:
    def test_single_condition_unwraps(self):
        node = {"type": "or", "conditions": [cond("x", "eq", 1)]}
        expr, params = translate(node)
        assert expr == 'c["x"] = @v0'

    def test_two_conditions_produces_or(self):
        node = {
            "type": "or",
            "conditions": [cond("a", "lt", 5), cond("b", "gte", 10)],
        }
        expr, params = translate(node)
        assert expr == '(c["a"] < @v0) OR (c["b"] >= @v1)'
        assert params == [param("@v0", 5), param("@v1", 10)]

    def test_empty_conditions_returns_none(self):
        node = {"type": "or", "conditions": []}
        assert translate(node) == (None, [])


# ---------------------------------------------------------------------------
# not-node
# ---------------------------------------------------------------------------

class TestNotNode:
    def test_not_wraps_with_not(self):
        node = {"type": "not", "condition": cond("active", "eq", True)}
        expr, params = translate(node)
        assert expr == 'NOT (c["active"] = @v0)'
        assert params == [param("@v0", True)]

    def test_not_with_and_inner(self):
        inner = {
            "type": "and",
            "conditions": [cond("x", "gt", 0), cond("y", "lt", 10)],
        }
        node = {"type": "not", "condition": inner}
        expr, _ = translate(node)
        assert expr == 'NOT ((c["x"] > @v0) AND (c["y"] < @v1))'

    def test_not_exists(self):
        node = {"type": "not", "condition": cond("field", "exists", True)}
        expr, params = translate(node)
        assert expr == 'NOT (IS_DEFINED(c["field"]))'
        assert params == []


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_unknown_op_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown filter operator"):
            translate(cond("x", "regex", ".*"))

    def test_unknown_node_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown filter AST node type"):
            translate({"type": "xor", "conditions": []})


# ---------------------------------------------------------------------------
# Global counter: no alias collisions in compound filters
# ---------------------------------------------------------------------------

class TestGlobalCounters:
    def test_distinct_value_aliases_across_fields(self):
        """A compound filter over three distinct fields must use @v0/@v1/@v2
        with no collisions, and parameters list preserves insertion order."""
        node = {
            "type": "and",
            "conditions": [
                cond("alpha", "eq", 1),
                cond("beta", "gt", 2),
                cond("gamma", "lte", 3),
            ],
        }
        expr, params = translate(node)
        assert expr == (
            '(c["alpha"] = @v0) AND (c["beta"] > @v1) AND (c["gamma"] <= @v2)'
        )
        assert params == [
            param("@v0", 1),
            param("@v1", 2),
            param("@v2", 3),
        ]

    def test_in_then_eq_no_collision(self):
        """in_ expands multiple @vN aliases; a subsequent field must continue
        from the correct counter, not restart at @v0."""
        node = {
            "type": "and",
            "conditions": [
                cond("status", "in", ["a", "b"]),
                cond("age", "gt", 18),
            ],
        }
        expr, params = translate(node)
        assert params[0] == param("@v0", "a")
        assert params[1] == param("@v1", "b")
        assert params[2] == param("@v2", 18)
        assert 'c["status"] IN (@v0, @v1)' in expr
        assert 'c["age"] > @v2' in expr

    def test_exists_does_not_consume_counter(self):
        """exists must not consume an @vN slot; a following condition must use
        @v0, not @v1."""
        node = {
            "type": "and",
            "conditions": [
                cond("email", "exists", True),
                cond("age", "gt", 18),
            ],
        }
        expr, params = translate(node)
        # Only one parameter — from the gt condition
        assert params == [param("@v0", 18)]
        assert 'IS_DEFINED(c["email"])' in expr
        assert 'c["age"] > @v0' in expr

    def test_nin_then_eq_no_collision(self):
        """nin_ expands multiple @vN aliases; subsequent fields continue."""
        node = {
            "type": "and",
            "conditions": [
                cond("role", "nin", ["admin", "root"]),
                cond("active", "eq", True),
            ],
        }
        expr, params = translate(node)
        assert params[0] == param("@v0", "admin")
        assert params[1] == param("@v1", "root")
        assert params[2] == param("@v2", True)
        assert 'NOT (c["role"] IN (@v0, @v1))' in expr
        assert 'c["active"] = @v2' in expr

    def test_bracket_notation_for_reserved_word_field(self):
        """Field named 'value' (a Cosmos reserved word) uses bracket notation."""
        expr, params = translate(cond("value", "eq", 42))
        assert expr == 'c["value"] = @v0'
        assert params == [param("@v0", 42)]

    def test_bracket_notation_for_field_with_space(self):
        """Field names with spaces are valid in bracket notation."""
        expr, params = translate(cond("first name", "eq", "Bob"))
        assert expr == 'c["first name"] = @v0'
        assert params == [param("@v0", "Bob")]
