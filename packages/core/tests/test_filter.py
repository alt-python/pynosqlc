"""
test_filter.py — Unit tests for Filter builder and FieldCondition.

Ports filter.spec.js describe blocks:
  - single conditions (all 12 operators)
  - compound and
  - isolation (no shared state, build() returns copy)
  - empty filter
  - or_ compound
  - not_
"""

import pytest
from pynosqlc.core.filter import Filter, FieldCondition


# ── Helpers ────────────────────────────────────────────────────────────────

def leaf(field, op, value):
    return {"type": "condition", "field": field, "op": op, "value": value}


# ── Single conditions ──────────────────────────────────────────────────────

class TestSingleConditions:
    def test_eq_builds_correct_leaf(self):
        ast = Filter.where("name").eq("Alice").build()
        assert ast == leaf("name", "eq", "Alice")

    def test_ne_builds_correct_leaf(self):
        ast = Filter.where("status").ne("inactive").build()
        assert ast == leaf("status", "ne", "inactive")

    def test_gt_builds_correct_leaf(self):
        ast = Filter.where("age").gt(18).build()
        assert ast == leaf("age", "gt", 18)

    def test_gte_builds_correct_leaf(self):
        ast = Filter.where("score").gte(100).build()
        assert ast == leaf("score", "gte", 100)

    def test_lt_builds_correct_leaf(self):
        ast = Filter.where("price").lt(50).build()
        assert ast == leaf("price", "lt", 50)

    def test_lte_builds_correct_leaf(self):
        ast = Filter.where("rating").lte(5).build()
        assert ast == leaf("rating", "lte", 5)

    def test_contains_builds_correct_leaf(self):
        ast = Filter.where("tags").contains("js").build()
        assert ast == leaf("tags", "contains", "js")

    def test_in_builds_correct_leaf(self):
        ast = Filter.where("status").in_(["active", "pending"]).build()
        assert ast == leaf("status", "in", ["active", "pending"])

    def test_nin_builds_correct_leaf(self):
        ast = Filter.where("status").nin(["deleted", "banned"]).build()
        assert ast == leaf("status", "nin", ["deleted", "banned"])

    def test_exists_true_builds_correct_leaf(self):
        ast = Filter.where("email").exists(True).build()
        assert ast == leaf("email", "exists", True)

    def test_exists_false_builds_correct_leaf(self):
        ast = Filter.where("deletedAt").exists(False).build()
        assert ast == leaf("deletedAt", "exists", False)

    def test_exists_defaults_to_true(self):
        ast = Filter.where("email").exists().build()
        assert ast == leaf("email", "exists", True)


# ── Compound conditions ────────────────────────────────────────────────────

class TestCompoundConditions:
    def test_two_conditions_wrap_in_and(self):
        ast = Filter.where("age").gt(18).and_("name").eq("Alice").build()
        assert ast == {
            "type": "and",
            "conditions": [
                leaf("age", "gt", 18),
                leaf("name", "eq", "Alice"),
            ],
        }

    def test_three_conditions_wrap_in_and(self):
        ast = (
            Filter.where("age").gt(18)
            .and_("status").eq("active")
            .and_("country").eq("AU")
            .build()
        )
        assert ast == {
            "type": "and",
            "conditions": [
                leaf("age", "gt", 18),
                leaf("status", "eq", "active"),
                leaf("country", "eq", "AU"),
            ],
        }

    def test_mixed_operators_compound_correctly(self):
        ast = (
            Filter.where("price").lt(100)
            .and_("tags").contains("sale")
            .and_("stock").gte(1)
            .build()
        )
        assert ast["type"] == "and"
        assert len(ast["conditions"]) == 3
        assert ast["conditions"][1]["op"] == "contains"


# ── Isolation ──────────────────────────────────────────────────────────────

class TestIsolation:
    def test_two_separate_where_calls_do_not_share_state(self):
        f1 = Filter.where("a").eq(1)
        f2 = Filter.where("b").eq(2)
        assert f1.build() == leaf("a", "eq", 1)
        assert f2.build() == leaf("b", "eq", 2)

    def test_build_returns_copy_not_reference(self):
        f = Filter.where("x").eq(42)
        ast1 = f.build()
        ast2 = f.build()
        ast1["value"] = 999
        assert ast2["value"] == 42


# ── Empty filter ───────────────────────────────────────────────────────────

class TestEmptyFilter:
    def test_new_filter_instance_gives_empty_and_node(self):
        f = Filter()
        assert f.build() == {"type": "and", "conditions": []}


# ── Or compound ───────────────────────────────────────────────────────────

class TestOrCompound:
    def test_or_with_two_ast_nodes_wraps_in_or(self):
        ast1 = Filter.where("status").eq("active").build()
        ast2 = Filter.where("status").eq("pending").build()
        result = Filter.or_(ast1, ast2)
        assert result == {
            "type": "or",
            "conditions": [
                leaf("status", "eq", "active"),
                leaf("status", "eq", "pending"),
            ],
        }

    def test_or_accepts_filter_instances_and_calls_build_automatically(self):
        f1 = Filter.where("a").eq(1)
        f2 = Filter.where("b").eq(2)
        result = Filter.or_(f1, f2)
        assert result["type"] == "or"
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["field"] == "a"
        assert result["conditions"][1]["field"] == "b"

    def test_or_with_three_conditions(self):
        result = Filter.or_(
            Filter.where("x").eq(1).build(),
            Filter.where("x").eq(2).build(),
            Filter.where("x").eq(3).build(),
        )
        assert result["type"] == "or"
        assert len(result["conditions"]) == 3


# ── Not ────────────────────────────────────────────────────────────────────

class TestNot:
    def test_not_wraps_build_in_not_node(self):
        result = Filter.where("status").eq("inactive").not_()
        assert result == {
            "type": "not",
            "condition": leaf("status", "eq", "inactive"),
        }

    def test_compound_filter_not(self):
        result = Filter.where("age").lt(18).and_("status").ne("active").not_()
        assert result["type"] == "not"
        assert result["condition"]["type"] == "and"
        assert len(result["condition"]["conditions"]) == 2
