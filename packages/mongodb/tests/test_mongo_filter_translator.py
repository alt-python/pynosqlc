"""
Unit tests for MongoFilterTranslator.

Covers:
- All 10 operators: eq, ne, gt, gte, lt, lte, contains, in, nin, exists
- 'id' field maps to '_id'
- and-node with 1 condition unwraps to the inner filter
- and-node with 2 conditions → {$and: [...]}
- or-node with 1 condition unwraps
- or-node with 2 conditions → {$or: [...]}
- not-node → {$nor: [inner]}
- None ast → {}
- empty dict ast → {}
- unknown op raises ValueError
- unknown node type raises ValueError
"""

import pytest

from pynosqlc.mongodb.mongo_filter_translator import MongoFilterTranslator

translate = MongoFilterTranslator.translate


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
    def test_none_returns_empty(self):
        assert translate(None) == {}

    def test_empty_dict_returns_empty(self):
        assert translate({}) == {}


# ---------------------------------------------------------------------------
# All 10 operators on a regular field
# ---------------------------------------------------------------------------

class TestOperators:
    def test_eq(self):
        result = translate(cond("name", "eq", "Alice"))
        assert result == {"name": {"$eq": "Alice"}}

    def test_ne(self):
        result = translate(cond("status", "ne", "inactive"))
        assert result == {"status": {"$ne": "inactive"}}

    def test_gt(self):
        result = translate(cond("age", "gt", 18))
        assert result == {"age": {"$gt": 18}}

    def test_gte(self):
        result = translate(cond("score", "gte", 90))
        assert result == {"score": {"$gte": 90}}

    def test_lt(self):
        result = translate(cond("price", "lt", 100))
        assert result == {"price": {"$lt": 100}}

    def test_lte(self):
        result = translate(cond("rank", "lte", 5))
        assert result == {"rank": {"$lte": 5}}

    def test_contains(self):
        result = translate(cond("tags", "contains", "python"))
        assert result == {"tags": "python"}

    def test_in(self):
        result = translate(cond("category", "in", ["a", "b", "c"]))
        assert result == {"category": {"$in": ["a", "b", "c"]}}

    def test_nin(self):
        result = translate(cond("role", "nin", ["admin", "root"]))
        assert result == {"role": {"$nin": ["admin", "root"]}}

    def test_exists_true(self):
        result = translate(cond("email", "exists", True))
        assert result == {"email": {"$exists": True}}

    def test_exists_false(self):
        result = translate(cond("deleted_at", "exists", False))
        assert result == {"deleted_at": {"$exists": False}}


# ---------------------------------------------------------------------------
# 'id' field maps to '_id'
# ---------------------------------------------------------------------------

class TestIdMapping:
    def test_id_maps_to_underscore_id(self):
        result = translate(cond("id", "eq", "abc123"))
        assert result == {"_id": {"$eq": "abc123"}}

    def test_id_ne(self):
        result = translate(cond("id", "ne", "xyz"))
        assert result == {"_id": {"$ne": "xyz"}}

    def test_other_id_field_not_mapped(self):
        # Fields that merely contain 'id' as a substring should NOT be remapped
        result = translate(cond("user_id", "eq", 1))
        assert result == {"user_id": {"$eq": 1}}


# ---------------------------------------------------------------------------
# and-node
# ---------------------------------------------------------------------------

class TestAndNode:
    def test_single_condition_unwraps(self):
        node = {"type": "and", "conditions": [cond("x", "eq", 1)]}
        result = translate(node)
        assert result == {"x": {"$eq": 1}}

    def test_two_conditions_produces_and_list(self):
        node = {
            "type": "and",
            "conditions": [cond("x", "eq", 1), cond("y", "gt", 0)],
        }
        result = translate(node)
        assert result == {"$and": [{"x": {"$eq": 1}}, {"y": {"$gt": 0}}]}

    def test_empty_conditions_returns_empty(self):
        node = {"type": "and", "conditions": []}
        assert translate(node) == {}

    def test_missing_conditions_key_returns_empty(self):
        node = {"type": "and"}
        assert translate(node) == {}


# ---------------------------------------------------------------------------
# or-node
# ---------------------------------------------------------------------------

class TestOrNode:
    def test_single_condition_unwraps(self):
        node = {"type": "or", "conditions": [cond("x", "eq", 1)]}
        result = translate(node)
        assert result == {"x": {"$eq": 1}}

    def test_two_conditions_produces_or_list(self):
        node = {
            "type": "or",
            "conditions": [cond("a", "lt", 5), cond("b", "gte", 10)],
        }
        result = translate(node)
        assert result == {"$or": [{"a": {"$lt": 5}}, {"b": {"$gte": 10}}]}

    def test_empty_conditions_returns_empty(self):
        node = {"type": "or", "conditions": []}
        assert translate(node) == {}


# ---------------------------------------------------------------------------
# not-node
# ---------------------------------------------------------------------------

class TestNotNode:
    def test_not_wraps_in_nor(self):
        node = {"type": "not", "condition": cond("active", "eq", False)}
        result = translate(node)
        assert result == {"$nor": [{"active": {"$eq": False}}]}

    def test_not_with_and_inner(self):
        inner = {
            "type": "and",
            "conditions": [cond("x", "gt", 0), cond("y", "lt", 10)],
        }
        node = {"type": "not", "condition": inner}
        result = translate(node)
        assert result == {"$nor": [{"$and": [{"x": {"$gt": 0}}, {"y": {"$lt": 10}}]}]}


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
