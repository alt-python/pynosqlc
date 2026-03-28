"""
redis_client.py — Redis Client implementation.

Each collection is created on demand and not cached here — the parent
Client base class caches by name via get_collection().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pynosqlc.core.client import Client
from pynosqlc.redis.redis_collection import RedisCollection

if TYPE_CHECKING:
    import redis.asyncio as aioredis


class RedisClient(Client):
    """Client backed by a redis-py async connection.

    Args:
        url: the pynosqlc URL used to open this connection
             (e.g. ``'pynosqlc:redis://localhost:6379'``)
        r: a connected ``redis.asyncio`` client instance
    """

    def __init__(self, url: str, r: "aioredis.Redis") -> None:
        super().__init__({"url": url})
        self._r = r

    def _get_collection(self, name: str) -> RedisCollection:
        """Create and return a :class:`RedisCollection` for *name*."""
        return RedisCollection(self, name, self._r)

    async def _close(self) -> None:
        """Close the underlying redis-py connection."""
        await self._r.aclose()
