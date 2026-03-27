"""DynamoDB driver for pynosqlc.

Importing this package auto-registers the DynamoDriver with DriverManager.
"""

from __future__ import annotations

from pynosqlc.dynamodb.dynamo_filter_translator import DynamoFilterTranslator
from pynosqlc.dynamodb.dynamo_client import DynamoClient
from pynosqlc.dynamodb.dynamo_collection import DynamoCollection

# Import last — triggers module-level DriverManager.register_driver() call.
from pynosqlc.dynamodb.dynamo_driver import DynamoDriver  # noqa: F401  (side-effect import)

__all__ = [
    "DynamoDriver",
    "DynamoClient",
    "DynamoCollection",
    "DynamoFilterTranslator",
]
