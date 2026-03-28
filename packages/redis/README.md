# pynosqlc-redis

Redis 7 driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — a
JDBC-inspired unified async NoSQL access layer for Python.

Install this driver to connect pynosqlc to a Redis 7 instance using the
redis-py async client. All pynosqlc operations — `store`, `get`, `insert`,
`update`, `delete`, and `find` — are supported.

## Requirements

- Python 3.12+
- Redis 7.0+ instance (local or remote)
- `pynosqlc-core` and `pynosqlc-memory` (installed automatically as dependencies)

## Installation

```bash
pip install alt-python-pynosqlc-redis
```

## Quick Start

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.redis  # auto-registers RedisDriver on import

async def main():
    async with await DriverManager.get_client('pynosqlc:redis://localhost:6379') as client:
        col = client.get_collection('orders')

        # Store a document at a known key (upsert semantics)
        await col.store('order-001', {'item': 'widget', 'qty': 5, 'status': 'pending'})

        # Retrieve a document by key
        doc = await col.get('order-001')
        print(doc)  # {'item': 'widget', 'qty': 5, 'status': 'pending'}

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
pynosqlc:redis://<host>:<port>
```

The `pynosqlc:` prefix is stripped before the URL is passed to redis-py, so
`redis://` becomes the effective scheme. Any format accepted by
`redis.asyncio.from_url` can be used, including `rediss://` for TLS:

| URL | Description |
|-----|-------------|
| `pynosqlc:redis://localhost:6379` | Local Redis on the default port |
| `pynosqlc:redis://redis.example.com:6379` | Remote Redis instance |
| `pynosqlc:rediss://redis.example.com:6380` | Remote Redis with TLS (`rediss://`) |

## Storage Layout

Each document and collection index is stored as a separate Redis key:

| Redis key | Type | Contents |
|-----------|------|----------|
| `pynosqlc:<collection>:<doc_key>` | String | JSON-serialised document |
| `pynosqlc:<collection>:_keys` | Set | All doc keys in the collection |

For example, storing a document in the `orders` collection under key `order-001`
creates:

- `pynosqlc:orders:order-001` → `{"item": "widget", "qty": 5}`
- `pynosqlc:orders:_keys` → `{"order-001"}`

## Filtering

Filters are evaluated **in-process** after fetching all documents from Redis.
`find()` retrieves the entire collection in a single pipeline batch GET, then
applies the pynosqlc filter AST in memory using `MemoryFilterEvaluator`.

There is no server-side query translation. For collections expected to hold
large numbers of documents, consider partitioning data into smaller collections
or evaluating Redis Search as a complementary tool.

All filter operators are supported: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`,
`contains`, `in_`, `nin`, `exists`, and their `and_` / `or_` / `not_`
combinators.

## Connection Notes

- All connections use `decode_responses=True` — values are returned as `str`,
  so there is no byte-decoding step before `json.loads`.
- redis-py's default connection pool is used; pool size is not currently
  configurable through pynosqlc's `properties` argument.
- `find()` uses a Redis pipeline with `transaction=False` to batch-GET all
  documents in a single round trip without acquiring a `MULTI/EXEC` lock.

## Troubleshooting

**`ConnectionError: Error 111 connecting to localhost:6379`**
Redis is not running or is not reachable on the configured host and port.
Verify with `redis-cli -h <host> -p <port> ping` — you should receive `PONG`.

**`ImportError: No module named 'pynosqlc.redis'`**
The package is not installed. Run `pip install alt-python-pynosqlc-redis`.

**`ValueError: No driver found for URL ...`**
The import `import pynosqlc.redis` was not executed before calling
`DriverManager.get_client(...)`. The import is what triggers driver
registration — it must come before any `get_client` call.

**Filter returns no results despite documents being present**
Confirm you called `.build()` at the end of your filter chain:
`Filter.where('field').eq('value').build()`. Passing an unbuilt `FieldCondition`
object instead of the built `dict` will match nothing.

## Further Reading

- [pynosqlc API reference](../../docs/api-reference.md) — complete method signatures
- [Driver implementation guide](../../docs/driver-guide.md) — how pynosqlc drivers work
- [Getting started tutorial](../../docs/getting-started.md) — step-by-step introduction
