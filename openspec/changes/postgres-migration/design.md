# Postgres Migration - Design

## Context

The backend currently uses Python's `sqlite3` module directly. `app/database.py`
contains the full SQLite DDL, startup schema creation, idempotent seed/backfill
logic, connection management, and SQLite FTS5 setup. Services and routes pass raw
connections around and issue raw SQL directly.

The app is not live yet, so this can be a pre-launch platform port instead of a
zero-downtime production data migration. The main goal is to move the production
path to Postgres before customer traffic exists while keeping the current service
layer shape recognizable.

## Goals / Non-Goals

**Goals:**
- Make Postgres the only app database backend.
- Use Alembic for versioned schema migrations.
- Keep raw SQL service functions and explicit transaction boundaries.
- Use pooled Postgres connections without blocking FastAPI's event loop from
  async route handlers.
- Port schema, constraints, indexes, seed data, full-text search, and test setup
  to Postgres.
- Port operational scripts and smoke-test setup that currently create or seed
  SQLite files.
- Preserve user-facing behavior for catalog, cart, checkout, admin, auth,
  payments, courier flows, inventory, legal/content pages, and analytics reads
  that depend on the app database.

**Non-Goals:**
- Supporting SQLite and Postgres at the same time.
- Introducing SQLAlchemy ORM models.
- Performing a live production cutover with dual writes or replication.
- Migrating DuckDB analytics storage to Postgres.
- Redesigning domain schemas beyond changes needed for Postgres correctness.

## Decisions

### 1. Postgres-only, not dual database support

The app will remove SQLite as a runtime backend and use `DATABASE_URL` for the
main app database.

Alternative considered: keep both SQLite and Postgres behind a dialect layer.
That would preserve local file-based development, but it would double the SQL
surface, hide production-only failures until later, and make the test matrix much
larger. Because the app is pre-launch, a clean Postgres-only port is cheaper and
safer.

### 2. Raw SQL remains the service-layer style

Use `psycopg[binary,pool]` for Postgres access. Keep the current pattern where
routes and services receive a connection and execute explicit SQL.

The first pass should avoid an ORM rewrite. A small compatibility layer can
provide `get_db()`, connection-pool ownership, transaction handling, row
factories, and helpers for common query/result behavior. Code that currently
depends on `sqlite3.Row` positional access should be updated or isolated behind a
row compatibility adapter.

Because psycopg network I/O is materially different from in-process SQLite, async
FastAPI routes must not run synchronous database work directly on the event loop.
Implementation can either convert DB-heavy endpoints to sync route functions
where FastAPI runs them in the threadpool, or keep async routes and move database
work behind `run_in_threadpool` boundaries. The choice can vary by route, but the
final app must have an explicit pattern and tests/smoke coverage for startup and
request responsiveness.

### 3. Alembic owns schema changes

`init_db()` will stop creating tables at app startup. Alembic becomes the only
schema writer.

Alembic migration order is defined by its revision graph, not by filenames or
timestamps. Every migration script must declare a stable `revision` id and the
correct `down_revision`; `alembic upgrade head` follows that chain to resolve the
current head revision.

The initial migration will be hand-written Postgres DDL based on the current
fresh SQLite schema. It should include tables, constraints, indexes, triggers or
trigger alternatives, seed rows that are structural defaults, and the full-text
search indexes needed by product search.

The application should verify that the connected database is at Alembic head on
startup by comparing the database's current revision against the script
directory's head revision(s). It must fail with a clear error if migrations have
not been applied or the database has diverged. Local developer commands must run
`alembic upgrade head` explicitly, and Compose should include either a documented
migration command or a one-shot migration service so backend startup is not
responsible for mutating schema.

### 4. Keep schema semantics conservative

Preserve existing logical types first:
- money remains integer cents
- public ids remain text
- timestamps become `timestamptz` where the app treats them as instants
- existing 0/1 flag columns remain small integers with `0`/`1` checks in the
  first pass unless the owning service is deliberately refactored and tested
- JSON-like columns remain `text` unless the owning service is updated and tested
  for `jsonb`

This reduces the blast radius. More opinionated type changes can happen after the
database backend is stable.

Postgres returns richer Python values than SQLite. Timestamp responses should keep
their public API shape stable by using explicit serialization helpers or response
model updates. The migration should not accidentally leak raw `datetime` objects
where string timestamps are expected by tests or frontend code.

### 5. SQLite SQL patterns get explicit Postgres replacements

Known replacements:
- `?` placeholders -> `%s` / psycopg parameters
- `datetime('now')` / `date('now')` -> `CURRENT_TIMESTAMP` / `CURRENT_DATE`
- `INSERT OR IGNORE` -> `INSERT ... ON CONFLICT DO NOTHING`
- `INSERT OR REPLACE` -> `INSERT ... ON CONFLICT DO UPDATE`
- `last_insert_rowid()` / `cursor.lastrowid` -> `RETURNING id`
- `AUTOINCREMENT` -> identity columns
- dynamic `IN (?, ?, ...)` lists -> `= ANY(%s)` array parameters or a shared
  placeholder helper
- `PRAGMA` / `sqlite_master` / `PRAGMA table_info` -> Postgres catalog queries
- `BEGIN IMMEDIATE` -> explicit transaction plus row-level locks or atomic update
  predicates
- FTS5 virtual tables -> Postgres full-text search expression indexes
- `sqlite3.IntegrityError` / `sqlite3.Error` catches -> psycopg exception classes
  or app-level database exception wrappers

### 6. Product search moves to Postgres full-text search

Replace the current locale-specific FTS5 tables with Postgres full-text search.
Use indexed expressions over localized name and description fields, with SQL-level
filters and pagination kept in the query.

Use the `simple` text search configuration initially unless Bulgarian/English
stemming is deliberately validated. This preserves predictable token matching and
keeps launch risk low.

### 7. Tests run against Postgres

Shared fixtures should create one isolated Postgres database per pytest-xdist
worker, run Alembic migrations once per worker database, and truncate data tables
between tests in foreign-key-safe order. Tests in a single worker are sequential,
so this preserves the existing cleanup model without paying migration cost per
test module.

Tests that assert SQLite internals should be rewritten to assert behavior, schema
constraints, or Postgres catalog state. Old SQLite migration tests can be removed
or replaced by Alembic migration tests.

### 8. No live customer data migration is required

Because the app is not live, the implementation can drop and recreate local dev
databases. If useful local content exists in `atelier_marie.db`, add an optional
one-time import/export helper after the core Postgres port works. That helper is
not part of launch correctness.

### 9. Active changes are reconciled before DDL is frozen

Current active-change reconciliation:
- `econt-delivery-integration`: include its completed courier metadata/settings schema in the initial Postgres baseline; defer only real-credential smoke task 13.5 because it has no schema impact.
- `gdpr-data-erasure`: no new schema is required; implement its service/API behavior against the Postgres baseline when that change is resumed.
- `core-ecommerce`: stale bootstrap plan that still references SQLite; superseded by the current application schema and this Postgres migration.

The repository has other active OpenSpec changes. Before writing the initial
Postgres migration, inspect active changes and current app schema ownership. The
initial migration should represent the intended launch schema, not merely the
schema that happened to exist when this proposal was drafted.

If an active change has pending schema tasks that should ship before launch, land
or explicitly defer that schema before finalizing the initial Postgres migration.
This avoids creating an initial migration that immediately needs corrective
follow-up migrations for already-known work.

## Risks / Trade-offs

- Broad raw-SQL surface -> Port by domain and keep tests green after each slice.
- Row-shape differences between `sqlite3.Row` and psycopg rows -> Add a small DB
  adapter or update positional row access intentionally.
- Event-loop blocking from sync Postgres calls in async routes -> Use sync route
  handlers or `run_in_threadpool` boundaries for DB-heavy work.
- Timestamp and 0/1 flag shape drift -> Keep explicit compatibility rules and
  targeted API/model tests.
- Different concurrency behavior -> Add focused concurrent checkout, reservation,
  email claim, payment, and courier polling tests.
- Search ranking/tokenization changes -> Keep requirements behavioral and verify
  locale search/filter/pagination results, not exact FTS5 internals.
- Startup no longer creates schema -> Add clear local commands and fail fast when
  Alembic migrations are missing.
- Test runtime may increase -> Use worker-level database isolation and avoid
  recreating the whole cluster per test.
- Active-change drift -> Review active OpenSpec changes before freezing the
  initial migration and document anything intentionally deferred.

## Migration Plan

1. Review active OpenSpec changes and decide which pending schema work belongs in
   the launch Postgres baseline.
2. Add Postgres dependencies, config, Compose service, Alembic scaffolding, and
   local commands.
3. Write the initial hand-authored Postgres migration and structural seed data.
4. Replace the database connection layer with psycopg pooling and migration-head
   checks.
5. Port SQL by domain: foundation/session/cart/products/search/orders/payments,
   then admin/content/couriers/inventory/accounting.
6. Port operational scripts and browser smoke setup to Postgres URLs and migrated
   schema assumptions.
7. Move shared tests and fixtures to Postgres and remove SQLite-only migration
   assertions.
8. Refresh docs, env examples, deployment notes, and schema reference.
9. Run backend tests, targeted concurrency tests, frontend tests, and a local
   Compose smoke test.

Rollback is branch-level before launch: revert the change, drop the local
Postgres database, and continue from the SQLite branch if needed. No production
rollback procedure is required because there is no live customer data yet.

## Open Questions

- Whether to add a small optional SQLite-to-Postgres local content import helper.
- Exact psycopg pool sizing defaults for local Docker and production.
