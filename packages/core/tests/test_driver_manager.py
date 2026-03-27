"""
test_driver_manager.py — Unit tests for DriverManager registry.

Ports driverManager.spec.js with a minimal stub Driver/Client/Collection.

Tests cover: starts_empty, register, no_double_register, deregister,
get_client_routes_correctly, get_client_raises_on_no_match, clear,
get_drivers_returns_copy.

DriverManager.get_client is async — asyncio_mode=auto (set in pyproject.toml)
means async test functions run without @pytest.mark.asyncio.
"""

import pytest
from pynosqlc.core.driver import Driver
from pynosqlc.core.client import Client
from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.core.driver_manager import DriverManager


# ── Stub implementations ───────────────────────────────────────────────────

class StubCollection(Collection):
    """Minimal collection that satisfies all abstract hooks."""

    async def _get(self, key):
        return {"key": key}

    async def _store(self, key, doc):
        pass

    async def _delete(self, key):
        pass

    async def _insert(self, doc):
        return "stub-id"

    async def _update(self, key, patch):
        pass

    async def _find(self, filter):
        return Cursor([])


class StubClient(Client):
    """Minimal client backed by StubCollection."""

    def _get_collection(self, name: str) -> StubCollection:
        return StubCollection(self, name)


class StubDriver(Driver):
    """Accepts URLs that start with a configured prefix."""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def accepts_url(self, url: str) -> bool:
        return url.startswith(self._prefix)

    async def connect(self, url: str, properties: dict | None = None) -> StubClient:
        return StubClient({"url": url})


# ── Tests ──────────────────────────────────────────────────────────────────

class TestDriverManager:
    def setup_method(self):
        """Clear registry before each test for isolation."""
        DriverManager.clear()

    def test_starts_empty(self):
        assert DriverManager.get_drivers() == []

    def test_registers_a_driver(self):
        d = StubDriver("pynosqlc:stub:")
        DriverManager.register_driver(d)
        assert len(DriverManager.get_drivers()) == 1

    def test_does_not_double_register_same_instance(self):
        d = StubDriver("pynosqlc:stub:")
        DriverManager.register_driver(d)
        DriverManager.register_driver(d)
        assert len(DriverManager.get_drivers()) == 1

    def test_deregisters_a_driver(self):
        d = StubDriver("pynosqlc:stub:")
        DriverManager.register_driver(d)
        DriverManager.deregister_driver(d)
        assert len(DriverManager.get_drivers()) == 0

    async def test_get_client_routes_to_correct_driver(self):
        dA = StubDriver("pynosqlc:a:")
        dB = StubDriver("pynosqlc:b:")
        DriverManager.register_driver(dA)
        DriverManager.register_driver(dB)
        client = await DriverManager.get_client("pynosqlc:b:test")
        assert isinstance(client, StubClient)
        assert client.get_url() == "pynosqlc:b:test"

    async def test_get_client_raises_when_no_driver_matches(self):
        DriverManager.register_driver(StubDriver("pynosqlc:x:"))
        with pytest.raises(ValueError, match="No suitable driver"):
            await DriverManager.get_client("pynosqlc:unknown:test")

    def test_clear_resets_registry(self):
        DriverManager.register_driver(StubDriver("pynosqlc:a:"))
        DriverManager.clear()
        assert DriverManager.get_drivers() == []

    def test_get_drivers_returns_copy_not_internal_array(self):
        d = StubDriver("pynosqlc:a:")
        DriverManager.register_driver(d)
        drivers = DriverManager.get_drivers()
        drivers.pop()
        assert len(DriverManager.get_drivers()) == 1
