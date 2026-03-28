# pynosqlc-redis

Redis driver for [pynosqlc](https://github.com/alt-python/pynosqlc) — connects to a Redis 7 instance via redis-py (async).

## Install

```
pip install pynosqlc-redis
```

## Requirements

- Python 3.12+
- redis 5.0+ (`redis[asyncio]`)
- A running Redis 7 instance

## Usage

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.redis  # auto-registers RedisDriver

async def main():
    async with await DriverManager.get_client('pynosqlc:redis://localhost:6379') as client:
        col = client.get_collection('orders')

        # store / get
        await col.store('o1', {'item': 'widget', 'qty': 5})
        doc = await col.get('o1')
        print(doc)  # {'item': 'widget', 'qty': 5}

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
pynosqlc:redis://<host>:<port>
```

Examples:

| URL | Description |
|---|---|
| `pynosqlc:redis://localhost:6379` | Local Redis on default port |
| `pynosqlc:redis://redis.example.com:6379` | Remote Redis instance |

The `pynosqlc:` prefix is stripped before the URL is passed to redis-py, so any URL scheme accepted by `redis.asyncio.from_url` (including `rediss://` for TLS) works by replacing `redis://` in the URL.

## Storage layout

| Redis key | Type | Contents |
|---|---|---|
| `pynosqlc:<collection>:<doc_key>` | String | JSON-serialised document |
| `pynosqlc:<collection>:_keys` | Set | All doc keys in the collection |

Documents are stored as JSON strings. All key lookups use the namespaced prefix `pynosqlc:<collection>:`. The Set index holds all doc keys and is used to enumerate documents during `find`.

## Filtering

Filters are evaluated **in-process** after fetching all documents from Redis. There is no server-side query translation. For large collections, consider limiting result sets at the application level or adding a Redis Search integration.

## Notes

- All connections use `decode_responses=True` — documents round-trip as strings, not bytes.
- `find` uses a Redis pipeline for a single-round-trip batch GET of all documents.
- No connection pooling configuration is exposed; redis-py's default connection pool is used.
