# JDBC to pynosqlc Migration Guide

pynosqlc is deliberately inspired by JDBC. If you've written JDBC code in Java,
the mental model transfers cleanly — but everything is async-first, NoSQL-only,
and Python idiomatic. This guide maps every JDBC concept to its pynosqlc
equivalent with working Python code throughout.

---

## Overview

JDBC and pynosqlc share the same architectural backbone:

| Concept | JDBC | pynosqlc |
|---------|------|---------|
| Central registry | `DriverManager` | `DriverManager` |
| Driver detection | `Class.forName()` side-effect | `import pynosqlc.memory` side-effect |
| Connection | `Connection` | `Client` |
| Query descriptor | `Statement` / `PreparedStatement` | `Filter.where(...).build()` |
| Result iteration | `ResultSet` | `Cursor` |

The key differences:

- **Async-first.** Every I/O method is `async def`. There is no sync fallback.
- **NoSQL-only.** There are no SQL strings, no schemas, no tables — only
  collections of documents (`dict`).
- **No PreparedStatement.** The `Filter` builder produces a plain Python `dict`
  (the filter AST) that drivers interpret natively. No string interpolation, no
  risk of injection.
- **No transactions in M1/M2.** Transaction support is planned but not yet
  implemented. See [What's Not There](#whats-not-there).

---

## DriverManager and Connection Management

In JDBC you call `DriverManager.getConnection(url)` — a sync call that returns
a `Connection`. In pynosqlc you call `DriverManager.get_client(url)` — an
`async def` coroutine that returns a `Client`.

**Java:**

```java
// JDBC
Connection conn = DriverManager.getConnection("jdbc:postgresql://localhost/mydb");
// ... use conn ...
conn.close();
```

**Python:**

```python
import asyncio
from pynosqlc.core import DriverManager
import pynosqlc.memory  # auto-registers MemoryDriver on import

async def main():
    # get_client is async — await it first, then enter the context manager
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        # client is automatically closed when the block exits
        pass

asyncio.run(main())
```

> **Critical pattern:** `async with await DriverManager.get_client(url) as client:`
>
> Two operations happen on that one line:
> 1. `await DriverManager.get_client(url)` — runs the coroutine, returns a `Client`
> 2. `async with <client>` — enters the async context manager, ensures `close()` is called
>
> You cannot write `async with DriverManager.get_client(url)` (missing `await`) —
> `get_client` is an `async def`, so calling it without `await` gives you an
> unawaited coroutine, not a `Client`.

**Manual open/close (equivalent to JDBC's explicit `conn.close()`):**

```python
import asyncio
from pynosqlc.core import DriverManager
import pynosqlc.memory

async def main():
    client = await DriverManager.get_client('pynosqlc:memory:')
    try:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice'})
    finally:
        await client.close()  # close() is async — must be awaited

asyncio.run(main())
```

### ClientDataSource (DataSource equivalent)

JDBC applications often inject a `DataSource` rather than calling
`DriverManager` directly. pynosqlc provides `ClientDataSource`:

```python
from pynosqlc.core import ClientDataSource
import pynosqlc.memory

ds = ClientDataSource({'url': 'pynosqlc:memory:'})

async def main():
    async with await ds.get_client() as client:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice'})
```

---

## Collections, Not SQL Tables

In JDBC you target a table by writing its name in a SQL string
(`SELECT * FROM users`). In pynosqlc you call `client.get_collection(name)` —
a **synchronous** method that returns (or creates) a `Collection` object.

**Java:**

```java
// JDBC
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery("SELECT * FROM users");
```

**Python:**

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        # get_collection is SYNC — no await
        col = client.get_collection('users')

        # store a document
        await col.store('u1', {'name': 'Alice', 'age': 30, 'role': 'admin'})

        # retrieve by primary key
        doc = await col.get('u1')
        print(doc['name'])   # Alice

asyncio.run(main())
```

> **`get_collection` is synchronous.** Do not `await` it. The call is cheap —
> it returns a cached `Collection` instance for repeated calls with the same name.

### Key-based operations

| JDBC | pynosqlc |
|------|---------|
| `INSERT INTO users VALUES (...)` | `await col.store('key', doc)` or `await col.insert(doc)` |
| `SELECT * FROM users WHERE id = ?` | `await col.get('key')` |
| `UPDATE users SET ... WHERE id = ?` | `await col.update('key', patch)` |
| `DELETE FROM users WHERE id = ?` | `await col.delete('key')` |

`store(key, doc)` is upsert — it creates or fully replaces.
`update(key, patch)` shallow-merges only the supplied fields.
`insert(doc)` returns the driver-assigned key string.

---

## Filter Builder, Not SQL WHERE

JDBC uses `PreparedStatement` to bind parameters into a SQL string:

**Java:**

```java
// JDBC PreparedStatement
PreparedStatement ps = conn.prepareStatement(
    "SELECT * FROM users WHERE age > ? AND role = ?"
);
ps.setInt(1, 18);
ps.setString(2, "admin");
ResultSet rs = ps.executeQuery();
```

pynosqlc replaces both the SQL string and the parameter binding with a
chainable `Filter` builder that produces a plain Python `dict` (the filter
AST):

**Python:**

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

        # Filter replaces PreparedStatement — no SQL strings, no injection risk
        ast = Filter.where('age').gt(18).and_('role').eq('admin').build()
        cursor = await col.find(ast)
        async for doc in cursor:
            print(doc['name'])   # Alice

asyncio.run(main())
```

### Filter operators

| SQL / JDBC | pynosqlc Filter | Notes |
|-----------|----------------|-------|
| `field = ?` | `.eq(value)` | |
| `field != ?` | `.ne(value)` | |
| `field > ?` | `.gt(value)` | |
| `field >= ?` | `.gte(value)` | |
| `field < ?` | `.lt(value)` | |
| `field <= ?` | `.lte(value)` | |
| `field IN (?, ?, ?)` | `.in_([v1, v2, v3])` | trailing `_` avoids Python `in` keyword |
| `field NOT IN (...)` | `.nin([v1, v2, v3])` | |
| `field LIKE '%x%'` | `.contains(value)` | substring / list membership |
| `field IS NOT NULL` | `.exists(True)` | |
| `field IS NULL` | `.exists(False)` | |
| `WHERE a AND b` | `.and_(field).op(value)` | chained on same `Filter` |
| `WHERE a OR b` | `Filter.or_(f1, f2)` | classmethod, returns ready-to-use AST |
| `NOT (...)` | `filter.not_()` | wraps in negation node |

> **Python keyword avoidance:** `and_()`, `or_()`, `not_()`, `in_()` have
> trailing underscores following PEP 8 convention to avoid collision with Python
> reserved keywords. The AST operator key for `in_()` is `'in'` (not `'in_'`).

### Always call `.build()`

`Filter.where('age').gt(18)` returns a `Filter` instance. `col.find()` requires
the AST `dict`. You must always call `.build()` to get the dict:

```python
ast = Filter.where('age').gt(18).build()   # correct — ast is a dict
cursor = await col.find(ast)
```

`Filter.or_()` and `filter.not_()` return the AST dict directly — do **not**
call `.build()` on their results:

```python
# OR — returns dict directly, no .build() needed
ast = Filter.or_(
    Filter.where('role').eq('admin'),
    Filter.where('role').eq('editor'),
)
cursor = await col.find(ast)

# NOT — returns dict directly, no .build() needed
ast = Filter.where('age').gte(18).not_()
cursor = await col.find(ast)
```

---

## Async-Only API

JDBC is entirely synchronous — every method blocks until the database responds.
pynosqlc is entirely asynchronous — every I/O method is `async def` and must be
`await`ed.

| Category | JDBC | pynosqlc |
|----------|------|---------|
| Open connection | sync `DriverManager.getConnection()` | `async def get_client()` — must `await` |
| Close connection | sync `conn.close()` | `async def close()` — must `await` |
| Store document | (INSERT) | `async def store()` — must `await` |
| Get by key | (SELECT WHERE id=) | `async def get()` — must `await` |
| Query | sync `executeQuery()` | `async def find()` — must `await` |
| Cursor advance | sync `ResultSet.next()` | `async def next()` — must `await` |
| Get current doc | sync `ResultSet.getXxx()` | sync `get_document()` — **no** `await` |

There is **no sync fallback.** If you call an async method without `await`,
Python silently creates an unawaited coroutine and the operation never executes.

All pynosqlc code must run inside an `async def` function, driven by
`asyncio.run()` at the top level (or an existing event loop in web frameworks):

```python
import asyncio
from pynosqlc.core import DriverManager
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('items')
        await col.store('k1', {'value': 42})
        doc = await col.get('k1')
        print(doc['value'])   # 42

asyncio.run(main())
```

---

## Cursors and Result Sets

JDBC `ResultSet` and pynosqlc `Cursor` both represent a stream of query
results. The iteration patterns differ.

### Idiomatic iteration — `async for`

The preferred pynosqlc pattern mirrors JDBC's enhanced for-loop:

**Java:**

```java
// JDBC (Java 5+ enhanced for-loop not available for ResultSet — while is idiomatic)
ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE age > 18");
while (rs.next()) {
    String name = rs.getString("name");
    System.out.println(name);
}
```

**Python:**

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice', 'age': 30})
        await col.store('u2', {'name': 'Bob', 'age': 25})

        ast = Filter.where('age').gt(18).build()
        cursor = await col.find(ast)

        # async for is the idiomatic path — cursor closes automatically
        async for doc in cursor:
            print(doc['name'])

asyncio.run(main())
# Alice
# Bob
```

### Manual next/get_document loop

The `next()`/`get_document()` two-call pattern mirrors JDBC's
`rs.next()` / `rs.getXxx()` pattern exactly — but `next()` is `async`:

**Java:**

```java
ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE age > 18");
while (rs.next()) {
    String name = rs.getString("name");
    System.out.println(name);
}
rs.close();
```

**Python:**

```python
import asyncio
from pynosqlc.core import DriverManager, Filter
import pynosqlc.memory

async def main():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('users')
        await col.store('u1', {'name': 'Alice', 'age': 30})
        await col.store('u2', {'name': 'Bob', 'age': 25})

        ast = Filter.where('age').gt(18).build()
        cursor = await col.find(ast)

        # next() returns bool (True = doc available), not the document itself
        while await cursor.next():
            doc = cursor.get_document()  # sync — no await
            print(doc['name'])
        await cursor.close()

asyncio.run(main())
# Alice
# Bob
```

> **`cursor.next()` returns `bool`, not a document.**
>
> - `await cursor.next()` → `True` if a document is available at the current position; `False` when exhausted.
> - `cursor.get_document()` → retrieves the document at the current position (sync, no `await`).
>
> This matches JDBC's two-call pattern: `rs.next()` advances and returns a
> boolean; `rs.getString()` retrieves the current value.

### Bulk access

If you want all results as a list without iteration:

```python
cursor = await col.find(ast)
docs = cursor.get_documents()   # sync — returns list[dict]
for doc in docs:
    print(doc['name'])
```

This is equivalent to JDBC's `while (rs.next()) { list.add(...); }` pattern
but without the loop boilerplate.

---

## Driver Registration

### JDBC: `Class.forName()`

JDBC loads a driver by name and the driver registers itself as a side effect:

```java
Class.forName("com.mysql.cj.jdbc.Driver");  // loads class, triggers static initialiser
Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/mydb");
```

### pynosqlc: import side-effect

pynosqlc works the same way — importing a driver package triggers
`DriverManager.register_driver()` as a module-level side effect:

```python
import pynosqlc.memory   # module-level code calls DriverManager.register_driver()

from pynosqlc.core import DriverManager

async def main():
    # Now get_client accepts 'pynosqlc:memory:' URLs
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        pass
```

You can verify which drivers are registered at any time:

```python
from pynosqlc.core import DriverManager
import pynosqlc.memory

drivers = DriverManager.get_drivers()
print([type(d).__name__ for d in drivers])   # ['MemoryDriver']
```

### URL scheme

pynosqlc URLs follow `pynosqlc:<subprotocol>:<connection-details>`, not JDBC's
`jdbc:<driver>:<connection-details>`:

| JDBC URL | pynosqlc URL |
|----------|-------------|
| `jdbc:h2:mem:test` | `pynosqlc:memory:` |
| `jdbc:mysql://host/db` | `pynosqlc:mongodb://host:27017/db` |
| `jdbc:dynamodb:region` | `pynosqlc:dynamodb:us-east-1` |

---

## Concept Mapping Table

Complete JDBC-to-pynosqlc cheat sheet:

| JDBC | pynosqlc | Notes |
|------|---------|-------|
| `Class.forName('com.example.Driver')` | `import pynosqlc.memory` | auto-registers on import |
| `DriverManager.getConnection(url)` | `await DriverManager.get_client(url)` | async, returns context manager |
| `Connection` | `Client` | use `async with` |
| `DataSource` | `ClientDataSource` | same pattern, async `get_client()` |
| `Statement` / `PreparedStatement` | `Filter.where(...).build()` | no SQL strings |
| `ResultSet` | `Cursor` | `async for`, bool `next()` |
| `ResultSet.next()` | `await cursor.next()` → `bool`; `cursor.get_document()` | two-call pattern |
| `statement.executeQuery()` | `await col.find(filter_ast)` | returns `Cursor` |
| `statement.executeUpdate()` | `await col.store(key, doc)` | upsert semantics |
| `table name in SQL` | `client.get_collection(name)` | sync, returns cached `Collection` |
| `connection.close()` | `await client.close()` | or `async with` |
| `rs.close()` | `await cursor.close()` | automatic with `async for` |
| `conn.createStatement()` | `client.get_collection(name)` | collection is the query target |
| `ps.setXxx(i, value)` | `.where(field).op(value)` | type-safe, no placeholders |
| `jdbc:<driver>:<details>` | `pynosqlc:<subprotocol>:<details>` | same concept, different scheme |

---

## What's Not There

pynosqlc deliberately omits several JDBC features:

### No PreparedStatement

There are no SQL strings in pynosqlc — no `PreparedStatement`, no parameter
placeholders, no string interpolation. The `Filter` builder is the only
supported query mechanism. This eliminates the entire class of SQL injection
vulnerabilities by design.

### No transactions (M1/M2)

Transaction support (`BEGIN` / `COMMIT` / `ROLLBACK`, `Connection.setAutoCommit()`)
is not implemented in Milestones 1 and 2. Attempting atomic multi-document
operations requires application-level logic or choosing a backend that supports
it natively. Transaction support is planned for a future milestone.

### No ResultSetMetaData

pynosqlc documents are plain Python `dict`s. There is no `ResultSetMetaData`,
no column type inspection, and no schema introspection API. The document
structure is whatever the application wrote — or whatever the backend stored.

### No batch statements

There is no equivalent to JDBC's `Statement.addBatch()` / `executeBatch()`.
Multiple documents must be written with individual `store()` or `insert()`
calls, or by driver-specific bulk mechanisms if the backend supports them.

### No connection pooling API

pynosqlc does not expose a connection pool configuration API analogous to
JDBC connection pool properties. Pooling behaviour is driver-specific — some
async clients (e.g. `motor` for MongoDB) manage their own internal pools.

### No stored procedures or callable statements

There is no equivalent to JDBC's `CallableStatement`. pynosqlc only supports
document CRUD and filter-based queries.
