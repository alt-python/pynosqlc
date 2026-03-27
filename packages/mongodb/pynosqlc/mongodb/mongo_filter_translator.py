"""
mongo_filter_translator.py — Translates a pynosqlc Filter AST to a MongoDB filter dict.

Handles all four AST node types:
  Leaf:  { type: 'condition', field, op, value }
  And:   { type: 'and',  conditions: [...] }
  Or:    { type: 'or',   conditions: [...] }
  Not:   { type: 'not',  condition: ... }

Supported operators:
  eq, ne, gt, gte, lt, lte, contains, in, nin, exists

Special field mapping:
  'id' → '_id'
"""

from __future__ import annotations

from typing import Any


class MongoFilterTranslator:
    """Stateless translator from pynosqlc Filter AST to MongoDB filter dict."""

    @staticmethod
    def translate(ast: dict | None) -> dict:
        """Translate a Filter AST node to a MongoDB query filter.

        Args:
            ast: a Filter AST node, or ``None`` / empty dict (matches all).

        Returns:
            A MongoDB-compatible filter dict.

        Raises:
            ValueError: if an unknown AST node type or operator is encountered.
        """
        if not ast:
            return {}

        node_type = ast.get("type")

        if node_type == "and":
            conditions = ast.get("conditions") or []
            if not conditions:
                return {}
            parts = [MongoFilterTranslator.translate(c) for c in conditions]
            if len(parts) == 1:
                return parts[0]
            return {"$and": parts}

        if node_type == "or":
            conditions = ast.get("conditions") or []
            if not conditions:
                return {}
            parts = [MongoFilterTranslator.translate(c) for c in conditions]
            if len(parts) == 1:
                return parts[0]
            return {"$or": parts}

        if node_type == "not":
            inner = MongoFilterTranslator.translate(ast.get("condition"))
            return {"$nor": [inner]}

        if node_type == "condition":
            return MongoFilterTranslator._translate_condition(ast)

        raise ValueError(f"Unknown filter AST node type: {node_type!r}")

    @staticmethod
    def _translate_condition(node: dict) -> dict:
        """Translate a condition AST leaf to a MongoDB filter expression.

        Args:
            node: ``{ field, op, value }``

        Returns:
            A MongoDB filter dict for this condition.

        Raises:
            ValueError: if the operator is not recognised.
        """
        field: str = node["field"]
        op: str = node["op"]
        value: Any = node.get("value")

        # Special field mapping: logical 'id' → MongoDB '_id'
        if field == "id":
            field = "_id"

        if op == "eq":
            return {field: {"$eq": value}}

        if op == "ne":
            return {field: {"$ne": value}}

        if op == "gt":
            return {field: {"$gt": value}}

        if op == "gte":
            return {field: {"$gte": value}}

        if op == "lt":
            return {field: {"$lt": value}}

        if op == "lte":
            return {field: {"$lte": value}}

        if op == "contains":
            # MongoDB native array/string containment: {field: value}
            return {field: value}

        if op == "in":
            return {field: {"$in": value}}

        if op == "nin":
            return {field: {"$nin": value}}

        if op == "exists":
            return {field: {"$exists": value}}

        raise ValueError(f"Unknown filter operator: {op!r}")
