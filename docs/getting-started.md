# Getting Started with pynosqlc

pynosqlc is a JDBC-inspired unified async NoSQL access layer for Python.
The central idea: switch databases by changing a URL string — your application
code is identical whether you are talking to an in-memory store, MongoDB,
DynamoDB, or Cosmos DB.

This tutorial takes you from a fresh virtual environment through storing,
querying, and switching backends. All code blocks run verbatim against the
zero-dependency in-memory driver.

---

## Prerequisites

- Python 3.12 or newer
- `pip` (bundled with CPython 3.12+)
- A terminal with an active virtual environment (see Installation)

---

## Installation

Create a virtual environment and install the two packages you need for this
tutorial:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install pynosqlc-core pynosqlc-memory
```

Create a file called `demo.py` — you will fill it in step by step below.

> **PyPI status:** pynosqlc packages are currently distributed as source
> distributions. Install from the repo root with
> `pip install packages/core packages/memory` if you are working from the
> source tree.

---

## Step 1: Connect and Store

The entry point for every pynosqlc program is `DriverManager.get_client()`.
It is an `async def` coroutine, so you must `await` it before passing the
result to `async with`:

```python
import asyncio
from pynosqlc.core import DriverManager
import pynosqlc.memory          # auto-registers MemoryDriver on import

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')

        # store() writes a document at a known key (upsert semantics)
        await col.store('u1', {'name': 'Alice', 'age': 30, 'role': 'admin'})

        # get() retrieves the document by key
        alice = await col.get('u1')
        print('get:', alice['name'], alice['age'])

asyncio.run(main())
# get: Alice 30
```

**JS → Python:** In JavaScript you write `async with (await DriverManager.getClient(...))`.
Python requires the same two-step pattern: `await` the coroutine first,
then enter the context manager with `async with`.

The context manager calls `client.close()` on exit regardless of exceptions,
so you never leak connections.

---

## Step 2: Insert and Update

`insert()` writes a document without a pre-assigned key and returns the key
the driver assigned. `update()` shallow-merges the supplied fields into the
existing document — it does not replace it wholesale.

```python
import asyncio
from pynosqlc.core import DriverManager
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')

        # insert() returns the assigned key
        key = await col.insert({'name': 'Bob', 'age': 25, 'role': 'viewer'})
        print('assigned key:', key)

        # update() merges — only the supplied fields change
        await col.update(key, {'role': 'editor'})
        bob = await col.get(key)
        print('after update:', bob['role'])   # editor
        print('unchanged:', bob['name'])       # Bob

asyncio.run(main())
# assigned key: <driver-generated id>
# after update: editor
# unchanged: Bob
```

**JS → Python:** Method names follow Python snake_case conventions:
`get_client`, `get_collection`, `get_documents` — not camelCase.

---

## Step 3: Query with a Filter

`col.find()` accepts a filter AST produced by `Filter.where(...).build()`.
You must always call `.build()` — `find()` takes the dict, not the `Filter`
object itself.

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice', 'age': 30, 'role': 'admin'})
        await col.store('u2', {'name': 'Bob',   'age': 25, 'role': 'editor'})
        await col.store('u3', {'name': 'Carol', 'age': 17, 'role': 'viewer'})

        # Find everyone older than 18 AND whose role is 'admin'
        ast = Filter.where('age').gt(18).and_('role').eq('admin').build()
        cursor = await col.find(ast)

        async for doc in cursor:
            print('found:', doc['name'])

asyncio.run(main())
# found: Alice
```

**JS → Python:** `.build()` is always explicit. JavaScript's `find()` accepted
a builder object directly; Python's `find()` requires the plain dict produced
by `.build()`.

---

## Step 4: Iterate a Cursor

`col.find()` returns a `Cursor`. There are two ways to consume it:

**`async for` (recommended):** Yields one document at a time. The cursor
closes automatically when iteration is complete.

```python
cursor = await col.find(ast)
async for doc in cursor:
    print(doc['name'])
```

**`cursor.get_documents()` (bulk):** Returns all buffered documents as a list
of shallow copies, without needing to call `next()` first. Useful when you
want to process results as a list rather than streaming them.

```python
cursor = await col.find(ast)
docs = cursor.get_documents()
for doc in docs:
    print(doc['name'])
```

**JS → Python:** `async for doc in cursor:` replaces JavaScript's
`for await (const doc of cursor)` idiom.

---

## Step 5: Chained and Compound Filters

The filter builder supports AND chains, OR combinations, and NOT negation.
Method names ending with an underscore (`and_`, `or_`, `in_`) avoid collision
with Python reserved keywords (PEP 8 trailing underscore convention).

### AND chain

```python
# age > 18 AND role == 'admin'
ast = Filter.where('age').gt(18).and_('role').eq('admin').build()
```

### OR combination

`Filter.or_()` is a classmethod that accepts two or more built ASTs
(or `Filter` instances — `.build()` is called automatically):

```python
# role == 'admin' OR role == 'editor'
ast = Filter.or_(
    Filter.where('role').eq('admin'),
    Filter.where('role').eq('editor'),
)
# ast is already a plain dict — do NOT call .build() on the result
```

### NOT negation

Call `.not_()` on a `Filter` instance (after chaining, before `.build()`):

```python
# NOT (age >= 18)  →  everyone under 18
ast = Filter.where('age').gte(18).not_()
```

### Full example

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice', 'age': 30, 'role': 'admin'})
        await col.store('u2', {'name': 'Bob',   'age': 25, 'role': 'editor'})
        await col.store('u3', {'name': 'Carol', 'age': 17, 'role': 'viewer'})

        # OR: admin or editor
        ast = Filter.or_(
            Filter.where('role').eq('admin'),
            Filter.where('role').eq('editor'),
        )
        cursor = await col.find(ast)
        docs = cursor.get_documents()
        print('OR:', sorted(d['name'] for d in docs))

        # NOT: under 18
        ast = Filter.where('age').gte(18).not_()
        cursor = await col.find(ast)
        async for doc in cursor:
            print('NOT:', doc['name'])

asyncio.run(main())
# OR: ['Alice', 'Bob']
# NOT: Carol
```

---

## Step 6: Switch to MongoDB

This is the point of pynosqlc — changing backends means changing a URL string
and one import. Nothing else in your application changes.

**Memory (zero setup):**

```python
import pynosqlc.memory

async with await DriverManager.get_client('pynosqlc:memory:') as client:
    ...
```

**MongoDB (change two lines):**

```python
import pynosqlc.mongodb          # ← swap the import

async with await DriverManager.get_client(
    'pynosqlc:mongodb://localhost:27017/mydb'    # ← swap the URL
) as client:
    col = client.get_collection('users')        # everything else is identical
    await col.store('u1', {'name': 'Alice', 'age': 30})
    ...
```

The database name is embedded in the URL path (`/mydb`). Install the driver
with:

```bash
pip install pynosqlc-mongodb
```

Other available drivers:

| URL prefix | Package | Backend |
|---|---|---|
| `pynosqlc:memory:` | `pynosqlc-memory` | In-memory (testing/CI) |
| `pynosqlc:mongodb://...` | `pynosqlc-mongodb` | MongoDB (pymongo async) |
| `pynosqlc:dynamodb:` | `pynosqlc-dynamodb` | AWS DynamoDB (aioboto3) |
| `pynosqlc:cosmosdb:` | `pynosqlc-cosmosdb` | Azure Cosmos DB (azure-cosmos aio) |

---

## What You've Learned

- **`async with await DriverManager.get_client(url)`** — always `await` the coroutine before entering the context manager
- **`client.get_collection(name)`** — returns a cached collection; no await needed
- **`store(key, doc)` / `get(key)`** — upsert at a known key; retrieve by key
- **`insert(doc)`** — driver-assigned key, returned as a string
- **`update(key, fields)`** — shallow merge; only supplied fields change
- **`Filter.where(field).op(value).and_(...).build()`** — always end chains with `.build()`
- **`Filter.or_(...)`** — classmethod returning a ready-to-use AST dict
- **`filter.not_()`** — wraps the current filter in a not node
- **`async for doc in cursor:`** — idiomatic async iteration
- **`cursor.get_documents()`** — bulk access without iteration
- **Switching backends:** one import + one URL string

### Next Steps

- [`docs/api-reference.md`](api-reference.md) — full method signatures and return types for all `Collection`, `Cursor`, `Filter`, and `DriverManager` APIs
- [`docs/driver-guide.md`](driver-guide.md) — connection properties, authentication, and driver-specific configuration for MongoDB, DynamoDB, and Cosmos DB
