"""
cassandra_driver.py — Cassandra pynosqlc driver.

Handles URL: pynosqlc:cassandra:host:port/keyspace
Auto-registers with DriverManager on import.

cassandra-driver uses a synchronous API; all blocking calls are executed
via asyncio.get_event_loop().run_in_executor(None, ...) so they don't
block the event loop.

AsyncioConnection is used as the connection class so that the
cassandra-driver internal reactor integrates with the running asyncio
event loop instead of spawning its own thread.
"""

from __future__ import annotations

import asyncio

from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.cassandra.cassandra_client import CassandraClient


class CassandraDriver(Driver):
    """Driver that creates :class:`CassandraClient` instances.

    URL format: ``pynosqlc:cassandra:host:port/keyspace``
    Default port: 9042
    Default keyspace: ``pynosqlc``
    """

    URL_PREFIX: str = "pynosqlc:cassandra:"

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` for ``'pynosqlc:cassandra:...'`` URLs."""
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> CassandraClient:
        """Parse URL, connect, and return a :class:`CassandraClient`.

        URL format: ``pynosqlc:cassandra:host:port/keyspace``
        Example:    ``pynosqlc:cassandra:localhost:9042/pynosqlc_test``

        Connection errors from cassandra-driver propagate directly —
        ``NoHostAvailable`` is the expected signal when Cassandra is absent
        (used by compliance tests to skip).
        """
        from cassandra.cluster import Cluster
        from cassandra.io.asyncioreactor import AsyncioConnection
        from cassandra.query import dict_factory

        # Parse: strip prefix → "host:port/keyspace"
        tail = url[len(self.URL_PREFIX):]
        if "/" in tail:
            host_port, keyspace = tail.split("/", 1)
        else:
            host_port, keyspace = tail, "pynosqlc"

        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 9042

        loop = asyncio.get_event_loop()

        cluster = Cluster(
            contact_points=[host],
            port=port,
            connection_class=AsyncioConnection,
        )
        session = await loop.run_in_executor(None, lambda: cluster.connect())
        await loop.run_in_executor(
            None,
            session.execute,
            (
                f"CREATE KEYSPACE IF NOT EXISTS {keyspace} "
                f"WITH REPLICATION = {{'class': 'SimpleStrategy', 'replication_factor': 1}}"
            ),
        )
        await loop.run_in_executor(None, session.set_keyspace, keyspace)
        session.row_factory = dict_factory

        return CassandraClient(url, cluster, session, keyspace)


# Auto-register on import — a single shared instance is sufficient.
_driver = CassandraDriver()
DriverManager.register_driver(_driver)
