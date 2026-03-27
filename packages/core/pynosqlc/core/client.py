"""
client.py — Abstract base class for a pynosqlc client session.

Drivers override ``_get_collection()`` and ``_close()``.
Manages a cache of Collection instances keyed by name.
Implements the async context manager protocol (``async with``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pynosqlc.core.driver_manager import DriverManager

if TYPE_CHECKING:
    from pynosqlc.core.collection import Collection


class Client(ABC):
    """A session to a NoSQL database.

    Args:
        config: optional dict; recognises key ``'url'``.
    """

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self._url: str | None = cfg.get("url")
        self._closed: bool = False
        self._collections: dict[str, "Collection"] = {}

    # ── Async context manager ──────────────────────────────────────────────

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    # ── Public API ─────────────────────────────────────────────────────────

    def get_collection(self, name: str) -> "Collection":
        """Return a (cached) Collection by name.

        Raises:
            RuntimeError: if the client is closed
        """
        self._check_closed()
        if name not in self._collections:
            self._collections[name] = self._get_collection(name)
        return self._collections[name]

    async def close(self) -> None:
        """Close the client and release all resources."""
        self._closed = True
        self._collections.clear()
        await self._close()

    def is_closed(self) -> bool:
        """Return ``True`` if the client has been closed."""
        return self._closed

    def get_url(self) -> str | None:
        """Return the pynosqlc URL this client was opened with."""
        return self._url

    # ── Abstract implementation hooks ──────────────────────────────────────

    @abstractmethod
    def _get_collection(self, name: str) -> "Collection":
        """Create and return a new Collection instance for *name*."""

    async def _close(self) -> None:
        """Override to release driver-specific resources on close."""

    # ── Internal helpers ───────────────────────────────────────────────────

    def _check_closed(self) -> None:
        if self._closed:
            raise RuntimeError("Client is closed")


class ClientDataSource:
    """Convenience factory that wraps :meth:`DriverManager.get_client`.

    Mirrors pydbc's DataSource pattern.

    Args:
        config: dict with keys:
            - ``url`` (required) — pynosqlc URL
            - ``username`` (optional)
            - ``password`` (optional)
            - ``properties`` (optional) — additional driver-specific options
    """

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self._url: str = cfg["url"]
        self._properties: dict = {
            "username": cfg.get("username"),
            "password": cfg.get("password"),
            **(cfg.get("properties") or {}),
        }

    async def get_client(self) -> Client:
        """Return a client from the configured data source."""
        return await DriverManager.get_client(self._url, self._properties)

    def get_url(self) -> str:
        """Return the configured pynosqlc URL."""
        return self._url
