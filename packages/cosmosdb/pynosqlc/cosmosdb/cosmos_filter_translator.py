"""
cosmos_filter_translator.py — Translates a pynosqlc Filter AST to a Cosmos DB
SQL WHERE clause with positional ``@vN`` parameters.

Returns
-------
tuple[str | None, list[dict]]
    ``(where_clause, parameters)``

    * ``where_clause`` is the SQL fragment to embed after ``WHERE``, or
      ``None`` when the AST matches everything.
    * ``parameters`` is the list of ``{"name": "@vN", "value": <val>}`` dicts
      that ``container.query_items(query=..., parameters=...)`` expects.

Design
------
A fresh ``_TranslatorState`` is created for each ``translate()`` call.  The
state carries a single monotonically-increasing ``idx`` counter used for both
the ``@vN`` parameter names.  Field paths are inlined directly into the SQL
string using bracket notation (``c["fieldname"]``) so no separate name-alias
dict is needed.

Bracket notation avoids Cosmos DB reserved-word conflicts and handles field
names with spaces or special characters.

Supported operators
-------------------
eq, ne, gt, gte, lt, lte, contains, in, nin, exists

Composite node types
--------------------
and, or, not
"""

from __future__ import annotations

from typing import Any


class CosmosFilterTranslator:
    """Stateless translator from pynosqlc Filter AST to Cosmos DB SQL pair."""

    @staticmethod
    def translate(
        ast: dict | None,
    ) -> tuple[str | None, list[dict]]:
        """Translate a Filter AST node to a Cosmos DB SQL (clause, params) pair.

        Args:
            ast: a Filter AST node, or ``None`` / empty dict (matches all).

        Returns:
            A tuple of ``(where_clause, parameters)``.  When the AST is falsy
            or has no conditions, returns ``(None, [])``.

        Raises:
            ValueError: if an unknown AST node type or operator is encountered.
        """
        if not ast:
            return (None, [])

        # An 'and' / 'or' node with an empty conditions list also means "match all"
        if ast.get("type") in ("and", "or") and not ast.get("conditions"):
            return (None, [])

        state = _TranslatorState()
        expr = state._node(ast)
        if expr is None:
            return (None, [])
        return (expr, state.parameters)


# ---------------------------------------------------------------------------
# Internal stateful translator
# ---------------------------------------------------------------------------


class _TranslatorState:
    """Carries mutable translation state for a single translate() call."""

    def __init__(self) -> None:
        self.idx: int = 0
        self.parameters: list[dict] = []

    # ── Counter helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _field_path(field: str) -> str:
        """Return the Cosmos SQL bracket-notation path for *field*."""
        return f'c["{field}"]'

    def _value_alias(self, value: Any) -> str:
        """Allocate the next @vN alias, record in parameters, and return alias."""
        alias = f"@v{self.idx}"
        self.parameters.append({"name": alias, "value": value})
        self.idx += 1
        return alias

    # ── Node dispatcher ──────────────────────────────────────────────────────

    def _node(self, ast: dict) -> str | None:
        """Recursively translate an AST node to a SQL expression string."""
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

        fp = self._field_path(field)

        if op == "eq":
            va = self._value_alias(value)
            return f'{fp} = {va}'

        if op == "ne":
            va = self._value_alias(value)
            return f'{fp} != {va}'

        if op == "gt":
            va = self._value_alias(value)
            return f'{fp} > {va}'

        if op == "gte":
            va = self._value_alias(value)
            return f'{fp} >= {va}'

        if op == "lt":
            va = self._value_alias(value)
            return f'{fp} < {va}'

        if op == "lte":
            va = self._value_alias(value)
            return f'{fp} <= {va}'

        if op == "contains":
            va = self._value_alias(value)
            return f'ARRAY_CONTAINS({fp}, {va})'

        if op == "exists":
            # exists adds no parameter entry
            if value:
                return f'IS_DEFINED({fp})'
            else:
                return f'NOT IS_DEFINED({fp})'

        if op == "in":
            values = value or []
            if not values:
                return "1=0"
            aliases = [self._value_alias(v) for v in values]
            alias_list = ", ".join(aliases)
            return f'{fp} IN ({alias_list})'

        if op == "nin":
            values = value or []
            if not values:
                return "1=1"
            aliases = [self._value_alias(v) for v in values]
            alias_list = ", ".join(aliases)
            return f'NOT ({fp} IN ({alias_list}))'

        raise ValueError(f"Unknown filter operator: {op!r}")
