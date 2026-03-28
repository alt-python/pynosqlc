# pynosqlc

A JDBC-inspired unified async NoSQL access layer for Python — switch databases by changing a URL string.

## Packages

| Package | Description | Install |
|---|---|---|
| alt-python-pynosqlc-core | ABCs, DriverManager, Filter, compliance suite | `pip install alt-python-pynosqlc-core` |
| alt-python-pynosqlc-memory | Zero-dep in-memory driver (testing/CI) | `pip install alt-python-pynosqlc-memory` |
| alt-python-pynosqlc-mongodb | MongoDB driver (pymongo AsyncMongoClient) | `pip install alt-python-pynosqlc-mongodb` |
| alt-python-pynosqlc-dynamodb | DynamoDB driver (aioboto3) | `pip install alt-python-pynosqlc-dynamodb` |
| alt-python-pynosqlc-cosmosdb | Azure Cosmos DB driver (azure-cosmos aio) | `pip install alt-python-pynosqlc-cosmosdb` |
| alt-python-pynosqlc-redis | Redis driver (redis-py async) | `pip install alt-python-pynosqlc-redis` |
| alt-python-pynosqlc-cassandra | Cassandra driver (cassandra-driver, async-wrapped) | `pip install alt-python-pynosqlc-cassandra` |

## Quick Start

### Memory (zero setup)

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.memory  # auto-registers MemoryDriver

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice', 'age': 30})
        async for doc in await col.find(Filter.where('age').gt(25).build()):
            print(doc)

asyncio.run(main())
```

### Switching to MongoDB (change one line)

```python
import pynosqlc.mongodb  # auto-registers MongoDriver

# Replace the URL — everything else stays the same:
async with await DriverManager.get_client('pynosqlc:mongodb://localhost:27017/mydb') as client:
    ...
```

## All Drivers

| URL | Package | Backend |
|---|---|---|
| `pynosqlc:memory:` | `alt-python-pynosqlc-memory` | In-memory (testing/CI) — zero dependencies |
| `pynosqlc:mongodb://<host>:<port>/<db>` | `alt-python-pynosqlc-mongodb` | MongoDB (pymongo AsyncMongoClient) |
| `pynosqlc:dynamodb:<region>` | `alt-python-pynosqlc-dynamodb` | AWS DynamoDB (aioboto3) |
| `pynosqlc:cosmosdb:<endpoint>` | `alt-python-pynosqlc-cosmosdb` | Azure Cosmos DB (azure-cosmos aio) |
| `pynosqlc:redis://<host>:<port>` | `alt-python-pynosqlc-redis` | Redis 7 (redis-py async) |
| `pynosqlc:cassandra:<host>:<port>/<keyspace>` | `alt-python-pynosqlc-cassandra` | Cassandra 4 (cassandra-driver) |

## Filter Operators

| Method | Description | Example |
|---|---|---|
| `.eq(v)` | Equal | `.where('status').eq('active')` |
| `.ne(v)` | Not equal | `.where('status').ne('deleted')` |
| `.gt(v)` | Greater than | `.where('age').gt(18)` |
| `.gte(v)` | Greater than or equal | `.where('score').gte(100)` |
| `.lt(v)` | Less than | `.where('price').lt(50)` |
| `.lte(v)` | Less than or equal | `.where('qty').lte(0)` |
| `.contains(v)` | Contains value | `.where('tags').contains('python')` |
| `.in_(v)` | In list | `.where('role').in_(['admin', 'user'])` |
| `.nin(v)` | Not in list | `.where('status').nin(['banned'])` |
| `.exists(b)` | Field exists | `.where('email').exists(True)` |

## Chaining Filters

Filters chain with `.and_()` for multiple conditions, `Filter.or_()` for alternatives, and `.not_()` for negation:

```python
from pynosqlc.core import Filter

# AND: age > 18 AND status == 'active'
f = Filter.where('age').gt(18).and_('status').eq('active')

# OR: status == 'trial' OR status == 'premium'
f = Filter.or_(
    Filter.where('status').eq('trial'),
    Filter.where('status').eq('premium'),
)

# NOT: exclude banned users
f = Filter.where('status').eq('banned').not_()
```

## Requirements

- Python 3.12+
- Async-first: all collection methods are `async def`
