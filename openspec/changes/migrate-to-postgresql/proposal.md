## Why

SQLite has served the project well during development, but as we prepare to host AtelierMarie in production it becomes the wrong tool for the job. A single-file DB pinned to one machine makes zero-downtime deploys awkward, backups error-prone, and horizontal moves (managed DB, read replicas, migrating between VPS providers) effectively impossible. PostgreSQL gives us proper concurrent writes (`SELECT ... FOR UPDATE` for stock races), first-class migrations, network-attached storage, off-the-shelf managed hosting options, and a search engine (`tsvector` + GIN) that replaces our FTS5 dependency without vendor lock-in. Doing this migration now — before real customer orders exist — is dramatically cheaper than doing it after launch.

## What Changes

- **BREAKING**: Replace SQLite (WAL mode) with PostgreSQL 16 as the system of record for Layer 1.
- Swap `sqlite3` driver for `asyncpg` (async, connection-pooled) accessed through a thin repository/connection layer in `app/database.py`.
- Introduce **Alembic** for versioned schema migrations; retire the ad-hoc `CREATE TABLE IF NOT EXISTS` bootstrap that runs at app startup.
- Rewrite **product search** from SQLite FTS5 virtual table + triggers to PostgreSQL `tsvector` column + GIN index + trigger-maintained lexeme updates.
- Replace SQLite's implicit last-writer-wins on stock decrement with explicit `SELECT ... FOR UPDATE` row locks during checkout; keep the `CHECK (stock >= 0)` constraint as the DB-level backstop.
- Move the hourly expired-session cleanup task from Python asyncio to a SQL-native `DELETE ... WHERE expires_at < NOW()` executed by the same background task, plus a partial index on `expires_at`.
- Add `DATABASE_URL` (Postgres DSN) to `app/config.py`; remove `SQLITE_PATH` and related settings.
- Update test infrastructure: replace in-memory `:memory:` SQLite fixture with a per-worker Postgres test database (created/torn down via a session-scoped fixture, isolated via `TRUNCATE ... RESTART IDENTITY CASCADE` between tests).
- Provide a one-shot **data migration script** (`scripts/migrate_sqlite_to_postgres.py`) that copies existing rows from the SQLite dev DB into the Postgres schema — useful for dev, safe to delete post-cutover since production has no data yet.
- Update `Makefile` targets (`make dev-backend`, `make test-backend`) to spin up/tear down a local Postgres via Docker Compose when no `DATABASE_URL` is set.
- Deployment docs: document the two hosting shapes (self-hosted Postgres on the same VPS vs. managed Neon/Supabase) with tuning defaults.

## Capabilities

### New Capabilities
- `postgresql-persistence`: The Postgres-backed database layer — connection/pool management, transaction primitives (`SELECT ... FOR UPDATE`), schema migrations via Alembic, and the operational contract Layer 1 code relies on.
- `postgres-fts-search`: Product full-text search backed by `tsvector` + GIN, replacing SQLite FTS5. Covers indexed columns, trigger-maintained lexemes, query construction (`plainto_tsquery` / `websearch_to_tsquery`), and ranking.

### Modified Capabilities
- `project-foundation`: Tech stack shifts from SQLite (WAL) to PostgreSQL 16; adds Alembic and `asyncpg` as core dependencies.
- `product-service`: Search implementation swaps from FTS5 to `tsvector`; concurrent stock decrement now uses `SELECT ... FOR UPDATE`.
- `product-public-api` / `product-admin-api`: Search endpoint behavior unchanged externally, but the requirement to "use FTS5" becomes "use Postgres full-text search". Product ID type stays text.
- `checkout-flow`: Stock-decrement requirement upgraded from "atomic under WAL" to "row-locked via `SELECT ... FOR UPDATE` inside the checkout transaction" — closes the concurrent-checkout race that was implicit-only in SQLite.
- `concurrency-safety`: Requirements around stock consistency and session cleanup are re-stated against Postgres semantics.
- `session-auth-lifecycle` / `session-lifecycle`: Expired-session cleanup requirement changed from Python-side sweep to SQL-native `DELETE` with `expires_at` index.
- `test-fixtures`: Test DB requirement changes from in-memory SQLite to a per-worker Postgres database with `TRUNCATE` isolation.
- `backend-query-optimization`: Indexing strategy is restated for Postgres (partial indexes, GIN, `expires_at`).
- `error-handling-hardening`: Error taxonomy adds Postgres-specific failure modes (connection loss, deadlock, unique-violation `23505`, check-violation `23514`) mapped to existing custom exceptions.
- `structured-logging`: Log context adds Postgres query duration and pool-saturation warnings.

## Impact

**Code**
- `app/database.py` — full rewrite (SQLite → asyncpg pool)
- `app/services/*` — every service that touches the DB gets its query layer updated (parameter placeholders `?` → `$1`, `sqlite3.Row` → `asyncpg.Record`, transactions via `async with pool.acquire() as conn: async with conn.transaction():`)
- `app/services/product_service.py` — search rewrite
- `app/services/order_service.py` / `cart_service.py` — checkout uses `SELECT ... FOR UPDATE`
- `app/services/auth_service.py` — session cleanup query
- `app/utils/row_access.py` — likely retired (asyncpg.Record already dict-like)
- `app/config.py` — `DATABASE_URL` replaces `SQLITE_PATH`
- `app/main.py` — lifespan opens/closes the asyncpg pool
- `tests/conftest.py` + `tests/realapp/conftest.py` — Postgres fixtures
- `scripts/seed_products.py` — Postgres-compatible upserts

**New files**
- `alembic.ini`, `migrations/` directory with initial revision capturing current schema
- `scripts/migrate_sqlite_to_postgres.py` (one-shot)
- `docker-compose.yml` (local Postgres for dev/test)

**Dependencies (pyproject / requirements)**
- Add: `asyncpg`, `alembic`, `psycopg[binary]` (Alembic's sync driver)
- Remove: nothing (stdlib `sqlite3` stays for the one-shot migration script only)

**APIs**
- No external HTTP API changes. Response shapes are identical.
- Search endpoint semantics slightly better (stemming, stop-words) — additive.

**Ops / Deployment**
- New env var: `DATABASE_URL`
- Deploy target grows a Postgres instance (self-hosted on the VPS, or managed)
- Backup strategy shifts from copying `db.sqlite` to `pg_dump` / `pgbackrest`
- `make dev-backend` gains a dependency on Docker (or a locally installed Postgres)

**Non-impact**
- Layer 2 (analytics/ML) is untouched — it never existed in code and is still deferred. DuckDB is still the planned analytics store.
- Frontend is untouched — no API contract changes.
- Product IDs remain text (SKU/slug); prices remain `int` cents (now `BIGINT`).
