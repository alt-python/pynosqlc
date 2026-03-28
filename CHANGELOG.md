# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Authors

- Craig Parravicini
- Claude (Anthropic)

---

## [1.0.0] — 2026-03-28

Initial public release of the `alt-python-pynosqlc` package family.

### Added

#### Core (`alt-python-pynosqlc-core`)

- `DriverManager` — class-level registry with `get_client(url, properties)`,
  `register_driver`, `deregister_driver`, `clear`, and `get_drivers`
- `Driver` ABC — `accepts_url(url)` and `async connect(url, properties)`
- `Client` ABC — async context manager, `get_collection(name)`, `async close()`
- `Collection` ABC — six hook methods: `_get`, `_store`, `_delete`, `_insert`,
  `_update`, `_find`; public dispatch methods with identical names
- `Cursor` — async iterator (`async for`), `next()`, `get_document()`,
  `get_documents()`
- `Filter` / `FieldCondition` — chainable filter builder with ten operators:
  `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`, `in_`, `nin`, `exists`;
  combinators `and_`, `or_`, `not_`; produces a plain-dict AST via `.build()`
- `ClientDataSource` — JDBC-style `DataSource` wrapper; holds a URL and
  optional properties; vends clients via `get_client()`
- `UnsupportedOperationError` — raised by unimplemented hook methods
- `run_compliance(factory)` — portable pytest fixture set; 24 tests covering
  KV, document, lifecycle, and find operations; any driver runs it unmodified
- `py.typed` marker — full PEP 561 type-hint support

#### Memory driver (`alt-python-pynosqlc-memory`)

- `MemoryDriver` / `MemoryClient` / `MemoryCollection` — zero-dependency
  in-process dict-backed driver; URL scheme `pynosqlc:memory:`
- `MemoryFilterEvaluator` — pure-Python AST evaluator; reused by the Redis and
  Cassandra drivers for in-process filtering
- Auto-registers on `import pynosqlc.memory`

#### MongoDB driver (`alt-python-pynosqlc-mongodb`)

- `MongoDriver` / `MongoClient` / `MongoCollection` — pymongo
  `AsyncMongoClient` backend; URL scheme
  `pynosqlc:mongodb://<host>:<port>/<db>`
- `MongoFilterTranslator` — converts the pynosqlc Filter AST to a pymongo
  query dict; all ten operators supported
- Auto-registers on `import pynosqlc.mongodb`

#### DynamoDB driver (`alt-python-pynosqlc-dynamodb`)

- `DynamoDriver` / `DynamoClient` / `DynamoCollection` — aioboto3 resource
  API backend; URL scheme `pynosqlc:dynamodb:<region>`
- `DynamoFilterTranslator` — converts the Filter AST to a DynamoDB
  `FilterExpression` using `boto3.dynamodb.conditions`; all ten operators
  supported
- Auto-registers on `import pynosqlc.dynamodb`

#### Cosmos DB driver (`alt-python-pynosqlc-cosmosdb`)

- `CosmosDriver` / `CosmosClient` / `CosmosCollection` — azure-cosmos aio
  client backend; URL scheme `pynosqlc:cosmosdb:<endpoint>`; supports the
  Cosmos DB emulator via `pynosqlc:cosmosdb:local`
- `CosmosFilterTranslator` — converts the Filter AST to a Cosmos DB SQL
  WHERE clause; all ten operators supported
- Auto-registers on `import pynosqlc.cosmosdb`

#### Redis driver (`alt-python-pynosqlc-redis`)

- `RedisDriver` / `RedisClient` / `RedisCollection` — redis-py async client
  backend; URL scheme `pynosqlc:redis://<host>:<port>`
- Documents stored as JSON strings under namespaced keys
  (`pynosqlc:<collection>:<key>`); collection membership tracked in a Redis Set
  index (`pynosqlc:<collection>:_keys`)
- `find()` uses a pipeline batch GET (single round trip) then applies
  `MemoryFilterEvaluator` in-process — no server-side filter translation
- Auto-registers on `import pynosqlc.redis`

#### Cassandra driver (`alt-python-pynosqlc-cassandra`)

- `CassandraDriver` / `CassandraClient` / `CassandraCollection` —
  cassandra-driver backend bridged into asyncio via `run_in_executor`; URL
  scheme `pynosqlc:cassandra:<host>:<port>/<keyspace>`
- Each collection maps to a CQL table `(pk TEXT PRIMARY KEY, data TEXT)`;
  keyspace and tables created automatically on first use
- `find()` performs a full table scan then applies `MemoryFilterEvaluator`
  in-process — no CQL filter translation
- Auto-registers on `import pynosqlc.cassandra`

#### Documentation

- `docs/getting-started.md` — nine-section Diátaxis tutorial; all examples
  verified against the memory driver
- `docs/api-reference.md` — complete reference for all public symbols,
  operators, URL schemes, and error types
- `docs/driver-guide.md` — five-step how-to guide for implementing a custom
  driver; packaging conventions; reference implementations table for all six
  drivers
- `docs/jdbc-migration.md` — explanation mapping every JDBC concept to its
  pynosqlc equivalent; side-by-side Java/Python code blocks
- Per-package `README.md` for all seven packages

#### CI

- GitHub Actions workflow — runs the offline test suite (memory, core, filter
  unit tests) on push and pull request; publishes packages to PyPI on version
  tags

[1.0.0]: https://github.com/alt-python/pynosqlc/releases/tag/v1.0.0
