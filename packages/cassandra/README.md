# pynosqlc-cassandra

Cassandra driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — connects to a Cassandra 4 instance via cassandra-driver (sync wrapped with run_in_executor).

## Install

```
pip install pynosqlc-cassandra
```

## Requirements

- Python 3.12+
- cassandra-driver 3.29.1+
- A running Cassandra 4 instance

## Usage

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.cassandra  # auto-registers CassandraDriver

async def main():
    async with await DriverManager.get_client(
        'pynosqlc:cassandra:localhost:9042/pynosqlc_test'
    ) as client:
        col = client.get_collection('orders')

        # store / get
        await col.store('o1', {'item': 'widget', 'qty': 5})
        doc = await col.get('o1')
        print(doc)  # {'item': 'widget', 'qty': 5, '_id': 'o1'}

        # insert (auto-generates _id)
        key = await col.insert({'item': 'gadget', 'qty': 2})

        # update (merge patch)
        await col.update('o1', {'qty': 10})

        # find with filter
        f = Filter.where('qty').gt(3).build()
        async for doc in await col.find(f):
            print(doc)

        # delete
        await col.delete('o1')

asyncio.run(main())
```

## URL scheme

```
pynosqlc:cassandra:<host>:<port>/<keyspace>
```

Examples:

| URL | Description |
|---|---|
| `pynosqlc:cassandra:localhost:9042/pynosqlc_test` | Local Cassandra, named keyspace |
| `pynosqlc:cassandra:localhost:9042/pynosqlc` | Local Cassandra, default keyspace |
| `pynosqlc:cassandra:cassandra.example.com:9042/prod` | Remote instance |

## Storage layout

Each pynosqlc collection maps to a Cassandra table in the active keyspace:

```cql
CREATE TABLE IF NOT EXISTS <collection_name> (
    pk   TEXT PRIMARY KEY,
    data TEXT
)
```

Documents are stored as JSON strings in the `data` column. The `pk` column holds the document key.

## Filtering

Filters are evaluated **in-process** after a full table scan. There is no CQL translation — suitable for test/dev workloads.

## Notes

- cassandra-driver uses a synchronous API; all blocking calls run via `asyncio.run_in_executor`.
- The default cassandra-driver reactor (thread-based) is used rather than `AsyncioConnection`, since `AsyncioConnection` cannot hook into the asyncio event loop from a thread-pool executor thread.
- The keyspace is created automatically with `SimpleStrategy` replication factor 1 on first connect.
- Tables are created automatically on first use of each collection.
