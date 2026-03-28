"""
cassandra_collection.py — Cassandra Collection implementation.

Storage layout
--------------
Each pynosqlc collection maps to one Cassandra table:

    CREATE TABLE IF NOT EXISTS <name> (
        pk   TEXT PRIMARY KEY,
        data TEXT
    )

Documents are stored as JSON in the ``data`` column.  Filtering is
performed in-process using :class:`MemoryFilterEvaluator` after a full
table scan — appropriate for test/dev workloads.

All session.execute() calls are dispatched via run_in_executor so they
don't block the asyncio event loop.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING

from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.memory.memory_filter_evaluator import MemoryFilterEvaluator

if TYPE_CHECKING:
    from cassandra.cluster import Session

    from pynosqlc.core.client import Client


class CassandraCollection(Collection):
    """Collection backed by a Cassandra table (pk TEXT, data TEXT).

    Args:
        client: the owning :class:`CassandraClient`
        name: collection name (used as the CQL table name)
        session: the shared cassandra-driver ``Session``
    """

    def __init__(self, client: "Client", name: str, session: "Session") -> None:
        super().__init__(client, name)
        self._session = session
        self._table_ready: bool = False

    # ── Table bootstrap ────────────────────────────────────────────────────

    async def _ensure_table(self) -> None:
        """Create the backing table if it does not yet exist."""
        if self._table_ready:
            return
        loop = asyncio.get_event_loop()
        cql = (
            f"CREATE TABLE IF NOT EXISTS {self._name} ("
            f"pk TEXT PRIMARY KEY, data TEXT)"
        )
        await loop.run_in_executor(None, self._session.execute, cql)
        self._table_ready = True

    # ── Abstract implementation hooks ──────────────────────────────────────

    async def _get(self, key: str) -> dict | None:
        await self._ensure_table()
        loop = asyncio.get_event_loop()
        cql = f"SELECT data FROM {self._name} WHERE pk = %s"
        rows = await loop.run_in_executor(None, self._session.execute, cql, (key,))
        row = rows.one()
        return json.loads(row["data"]) if row is not None else None

    async def _store(self, key: str, doc: dict) -> None:
        await self._ensure_table()
        loop = asyncio.get_event_loop()
        cql = f"INSERT INTO {self._name} (pk, data) VALUES (%s, %s)"
        await loop.run_in_executor(
            None, self._session.execute, cql, (key, json.dumps(doc))
        )

    async def _delete(self, key: str) -> None:
        await self._ensure_table()
        loop = asyncio.get_event_loop()
        cql = f"DELETE FROM {self._name} WHERE pk = %s"
        await loop.run_in_executor(None, self._session.execute, cql, (key,))

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
        await self._ensure_table()
        loop = asyncio.get_event_loop()
        cql = f"SELECT pk, data FROM {self._name}"
        rows = await loop.run_in_executor(None, self._session.execute, cql)

        results = []
        for row in rows:
            doc = json.loads(row["data"])
            if MemoryFilterEvaluator.matches(doc, ast):
                results.append(doc)

        return Cursor(results)
