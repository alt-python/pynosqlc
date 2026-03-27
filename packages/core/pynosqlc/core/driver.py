"""
driver.py — Abstract base class for pynosqlc drivers.

Each driver implementation registers itself with DriverManager on import
and declares which URL schemes it handles.

URL scheme: pynosqlc:<subprotocol>:<connection-details>
e.g. pynosqlc:mongodb://localhost:27017/mydb
     pynosqlc:memory:
     pynosqlc:dynamodb:us-east-1
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynosqlc.core.client import Client


class Driver(ABC):
    """Creates client connections to a specific NoSQL database type."""

    @abstractmethod
    def accepts_url(self, url: str) -> bool:
        """Return True if this driver handles the given pynosqlc URL.

        Args:
            url: e.g. ``'pynosqlc:mongodb://localhost:27017/mydb'``
        """

    @abstractmethod
    async def connect(self, url: str, properties: dict | None = None) -> "Client":
        """Create a client connection to the database.

        Args:
            url: pynosqlc URL
            properties: optional dict with driver-specific options
                        (e.g. username, password, endpoint)
        """
