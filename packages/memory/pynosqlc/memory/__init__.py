"""
pynosqlc.memory — In-memory driver for pynosqlc.

Zero-dependency dict-backed storage. Auto-registers with DriverManager on import.
URL scheme: pynosqlc:memory:

Usage::

    import pynosqlc.memory  # registers MemoryDriver
    from pynosqlc.core import DriverManager

    client = await DriverManager.get_client("pynosqlc:memory:")
"""

from __future__ import annotations

# Import the driver module to trigger auto-registration with DriverManager.
from pynosqlc.memory.memory_driver import MemoryDriver, _driver  # noqa: F401
from pynosqlc.memory.memory_client import MemoryClient
from pynosqlc.memory.memory_collection import MemoryCollection
from pynosqlc.memory.memory_filter_evaluator import MemoryFilterEvaluator

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__ = [
    "MemoryDriver",
    "MemoryClient",
    "MemoryCollection",
    "MemoryFilterEvaluator",
]
