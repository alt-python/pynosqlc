"""
cosmos_client.py — CosmosClient: a pynosqlc Client backed by azure-cosmos aio.
"""

from __future__ import annotations

from typing import Any

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient as NativeCosmosClient

from pynosqlc.core.client import Client
from pynosqlc.cosmosdb.cosmos_collection import CosmosCollection


class CosmosClient(Client):
    """A pynosqlc Client backed by :class:`azure.cosmos.aio.CosmosClient`.

    Args:
        url: the original ``pynosqlc:cosmosdb:<target>`` URL.
        endpoint: the Cosmos DB endpoint URL.
        key: the Cosmos DB account key.
        db_id: the database name to use (created if it does not exist).
        client_kwargs: extra keyword arguments forwarded to
            :class:`azure.cosmos.aio.CosmosClient`.
    """

    def __init__(
        self,
        url: str,
        endpoint: str,
        key: str,
        db_id: str,
        client_kwargs: dict | None = None,
    ) -> None:
        super().__init__({"url": url})
        self._endpoint = endpoint
        self._key = key
        self._db_id = db_id
        self._client_kwargs: dict = client_kwargs or {}
        self._native_ctx: NativeCosmosClient | None = None
        self._database: Any = None
        self._container_cache: dict[str, Any] = {}

    async def _open(self) -> None:
        """Open the native Cosmos DB client and resolve the target database.

        Must be called by the driver after constructing this client.
        """
        self._native_ctx = NativeCosmosClient(
            url=self._endpoint,
            credential=self._key,
            **self._client_kwargs,
        )
        await self._native_ctx.__aenter__()
        self._database = await self._native_ctx.create_database_if_not_exists(
            id=self._db_id
        )

    async def _close(self) -> None:
        """Exit the native Cosmos DB client context manager."""
        if self._native_ctx is not None:
            await self._native_ctx.__aexit__(None, None, None)
            self._native_ctx = None
            self._database = None
            self._container_cache.clear()

    def _get_collection(self, name: str) -> CosmosCollection:
        """Create and return a :class:`CosmosCollection` for *name*."""
        return CosmosCollection(self, name)

    async def ensure_container(self, name: str) -> Any:
        """Return a Cosmos DB container proxy for *name*, creating it if needed.

        Uses ``/id`` as the partition key path.  The container proxy is cached
        after the first successful call so the SDK round-trip is only paid once
        per container name per client lifetime.

        Args:
            name: the container (collection) name.

        Returns:
            The :class:`azure.cosmos.aio.ContainerProxy` for the container.
        """
        if name in self._container_cache:
            return self._container_cache[name]

        container = await self._database.create_container_if_not_exists(
            id=name,
            # PartitionKey must come from azure.cosmos (sync), not azure.cosmos.aio
            partition_key=PartitionKey(path="/id"),
        )
        self._container_cache[name] = container
        return container
