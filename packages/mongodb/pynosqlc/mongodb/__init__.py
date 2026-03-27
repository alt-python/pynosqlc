"""pynosqlc.mongodb — MongoDB driver for pynosqlc.

Importing this package auto-registers the MongoDriver with DriverManager.
"""

from pynosqlc.mongodb.mongo_filter_translator import MongoFilterTranslator
from pynosqlc.mongodb.mongo_collection import MongoCollection
from pynosqlc.mongodb.mongo_client import MongoClient

# Import mongo_driver last — it auto-registers _driver with DriverManager.
from pynosqlc.mongodb.mongo_driver import MongoDriver, _driver  # noqa: F401

__all__ = [
    "MongoDriver",
    "MongoClient",
    "MongoCollection",
    "MongoFilterTranslator",
]
