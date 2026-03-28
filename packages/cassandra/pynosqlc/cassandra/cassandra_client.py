"""
cassandra_client.py — Cassandra Client implementation.

Each collection is created on demand; the parent Client base class
caches by name via get_collection().
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pynosqlc.core.client import Client
from pynosqlc.cassandra.cassandra_collection import CassandraCollection

if TYPE_CHECKING:
    from cassandra.cluster import Cluster, Session


class CassandraClient(Client):
    """Client backed by a cassandra-driver synchronous session.

    Args:
        url: the pynosqlc URL used to open this connection
        cluster: the connected ``Cluster`` instance (for shutdown)
        session: the connected ``Session`` instance
        keyspace: the active Cassandra keyspace
    """

    def __init__(
        self,
        url: str,
        cluster: "Cluster",
        session: "Session",
        keyspace: str,
    ) -> None:
        super().__init__({"url": url})
        self._cluster = cluster
        self._session = session
        self._keyspace = keyspace

    def _get_collection(self, name: str) -> CassandraCollection:
        """Create and return a :class:`CassandraCollection` for *name*."""
        return CassandraCollection(self, name, self._session)

    async def _close(self) -> None:
        """Shut down the underlying Cassandra cluster connection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._cluster.shutdown)
