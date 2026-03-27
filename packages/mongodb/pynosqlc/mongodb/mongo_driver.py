"""
mongo_driver.py — MongoDriver: connects to MongoDB via pymongo AsyncMongoClient.

URL scheme: pynosqlc:mongodb://<host>:<port>/<dbname>
Auto-registers with DriverManager on import.
"""

from __future__ import annotations

import urllib.parse

from pymongo import AsyncMongoClient

from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.mongodb.mongo_client import MongoClient


class MongoDriver(Driver):
    """Driver that creates :class:`MongoClient` instances.

    URL prefix: ``pynosqlc:mongodb://``
    """

    URL_PREFIX: str = "pynosqlc:mongodb://"

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` for ``'pynosqlc:mongodb://'`` URLs."""
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> MongoClient:
        """Create and return a new :class:`MongoClient`.

        Strips the ``pynosqlc:`` prefix to obtain the native MongoDB URL,
        extracts the database name from the URL path, and returns an open
        :class:`MongoClient`.

        Args:
            url: ``pynosqlc:mongodb://<host>:<port>/<dbname>``
            properties: optional dict; ``serverSelectionTimeoutMS`` is
                        forwarded to pymongo (default: 5000).

        Returns:
            An open :class:`MongoClient`.
        """
        props = properties or {}

        # Strip 'pynosqlc:' prefix → 'mongodb://...'
        native_url = url[len("pynosqlc:"):]

        parsed = urllib.parse.urlparse(native_url)
        db_name = parsed.path.lstrip("/") or "test"
        server_url = f"{parsed.scheme}://{parsed.netloc}"

        options: dict = {
            "serverSelectionTimeoutMS": props.get("serverSelectionTimeoutMS", 5000),
        }

        native_client = AsyncMongoClient(server_url, **options)
        db = native_client.get_database(db_name)
        return MongoClient(url, native_client, db)


# Auto-register on import — a single shared instance is sufficient.
_driver = MongoDriver()
DriverManager.register_driver(_driver)
