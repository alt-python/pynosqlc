"""
memory_driver.py — In-memory pynosqlc driver.

Handles URL: pynosqlc:memory:
Auto-registers with DriverManager on import.
"""

from __future__ import annotations

from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.memory.memory_client import MemoryClient


class MemoryDriver(Driver):
    """Driver that creates :class:`MemoryClient` instances.

    URL prefix: ``pynosqlc:memory:``
    """

    URL_PREFIX: str = "pynosqlc:memory:"

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` for ``'pynosqlc:memory:'`` URLs."""
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> MemoryClient:
        """Create and return a new :class:`MemoryClient`."""
        return MemoryClient(url)


# Auto-register on import — a single shared instance is sufficient.
_driver = MemoryDriver()
DriverManager.register_driver(_driver)
