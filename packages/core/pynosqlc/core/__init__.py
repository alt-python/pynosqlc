"""
pynosqlc.core — Core abstraction hierarchy for pynosqlc.

Provides:
  Driver                 — ABC for NoSQL drivers
  DriverManager          — Registry and URL-based connection dispatcher
  Client                 — ABC for database clients (async context manager)
  ClientDataSource       — Connection factory wrapping DriverManager
  Collection             — ABC for collections / tables / buckets
  Cursor                 — Cursor-based and bulk document access (async iterable)
  Filter                 — Chainable query filter builder
  FieldCondition         — Field-level condition within a Filter
  UnsupportedOperationError — Raised when a driver does not implement an operation
"""

from __future__ import annotations

from pynosqlc.core.errors import UnsupportedOperationError
from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.core.cursor import Cursor
from pynosqlc.core.collection import Collection
from pynosqlc.core.client import Client, ClientDataSource
from pynosqlc.core.filter import Filter, FieldCondition

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__ = [
    "Driver",
    "DriverManager",
    "Client",
    "ClientDataSource",
    "Collection",
    "Cursor",
    "Filter",
    "FieldCondition",
    "UnsupportedOperationError",
]
