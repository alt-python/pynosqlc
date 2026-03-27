"""
pynosqlc.core.testing — Shared compliance test utilities.

Exports:
    run_compliance: Register a pytest compliance suite into the calling module.
"""

from pynosqlc.core.testing.compliance import run_compliance

__all__ = ["run_compliance"]
