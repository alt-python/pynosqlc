# pynosqlc-mongodb

MongoDB driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — connects to MongoDB via pymongo's `AsyncMongoClient`.

## Install

```
pip install alt-python-pynosqlc-mongodb
```

## Requirements

- Python 3.12+
- MongoDB 4.4+
- pymongo 4.6+

## Usage

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.mongodb  # auto-registers MongoDriver

async def main():
    async with await DriverManager.get_client(
        'pynosqlc:mongodb://localhost:27017/mydb'
    ) as client:
        col = client.get_collection('orders')
        await col.store('o1', {'item': 'widget', 'qty': 5})
        f = Filter.where('qty').gt(0).build()
        async for doc in await col.find(f):
            print(doc)

asyncio.run(main())
```

## URL scheme

```
pynosqlc:mongodb://<host>:<port>/<dbname>
```

Example: `pynosqlc:mongodb://localhost:27017/mydb`

The `pynosqlc:` prefix is stripped before passing the URL to pymongo — the
remainder is a standard MongoDB connection string, so replica set URIs and
authentication options (e.g. `mongodb://user:pass@host/db`) work as-is.
