"""
test_compliance.py — Memory driver compliance tests.

Wires the shared pynosqlc.core compliance suite into the memory package.
Each test run gets a fresh MemoryClient by clearing and re-importing.
"""

from __future__ import annotations

from pynosqlc.core import DriverManager
from pynosqlc.core.testing import run_compliance
import pynosqlc.memory  # noqa: F401 — registers MemoryDriver on import


async def _factory():
    """Return a fresh, open MemoryClient for each test class fixture."""
    DriverManager.clear()
    # Re-import to re-register after clear — safe because Python caches modules.
    from pynosqlc.memory.memory_driver import _driver  # noqa: F401
    DriverManager.register_driver(_driver)
    return await DriverManager.get_client("pynosqlc:memory:")


run_compliance(_factory)
