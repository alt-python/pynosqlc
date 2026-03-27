"""
test_compliance.py — DynamoDB driver compliance tests.

Wires the shared pynosqlc.core compliance suite into the dynamodb package.
Each test run gets a fresh DynamoClient connected to a real DynamoDB instance.

Set DYNAMODB_ENDPOINT to override the default local endpoint (default: http://localhost:8000).
Set DYNAMODB_REGION to override the default region (default: us-east-1).
Tests are skipped automatically if DynamoDB Local is not reachable.
"""

from __future__ import annotations

import os

import pytest

from pynosqlc.core import DriverManager
from pynosqlc.core.testing import run_compliance
import pynosqlc.dynamodb  # noqa: F401 — registers DynamoDriver on import
from pynosqlc.dynamodb.dynamo_driver import _driver

DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")
DYNAMODB_REGION = os.environ.get("DYNAMODB_REGION", "us-east-1")
DYNAMODB_URL = f"pynosqlc:dynamodb:{DYNAMODB_REGION}"


async def _factory():
    """Return a fresh, open DynamoClient for each test class fixture.

    Clears and re-registers the driver, connects to DynamoDB, deletes any
    leftover compliance tables so ensure_table recreates them cleanly, and
    returns the client.

    Skips the test if DynamoDB is not reachable.
    """
    DriverManager.clear()
    DriverManager.register_driver(_driver)

    try:
        client = await DriverManager.get_client(
            DYNAMODB_URL,
            {"endpoint": DYNAMODB_ENDPOINT},
        )
    except Exception as e:
        pytest.skip(f"DynamoDB not available: {e}")

    # Delete compliance tables from any prior run so tests are isolated.
    # Deleting the table and removing it from the cache forces ensure_table
    # to recreate it fresh on first use — simpler than clearing items.
    for table_name in ("compliance_kv", "compliance_doc", "compliance_find"):
        try:
            table = await client._resource.Table(table_name)
            await table.delete()
            client._table_cache.discard(table_name)
        except Exception:
            pass  # Table may not exist yet; that's fine.

    return client


run_compliance(_factory)
