"""
cosmos_driver.py — CosmosDriver: connects to Azure Cosmos DB via azure-cosmos.

URL scheme: pynosqlc:cosmosdb:<target>
  where <target> is one of:
    local                 → Cosmos DB emulator at http://localhost:8081
    localhost             → same as local
    localhost:PORT        → Cosmos DB emulator at http://localhost:PORT
    https://...           → Azure Cosmos DB endpoint (requires 'key' property)

Auto-registers with DriverManager on import.
"""

from __future__ import annotations

from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.cosmosdb.cosmos_client import CosmosClient

# Well-known Cosmos DB emulator master key.
_EMULATOR_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)


class CosmosDriver(Driver):
    """Driver that creates :class:`CosmosClient` instances.

    URL prefix: ``pynosqlc:cosmosdb:``
    """

    URL_PREFIX: str = "pynosqlc:cosmosdb:"

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` for ``'pynosqlc:cosmosdb:'`` URLs."""
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> CosmosClient:
        """Create and return an open :class:`CosmosClient`.

        Args:
            url: ``pynosqlc:cosmosdb:<target>``
            properties: optional dict; supports:
                - ``endpoint``: override endpoint URL (for local target)
                - ``key``: account key (required for https:// target)
                - ``db_id``: database name (default: ``'pynosqlc'``)
                - any extra keyword args passed through to
                  :class:`azure.cosmos.aio.CosmosClient`

        Returns:
            An open :class:`CosmosClient`.

        Raises:
            ValueError: if an ``https://`` target is used without ``key``.
        """
        props = properties or {}

        target = url[len(self.URL_PREFIX):]
        db_id = props.pop("db_id", "pynosqlc")

        # Determine endpoint and key from the target string.
        if target in ("local", "localhost") or target.startswith("localhost:"):
            # Cosmos DB emulator
            endpoint = props.pop(
                "endpoint",
                "http://localhost:8081",
            )
            key = props.pop("key", _EMULATOR_KEY)
        elif target.startswith("https://"):
            endpoint = target
            if "key" not in props:
                raise ValueError(
                    f"CosmosDriver: 'key' property is required for endpoint {target!r}"
                )
            key = props.pop("key")
        else:
            # Treat unknown targets as the endpoint directly.
            endpoint = target
            key = props.pop("key", _EMULATOR_KEY)

        client = CosmosClient(url, endpoint, key, db_id, props)
        await client._open()
        return client


# Auto-register on import — a single shared instance is sufficient.
_driver = CosmosDriver()
DriverManager.register_driver(_driver)
