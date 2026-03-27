"""
memory_client.py — In-memory Client implementation.

Each collection gets its own isolated dict. Collections are cached by the
parent Client base class via get_collection() caching.
"""

from __future__ import annotations

from pynosqlc.core.client import Client
from pynosqlc.memory.memory_collection import MemoryCollection


class MemoryClient(Client):
    """Client backed entirely by in-process dicts.

    Args:
        url: the pynosqlc URL used to open this connection
             (e.g. ``'pynosqlc:memory:'``)
    """

    def __init__(self, url: str) -> None:
        super().__init__({"url": url})
        # Maps collection name → backing dict for that collection.
        self._stores: dict[str, dict] = {}

    def _get_collection(self, name: str) -> MemoryCollection:
        """Create (or reuse) the backing dict for *name* and return a
        new :class:`MemoryCollection` wrapping it."""
        if name not in self._stores:
            self._stores[name] = {}
        return MemoryCollection(self, name, self._stores[name])

    async def _close(self) -> None:
        """Clear all in-memory stores on close."""
        self._stores.clear()
