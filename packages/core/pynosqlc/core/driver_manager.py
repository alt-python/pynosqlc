"""
driver_manager.py — Registry for pynosqlc drivers.

Drivers register themselves on import. When get_client() is called,
DriverManager iterates registered drivers to find one that accepts the URL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynosqlc.core.driver import Driver
    from pynosqlc.core.client import Client


class DriverManager:
    """Class-level registry for pynosqlc drivers."""

    _drivers: list["Driver"] = []

    @classmethod
    def register_driver(cls, driver: "Driver") -> None:
        """Register a driver instance (idempotent — no duplicates)."""
        if driver not in cls._drivers:
            cls._drivers.append(driver)

    @classmethod
    def deregister_driver(cls, driver: "Driver") -> None:
        """Remove a previously registered driver."""
        cls._drivers = [d for d in cls._drivers if d is not driver]

    @classmethod
    async def get_client(
        cls,
        url: str,
        properties: dict | None = None,
    ) -> "Client":
        """Return a client from the first driver that accepts *url*.

        Args:
            url: pynosqlc URL (e.g. ``'pynosqlc:memory:'``)
            properties: optional driver-specific connection properties

        Raises:
            ValueError: if no registered driver accepts the URL
        """
        if properties is None:
            properties = {}
        for driver in cls._drivers:
            if driver.accepts_url(url):
                return await driver.connect(url, properties)
        raise ValueError(
            f"No suitable driver found for URL: {url!r}. "
            f"Registered drivers: {[type(d).__name__ for d in cls._drivers]}"
        )

    @classmethod
    def get_drivers(cls) -> list["Driver"]:
        """Return a copy of the registered driver list."""
        return list(cls._drivers)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered drivers (for testing)."""
        cls._drivers = []
