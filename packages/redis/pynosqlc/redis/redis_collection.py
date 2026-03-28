"""
redis_collection.py — Redis Collection implementation.

Storage layout
--------------
Document key : ``pynosqlc:<collection>:<doc_key>``  → JSON string
Index key    : ``pynosqlc:<collection>:_keys``       → Redis Set of all doc keys

All documents are stored as JSON strings.  Filtering is performed in-process
using :class:`MemoryFilterEvaluator` after fetching all keys from the index Set.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.memory.memory_filter_evaluator import MemoryFilterEvaluator

if TYPE_CHECKING:
    import redis.asyncio as aioredis

    from pynosqlc.core.client import Client


class RedisCollection(Collection):
    """Collection backed by Redis strings (JSON) and a Set index.

    Args:
        client: the owning :class:`RedisClient`
        name: collection name
        r: the shared ``redis.asyncio`` connection
    """

    def __init__(self, client: "Client", name: str, r: "aioredis.Redis") -> None:
        super().__init__(client, name)
        self._r = r

    # ── Key helpers ────────────────────────────────────────────────────────

    def _prefix(self, key: str) -> str:
        """Return the Redis key for *doc_key* in this collection."""
        return f"pynosqlc:{self._name}:{key}"

    @property
    def _index_key(self) -> str:
        """Redis Set key that holds all doc keys in this collection."""
        return f"pynosqlc:{self._name}:_keys"

    # ── Abstract implementation hooks ──────────────────────────────────────

    async def _get(self, key: str) -> dict | None:
        raw = await self._r.get(self._prefix(key))
        return json.loads(raw) if raw is not None else None

    async def _store(self, key: str, doc: dict) -> None:
        await self._r.set(self._prefix(key), json.dumps(doc))
        await self._r.sadd(self._index_key, key)

    async def _delete(self, key: str) -> None:
        await self._r.delete(self._prefix(key))
        await self._r.srem(self._index_key, key)

    async def _insert(self, doc: dict) -> str:
        key = str(uuid.uuid4())
        await self._store(key, {**doc, "_id": key})
        return key

    async def _update(self, key: str, patch: dict) -> None:
        existing = await self._get(key)
        if existing is None:
            raise KeyError(f"Document not found for key: {key!r}")
        await self._store(key, {**existing, **patch})

    async def _find(self, ast: dict) -> Cursor:
        keys = await self._r.smembers(self._index_key)
        if not keys:
            return Cursor([])

        # Fetch all documents in a single pipeline round-trip.
        async with self._r.pipeline(transaction=False) as pipe:
            for k in keys:
                pipe.get(self._prefix(k))
            raw_docs = await pipe.execute()

        results = []
        for raw in raw_docs:
            if raw is None:
                continue
            doc = json.loads(raw)
            if MemoryFilterEvaluator.matches(doc, ast):
                results.append(doc)

        return Cursor(results)
