"""
collection.py — Abstract base class for a named collection (table/bucket).

Driver implementations override the ``_`` methods. All base ``_`` methods
raise ``UnsupportedOperationError`` — drivers implement only what their
backend supports.

Operations
----------
Key-value : get(key), store(key, doc), delete(key)
Document  : insert(doc), update(key, patch)
Query     : find(ast)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pynosqlc.core.errors import UnsupportedOperationError

if TYPE_CHECKING:
    from pynosqlc.core.client import Client
    from pynosqlc.core.cursor import Cursor


class Collection(ABC):
    """Represents a named collection within a :class:`Client`."""

    def __init__(self, client: "Client", name: str) -> None:
        self._client = client
        self._name = name
        self._closed: bool = False

    def get_name(self) -> str:
        """Return the collection name."""
        return self._name

    # ── Public API ─────────────────────────────────────────────────────────

    async def get(self, key: str) -> dict | None:
        """Retrieve a document by its primary key.

        Returns:
            The document dict, or ``None`` if the key does not exist.
        """
        self._check_closed()
        return await self._get(key)

    async def store(self, key: str, doc: dict) -> None:
        """Store (upsert) a document under *key*."""
        self._check_closed()
        await self._store(key, doc)

    async def delete(self, key: str) -> None:
        """Delete the document at *key*.  No-op if the key does not exist."""
        self._check_closed()
        await self._delete(key)

    async def insert(self, doc: dict) -> str:
        """Insert a document and return the backend-assigned key / ``_id``."""
        self._check_closed()
        return await self._insert(doc)

    async def update(self, key: str, patch: dict) -> None:
        """Patch the document at *key*.

        Only provided fields are updated; others are preserved (shallow merge).
        """
        self._check_closed()
        await self._update(key, patch)

    async def find(self, ast: dict) -> "Cursor":
        """Find documents matching the given filter AST.

        Args:
            ast: a built filter AST from ``Filter.build()``

        Returns:
            A :class:`~pynosqlc.core.Cursor` over matching documents.
        """
        self._check_closed()
        return await self._find(ast)

    # ── Abstract implementation hooks ──────────────────────────────────────

    async def _get(self, key: str) -> dict | None:
        raise UnsupportedOperationError("get() is not supported by this driver")

    async def _store(self, key: str, doc: dict) -> None:
        raise UnsupportedOperationError("store() is not supported by this driver")

    async def _delete(self, key: str) -> None:
        raise UnsupportedOperationError("delete() is not supported by this driver")

    async def _insert(self, doc: dict) -> str:
        raise UnsupportedOperationError("insert() is not supported by this driver")

    async def _update(self, key: str, patch: dict) -> None:
        raise UnsupportedOperationError("update() is not supported by this driver")

    async def _find(self, ast: dict) -> "Cursor":
        raise UnsupportedOperationError("find() is not supported by this driver")

    # ── Internal helpers ───────────────────────────────────────────────────

    def _check_closed(self) -> None:
        if self._closed:
            raise RuntimeError("Collection is closed")
