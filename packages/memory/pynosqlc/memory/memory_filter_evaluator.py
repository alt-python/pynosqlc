"""
memory_filter_evaluator.py — Applies a Filter AST to an in-memory document.

Handles:
  Leaf:  { type: 'condition', field, op, value }
  And:   { type: 'and', conditions: [...] }
  Or:    { type: 'or',  conditions: [...] }
  Not:   { type: 'not', condition: ... }

Supported operators: eq, ne, gt, gte, lt, lte, contains, in_, nin, exists
"""

from __future__ import annotations

from typing import Any


class MemoryFilterEvaluator:
    """Stateless filter evaluator for in-memory documents."""

    @staticmethod
    def matches(doc: dict, ast: dict | None) -> bool:
        """Test whether *doc* matches the given filter AST.

        Args:
            doc: the document to test
            ast: a Filter AST node, or ``None`` (matches all)

        Returns:
            ``True`` if the document matches.

        Raises:
            ValueError: if an unknown AST node type or operator is encountered.
        """
        if ast is None:
            return True

        node_type = ast.get("type")

        if node_type == "and":
            conditions = ast.get("conditions") or []
            if not conditions:
                return True
            return all(MemoryFilterEvaluator.matches(doc, c) for c in conditions)

        if node_type == "or":
            conditions = ast.get("conditions") or []
            if not conditions:
                return False
            return any(MemoryFilterEvaluator.matches(doc, c) for c in conditions)

        if node_type == "not":
            return not MemoryFilterEvaluator.matches(doc, ast.get("condition"))

        if node_type == "condition":
            return MemoryFilterEvaluator._eval_condition(doc, ast)

        raise ValueError(f"Unknown filter AST node type: {node_type!r}")

    @staticmethod
    def _eval_condition(doc: dict, node: dict) -> bool:
        field: str = node["field"]
        op: str = node["op"]
        value: Any = node.get("value")

        field_value = MemoryFilterEvaluator._resolve(doc, field)

        if op == "eq":
            return field_value == value

        if op == "ne":
            return field_value != value

        if op == "gt":
            return field_value is not None and field_value > value

        if op == "gte":
            return field_value is not None and field_value >= value

        if op == "lt":
            return field_value is not None and field_value < value

        if op == "lte":
            return field_value is not None and field_value <= value

        if op == "contains":
            if isinstance(field_value, (list, str)):
                return value in field_value
            return False

        if op == "in":
            if not isinstance(value, list):
                return False
            return field_value in value

        if op == "nin":
            if not isinstance(value, list):
                return True
            return field_value not in value

        if op == "exists":
            if value is False:
                return field_value is None
            return field_value is not None

        raise ValueError(f"Unknown filter operator: {op!r}")

    @staticmethod
    def _resolve(doc: dict, field: str) -> Any:
        """Resolve a (potentially dot-notation) field path from a document.

        Examples:
            ``'name'`` → ``doc['name']``
            ``'address.city'`` → ``doc['address']['city']``

        Returns ``None`` if any segment in the path is absent.
        """
        if "." not in field:
            return doc.get(field)
        obj: Any = doc
        for key in field.split("."):
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
        return obj
