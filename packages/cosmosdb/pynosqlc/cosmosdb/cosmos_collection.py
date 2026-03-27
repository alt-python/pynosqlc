"""
cosmos_collection.py — CosmosCollection: a pynosqlc Collection backed by a
Cosmos DB container.

The document primary key is stored as the Cosmos DB item ``id`` field.
Internal Cosmos DB metadata fields (prefixed with ``_``) are stripped from all
returned documents.
"""

from __future__ import annotations

import uuid

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.cosmosdb.cosmos_filter_translator import CosmosFilterTranslator


def _strip_internal(item: dict) -> dict:
    """Remove Cosmos DB internal metadata fields (those starting with ``_``).

    The ``id`` field is preserved — it is the user-visible document key.

    Args:
        item: a raw Cosmos DB item dict.

    Returns:
        The item with all ``_``-prefixed keys removed.
    """
    return {k: v for k, v in item.items() if not k.startswith("_")}


class CosmosCollection(Collection):
    """A pynosqlc Collection backed by a Cosmos DB container.

    The container is created on first access with ``/id`` as the partition key.
    :meth:`CosmosClient.ensure_container` is called at the start of every
    operation — it is a no-op after the first successful call.

    Args:
        client: the owning :class:`~pynosqlc.cosmosdb.CosmosClient`.
        name: the container / collection name.
    """

    def __init__(self, client, name: str) -> None:
        super().__init__(client, name)

    async def _get(self, key: str) -> dict | None:
        """Retrieve a document by its ``id``."""
        container = await self._client.ensure_container(self._name)
        try:
            item = await container.read_item(item=key, partition_key=key)
        except CosmosResourceNotFoundError:
            return None
        return _strip_internal(item)

    async def _store(self, key: str, doc: dict) -> None:
        """Upsert a document, setting ``id = key``."""
        container = await self._client.ensure_container(self._name)
        await container.upsert_item(body={**doc, "id": key})

    async def _delete(self, key: str) -> None:
        """Delete the document at ``id = key``.  Silent if not found."""
        container = await self._client.ensure_container(self._name)
        try:
            await container.delete_item(item=key, partition_key=key)
        except CosmosResourceNotFoundError:
            pass

    async def _insert(self, doc: dict) -> str:
        """Insert a document with a generated UUID ``id``; return the id."""
        container = await self._client.ensure_container(self._name)
        id_ = str(uuid.uuid4())
        await container.upsert_item(body={**doc, "id": id_})
        return id_

    async def _update(self, key: str, patch: dict) -> None:
        """Patch the document at ``id = key`` by merging *patch* into it.

        Reads the current document, merges the patch (shallow), and upserts.
        The ``id`` field is always preserved as *key*.
        """
        container = await self._client.ensure_container(self._name)
        existing = await self._get(key) or {}
        merged = {**existing, **patch, "id": key}
        await container.upsert_item(body=merged)

    async def _find(self, ast: dict) -> Cursor:
        """Find documents matching the filter AST.

        Translates the AST to a Cosmos DB SQL WHERE clause, runs the query,
        strips internal fields from each result, and wraps results in a
        :class:`~pynosqlc.core.Cursor`.
        """
        container = await self._client.ensure_container(self._name)

        where_clause, parameters = CosmosFilterTranslator.translate(ast)

        if where_clause is not None:
            sql = f"SELECT * FROM c WHERE {where_clause}"
        else:
            sql = "SELECT * FROM c"

        docs = [
            _strip_internal(item)
            async for item in container.query_items(
                query=sql,
                parameters=parameters,
            )
        ]

        return Cursor(docs)
