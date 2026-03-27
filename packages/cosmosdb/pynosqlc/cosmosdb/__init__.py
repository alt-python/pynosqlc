"""
pynosqlc.cosmosdb — Azure Cosmos DB driver for pynosqlc.

Importing this package auto-registers the CosmosDriver with the global
DriverManager via the module-level ``_driver`` sentinel in cosmos_driver.py.
"""

from pynosqlc.cosmosdb.cosmos_driver import CosmosDriver, _driver
from pynosqlc.cosmosdb.cosmos_client import CosmosClient
from pynosqlc.cosmosdb.cosmos_collection import CosmosCollection

__all__ = ["CosmosDriver", "CosmosClient", "CosmosCollection", "_driver"]
