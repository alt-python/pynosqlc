"""
errors.py — Custom exception classes for pynosqlc.
"""

from __future__ import annotations


class UnsupportedOperationError(Exception):
    """Raised when a driver does not implement an optional Collection operation.

    Callers can ``isinstance``-check this to handle gracefully.
    """
