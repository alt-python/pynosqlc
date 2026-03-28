# Changelog

All notable changes to pynosqlc are documented here.
Versions are released together across all packages (`alt-python-pynosqlc-*`).

---

## [1.0.1] - 2026-03-28

### Fixed
- Publish workflow: fixed dist output path — `uv build --directory packages/<pkg>` resolved
  `--out-dir` relative to the changed directory, doubling the path. Switched to
  `uv build --package alt-python-pynosqlc-<pkg> --out-dir packages/<pkg>/dist` from the
  workspace root so `uv publish` finds the artifacts.

### Changed
- Publish workflow: switched from OIDC trusted publishing to token auth via
  `UV_PUBLISH_TOKEN` secret (`secrets.UV_PUBLISH_TOKEN`). Removed `id-token: write`
  permission.
- Publish workflow: added `redis` and `cassandra` to the publish matrix (were missing
  from the initial workflow).
- All packages: added `[project.urls]` block — `Homepage`, `Repository`, `Documentation`
  (GitHub README `#getting-started` anchor), and `Bug Tracker` (GitHub Issues).

---

## [1.0.0] - 2026-03-28

### Added
- `alt-python-pynosqlc-core`: Driver, DriverManager, Client, Collection, Cursor, Filter,
  FieldCondition, UnsupportedOperationError, and the shared compliance test suite.
- `alt-python-pynosqlc-memory`: Zero-dependency in-memory driver backed by Python dicts.
  Intended for unit testing without a live database.
- `alt-python-pynosqlc-mongodb`: Async MongoDB driver using `pymongo` (AsyncMongoClient).
- `alt-python-pynosqlc-dynamodb`: Async DynamoDB driver using `aioboto3`.
- `alt-python-pynosqlc-cosmosdb`: Async Azure Cosmos DB driver using `azure-cosmos`.
- `alt-python-pynosqlc-redis`: Async Redis driver using `redis-py`. Stores documents as
  JSON strings; uses a Redis Set per collection as a key index. In-memory filter
  evaluation via `MemoryFilterEvaluator`.
- `alt-python-pynosqlc-cassandra`: Async Cassandra driver using `cassandra-driver` with
  thread-based reactor. Stores documents as JSON in a wide column table; in-memory filter
  evaluation via `MemoryFilterEvaluator`.
- Full compliance suite (24 tests) passing for all seven drivers against live backends.
- CI workflow (`ci.yml`): runs offline tests (core + memory) on every push and PR.
- Publish workflow (`publish.yml`): publishes all packages to PyPI on version tag push.
- Documentation: `docs/getting-started.md`, `docs/api-reference.md`,
  `docs/driver-guide.md`, `docs/jdbc-migration.md`, and per-package READMEs.
