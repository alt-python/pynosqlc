"""
test_compliance.py — CosmosDB driver compliance tests.

Wires the shared pynosqlc.core compliance suite into the cosmosdb package.
Each test run gets a fresh CosmosClient connected to a real Cosmos DB instance.

Set COSMOS_ENDPOINT to override the default local endpoint (default: http://localhost:8081).
Set COSMOS_DB to override the database name (default: pynosqlc_ci).
Tests are skipped automatically if the Cosmos emulator is not reachable.
"""

from __future__ import annotations

import os

import pytest

from pynosqlc.core import DriverManager
from pynosqlc.core.testing import run_compliance
import pynosqlc.cosmosdb  # noqa: F401 — registers CosmosDriver on import
from pynosqlc.cosmosdb.cosmos_driver import _driver

COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT", "http://localhost:8081")
COSMOS_DB = os.environ.get("COSMOS_DB", "pynosqlc_ci")
COSMOS_URL = "pynosqlc:cosmosdb:local"


async def _factory():
    """Return a fresh, open CosmosClient for each test class fixture.

    Clears and re-registers the driver, connects to Cosmos DB, deletes any
    leftover compliance containers so ensure_container recreates them cleanly,
    and returns the client.

    Skips the test if the Cosmos emulator is not reachable.
    """
    DriverManager.clear()
    DriverManager.register_driver(_driver)

    try:
        client = await DriverManager.get_client(
            COSMOS_URL,
            {"db_id": COSMOS_DB, "endpoint": COSMOS_ENDPOINT},
        )
    except Exception as e:
        pytest.skip(f"CosmosDB not available: {e}")

    # Delete compliance containers from any prior run so tests are isolated.
    # Deleting the container and removing it from the cache forces ensure_container
    # to recreate it fresh on first use — simpler than clearing items.
    for name in ("compliance_kv", "compliance_doc", "compliance_find"):
        try:
            await client._database.delete_container(name)
            client._container_cache.pop(name, None)
        except Exception:
            pass  # Container may not exist yet; that's fine.

    return client


run_compliance(_factory)
