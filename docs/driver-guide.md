# pynosqlc Driver Implementation Guide

This guide walks you through writing a compliant custom driver for pynosqlc.
Follow the five steps in order. The memory driver (`packages/memory/`) is the
canonical reference — every pattern shown here matches what it does.

---

## Overview

A driver package contains five components:

1. **Driver** — detects which URLs it handles and opens connections
2. **Client** — holds the live connection and vends Collections
3. **Collection** — executes the six data operations against the backend
4. **FilterTranslator** — converts the pynosqlc Filter AST to your backend's query language
5. **Compliance tests** — run the shared suite to prove correctness

After you register the driver with `DriverManager`, users open connections with
`await DriverManager.get_client('pynosqlc:mydb:...')`. No further setup required.

---

## Step 1: Implement the Driver class

Subclass `Driver` and implement two methods:

- `accepts_url(url)` — return `True` if this driver owns the URL
- `connect(url, properties)` — create and return a `Client`

```python
from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from mypackage.my_client import MyClient


class MyDriver(Driver):
    URL_PREFIX = "pynosqlc:mydb:"

    def accepts_url(self, url: str) -> bool:
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(self, url: str, properties: dict | None = None) -> MyClient:
        return await MyClient.create(url, properties or {})


# Auto-register on import — one shared instance is enough
_driver = MyDriver()
DriverManager.register_driver(_driver)
```

**URL scheme:** `pynosqlc:<subprotocol>:` — e.g. `pynosqlc:mydb:` or
`pynosqlc:mydb:us-east-1`.

`accepts_url` is called for every registered driver; keep it cheap (a simple
`str.startswith` check is fine).

---

## Step 2: Implement the Client class

Subclass `Client` and implement two methods:

- `_get_collection(name)` — **SYNC** — create and return a `Collection` for `name`
- `_close()` — **async** — release driver-specific resources (connection pool, etc.)

```python
from pynosqlc.core.client import Client
from mypackage.my_collection import MyCollection


class MyClient(Client):
    def __init__(self, url: str, native_conn) -> None:
        super().__init__({"url": url})   # config dict — not kwargs
        self._native_conn = native_conn

    @classmethod
    async def create(cls, url: str, properties: dict) -> "MyClient":
        native_conn = await _open_native_connection(url, properties)
        return cls(url, native_conn)

    def _get_collection(self, name: str) -> MyCollection:
        # SYNC — do NOT add `async` here
        return MyCollection(self, name)

    async def _close(self) -> None:
        await self._native_conn.close()
```

**Key detail:** `_get_collection` is **synchronous**. The base class caches the
result — it will only be called once per collection name per client session.

`Client` already implements `__aenter__` / `__aexit__`, so callers can use:

```python
async with await DriverManager.get_client("pynosqlc:mydb:...") as client:
    col = client.get_collection("users")
```

The `await` comes before `async with` because `get_client` is `async def` and
returns a context manager — first `await` the coroutine, then enter the context.

---

## Step 3: Implement the Collection class

Subclass `Collection` and override the six async hook methods. All hooks default
to raising `UnsupportedOperationError` — implement only the ones your backend
supports.

```python
import uuid
from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from mypackage.my_filter_translator import MyFilterTranslator


class MyCollection(Collection):
    """Collection backed by the My database."""

    def __init__(self, client, name: str) -> None:
        super().__init__(client, name)
        # Access the collection name as self._name — there is no public .name property

    # ── Key-value operations ───────────────────────────────────────────────

    async def _get(self, key: str) -> dict | None:
        result = await self._client._native_conn.get(self._name, key)
        return result or None

    async def _store(self, key: str, doc: dict) -> None:
        await self._client._native_conn.put(self._name, key, doc)

    async def _delete(self, key: str) -> None:
        await self._client._native_conn.remove(self._name, key)

    # ── Document operations ────────────────────────────────────────────────

    async def _insert(self, doc: dict) -> str:
        key = str(uuid.uuid4())              # generate UUID4 key
        stored = {**doc, "_id": key}         # embed _id in the document
        await self._client._native_conn.put(self._name, key, stored)
        return key

    async def _update(self, key: str, patch: dict) -> None:
        existing = await self._client._native_conn.get(self._name, key)
        if existing is None:
            raise KeyError(f"Document not found: {key!r}")
        merged = {**existing, **patch}       # shallow merge
        await self._client._native_conn.put(self._name, key, merged)

    # ── Query operation ────────────────────────────────────────────────────

    async def _find(self, ast: dict) -> Cursor:
        backend_query = MyFilterTranslator.translate(ast)
        raw_results = await self._client._native_conn.scan(self._name, backend_query)
        return Cursor(raw_results)           # _find MUST return a Cursor instance
```

**Critical details:**

- Use `self._name` for the collection name — there is no public `.name` property.
- `_insert` generates `str(uuid.uuid4())` as the key and stores `{**doc, '_id': key}`.
- `_find` must return a `Cursor` instance (wrap your result list in `Cursor(results)`).
- All six hooks raise `UnsupportedOperationError` by default — not `NotImplementedError`.

---

## Step 4: Implement the FilterTranslator

The `_find(ast)` hook receives a filter AST produced by `Filter.build()`. Your
translator converts this generic AST into the query syntax your backend expects.

### AST node shapes

| Node type | Shape |
|-----------|-------|
| Leaf condition | `{'type': 'condition', 'field': str, 'op': str, 'value': Any}` |
| AND compound | `{'type': 'and', 'conditions': [node, ...]}` |
| OR compound | `{'type': 'or', 'conditions': [node, ...]}` |
| NOT compound | `{'type': 'not', 'condition': node}` |

### Supported operators

| `'op'` value | Meaning |
|--------------|---------|
| `'eq'` | `field == value` |
| `'ne'` | `field != value` |
| `'gt'` | `field > value` |
| `'gte'` | `field >= value` |
| `'lt'` | `field < value` |
| `'lte'` | `field <= value` |
| `'contains'` | field (string or list) contains value |
| `'in'` | field is one of the values list |
| `'nin'` | field is not in the values list |
| `'exists'` | field is present (True) or absent (False) |

> **Note:** The `in_()` operator on `FieldCondition` writes `'in'` into the
> AST — **not** `'in_'`. Match on `op == 'in'` in your translator.

```python
class MyFilterTranslator:
    @staticmethod
    def translate(ast: dict) -> dict:
        """Translate a pynosqlc filter AST to a backend-specific query dict."""
        node_type = ast.get("type")

        if node_type == "condition":
            field = ast["field"]
            op = ast["op"]
            value = ast["value"]
            return MyFilterTranslator._translate_condition(field, op, value)

        elif node_type == "and":
            parts = [MyFilterTranslator.translate(c) for c in ast["conditions"]]
            return {"$and": parts} if parts else {}

        elif node_type == "or":
            parts = [MyFilterTranslator.translate(c) for c in ast["conditions"]]
            return {"$or": parts}

        elif node_type == "not":
            inner = MyFilterTranslator.translate(ast["condition"])
            return {"$not": inner}

        return {}

    @staticmethod
    def _translate_condition(field: str, op: str, value) -> dict:
        mapping = {
            "eq":       lambda f, v: {f: {"$eq": v}},
            "ne":       lambda f, v: {f: {"$ne": v}},
            "gt":       lambda f, v: {f: {"$gt": v}},
            "gte":      lambda f, v: {f: {"$gte": v}},
            "lt":       lambda f, v: {f: {"$lt": v}},
            "lte":      lambda f, v: {f: {"$lte": v}},
            "contains": lambda f, v: {f: {"$elemMatch": v}},
            "in":       lambda f, v: {f: {"$in": v}},   # NOTE: 'in', not 'in_'
            "nin":      lambda f, v: {f: {"$nin": v}},
            "exists":   lambda f, v: {f: {"$exists": v}},
        }
        handler = mapping.get(op)
        if handler is None:
            raise ValueError(f"Unsupported operator: {op!r}")
        return handler(field, value)
```

---

## Step 5: Wire up compliance tests

The `run_compliance` function injects a complete set of pytest test classes into
your test module's namespace. All you need to provide is an async factory that
returns a fresh, open `Client`.

**Important:** `DriverManager.clear()` removes all registered drivers. After
calling it, you must explicitly re-register your driver. A bare re-import does
nothing — Python caches modules, so `import my_driver` does not re-execute
module-level code.

```python
from pynosqlc.core.testing import run_compliance
from pynosqlc.core import DriverManager
from mypackage.my_driver import _driver

async def _factory():
    DriverManager.clear()
    DriverManager.register_driver(_driver)
    return await DriverManager.get_client('pynosqlc:mydb:...')

run_compliance(_factory)
```

Save this as `tests/test_compliance.py` and run with pytest:

```bash
pytest tests/test_compliance.py -v
```

**If your backend does not support `find()` / scan**, pass `skip_find=True`:

```python
run_compliance(_factory, skip_find=True)
```

---

## Packaging

### Directory layout

```
pynosqlc-mydb/
├── pyproject.toml
└── pynosqlc/               # NO __init__.py here — namespace package
    └── mydb/               # __init__.py goes here (inner subpackage)
        ├── __init__.py
        ├── my_driver.py
        ├── my_client.py
        ├── my_collection.py
        └── my_filter_translator.py
```

> **Critical:** Do NOT create `pynosqlc/__init__.py`. The `pynosqlc` directory
> is an implicit namespace package shared across all pynosqlc driver packages.
> Any `__init__.py` in that directory turns it into a regular package, making
> all other sub-packages (core, memory, mongodb, …) undiscoverable. Only the
> inner `pynosqlc/mydb/` directory gets an `__init__.py`.

### pyproject.toml

```toml
[project]
name = "pynosqlc-mydb"          # hyphen-separated, PyPI style
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pynosqlc-core>=0.1.0",
    "my-backend-client>=1.0",   # your backend's async client library
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["pynosqlc/mydb"]    # inner package only — not pynosqlc/
```

### Auto-registration

Include this at the bottom of your driver module:

```python
_driver = MyDriver()
DriverManager.register_driver(_driver)
```

Users activate the driver with a bare import:

```python
import pynosqlc.mydb   # registers MyDriver on import
```

No other setup required. This mirrors the JDBC `Class.forName()` pattern.

---

## Reference Implementations

The memory driver is the simplest complete implementation — read these files
before writing your own:

| File | What it shows |
|------|---------------|
| `packages/memory/pynosqlc/memory/memory_driver.py` | `_driver` singleton, `accepts_url`, `connect`, auto-register |
| `packages/memory/pynosqlc/memory/memory_client.py` | Sync `_get_collection`, `super().__init__({'url': url})` |
| `packages/memory/pynosqlc/memory/memory_collection.py` | All six hooks, UUID4 `_insert`, `Cursor` return, `self._name` usage |
| `packages/memory/pynosqlc/memory/memory_filter_evaluator.py` | Pure-Python filter AST evaluation |
| `packages/memory/tests/test_compliance.py` | `DriverManager.clear()` + re-register pattern |
| `packages/redis/pynosqlc/redis/redis_collection.py` | Full-scan + `MemoryFilterEvaluator` pattern; pipeline batch GET; namespaced key scheme |
| `packages/cassandra/pynosqlc/cassandra/cassandra_collection.py` | `run_in_executor` bridging for blocking driver; lazy table creation; full-scan + `MemoryFilterEvaluator` |

Six drivers ship with pynosqlc. `memory`, `mongodb`, `dynamodb`, and `cosmosdb`
use server-side filtering (or no filtering for the in-memory case). `redis` and
`cassandra` use full-scan + `MemoryFilterEvaluator` for client-side filtering —
the right pattern when the backend has no query language of its own. For real I/O
and connection management examples, see `packages/mongodb/` (MongoDB),
`packages/dynamodb/` (DynamoDB), `packages/redis/` (Redis), or
`packages/cassandra/` (Cassandra).
