"""
test_compliance.py — Cassandra driver compliance tests.

Wires the shared pynosqlc.core compliance suite into the cassandra package.
Each test run gets a fresh CassandraClient connected to a live Cassandra 4 instance.

Set CASSANDRA_URL to override the default URL
(default: pynosqlc:cassandra:localhost:9042/pynosqlc_test).
Tests are skipped automatically if Cassandra is not reachable.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from pynosqlc.core import DriverManager
from pynosqlc.core.testing import run_compliance
import pynosqlc.cassandra  # noqa: F401 — registers CassandraDriver on import
from pynosqlc.cassandra.cassandra_driver import _driver

CASSANDRA_URL = os.environ.get(
    "CASSANDRA_URL", "pynosqlc:cassandra:localhost:9042/pynosqlc_test"
)


async def _factory():
    """Return a fresh, open CassandraClient for each test class fixture.

    Clears and re-registers the driver, connects to Cassandra, drops and
    recreates the keyspace so each test class starts with a clean slate,
    and returns the client.

    Skips the test if Cassandra is not reachable.
    """
    DriverManager.clear()
    DriverManager.register_driver(_driver)

    try:
        client = await DriverManager.get_client(CASSANDRA_URL)
        # Drop and recreate keyspace for a clean slate between test classes
        loop = asyncio.get_event_loop()
        keyspace = "pynosqlc_test"
        await loop.run_in_executor(
            None,
            client._session.execute,
            f"DROP KEYSPACE IF EXISTS {keyspace}",
        )
        await loop.run_in_executor(
            None,
            client._session.execute,
            (
                f"CREATE KEYSPACE IF NOT EXISTS {keyspace} "
                f"WITH REPLICATION = {{'class': 'SimpleStrategy', 'replication_factor': 1}}"
            ),
        )
        await loop.run_in_executor(None, client._session.set_keyspace, keyspace)
    except Exception as e:
        pytest.skip(f"Cassandra not available: {e}")

    return client


run_compliance(_factory)
