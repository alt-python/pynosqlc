"""
mongo_client.py — MongoClient: a pynosqlc Client backed by pymongo AsyncMongoClient.
"""

from __future__ import annotations

from pynosqlc.core.client import Client
from pynosqlc.mongodb.mongo_collection import MongoCollection


class MongoClient(Client):
    """A pynosqlc Client backed by a pymongo :class:`~pymongo.AsyncMongoClient`.

    Args:
        url: the original ``pynosqlc:mongodb://`` URL.
        native_client: the underlying pymongo ``AsyncMongoClient``.
        db: the pymongo ``AsyncDatabase`` to use.
    """

    def __init__(self, url: str, native_client, db) -> None:
        super().__init__({"url": url})
        self._native_client = native_client
        self._db = db

    def _get_collection(self, name: str) -> MongoCollection:
        """Create and return a :class:`MongoCollection` for *name*."""
        return MongoCollection(self, name, self._db[name])

    async def _close(self) -> None:
        """Close the underlying pymongo client."""
        await self._native_client.close()
