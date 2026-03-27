"""
dynamo_filter_translator.py — Translates a pynosqlc Filter AST to a DynamoDB
FilterExpression triple.

Returns
-------
tuple[str | None, dict, dict]
    (filter_expression, expression_attribute_names, expression_attribute_values)

When the AST is None or empty (no conditions), returns ``(None, {}, {})``.

Design
------
A fresh ``_TranslatorState`` is created for each ``translate()`` call.  The
state carries monotonically-increasing counters for field-name aliases
(``#n0``, ``#n1``, …) and value aliases (``:v0``, ``:v1``, …) so that
compound filters across multiple fields never produce collisions.

All field references go through ``ExpressionAttributeNames`` to avoid
DynamoDB reserved-word conflicts.

Supported operators
-------------------
eq, ne, gt, gte, lt, lte, contains, in, nin, exists

Composite node types
--------------------
and, or, not
"""

from __future__ import annotations

from typing import Any


class DynamoFilterTranslator:
    """Stateless translator from pynosqlc Filter AST to DynamoDB expression triple."""

    @staticmethod
    def translate(
        ast: dict | None,
    ) -> tuple[str | None, dict, dict]:
        """Translate a Filter AST node to a DynamoDB expression triple.

        Args:
            ast: a Filter AST node, or ``None`` / empty dict (matches all).

        Returns:
            A tuple of ``(filter_expression, expression_attribute_names,
            expression_attribute_values)``.  When the AST is falsy or has no
            conditions, returns ``(None, {}, {})``.

        Raises:
            ValueError: if an unknown AST node type or operator is encountered.
        """
        if not ast:
            return (None, {}, {})

        # An 'and' node with an empty conditions list also means "match all"
        if ast.get("type") in ("and", "or") and not ast.get("conditions"):
            return (None, {}, {})

        state = _TranslatorState()
        expr = state._node(ast)
        if expr is None:
            return (None, {}, {})
        return (expr, state.attr_names, state.attr_values)


# ---------------------------------------------------------------------------
# Internal stateful translator
# ---------------------------------------------------------------------------

class _TranslatorState:
    """Carries mutable translation state for a single translate() call."""

    def __init__(self) -> None:
        self.name_idx: int = 0
        self.value_idx: int = 0
        self.attr_names: dict[str, str] = {}
        self.attr_values: dict[str, Any] = {}

    # ── Counter helpers ──────────────────────────────────────────────────────

    def _field_alias(self, field: str) -> str:
        """Allocate the next #nX alias for *field* and record the mapping."""
        alias = f"#n{self.name_idx}"
        self.attr_names[alias] = field
        self.name_idx += 1
        return alias

    def _value_alias(self, value: Any) -> str:
        """Allocate the next :vX alias for *value* and record the mapping."""
        alias = f":v{self.value_idx}"
        self.attr_values[alias] = value
        self.value_idx += 1
        return alias

    # ── Node dispatcher ──────────────────────────────────────────────────────

    def _node(self, ast: dict) -> str | None:
        """Recursively translate an AST node to an expression string."""
        node_type = ast.get("type")

        if node_type == "and":
            return self._and_node(ast)

        if node_type == "or":
            return self._or_node(ast)

        if node_type == "not":
            return self._not_node(ast)

        if node_type == "condition":
            return self._condition(ast)

        raise ValueError(f"Unknown filter AST node type: {node_type!r}")

    # ── Composite nodes ──────────────────────────────────────────────────────

    def _and_node(self, ast: dict) -> str | None:
        conditions = ast.get("conditions") or []
        if not conditions:
            return None
        parts = [self._node(c) for c in conditions]
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        joined = " AND ".join(f"({p})" for p in parts)
        return joined

    def _or_node(self, ast: dict) -> str | None:
        conditions = ast.get("conditions") or []
        if not conditions:
            return None
        parts = [self._node(c) for c in conditions]
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        joined = " OR ".join(f"({p})" for p in parts)
        return joined

    def _not_node(self, ast: dict) -> str:
        inner = self._node(ast["condition"])
        return f"NOT ({inner})"

    # ── Leaf condition ───────────────────────────────────────────────────────

    def _condition(self, node: dict) -> str:
        field: str = node["field"]
        op: str = node["op"]
        value: Any = node.get("value")

        na = self._field_alias(field)

        if op == "eq":
            va = self._value_alias(value)
            return f"{na} = {va}"

        if op == "ne":
            va = self._value_alias(value)
            return f"{na} <> {va}"

        if op == "gt":
            va = self._value_alias(value)
            return f"{na} > {va}"

        if op == "gte":
            va = self._value_alias(value)
            return f"{na} >= {va}"

        if op == "lt":
            va = self._value_alias(value)
            return f"{na} < {va}"

        if op == "lte":
            va = self._value_alias(value)
            return f"{na} <= {va}"

        if op == "contains":
            va = self._value_alias(value)
            return f"contains({na}, {va})"

        if op == "exists":
            if value:
                return f"attribute_exists({na})"
            else:
                return f"attribute_not_exists({na})"

        if op == "in":
            # One OR clause per value; the field alias is shared
            clauses = []
            for v in value:
                va = self._value_alias(v)
                clauses.append(f"{na} = {va}")
            return "(" + " OR ".join(clauses) + ")"

        if op == "nin":
            # One AND clause per value; the field alias is shared
            clauses = []
            for v in value:
                va = self._value_alias(v)
                clauses.append(f"{na} <> {va}")
            return "(" + " AND ".join(clauses) + ")"

        raise ValueError(f"Unknown filter operator: {op!r}")
