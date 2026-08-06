# Postgres Migration - Proposal

## Why

AtelierMarie currently depends on a local SQLite file and startup schema creation, but the app is not live yet. Moving to Postgres now avoids carrying SQLite production constraints into launch and gives the project versioned migrations, stronger concurrency semantics, and a deployment shape closer to production.

## What Changes

- **BREAKING**: Replace SQLite as the app database with Postgres only.
- **BREAKING**: Replace `DATABASE_PATH` runtime configuration with `DATABASE_URL` for the app database.
- Add Alembic as the authoritative schema migration system.
- Add `psycopg` as the database driver while keeping the current raw-SQL service style.
- Add a Postgres connection-pool and request execution pattern that avoids blocking FastAPI's event loop with synchronous database I/O.
- Convert the current schema into a clean hand-written initial Postgres migration.
- Replace startup `CREATE TABLE IF NOT EXISTS` and SQLite migration/backfill logic with explicit Alembic migrations.
- Replace SQLite-specific SQL patterns with Postgres equivalents, including timestamp functions, conflict handling, generated ids, locking, catalog introspection, and full-text search.
- Add a Postgres service to Docker Compose for local development and test runs.
- Port operational scripts and browser smoke setup that currently seed or open SQLite files directly.
- Move tests from temp SQLite files to isolated per-worker Postgres test databases.
- Reconcile active OpenSpec changes before freezing the initial Postgres migration so pending schema work is not lost.

## Capabilities

### New Capabilities

- `postgres-database`: Postgres runtime configuration, connection handling, Alembic migrations, local Docker database, and database health expectations.

### Modified Capabilities

- `project-foundation`: Startup and environment requirements change from SQLite `DATABASE_PATH` and file initialization to Postgres `DATABASE_URL` and migration-managed schema.
- `concurrency-safety`: SQLite `BEGIN IMMEDIATE` requirements change to Postgres transaction and row-level locking behavior.
- `backend-query-optimization`: Product search requirements change from SQLite FTS5 to Postgres full-text search while keeping SQL-level filtering and pagination.
- `test-fixtures`: Test isolation requirements change from per-test SQLite files/connections to Postgres-backed per-worker test databases.

## Impact

- Backend dependencies: add `psycopg[binary,pool]`; add `alembic` to development tooling.
- Backend database layer: replace `sqlite3` connection management with a Postgres connection abstraction and row shape compatible with current services.
- Schema management: introduce `alembic.ini`, migration environment, and an initial Postgres DDL migration.
- Services and routes: update SQL syntax and transaction behavior across raw SQL call sites.
- Tests: update shared fixtures, helpers, old-DB migration tests, constraint tests, and SQL assertions for Postgres.
- Local/deployment config: update `.env` examples, Docker Compose, backend container dependencies, and database documentation.
- Documentation: refresh database schema docs, local development instructions, and troubleshooting notes.
