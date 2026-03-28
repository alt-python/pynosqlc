"""
test_compliance.py — Redis driver compliance tests.

Wires the shared pynosqlc.core compliance suite into the redis package.
Each test run gets a fresh RedisClient connected to a live Redis 7 instance.

Set REDIS_URL to override the default URL (default: pynosqlc:redis://localhost:6379).
Tests are skipped automatically if Redis is not reachable.
"""

from __future__ import annotations

import os

import pytest

from pynosqlc.core import DriverManager
from pynosqlc.core.testing import run_compliance
import pynosqlc.redis  # noqa: F401 — registers RedisDriver on import
from pynosqlc.redis.redis_driver import _driver

REDIS_URL = os.environ.get("REDIS_URL", "pynosqlc:redis://localhost:6379")


async def _factory():
    """Return a fresh, open RedisClient for each test class fixture.

    Clears and re-registers the driver, connects to Redis, flushes the DB
    so each test class starts with no leftover keys, and returns the client.

    Skips the test if Redis is not reachable.
    """
    DriverManager.clear()
    DriverManager.register_driver(_driver)

    try:
        client = await DriverManager.get_client(REDIS_URL)
        # Flush the entire DB — Redis has no per-collection teardown equivalent;
        # flushing gives every test class a guaranteed clean slate.
        # flushdb() is the first real network call — connection errors surface here.
        await client._r.flushdb()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    return client


run_compliance(_factory)
