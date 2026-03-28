"""
redis_driver.py — Redis pynosqlc driver.

Handles URL: pynosqlc:redis://host:port[/db]
Auto-registers with DriverManager on import.

The ``pynosqlc:`` prefix is stripped before passing the URL to redis-py,
so ``redis.asyncio.from_url`` receives a standard ``redis://`` URL.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.redis.redis_client import RedisClient


class RedisDriver(Driver):
    """Driver that creates :class:`RedisClient` instances.

    URL prefix: ``pynosqlc:redis:``
    """

    URL_PREFIX: str = "pynosqlc:redis:"

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` for ``'pynosqlc:redis://...'`` URLs."""
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> RedisClient:
        """Create and return a new :class:`RedisClient`.

        Strips the ``pynosqlc:`` prefix so redis-py receives a standard
        ``redis://host:port`` URL.  Connection errors from redis-py propagate
        directly — the exception message includes host/port and reason.
        """
        # "pynosqlc:redis://localhost:6379" → "redis://localhost:6379"
        native_url = url[len("pynosqlc:"):]
        r = aioredis.from_url(native_url, decode_responses=True)
        return RedisClient(url, r)


# Auto-register on import — a single shared instance is sufficient.
_driver = RedisDriver()
DriverManager.register_driver(_driver)
