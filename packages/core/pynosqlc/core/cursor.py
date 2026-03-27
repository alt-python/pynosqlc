"""
cursor.py — Cursor over a find() result set.

Provides cursor-based iteration (next/get_document) plus bulk access
(get_documents) and implements the async iterator protocol for use with
``async for``.

The base class buffers all results in a list. Driver implementations may
subclass Cursor to support streaming from the database.
"""

from __future__ import annotations


class Cursor:
    """Async-iterable cursor over a collection of documents.

    Args:
        documents: pre-buffered result list (pass ``[]`` for an empty cursor)
    """

    def __init__(self, documents: list[dict] | None = None) -> None:
        self._documents: list[dict] = documents if documents is not None else []
        self._cursor: int = -1
        self._closed: bool = False

    async def next(self) -> bool:
        """Advance to the next document.

        Returns:
            ``True`` if there is a current document; ``False`` when exhausted.
        """
        self._check_closed()
        self._cursor += 1
        return self._cursor < len(self._documents)

    def get_document(self) -> dict:
        """Return a shallow copy of the document at the current cursor position.

        Raises:
            RuntimeError: if the cursor is not on a valid document (call
                          ``next()`` first)
            RuntimeError: if the cursor is closed
        """
        self._check_closed()
        self._check_cursor()
        return dict(self._documents[self._cursor])

    def get_documents(self) -> list[dict]:
        """Return all documents as a list of shallow copies.

        Does not require ``next()`` to have been called — returns the full
        buffered result set.
        """
        self._check_closed()
        return [dict(d) for d in self._documents]

    async def close(self) -> None:
        """Close the cursor and release resources."""
        self._closed = True

    def is_closed(self) -> bool:
        """Return ``True`` if the cursor has been closed."""
        return self._closed

    # ── Async iterator protocol ────────────────────────────────────────────

    def __aiter__(self) -> "Cursor":
        return self

    async def __anext__(self) -> dict:
        has_more = await self.next()
        if has_more:
            return self.get_document()
        await self.close()
        raise StopAsyncIteration

    # ── Internal helpers ───────────────────────────────────────────────────

    def _check_closed(self) -> None:
        if self._closed:
            raise RuntimeError("Cursor is closed")

    def _check_cursor(self) -> None:
        if self._cursor < 0 or self._cursor >= len(self._documents):
            raise RuntimeError(
                "Cursor is not on a valid document — call next() first"
            )
