"""
pynosqlc.redis — Redis driver for pynosqlc.

Handles URLs of the form: pynosqlc:redis://host:port[/db]

Auto-registers ``RedisDriver`` with ``DriverManager`` on import via the
``redis_driver`` module.
"""

from __future__ import annotations

from pynosqlc.redis import redis_driver  # noqa: F401
from pynosqlc.redis.redis_client import RedisClient
from pynosqlc.redis.redis_collection import RedisCollection
from pynosqlc.redis.redis_driver import RedisDriver

__all__ = ["RedisDriver", "RedisClient", "RedisCollection"]
