"""
Unit tests for DynamoFilterTranslator.

Covers:
- All 10 operators: eq, ne, gt, gte, lt, lte, contains, in, nin, exists
- and-node with 1 condition unwraps (no wrapping parens)
- and-node with 2 conditions → "(expr1) AND (expr2)"
- or-node with 1 condition unwraps
- or-node with 2 conditions → "(expr1) OR (expr2)"
- not-node → "NOT (expr)"
- None ast → (None, {}, {})
- empty dict ast → (None, {}, {})
- empty and/or conditions → (None, {}, {})
- in_ multi-value expansion
- nin multi-value expansion
- exists(True) / exists(False) add no entry to attr_values
- unknown op raises ValueError
- unknown node type raises ValueError
- compound filter uses distinct #nX and :vX aliases with no collisions
"""

import pytest

from pynosqlc.dynamodb.dynamo_filter_translator import DynamoFilterTranslator

translate = DynamoFilterTranslator.translate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cond(field, op, value=None):
    """Convenience factory for condition AST nodes."""
    node = {"type": "condition", "field": field, "op": op}
    if value is not None:
        node["value"] = value
    return node


# ---------------------------------------------------------------------------
# None / empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_none_returns_triple_none(self):
        assert translate(None) == (None, {}, {})

    def test_empty_dict_returns_triple_none(self):
        assert translate({}) == (None, {}, {})

    def test_empty_and_conditions_returns_triple_none(self):
        assert translate({"type": "and", "conditions": []}) == (None, {}, {})

    def test_empty_or_conditions_returns_triple_none(self):
        assert translate({"type": "or", "conditions": []}) == (None, {}, {})


# ---------------------------------------------------------------------------
# All 10 operators on a regular field
# ---------------------------------------------------------------------------

class TestOperators:
    def test_eq(self):
        expr, names, values = translate(cond("name", "eq", "Alice"))
        assert names == {"#n0": "name"}
        assert values == {":v0": "Alice"}
        assert expr == "#n0 = :v0"

    def test_ne(self):
        expr, names, values = translate(cond("status", "ne", "inactive"))
        assert names == {"#n0": "status"}
        assert values == {":v0": "inactive"}
        assert expr == "#n0 <> :v0"

    def test_gt(self):
        expr, names, values = translate(cond("age", "gt", 18))
        assert names == {"#n0": "age"}
        assert values == {":v0": 18}
        assert expr == "#n0 > :v0"

    def test_gte(self):
        expr, names, values = translate(cond("score", "gte", 90))
        assert names == {"#n0": "score"}
        assert values == {":v0": 90}
        assert expr == "#n0 >= :v0"

    def test_lt(self):
        expr, names, values = translate(cond("price", "lt", 100))
        assert names == {"#n0": "price"}
        assert values == {":v0": 100}
        assert expr == "#n0 < :v0"

    def test_lte(self):
        expr, names, values = translate(cond("rank", "lte", 5))
        assert names == {"#n0": "rank"}
        assert values == {":v0": 5}
        assert expr == "#n0 <= :v0"

    def test_contains(self):
        expr, names, values = translate(cond("tags", "contains", "python"))
        assert names == {"#n0": "tags"}
        assert values == {":v0": "python"}
        assert expr == "contains(#n0, :v0)"

    def test_exists_true(self):
        expr, names, values = translate(cond("email", "exists", True))
        assert names == {"#n0": "email"}
        assert values == {}
        assert expr == "attribute_exists(#n0)"

    def test_exists_false(self):
        expr, names, values = translate(cond("deleted_at", "exists", False))
        assert names == {"#n0": "deleted_at"}
        assert values == {}
        assert expr == "attribute_not_exists(#n0)"

    def test_in(self):
        expr, names, values = translate(cond("category", "in", ["a", "b", "c"]))
        assert names == {"#n0": "category"}
        assert values == {":v0": "a", ":v1": "b", ":v2": "c"}
        assert expr == "(#n0 = :v0 OR #n0 = :v1 OR #n0 = :v2)"

    def test_nin(self):
        expr, names, values = translate(cond("role", "nin", ["admin", "root"]))
        assert names == {"#n0": "role"}
        assert values == {":v0": "admin", ":v1": "root"}
        assert expr == "(#n0 <> :v0 AND #n0 <> :v1)"


# ---------------------------------------------------------------------------
# in / nin expansion
# ---------------------------------------------------------------------------

class TestInNinExpansion:
    def test_in_single_value(self):
        expr, names, values = translate(cond("x", "in", ["only"]))
        assert expr == "(#n0 = :v0)"
        assert values == {":v0": "only"}

    def test_in_multi_value_aliases_present(self):
        expr, names, values = translate(cond("x", "in", [1, 2, 3, 4]))
        assert set(values.keys()) == {":v0", ":v1", ":v2", ":v3"}
        assert list(values.values()) == [1, 2, 3, 4]
        # All clauses reference the same field alias
        assert "#n0 = :v0" in expr
        assert "#n0 = :v3" in expr

    def test_nin_produces_and_chain(self):
        expr, names, values = translate(cond("status", "nin", ["a", "b"]))
        assert "AND" in expr
        assert "(#n0 <> :v0 AND #n0 <> :v1)" == expr

    def test_nin_multi_value(self):
        expr, names, values = translate(cond("x", "nin", [10, 20, 30]))
        assert expr == "(#n0 <> :v0 AND #n0 <> :v1 AND #n0 <> :v2)"
        assert values == {":v0": 10, ":v1": 20, ":v2": 30}


# ---------------------------------------------------------------------------
# exists does not add to attr_values
# ---------------------------------------------------------------------------

class TestExistsNoValue:
    def test_exists_true_no_value_alias(self):
        _, _, values = translate(cond("field", "exists", True))
        assert values == {}

    def test_exists_false_no_value_alias(self):
        _, _, values = translate(cond("field", "exists", False))
        assert values == {}


# ---------------------------------------------------------------------------
# and-node
# ---------------------------------------------------------------------------

class TestAndNode:
    def test_single_condition_unwraps(self):
        node = {"type": "and", "conditions": [cond("x", "eq", 1)]}
        expr, names, values = translate(node)
        assert expr == "#n0 = :v0"
        assert names == {"#n0": "x"}
        assert values == {":v0": 1}

    def test_two_conditions_produces_and(self):
        node = {
            "type": "and",
            "conditions": [cond("x", "eq", 1), cond("y", "gt", 0)],
        }
        expr, names, values = translate(node)
        assert expr == "(#n0 = :v0) AND (#n1 > :v1)"
        assert names == {"#n0": "x", "#n1": "y"}
        assert values == {":v0": 1, ":v1": 0}

    def test_empty_conditions_returns_none(self):
        node = {"type": "and", "conditions": []}
        assert translate(node) == (None, {}, {})


# ---------------------------------------------------------------------------
# or-node
# ---------------------------------------------------------------------------

class TestOrNode:
    def test_single_condition_unwraps(self):
        node = {"type": "or", "conditions": [cond("x", "eq", 1)]}
        expr, names, values = translate(node)
        assert expr == "#n0 = :v0"

    def test_two_conditions_produces_or(self):
        node = {
            "type": "or",
            "conditions": [cond("a", "lt", 5), cond("b", "gte", 10)],
        }
        expr, names, values = translate(node)
        assert expr == "(#n0 < :v0) OR (#n1 >= :v1)"
        assert names == {"#n0": "a", "#n1": "b"}
        assert values == {":v0": 5, ":v1": 10}

    def test_empty_conditions_returns_none(self):
        node = {"type": "or", "conditions": []}
        assert translate(node) == (None, {}, {})


# ---------------------------------------------------------------------------
# not-node
# ---------------------------------------------------------------------------

class TestNotNode:
    def test_not_wraps_with_not(self):
        node = {"type": "not", "condition": cond("active", "eq", True)}
        expr, names, values = translate(node)
        assert expr == "NOT (#n0 = :v0)"
        assert names == {"#n0": "active"}
        assert values == {":v0": True}

    def test_not_with_and_inner(self):
        inner = {
            "type": "and",
            "conditions": [cond("x", "gt", 0), cond("y", "lt", 10)],
        }
        node = {"type": "not", "condition": inner}
        expr, _, _ = translate(node)
        assert expr == "NOT ((#n0 > :v0) AND (#n1 < :v1))"


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
    def test_distinct_field_and_value_aliases(self):
        """A compound filter over three distinct fields must use #n0/#n1/#n2
        and :v0/:v1/:v2 with no collisions."""
        node = {
            "type": "and",
            "conditions": [
                cond("alpha", "eq", 1),
                cond("beta", "gt", 2),
                cond("gamma", "lte", 3),
            ],
        }
        expr, names, values = translate(node)
        # Three distinct field aliases
        assert set(names.keys()) == {"#n0", "#n1", "#n2"}
        assert names["#n0"] == "alpha"
        assert names["#n1"] == "beta"
        assert names["#n2"] == "gamma"
        # Three distinct value aliases
        assert set(values.keys()) == {":v0", ":v1", ":v2"}
        assert values[":v0"] == 1
        assert values[":v1"] == 2
        assert values[":v2"] == 3
        assert expr == "(#n0 = :v0) AND (#n1 > :v1) AND (#n2 <= :v2)"

    def test_in_then_eq_no_collision(self):
        """in_ expands multiple :vX aliases; a subsequent field must continue
        from the correct counter, not restart at :v0."""
        node = {
            "type": "and",
            "conditions": [
                cond("status", "in", ["a", "b"]),
                cond("age", "gt", 18),
            ],
        }
        expr, names, values = translate(node)
        # status → #n0, age → #n1
        assert names["#n0"] == "status"
        assert names["#n1"] == "age"
        # :v0 and :v1 consumed by in_, :v2 used for age
        assert values[":v0"] == "a"
        assert values[":v1"] == "b"
        assert values[":v2"] == 18
        assert "(#n0 = :v0 OR #n0 = :v1)" in expr
        assert "#n1 > :v2" in expr
