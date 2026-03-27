"""
test_compliance.py — MongoDB driver compliance tests.

Wires the shared pynosqlc.core compliance suite into the mongodb package.
Each test run gets a fresh MongoClient connected to a real MongoDB instance.

Set MONGODB_URL to override the default connection URL.
Tests are skipped automatically if MongoDB is not reachable.
"""

from __future__ import annotations

import os

import pytest

from pynosqlc.core import DriverManager
from pynosqlc.core.testing import run_compliance
import pynosqlc.mongodb  # noqa: F401 — registers MongoDriver on import
from pynosqlc.mongodb.mongo_driver import _driver

MONGODB_URL = os.environ.get(
    "MONGODB_URL", "pynosqlc:mongodb://localhost:27017/pynosqlc_test"
)


async def _factory():
    """Return a fresh, open MongoClient for each test class fixture.

    Clears and re-registers the driver, connects to MongoDB, drops any
    leftover compliance collections, and returns the client.

    Skips the test if MongoDB is not reachable.
    """
    DriverManager.clear()
    DriverManager.register_driver(_driver)

    try:
        client = await DriverManager.get_client(
            MONGODB_URL,
            {"serverSelectionTimeoutMS": 3000},
        )
        # Drop compliance collections from any prior run so tests are isolated.
        db = client._db
        for col_name in ("compliance_kv", "compliance_doc", "compliance_find"):
            try:
                await db.drop_collection(col_name)
            except Exception:
                pass  # Collection may not exist; that's fine.

        return client

    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")


run_compliance(_factory)
