"""
memory_collection.py — In-memory Collection implementation.

Backed by a plain dict shared with MemoryClient._stores.
All operations are synchronous internally but wrapped in async for interface
compatibility.

insert() generates a UUID4 key and stores it as ``_id`` inside the document.
update() shallow-merges the patch into the existing document.
find() applies the Filter AST via MemoryFilterEvaluator.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.memory.memory_filter_evaluator import MemoryFilterEvaluator

if TYPE_CHECKING:
    from pynosqlc.core.client import Client


class MemoryCollection(Collection):
    """Collection backed by a single dict shared with :class:`MemoryClient`.

    Args:
        client: the owning :class:`MemoryClient`
        name: collection name
        data: dict reference shared with the client's ``_stores`` registry
    """

    def __init__(self, client: "Client", name: str, data: dict) -> None:
        super().__init__(client, name)
        # Named _data (not _store) to avoid shadowing the abstract _store() method.
        self._data: dict[str, dict] = data

    async def _get(self, key: str) -> dict | None:
        doc = self._data.get(key)
        return dict(doc) if doc is not None else None

    async def _store(self, key: str, doc: dict) -> None:
        self._data[key] = dict(doc)

    async def _delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def _insert(self, doc: dict) -> str:
        key = str(uuid.uuid4())
        self._data[key] = {**doc, "_id": key}
        return key

    async def _update(self, key: str, patch: dict) -> None:
        existing = self._data.get(key)
        if existing is None:
            raise KeyError(f"Document not found for key: {key!r}")
        self._data[key] = {**existing, **patch}

    async def _find(self, ast: dict) -> Cursor:
        results = [
            dict(doc)
            for doc in self._data.values()
            if MemoryFilterEvaluator.matches(doc, ast)
        ]
        return Cursor(results)
