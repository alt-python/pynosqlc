"""
filter.py — Chainable query filter builder and field-level condition.

Usage::

    ast = Filter.where('age').gt(18).and_('name').eq('Alice').build()
    # → {'type': 'and', 'conditions': [
    #       {'type': 'condition', 'field': 'age',  'op': 'gt', 'value': 18},
    #       {'type': 'condition', 'field': 'name', 'op': 'eq', 'value': 'Alice'},
    #   ]}

Compound operators::

    Filter.or_(filter1.build(), filter2.build())
    # → {'type': 'or', 'conditions': [ast1, ast2]}

    Filter.where('status').eq('inactive').not_()
    # → {'type': 'not', 'condition': {'type': 'condition', ...}}

AST node shapes
---------------
Leaf  : ``{'type': 'condition', 'field': str, 'op': str, 'value': Any}``
And   : ``{'type': 'and',  'conditions': list[node]}``
Or    : ``{'type': 'or',   'conditions': list[node]}``
Not   : ``{'type': 'not',  'condition': node}``

Python keyword avoidance (PEP 8 trailing underscore)
-----------------------------------------------------
``and()`` → ``and_()``
``or()``  → ``or_()``  (classmethod)
``not()`` → ``not_()``
FieldCondition: ``in()`` → ``in_()``
"""

from __future__ import annotations

from typing import Any


class FieldCondition:
    """Represents a field-level condition within a :class:`Filter`.

    Created by :meth:`Filter.where` or :meth:`Filter.and_`.
    Operator methods add the condition to the owning Filter and return
    the Filter for further chaining.

    Supported operators: eq, ne, gt, gte, lt, lte, contains, in_, nin, exists
    """

    def __init__(self, field: str, filter_: "Filter") -> None:
        self._field = field
        self._filter = filter_

    def eq(self, value: Any) -> "Filter":
        """Equal: ``field == value``"""
        return self._add("eq", value)

    def ne(self, value: Any) -> "Filter":
        """Not equal: ``field != value``"""
        return self._add("ne", value)

    def gt(self, value: Any) -> "Filter":
        """Greater than: ``field > value``"""
        return self._add("gt", value)

    def gte(self, value: Any) -> "Filter":
        """Greater than or equal: ``field >= value``"""
        return self._add("gte", value)

    def lt(self, value: Any) -> "Filter":
        """Less than: ``field < value``"""
        return self._add("lt", value)

    def lte(self, value: Any) -> "Filter":
        """Less than or equal: ``field <= value``"""
        return self._add("lte", value)

    def contains(self, value: Any) -> "Filter":
        """Contains: field is a string/list that contains *value*."""
        return self._add("contains", value)

    def in_(self, values: list) -> "Filter":
        """In: ``field`` is one of *values*."""
        return self._add("in", values)

    def nin(self, values: list) -> "Filter":
        """Not in: ``field`` is not one of *values*."""
        return self._add("nin", values)

    def exists(self, value: bool = True) -> "Filter":
        """Exists: field is present (True) or absent/None (False)."""
        return self._add("exists", value)

    # ── Internal ────────────────────────────────────────────────────────────

    def _add(self, op: str, value: Any) -> "Filter":
        self._filter._add_condition(
            {"type": "condition", "field": self._field, "op": op, "value": value}
        )
        return self._filter


class Filter:
    """Chainable query filter builder.

    Build a filter using the fluent API, then call :meth:`build` to produce
    the AST dict passed to :meth:`~pynosqlc.core.Collection.find`.
    """

    def __init__(self) -> None:
        self._conditions: list[dict] = []

    @classmethod
    def where(cls, field: str) -> FieldCondition:
        """Start a new filter on *field*.

        Returns:
            A :class:`FieldCondition` whose operator methods return the
            owning :class:`Filter` for further chaining.
        """
        f = cls()
        return FieldCondition(field, f)

    @classmethod
    def or_(cls, *filters: "dict | Filter") -> dict:
        """Create an OR compound of two or more AST nodes or Filter instances.

        Each argument may be a built AST dict (result of ``filter.build()``)
        or a :class:`Filter` instance (``build()`` is called automatically).

        Returns:
            ``{'type': 'or', 'conditions': [...]}``
        """
        conditions = [f.build() if isinstance(f, Filter) else f for f in filters]
        return {"type": "or", "conditions": conditions}

    def and_(self, field: str) -> FieldCondition:
        """Chain an additional AND condition on a new *field*.

        Returns:
            A :class:`FieldCondition` whose operator methods return this
            :class:`Filter` for further chaining.
        """
        return FieldCondition(field, self)

    def not_(self) -> dict:
        """Negate this filter.

        Calls :meth:`build` internally and wraps the result in a not node.

        Returns:
            ``{'type': 'not', 'condition': <ast>}``
        """
        return {"type": "not", "condition": self.build()}

    def build(self) -> dict:
        """Build and return the filter AST.

        - Zero conditions → ``{'type': 'and', 'conditions': []}``
        - Single condition → the leaf node directly
        - Multiple conditions → ``{'type': 'and', 'conditions': [...]}``

        Each call returns a fresh copy — mutating the result does not affect
        the Filter.
        """
        if not self._conditions:
            return {"type": "and", "conditions": []}
        if len(self._conditions) == 1:
            return dict(self._conditions[0])
        return {"type": "and", "conditions": [dict(c) for c in self._conditions]}

    # ── Internal ────────────────────────────────────────────────────────────

    def _add_condition(self, node: dict) -> None:
        """Append a condition node (called by FieldCondition)."""
        self._conditions.append(node)
