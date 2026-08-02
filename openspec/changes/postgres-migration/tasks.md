# Postgres Migration - Tasks

## 1. Dependencies And Local Infrastructure

- [x] 1.1 Add `psycopg[binary,pool]` Postgres driver and pooling support to production dependencies.
- [x] 1.2 Add Alembic to development dependencies and regenerate the lockfile.
- [x] 1.3 Replace `DATABASE_PATH` settings with `DATABASE_URL` settings and production validation.
- [x] 1.4 Add a Postgres service, healthcheck, credentials, and persistent volume to `compose.yml`.
- [x] 1.5 Update `.env.example`, `.env.docker.example`, and local setup docs for Postgres URLs.
- [x] 1.6 Add Makefile or documented commands for starting Postgres, running migrations, and resetting the local dev DB.
- [x] 1.7 Add a local/Compose migration command or one-shot migration service so `alembic upgrade head` is explicit before backend startup.
- [x] 1.8 Review active OpenSpec changes and document which pending schema work is included in, or deferred from, the initial Postgres baseline.

## 2. Alembic Schema Foundation

- [x] 2.1 Add Alembic project scaffolding: `alembic.ini`, migration env, versions folder, URL loading from settings, and a migration script template with `revision` / `down_revision` metadata.
- [x] 2.2 Write the hand-authored initial Postgres migration for the intended launch schema after active-change reconciliation, with an explicit initial `revision` id and `down_revision = None`.
- [x] 2.3 Port core constraints, foreign keys, unique indexes, and check constraints into the initial migration.
- [x] 2.4 Port updated-at behavior from SQLite triggers to Postgres trigger functions or explicit service updates.
- [x] 2.5 Port structural seed data for taxonomy, FAQ, legal pages, cookies, banner, delivery, Econt, inventory, and about content.
- [x] 2.6 Add Postgres full-text search indexes for localized product search.
- [x] 2.7 Add a migration-head verification path that compares the database current revision against Alembic's script-directory head revision graph and fails startup when Alembic is missing, stale, or diverged.
- [x] 2.8 Preserve compatible timestamp serialization and 0/1 flag semantics in the initial schema or update all dependent code/tests explicitly.

## 3. Database Connection Layer

- [ ] 3.1 Replace SQLite `init_db()` behavior with Postgres connectivity and migration-state checks.
- [ ] 3.2 Replace `get_db()` with a psycopg-pool-backed context manager that commits on success and rolls back on error.
- [ ] 3.3 Provide keyed row access compatible with existing service transformations and public response serialization.
- [ ] 3.4 Add shared SQL helpers for dynamic `IN` lists, array parameters, `RETURNING id`, and common timestamp expressions.
- [ ] 3.5 Replace SQLite exception catches and type hints with psycopg exceptions or app-level database exception wrappers.
- [ ] 3.6 Replace SQLite-only helpers for table existence, columns, PRAGMA, and `sqlite_master` with Postgres catalog helpers where still needed.
- [ ] 3.7 Remove SQLite file permission, WAL, FTS5 reset, and old SQLite backfill code paths.

## 4. SQL Dialect Port By Domain

- [ ] 4.1 Create a tracked SQL audit for `sqlite3`, `?`, dynamic `IN` placeholders, `datetime('now')`, `date('now')`, `INSERT OR`, `last_insert_rowid`, `lastrowid`, `executescript`, `BEGIN IMMEDIATE`, `PRAGMA`, `sqlite_master`, `rowid`, and FTS5 usage.
- [ ] 4.2 Port session, auth, cart, rate-limit, and middleware SQL to Postgres syntax.
- [ ] 4.3 Port product, taxonomy, image, video, promotion, comments, and reactions SQL to Postgres syntax.
- [ ] 4.4 Port checkout, orders, returns, payments, payment settings, webhooks, and email outbox SQL to Postgres syntax.
- [ ] 4.5 Port delivery, courier polling, Speedy, Econt settings, and Econt fulfillment SQL to Postgres syntax.
- [ ] 4.6 Port content/legal/admin pages: FAQ, terms, privacy, cookies, about, banner, contact, locale, and admin dashboards.
- [ ] 4.7 Port inventory, production batches, accounting config, accounting documents, ledgers, exports, valuation, COGS, and finance-period SQL.
- [ ] 4.8 Update analytics service reads that currently query SQLite order totals so they query Postgres through the app DB layer.
- [ ] 4.9 Port operational scripts and QA smoke tooling, including `scripts/seed_products.py`, `scripts/sync_cookie_inventory.py`, and `scripts/chrome_smoke.mjs`, to `DATABASE_URL` and migrated Postgres setup.

## 5. Concurrency And Search Semantics

- [ ] 5.1 Replace checkout `BEGIN IMMEDIATE` behavior with Postgres transactions using row-level locks or atomic stock update predicates.
- [ ] 5.2 Replace payment reservation cleanup locking with Postgres-safe row claiming.
- [ ] 5.3 Replace email outbox, video transcode, and courier polling claim logic with `FOR UPDATE SKIP LOCKED` or equivalent safe leases.
- [ ] 5.4 Replace SQLite FTS5 product search queries with Postgres full-text search and SQL-level filters.
- [ ] 5.5 Verify search behavior for English and Bulgarian locales, category/taxonomy filters, stock filters, sorting, counts, and pagination.
- [ ] 5.6 Ensure sync Postgres database work in async routes runs through sync endpoints or `run_in_threadpool` boundaries instead of blocking the event loop.

## 6. Test Infrastructure

- [ ] 6.1 Implement pytest-xdist-safe Postgres isolation with one migrated database per worker and FK-safe cleanup between tests.
- [ ] 6.2 Update shared fixtures to run Alembic migrations before yielding app clients or service connections.
- [ ] 6.3 Update test helpers such as `make_session`, `seed_products`, cleanup ordering, and admin clients for psycopg connections.
- [ ] 6.4 Rewrite or remove SQLite-specific tests for PRAGMA, WAL, FTS shadow tables, `sqlite_master`, old SQLite migrations, and file paths.
- [ ] 6.5 Add Alembic migration tests for fresh database creation and schema-head validation.
- [ ] 6.6 Add focused Postgres concurrency tests for checkout stock, reservation cleanup, email claims, courier leases, and payment webhook idempotency.
- [ ] 6.7 Run the backend unit and realapp suites against Postgres and fix failures.

## 7. Application And Deployment Cleanup

- [ ] 7.1 Remove `atelier_marie.db` assumptions from runtime docs, Docker volumes, troubleshooting notes, and local commands.
- [ ] 7.2 Update `Dockerfile.backend` if system packages or health checks need Postgres-aware tooling.
- [ ] 7.3 Update deployment docs to require managed Postgres, `DATABASE_URL`, and explicit Alembic migration execution.
- [ ] 7.4 Refresh `docs/DATABASE_SCHEMA.md` and technical documentation from a migrated Postgres database.
- [ ] 7.5 Document that no live production data cutover is required because the app is pre-launch.

## 8. Verification

- [ ] 8.1 Run `alembic upgrade head` against an empty local Postgres database and inspect key tables, indexes, constraints, and seed rows.
- [ ] 8.2 Run backend tests against Postgres.
- [ ] 8.3 Run frontend tests that depend on API contract changes or mocked DB-backed behavior.
- [ ] 8.4 Run a local Compose smoke test for backend startup, health, product listing/search, cart, checkout, admin order view, and content pages.
- [ ] 8.5 Run lint and typecheck after the SQLite imports and type hints are removed or replaced.
- [ ] 8.6 Confirm `rg "sqlite3|DATABASE_PATH|atelier_marie\\.db|PRAGMA|sqlite_master|BEGIN IMMEDIATE|FTS5|datetime\\('now'\\)|INSERT OR|lastrowid|last_insert_rowid" app tests scripts docs deploy technical_documentation` has no unintended runtime leftovers.
