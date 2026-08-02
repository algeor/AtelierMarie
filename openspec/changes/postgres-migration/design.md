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

Pool ownership (Decision 2a): the `ConnectionPool` lives as a **module-global** in
`app/database.py`, mirroring today's `_db_path` global — not `app.state` or a
contextvar. This keeps `get_db()` the single chokepoint so the ~479 `conn`-taking
service functions and ~200 `with get_db()` call sites are untouched; an app.state/
request-scoped pool would force signature churn or hidden indirection through a
service layer built around bare `conn` parameters. `init_db(url)` opens the pool;
lifespan closes it on shutdown. Under pytest-xdist workers are separate processes,
so a per-process global pool does not fight test isolation. The pool's
`configure=` callback is the single place every pooled connection gets
`TimeZone=UTC` (Decision 12) and `row_factory=dict_row` (keyed row access) set
once, not per call.

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
- dynamic `IN (?, ?, ...)` lists -> `= ANY(%s)` array parameters (hand-rewrite;
  psycopg's array binding is strictly better than building N placeholders)
- `PRAGMA` / `sqlite_master` / `PRAGMA table_info` -> Postgres catalog queries
- `BEGIN IMMEDIATE` -> explicit transaction plus row-level locks or atomic update
  predicates
- FTS5 virtual tables -> Postgres full-text search expression indexes
- `sqlite3.IntegrityError` / `sqlite3.Error` catches -> psycopg exception classes
  or app-level database exception wrappers

Tooling split for the placeholder flip. psycopg does not accept `?` at all and
provides no SQL-string translator, so "use the library" applies only where the
library has real primitives:
- plain `?` -> `%s`: a scripted codemod (single lexical flip) with a mandatory
  human diff review, not a runtime shim.
- dynamic `IN` lists and identifier/column composition: use psycopg idioms
  (`= ANY(%s)`, `psycopg.sql.SQL` / `Identifier`) — the genuine library win.
- separate hand-audit for literal `%` (in `LIKE` patterns, `strftime`, etc.):
  under psycopg `%` is the parameter marker and must be doubled to `%%`. The
  `?`->`%s` codemod is blind to these because they contain no `?`, so this is a
  distinct pass and a hard prerequisite before flipping `get_db()`.

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

### 10. Locking taxonomy replaces coarse `BEGIN IMMEDIATE`

SQLite's `BEGIN IMMEDIATE` grabs a database-wide write lock up front. Postgres
has no equivalent and does not need one; each site is ported to the narrowest
Postgres primitive that preserves its actual invariant. Three styles, chosen
per call site by what is being protected:

- **Style A — pessimistic row lock (`SELECT ... FOR UPDATE`)**: read-decide-write
  where application logic branches on the locked value. Example: cart add-item,
  which reads `products.stock` to both validate and build the
  `InsufficientStockError` message.
- **Style B — atomic conditional update (`UPDATE ... WHERE stock >= %s`, check
  `rowcount`)**: the invariant is enforced by the DB predicate, no lock held
  across application logic. `rowcount == 0` means the race was lost / stock
  insufficient. Example: checkout's final stock decrement, backed by the existing
  `CHECK (stock >= 0)` constraint as the last line of defense.
- **`FOR UPDATE SKIP LOCKED`**: claim/lease patterns where concurrent workers must
  each grab a distinct row without blocking. Example: payment reservation cleanup,
  email outbox drain, courier polling. This is strictly better than anything
  SQLite offered and is the concrete implementation for tasks 5.2 and 5.3.

### 11. `datetime('now')` has two distinct roles

The ~200 occurrences are not one pattern. They split by role, and only one is a
mechanical sweep:

- **Role 1 — "stamp now"** (`SET updated_at = datetime('now')`,
  `VALUES (..., datetime('now'))`): mechanical replacement with
  `CURRENT_TIMESTAMP`. Safe, high volume, part of the Phase 1 sweep.
- **Role 2 — "now ± interval"** (`WHERE created_at < datetime('now', ?)`, where
  the `?` is a SQLite modifier string like `'-30 days'`): a semantic rewrite to
  `< CURRENT_TIMESTAMP - %s::interval` (or `- INTERVAL '30 days'`). The parameter
  **value** also changes form, so this cannot be a blind flip and belongs in the
  per-domain Phase 2 work. Known sites: `contact_service` claim expiry,
  `gdpr_service` suppressed-email aging.

### 12. Send `datetime` objects, not pre-formatted strings

Today several services format timestamps as strings before binding them
(`_SQLITE_DT_FMT`, `CANONICAL_DT_FMT`, `SQLITE_DATETIME_FORMAT`,
`strftime(...)`). Against `timestamptz` columns, binding a `'YYYY-MM-DD HH:MM:SS'`
string forces Postgres to cast text -> `timestamptz` using the session `TimeZone`;
if that is not UTC the result skews silently.

Decision: bind timezone-aware Python `datetime` objects and let psycopg adapt them
to `timestamptz` natively. This retires the string-format helper family and
removes the whole silent-skew class of bug. It touches every `_now()`-style helper,
so it is real per-domain work, not a sweep.

Guardrail regardless of progress: pin `TimeZone=UTC` on every pooled connection in
`get_db()`. Any string-param site that survives mid-migration then still casts
correctly. Cheap, one line, applied at pool setup.

### 13. Full-text search is an expression index, not a shadow table

The initial migration already builds GIN expression indexes
(`idx_products_search_en` / `_bg`) over
`to_tsvector('simple', COALESCE(name,'') || ' ' || COALESCE(description,''))` on
`products` directly. The query port therefore:

- drops the separate `products_fts_*` virtual tables and the `p.rowid = fts.rowid`
  joins; search runs against `products` itself.
- replaces FTS5 `MATCH` with `@@ websearch_to_tsquery('simple', %s)`.
- retires most of `_sanitize_fts5_query()` — `websearch_to_tsquery` accepts raw
  user input safely (Google-style parser). Keep a behavioral test asserting that
  the sanitizer's removal does not change observable search results.
- **requires the query's `to_tsvector(...)` expression to byte-match the migration's
  index expression**, or Postgres will not use the GIN index (silent full-scan).
  Tie `product_service` search to the migration with a comment.

### 14. Async/DB execution policy: tuned threadpool, not async psycopg

With SQLite, synchronous DB work inside an `async def` handler was invisible
(in-process, microseconds). With psycopg every query is network I/O, so sync DB
work on the event loop blocks all 182 handlers. Real launch traffic is small (a
family candle business), but the app must be durable and survive a stress test at
hundreds of concurrent requests. Durability here means DB work is off the event
loop, pools have headroom, bursts queue instead of crashing, and it is proven
under load — not raw multiplexing capacity.

Measured state: 182 `async def` handlers, 0 sync; 67 open `with get_db()` in the
handler body. They split into two buckets:

- **Bucket A** (cart, orders, auth, comments, contact, delivery, locale, webhooks,
  analytics, payment_settings; ~24 sites, no real `await`) -> **sync `def`
  handlers**. Delete `async`, leave the body and `with get_db()` unchanged;
  FastAPI runs `def` handlers in its threadpool, so one slow query cannot freeze
  the event loop. This is a Phase-1-style mechanical flip.
- **Bucket B** (`admin.py`; 43 DB sites, 17 holding a connection across a courier
  `await`) -> **stays `async def`**, with DB work wrapped in `run_in_threadpool`
  (opening `with get_db()` inside the threadpooled callable so the connection never
  crosses the thread boundary while open). This is Phase-2 careful per-handler work.

Reject async psycopg (`AsyncConnection`) for launch: it would convert ~479
conn-taking functions to `async` and contradict Decision 2, buying multiplexing
capacity that small real traffic does not need. Revisit only if real traffic data
shows the threadpool ceiling actually bites.

**Launch blockers (required for production-ready):**

1. psycopg pool size and Starlette threadpool size chosen together as `config.py`
   settings, with a pool wait timeout so bursts queue then fail clean. Seed
   defaults, to be validated (not trusted) by the stress test: pool `max_size`
   ~20, threadpool ~24 (threadpool >= pool so a thread never waits on a missing
   thread, only on a busy connection), wait timeout ~5-10s. Bounded above by
   Postgres `max_connections` (~100 default) on a single free-tier VPS, leaving
   headroom for migrations/admin. Pin `TimeZone=UTC` on pooled connections (also
   Decision 12).
2. No pooled connection held open across an httpx/courier `await`. Fix the 17
   Bucket-B admin handlers (representative: `admin.py:1251, 1324, 1578, 2855`) to
   read -> close -> `await` courier -> reopen to write. This is a
   connection-lifetime redesign, not a syntax port.
3. A net-new stress test (dev-only `locust`/`hey`) driving hundreds of concurrent
   requests at the money path and at least one Bucket-B courier route. Pass
   criteria: bounded p99 latency (no event-loop stall), no pool-exhaustion crash,
   graceful queueing under burst.

### 15. Test DB provisioning: migrated template, cloned per worker

Decision 7 sets the intent ("one isolated Postgres database per pytest-xdist
worker, migrate once, truncate between tests"). This pins the mechanics, because
the current SQLite fixtures (`conftest.py`) depend on three SQLite-specific
behaviors that do not survive a naive port.

**Provisioning — clone a migrated template, do not migrate per worker.**
`init_db(path)` is gone; schema now comes only from `alembic upgrade head`. Running
a full migration chain per worker (`-n auto` → one per core) is wasteful and grows
with every future revision. Instead, a session-scoped setup migrates one **template
database once**, then each worker does `CREATE DATABASE <worker_db> TEMPLATE
<template>` — a near-instant file copy, Postgres-native. The worker DB name is
derived from `PYTEST_XDIST_WORKER` (falling back to a single name when xdist is
off, e.g. `-p no:xdist`). Because xdist workers are separate processes with a
per-process module-global pool (Decision 2a), a per-worker database does not fight
isolation.

**Fixture scope flips module → session.** Today `db_path` / `app` / `db` are
`module`-scoped so `init_db` runs per file. Under the template-clone model the
worker database is created once per worker, so those fixtures become
**session-scoped** (session = one worker process). Consequence to accept: the
database no longer resets at module boundaries — only `_clean_tables` (autouse,
per test) resets state. Any test that silently relied on a fresh module DB will
surface and must be fixed to clean up after itself. This is a real behavioral
change, not a mechanical rename.

**Cleanup — `TRUNCATE`, but only the volatile tables; never the seed tables.**
The structural seed rows (taxonomy, FAQ, terms/privacy/cookies pages, site banner,
delivery/Econt/inventory settings, about content) now live **inside the initial
migration** (`20260802_0001`), not in `app.database` seed helpers. The clone carries
them into every worker DB. Therefore:
- Replace the ~60-table child-first `DELETE` list with
  `TRUNCATE <volatile tables> RESTART IDENTITY CASCADE` — `CASCADE` handles FK order
  and `RESTART IDENTITY` resets identity sequences so id-sensitive assertions stay
  stable across tests.
- The truncation set stays a **curated allowlist of volatile/data tables**, not
  "all tables". Migration-seed tables are deliberately excluded so their rows
  persist. This retires the SQLite path's re-seed calls
  (`_seed_site_banner` / `_seed_delivery_settings` / `_seed_inventory_settings`)
  entirely — there is nothing to re-seed because truncation never touches those
  tables. If a test mutates a seeded singleton (e.g. `site_banners`,
  `delivery_settings`), that table joins the truncate set **and** gets an explicit
  re-seed step, decided per table rather than globally.
- The `FakeSessionMiddleware` rebuild in the `app` fixture is ASGI-level and
  DB-agnostic; it ports unchanged. The one fake-session row it needs is inserted
  via psycopg after clone.

**Helpers move to psycopg.** `make_session` and `seed_products` take a
`sqlite3.Connection` and use `?` placeholders + `datetime('now')`; the `db` /
`service_db` fixtures hand tests a raw `sqlite3.Connection` with
`row_factory = sqlite3.Row` and `PRAGMA foreign_keys=ON`. Porting these is
test-infra work (Task 6.3), not part of the app `?`→`%s` sweep: the connection
**source** changes (pool/`dict_row`, no PRAGMA — FK enforcement is always on in
Postgres), the type hints change, and the SQL flips. `service_db` becomes a pooled
connection against the same worker DB rather than its own file.

**Tests require a reachable Postgres (no in-memory fallback).** Postgres has no
embedded/in-process mode, and Decision 1 removed the SQLite dialect, so there is no
zero-infra test path anymore. The decision: **tests assume a Postgres is already
reachable via `DATABASE_URL`** — locally the developer runs `docker compose up -d
postgres` once (the Compose service from tasks 1.4/1.7); CI provides a service
container. `make test-backend` documents/checks this prerequisite rather than
auto-starting a container. Testcontainers-style auto-start was considered and
rejected for the first pass: it adds a dependency and per-session start latency for
a convenience the Compose service already covers. The session-scoped setup then
migrates the template DB against that reachable server.

**Migration tests (Task 6.5).** With a single initial revision and
`down_revision = None`, the fresh-DB test asserts `alembic upgrade head` on an empty
database produces the expected tables/indexes/constraints/seed rows, and the
head-validation test asserts startup fails when the DB is behind head (Decision 3).
These replace the removed SQLite migration/PRAGMA/FTS-shadow-table tests (Task 6.4).

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
5. Port SQL using a hybrid sequence — breadth-first for mechanical flips,
   depth-first for semantic rewrites (see Decisions 10-13). The dividing line is
   mechanical vs semantic, not early vs late:
   - **Phase 1 (breadth, mechanical):** land the connection layer, then run the
     `?`->`%s` codemod and the Role-1 `datetime('now')`->`CURRENT_TIMESTAMP` sweep
     across all files as reviewed diffs. Run the `%%`-literal audit first as a
     prerequisite. Nothing is committed as "done" until reviewed.
   - **Phase 2 (depth, per-domain, green gate):** flip `get_db()` to psycopg, then
     port domains one at a time, fixing the semantic cases (`= ANY(%s)`,
     `FOR UPDATE` / SKIP LOCKED, interval math, `datetime` objects) and taking each
     domain's tests to green before moving on. Order by risk: the money path first
     (cart -> products/search -> checkout/orders/payments), then admin, content,
     couriers, inventory, accounting.
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
