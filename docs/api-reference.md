# pynosqlc API Reference

This document covers every public symbol in `pynosqlc.core`. All nine symbols
are importable from the top-level package:

```python
from pynosqlc.core import (
    DriverManager,
    ClientDataSource,
    Client,
    Collection,
    Cursor,
    Filter,
    FieldCondition,
    Driver,
    UnsupportedOperationError,
)
```

---

## DriverManager

Class-level (all methods are `@classmethod`) registry that maps pynosqlc URLs
to registered driver instances. Drivers call `DriverManager.register_driver()`
on import to advertise themselves. Applications call `get_client()` to open a
connection.

```python
from pynosqlc.core import DriverManager
import pynosqlc.memory  # auto-registers MemoryDriver

# Open a connection (get_client is async — always await it)
client = await DriverManager.get_client('pynosqlc:memory:')
await client.close()

# Preferred: use the async context manager
async with await DriverManager.get_client('pynosqlc:memory:') as client:
    col = client.get_collection('items')
```

### Methods

#### `DriverManager.get_client(url, properties=None)` → `Client` *(async)*

Return a `Client` from the first registered driver that accepts `url`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | pynosqlc URL (e.g. `'pynosqlc:memory:'`) |
| `properties` | `dict \| None` | Optional driver-specific connection properties |

**Returns:** `Client` — an open connection to the database.

**Raises:** `ValueError` — if no registered driver accepts the URL.

> **Important:** `get_client` is an `async def` coroutine. You must `await` it
> before entering `async with`. The pattern `async with await DriverManager.get_client(url) as client:` 
> is intentional — two operations: first `await` the coroutine, then enter the context manager.

#### `DriverManager.register_driver(driver)` → `None`

Register a `Driver` instance. Idempotent — registering the same instance twice
has no effect.

| Parameter | Type | Description |
|-----------|------|-------------|
| `driver` | `Driver` | Driver instance to register |

#### `DriverManager.deregister_driver(driver)` → `None`

Remove a previously registered driver instance.

| Parameter | Type | Description |
|-----------|------|-------------|
| `driver` | `Driver` | Driver instance to remove |

#### `DriverManager.clear()` → `None`

Remove all registered drivers. Primarily used in tests to reset state between
test cases. After calling `clear()`, no URLs will be accepted until drivers are
re-registered.

#### `DriverManager.get_drivers()` → `list[Driver]`

Return a copy of the current list of registered driver instances.

```python
drivers = DriverManager.get_drivers()
print([type(d).__name__ for d in drivers])
```

---

## ClientDataSource

A convenience factory that wraps `DriverManager.get_client()` and stores
connection configuration for repeated use. Mirrors the DataSource pattern from
JDBC.

```python
from pynosqlc.core import ClientDataSource
import pynosqlc.memory

ds = ClientDataSource({'url': 'pynosqlc:memory:'})
async with await ds.get_client() as client:
    col = client.get_collection('orders')
    await col.store('o1', {'amount': 99.0})
```

### Constructor

```python
ClientDataSource(config: dict | None = None)
```

| Config key | Type | Required | Description |
|------------|------|----------|-------------|
| `url` | `str` | Yes | pynosqlc URL string |
| `username` | `str` | No | Passed to the driver as a property |
| `password` | `str` | No | Passed to the driver as a property |
| `properties` | `dict` | No | Additional driver-specific options |

`config['url']` is required — a `KeyError` is raised if it is absent.

### Methods

#### `get_client()` → `Client` *(async)*

Open and return a new `Client` using the configured URL and properties.
Equivalent to calling `DriverManager.get_client(url, properties)` directly.

```python
client = await ds.get_client()
# remember to close when done, or use async with:
async with await ds.get_client() as client:
    ...
```

#### `get_url()` → `str`

Return the pynosqlc URL this data source was configured with.

```python
ds = ClientDataSource({'url': 'pynosqlc:memory:'})
print(ds.get_url())  # pynosqlc:memory:
```

---

## Client

Abstract base class for a database session. Driver implementations subclass
`Client` and override `_get_collection()` and `_close()`. Application code
uses only the public methods documented here.

`Client` implements the async context manager protocol — use `async with` to
ensure `close()` is called even when exceptions occur.

```python
async with await DriverManager.get_client('pynosqlc:memory:') as client:
    col = client.get_collection('sessions')
    # client is automatically closed when the block exits
```

### Methods

#### `get_collection(name)` → `Collection` *(sync)*

Return a (cached) `Collection` for `name`. Subsequent calls with the same name
return the same instance.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Collection (table / bucket) name |

**Returns:** `Collection`

**Raises:** `RuntimeError` — if the client has already been closed.

> **Note:** `get_collection` is synchronous — do **not** `await` it.

```python
col = client.get_collection('users')   # no await
```

#### `close()` → `None` *(async)*

Close the client and release all driver-specific resources. Calling `close()`
more than once is safe.

```python
await client.close()
```

#### `is_closed()` → `bool` *(sync)*

Return `True` if the client has been closed.

```python
if client.is_closed():
    print('already closed')
```

#### `get_url()` → `str | None` *(sync)*

Return the pynosqlc URL this client was opened with, or `None` if the client
was constructed without a URL.

```python
print(client.get_url())  # e.g. 'pynosqlc:memory:'
```

---

## Collection

Abstract base class for a named collection within a database (equivalent to a
table, bucket, or container depending on the backend). Driver implementations
subclass `Collection` and override the `_` hook methods.

All mutating methods (`store`, `delete`, `insert`, `update`) are `async` and
must be awaited. Methods that do not perform I/O (`get_name`) are synchronous.

```python
col = client.get_collection('products')
await col.store('p1', {'name': 'Widget', 'price': 9.99})
product = await col.get('p1')
print(product['name'])   # Widget
```

### Methods

#### `get(key)` → `dict | None` *(async)*

Retrieve a document by its primary key.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Primary key |

**Returns:** The document `dict`, or `None` if the key does not exist.

```python
doc = await col.get('p1')
if doc is None:
    print('not found')
```

#### `store(key, doc)` → `None` *(async)*

Store (upsert) a document under `key`. If a document already exists at `key`
it is fully replaced.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Primary key |
| `doc` | `dict` | Document to store |

```python
await col.store('p1', {'name': 'Widget', 'price': 9.99})
```

#### `delete(key)` → `None` *(async)*

Delete the document at `key`. No-op if the key does not exist.

```python
await col.delete('p1')
```

#### `insert(doc)` → `str` *(async)*

Insert a document and return the backend-assigned primary key. Use this when
you do not have a meaningful key to supply — the driver generates one.

| Parameter | Type | Description |
|-----------|------|-------------|
| `doc` | `dict` | Document to insert |

**Returns:** `str` — the generated primary key.

```python
key = await col.insert({'name': 'Gadget', 'price': 49.99})
print('assigned key:', key)
```

#### `update(key, patch)` → `None` *(async)*

Shallow-merge `patch` into the existing document at `key`. Only the fields in
`patch` are changed; all other fields are preserved.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Primary key of the document to update |
| `patch` | `dict` | Fields to merge into the document |

**Raises:** `RuntimeError` — if the key does not exist.

```python
await col.update('p1', {'price': 7.99})   # only price changes
```

#### `find(filter_ast)` → `Cursor` *(async)*

Query the collection for documents matching the given filter AST.

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter_ast` | `dict` | AST dict produced by `Filter.build()` or `Filter.or_()` |

**Returns:** `Cursor` — iterate with `async for` or call `get_documents()`.

```python
from pynosqlc.core import Filter

ast = Filter.where('price').lt(10.0).build()
cursor = await col.find(ast)
async for doc in cursor:
    print(doc['name'])
```

#### `get_name()` → `str` *(sync)*

Return the name this collection was opened with.

```python
print(col.get_name())   # e.g. 'products'
```

---

## Cursor

An async-iterable cursor over the documents returned by `Collection.find()`.
The base implementation buffers all results in memory. Driver implementations
may subclass `Cursor` to support streaming.

```python
cursor = await col.find(ast)

# Option 1: async for (recommended — closes automatically on exhaustion)
async for doc in cursor:
    print(doc)

# Option 2: manual next/get_document loop
while await cursor.next():
    doc = cursor.get_document()
    print(doc)
await cursor.close()

# Option 3: bulk access (no iteration required)
docs = cursor.get_documents()
```

### Methods

#### `next()` → `bool` *(async)*

Advance to the next document.

**Returns:** `True` if there is a current document; `False` when the cursor is
exhausted.

```python
while await cursor.next():
    print(cursor.get_document())
```

#### `get_document()` → `dict` *(sync)*

Return a shallow copy of the document at the current cursor position.

**Raises:** `RuntimeError` — if `next()` has not been called, or the cursor is
exhausted or closed.

#### `get_documents()` → `list[dict]` *(sync)*

Return all buffered documents as a list of shallow copies. Does not require
`next()` to have been called first. Useful for bulk access.

```python
cursor = await col.find(ast)
all_docs = cursor.get_documents()
```

#### `close()` → `None` *(async)*

Close the cursor and release resources. Called automatically when `async for`
iteration completes.

```python
await cursor.close()
```

#### `is_closed()` → `bool` *(sync)*

Return `True` if the cursor has been closed.

---

## Filter

A chainable filter builder. Use the fluent API to construct a query, then call
`build()` to produce the AST dict that `Collection.find()` accepts.

```python
from pynosqlc.core import Filter

# Single condition
ast = Filter.where('age').gt(18).build()

# AND chain
ast = Filter.where('age').gt(18).and_('role').eq('admin').build()

# OR combination
ast = Filter.or_(
    Filter.where('role').eq('admin'),
    Filter.where('role').eq('editor'),
)

# NOT negation
ast = Filter.where('age').gte(18).not_()
```

> **Python keyword avoidance:** `and_()`, `or_()`, and `not_()` have trailing
> underscores to avoid collision with Python reserved keywords, following
> PEP 8 convention.

### Class Methods

#### `Filter.where(field)` → `FieldCondition`

Start a new filter on `field`. Returns a `FieldCondition` whose operator
methods add the condition to a new `Filter` and return it for chaining.

```python
fc = Filter.where('status')   # returns FieldCondition
f  = fc.eq('active')          # returns Filter
ast = f.build()               # returns dict
# or fluently:
ast = Filter.where('status').eq('active').build()
```

#### `Filter.or_(*filters)` → `dict`

Create an OR compound node from two or more `Filter` instances or pre-built
AST dicts. Each `Filter` argument has `build()` called automatically.

**Returns:** `{'type': 'or', 'conditions': [...]}` — a ready-to-use AST dict.
Do **not** call `.build()` on the result.

```python
ast = Filter.or_(
    Filter.where('role').eq('admin'),
    Filter.where('role').eq('editor'),
    Filter.where('role').eq('owner'),
)
cursor = await col.find(ast)
```

### Instance Methods

#### `filter.and_(field)` → `FieldCondition`

Chain an additional AND condition on a new field. Returns a `FieldCondition`
whose operator methods add the condition to this `Filter`.

```python
ast = (
    Filter.where('age').gt(18)
          .and_('country').eq('AU')
          .build()
)
```

#### `filter.not_()` → `dict`

Negate this filter. Calls `build()` internally and wraps the result in a not
node.

**Returns:** `{'type': 'not', 'condition': <ast>}` — a ready-to-use AST dict.
Do **not** call `.build()` on the result.

```python
ast = Filter.where('age').gte(18).not_()   # everyone under 18
```

#### `filter.build()` → `dict`

Build and return the filter AST. The return value depends on how many
conditions have been added:

| Conditions | Return value |
|------------|-------------|
| Zero | `{'type': 'and', 'conditions': []}` |
| One | The single leaf condition node directly |
| Two or more | `{'type': 'and', 'conditions': [...]}` |

Each call returns a fresh copy — mutating the result does not affect the
`Filter` instance.

```python
ast = Filter.where('active').eq(True).build()
# → {'type': 'condition', 'field': 'active', 'op': 'eq', 'value': True}

ast = Filter.where('a').eq(1).and_('b').eq(2).build()
# → {'type': 'and', 'conditions': [
#       {'type': 'condition', 'field': 'a', 'op': 'eq', 'value': 1},
#       {'type': 'condition', 'field': 'b', 'op': 'eq', 'value': 2},
#   ]}

empty = Filter().build()
# → {'type': 'and', 'conditions': []}
```

---

## FieldCondition Operators

`FieldCondition` is returned by `Filter.where()` and `filter.and_()`. Call one
of the operator methods below to add the condition to the parent `Filter` and
return the `Filter` for further chaining.

```python
from pynosqlc.core import Filter

ast = Filter.where('score').gte(90).and_('grade').ne('F').build()
```

All operator methods return the parent `Filter` instance.

### Operator Table

| Method | AST `op` | Semantics |
|--------|----------|-----------|
| `eq(value)` | `'eq'` | `field == value` |
| `ne(value)` | `'ne'` | `field != value` |
| `gt(value)` | `'gt'` | `field > value` |
| `gte(value)` | `'gte'` | `field >= value` |
| `lt(value)` | `'lt'` | `field < value` |
| `lte(value)` | `'lte'` | `field <= value` |
| `contains(value)` | `'contains'` | field is a string or list that contains `value` |
| `in_(values)` | `'in'` | `field` is one of `values` (a list) |
| `nin(values)` | `'nin'` | `field` is not one of `values` (a list) |
| `exists(value=True)` | `'exists'` | field is present (`True`) or absent/`None` (`False`) |

> **`in_()` AST key:** The `in_()` method writes the AST operator key as
> `'in'` (not `'in_'`). The trailing underscore is only a Python-level naming
> convention to avoid the `in` keyword. All driver implementations match
> against `'in'`.

### Examples

```python
# eq / ne
Filter.where('status').eq('active').build()
Filter.where('status').ne('deleted').build()

# gt / gte / lt / lte
Filter.where('age').gt(18).build()
Filter.where('score').gte(90).and_('score').lte(100).build()

# contains
Filter.where('tags').contains('python').build()

# in_ — note: AST op is 'in', not 'in_'
ast = Filter.where('role').in_(['admin', 'editor']).build()
assert ast['op'] == 'in'   # correct key

# nin
Filter.where('status').nin(['deleted', 'banned']).build()

# exists
Filter.where('email').exists().build()
Filter.where('deleted_at').exists(False).build()
```

---

## Filter AST

The filter AST is a plain Python `dict`. `Collection.find()` accepts the AST
directly — drivers interpret it to generate backend-specific queries.

There are four node shapes:

### Condition (leaf node)

```python
{
    'type': 'condition',
    'field': str,   # field name
    'op':   str,    # operator key (see FieldCondition Operators table)
    'value': any,   # operand value
}
```

**Example:**
```python
{'type': 'condition', 'field': 'age', 'op': 'gt', 'value': 18}
```

### And (conjunctive node)

```python
{
    'type': 'and',
    'conditions': [node, ...],   # list of child nodes
}
```

**Example:**
```python
{
    'type': 'and',
    'conditions': [
        {'type': 'condition', 'field': 'age', 'op': 'gt', 'value': 18},
        {'type': 'condition', 'field': 'role', 'op': 'eq', 'value': 'admin'},
    ]
}
```

Zero conditions is valid: `{'type': 'and', 'conditions': []}` — matches all
documents.

### Or (disjunctive node)

```python
{
    'type': 'or',
    'conditions': [node, ...],   # list of child nodes
}
```

**Example:**
```python
{
    'type': 'or',
    'conditions': [
        {'type': 'condition', 'field': 'role', 'op': 'eq', 'value': 'admin'},
        {'type': 'condition', 'field': 'role', 'op': 'eq', 'value': 'editor'},
    ]
}
```

### Not (negation node)

```python
{
    'type': 'not',
    'condition': node,   # single child node (not a list)
}
```

**Example:**
```python
{
    'type': 'not',
    'condition': {'type': 'condition', 'field': 'active', 'op': 'eq', 'value': False}
}
```

### Building ASTs directly

You may construct AST dicts by hand instead of using the `Filter` builder:

```python
ast = {
    'type': 'and',
    'conditions': [
        {'type': 'condition', 'field': 'age', 'op': 'gte', 'value': 18},
        {'type': 'condition', 'field': 'active', 'op': 'eq', 'value': True},
    ]
}
cursor = await col.find(ast)
```

---

## URL Scheme

pynosqlc URLs follow the pattern `pynosqlc:<subprotocol>:<connection-details>`.
The subprotocol and connection-details format vary by driver.

| URL | Package | Backend |
|-----|---------|---------|
| `pynosqlc:memory:` | `alt-python-pynosqlc-memory` | In-memory (testing / CI) — zero dependencies |
| `pynosqlc:mongodb://<host>:<port>/<db>` | `alt-python-pynosqlc-mongodb` | MongoDB (pymongo AsyncMongoClient) |
| `pynosqlc:dynamodb:<region>` | `alt-python-pynosqlc-dynamodb` | AWS DynamoDB (aioboto3) |
| `pynosqlc:cosmosdb:local` | `alt-python-pynosqlc-cosmosdb` | Azure Cosmos DB (Emulator) |
| `pynosqlc:cosmosdb:<https-endpoint>` | `alt-python-pynosqlc-cosmosdb` | Azure Cosmos DB (cloud) |
| `pynosqlc:redis://<host>:<port>` | `alt-python-pynosqlc-redis` | Redis 7 (redis-py async) |
| `pynosqlc:cassandra:<host>:<port>/<keyspace>` | `alt-python-pynosqlc-cassandra` | Cassandra 4 (cassandra-driver) |

**Memory driver** — no configuration beyond the URL:

```python
import pynosqlc.memory
client = await DriverManager.get_client('pynosqlc:memory:')
```

**MongoDB driver** — database name is the URL path:

```python
import pynosqlc.mongodb
client = await DriverManager.get_client('pynosqlc:mongodb://localhost:27017/mydb')
```

**DynamoDB driver** — region follows the subprotocol:

```python
import pynosqlc.dynamodb
client = await DriverManager.get_client('pynosqlc:dynamodb:us-east-1')
```

**Cosmos DB driver** — pass `db_id` in `properties`:

```python
import pynosqlc.cosmosdb
client = await DriverManager.get_client(
    'pynosqlc:cosmosdb:https://myaccount.documents.azure.com:443/',
    properties={'db_id': 'mydb'},
)
```

**Redis driver** — host and port follow the `redis://` scheme:

```python
import pynosqlc.redis
client = await DriverManager.get_client('pynosqlc:redis://localhost:6379')
```

Filters are evaluated in-process after a full collection scan. See
[`packages/redis/README.md`](../packages/redis/README.md) for storage layout
and TLS configuration details.

**Cassandra driver** — host, port, and keyspace are colon-separated:

```python
import pynosqlc.cassandra
client = await DriverManager.get_client(
    'pynosqlc:cassandra:localhost:9042/my_keyspace'
)
```

The keyspace is created automatically with `SimpleStrategy` replication factor 1
if it does not exist. Tables are created per collection on first use. Filters are
evaluated in-process after a full table scan. See
[`packages/cassandra/README.md`](../packages/cassandra/README.md) for schema
details.

See [`docs/driver-guide.md`](driver-guide.md) for authentication, TLS, and
driver-specific `properties` keys.

---

## Errors

### `UnsupportedOperationError`

```python
from pynosqlc.core import UnsupportedOperationError
```

`UnsupportedOperationError(Exception)` — raised by the default `Collection`
hook methods (`_get`, `_store`, `_delete`, `_insert`, `_update`, `_find`) when
a driver subclass does not override them.

```python
try:
    await col.find(ast)
except UnsupportedOperationError as e:
    print('driver does not support find():', e)
```

Driver subclasses may also raise `RuntimeError` for operational failures
(e.g. key not found in `update()`, client closed). Use `isinstance` checks to
distinguish the two:

```python
try:
    await col.update('missing-key', {'x': 1})
except RuntimeError as e:
    print('operational error:', e)
except UnsupportedOperationError as e:
    print('not implemented by this driver:', e)
```

**When you might see this error:**

| Scenario | Exception |
|----------|-----------|
| Calling `find()` on a driver that only supports key-value ops | `UnsupportedOperationError` |
| Calling `update()` with a key that doesn't exist | `RuntimeError` |
| Calling any method on a closed client or collection | `RuntimeError` |
| `DriverManager.get_client()` with an unregistered URL | `ValueError` |
