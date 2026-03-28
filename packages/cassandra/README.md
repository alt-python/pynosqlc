# pynosqlc-cassandra

Cassandra 4 driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — a
JDBC-inspired unified async NoSQL access layer for Python.

Install this driver to connect pynosqlc to a Cassandra 4 instance using the
cassandra-driver library, bridged into Python's asyncio via
`asyncio.run_in_executor`. All pynosqlc operations — `store`, `get`, `insert`,
`update`, `delete`, and `find` — are supported.

## Requirements

- Python 3.12+
- Cassandra 4.0+ instance (local or remote)
- `pynosqlc-core` and `pynosqlc-memory` (installed automatically as dependencies)

## Installation

```bash
pip install alt-python-pynosqlc-cassandra
```

## Quick Start

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.cassandra  # auto-registers CassandraDriver on import

async def main():
    async with await DriverManager.get_client(
        'pynosqlc:cassandra:localhost:9042/my_keyspace'
    ) as client:
        col = client.get_collection('orders')

        # Store a document at a known key (upsert semantics)
        await col.store('order-001', {'item': 'widget', 'qty': 5, 'status': 'pending'})

        # Retrieve a document by key
        doc = await col.get('order-001')
        print(doc)  # {'item': 'widget', 'qty': 5, 'status': 'pending', '_id': 'order-001'}

        # Insert a document with a driver-assigned key
        key = await col.insert({'item': 'gadget', 'qty': 2, 'status': 'pending'})
        print(key)  # e.g. 'a1b2c3d4-...'

        # Update fields (shallow merge — only listed fields change)
        await col.update('order-001', {'qty': 10, 'status': 'shipped'})

        # Find documents matching a filter
        f = Filter.where('status').eq('pending').build()
        async for doc in await col.find(f):
            print(doc)

        # Delete a document
        await col.delete('order-001')

asyncio.run(main())
```

## URL Scheme

```
pynosqlc:cassandra:<host>:<port>/<keyspace>
```

| URL | Description |
|-----|-------------|
| `pynosqlc:cassandra:localhost:9042/my_keyspace` | Local Cassandra, named keyspace |
| `pynosqlc:cassandra:cassandra.example.com:9042/prod` | Remote instance |

The `<keyspace>` segment is required. If the keyspace does not exist, the driver
creates it automatically using `SimpleStrategy` with replication factor 1. For
production use, create the keyspace manually with appropriate replication
settings before connecting.

## Schema

Each pynosqlc collection maps to a Cassandra table in the configured keyspace:

```cql
CREATE TABLE IF NOT EXISTS <collection_name> (
    pk   TEXT PRIMARY KEY,
    data TEXT
);
```

- `pk` — the document key (string)
- `data` — the document serialised as a JSON string

Tables are created automatically on the first operation against a collection.
You do not need to create tables manually.

## Filtering

Filters are evaluated **in-process** after a full table scan. `find()` fetches
every row from the collection table, deserialises the `data` column, then
applies the pynosqlc filter AST in memory using `MemoryFilterEvaluator`. There
is no CQL WHERE clause generated.

This matches the design of the jsnosqlc Cassandra driver and is appropriate for
development, testing, and moderate-sized collections. For production workloads
with large tables, evaluate CQL secondary indexes or materialised views as
complementary tools.

All filter operators are supported: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`,
`contains`, `in_`, `nin`, `exists`, and their `and_` / `or_` / `not_`
combinators.

## Async Integration

cassandra-driver uses a synchronous API. This driver wraps every blocking CQL
call in `asyncio.get_event_loop().run_in_executor(None, ...)` so the asyncio
event loop is never blocked. The default cassandra-driver reactor
(thread-based) is used. Do not set `connection_class=AsyncioConnection` —
`AsyncioConnection` hooks into the event loop from the main thread and cannot
be used from a thread-pool executor.

## Troubleshooting

**`NoHostAvailable` or `ConnectionException` on connect**
Cassandra is not running or is not reachable on the configured host and port.
Verify with `cqlsh <host> <port>` — you should reach the CQL shell prompt.

**`ImportError: No module named 'pynosqlc.cassandra'`**
The package is not installed. Run `pip install alt-python-pynosqlc-cassandra`.

**`ValueError: No driver found for URL ...`**
The import `import pynosqlc.cassandra` was not executed before calling
`DriverManager.get_client(...)`. The import is what triggers driver
registration — it must come before any `get_client` call.

**`InvalidRequest: Keyspace '<name>' does not exist`**
This should not occur in normal use because the driver creates the keyspace
automatically. If you see this error, check that the connecting user has
`CREATE KEYSPACE` permission, or create the keyspace manually:

```cql
CREATE KEYSPACE my_keyspace
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
```

**Filter returns no results despite documents being present**
Confirm you called `.build()` at the end of your filter chain:
`Filter.where('field').eq('value').build()`. Passing an unbuilt `FieldCondition`
object instead of the built `dict` will match nothing.

## Further Reading

- [pynosqlc API reference](../../docs/api-reference.md) — complete method signatures
- [Driver implementation guide](../../docs/driver-guide.md) — how pynosqlc drivers work
- [Getting started tutorial](../../docs/getting-started.md) — step-by-step introduction
