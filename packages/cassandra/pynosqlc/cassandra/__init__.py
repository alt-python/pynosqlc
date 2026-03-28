"""
pynosqlc.cassandra — Cassandra driver for pynosqlc.

Handles URLs of the form: pynosqlc:cassandra:host:port/keyspace

Auto-registers ``CassandraDriver`` with ``DriverManager`` on import via
the ``cassandra_driver`` module.
"""

from __future__ import annotations

from pynosqlc.cassandra import cassandra_driver  # noqa: F401
from pynosqlc.cassandra.cassandra_client import CassandraClient
from pynosqlc.cassandra.cassandra_collection import CassandraCollection
from pynosqlc.cassandra.cassandra_driver import CassandraDriver

__all__ = ["CassandraDriver", "CassandraClient", "CassandraCollection"]
