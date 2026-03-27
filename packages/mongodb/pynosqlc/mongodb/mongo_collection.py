"""
mongo_collection.py — MongoCollection: a pynosqlc Collection backed by pymongo AsyncCollection.
"""

from __future__ import annotations

import uuid

from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.mongodb.mongo_filter_translator import MongoFilterTranslator


class MongoCollection(Collection):
    """A pynosqlc Collection backed by a pymongo ``AsyncCollection``.

    Args:
        client: the owning :class:`~pynosqlc.mongodb.MongoClient`.
        name: the collection name.
        col: the underlying pymongo ``AsyncCollection``.
    """

    def __init__(self, client, name: str, col) -> None:
        super().__init__(client, name)
        self._col = col

    async def _get(self, key: str) -> dict | None:
        """Retrieve a document by ``_id``."""
        doc = await self._col.find_one({"_id": key})
        return doc if doc else None

    async def _store(self, key: str, doc: dict) -> None:
        """Upsert a document, setting ``_id = key``."""
        await self._col.replace_one({"_id": key}, {**doc, "_id": key}, upsert=True)

    async def _delete(self, key: str) -> None:
        """Delete the document with ``_id = key``."""
        await self._col.delete_one({"_id": key})

    async def _insert(self, doc: dict) -> str:
        """Insert a document with a generated UUID ``_id``; return the id."""
        id_ = str(uuid.uuid4())
        await self._col.insert_one({**doc, "_id": id_})
        return id_

    async def _update(self, key: str, patch: dict) -> None:
        """Patch the document at ``_id = key`` with ``$set``."""
        await self._col.update_one({"_id": key}, {"$set": patch})

    async def _find(self, ast: dict) -> Cursor:
        """Find documents matching the filter AST.

        Translates the AST to a MongoDB filter dict, fetches all results
        into memory, and wraps them in a :class:`~pynosqlc.core.Cursor`.
        """
        query = MongoFilterTranslator.translate(ast)
        mongo_cursor = self._col.find(query)
        docs = await mongo_cursor.to_list()
        return Cursor(docs)
