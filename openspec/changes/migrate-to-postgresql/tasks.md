## 1. Infrastructure & Dependencies

- [ ] 1.1 Add `asyncpg`, `alembic`, and `psycopg[binary]` to `pyproject.toml` / requirements with pinned minimum versions
- [ ] 1.2 Create `docker-compose.yml` at repo root with a `postgres:16-alpine` service (user `atelier`, DB `atelier_marie`, healthcheck, named volume `pgdata`)
- [ ] 1.3 Add a dev-only compose override with `fsync=off`, `synchronous_commit=off`, `full_page_writes=off` for the test Postgres
- [ ] 1.4 Update `Makefile`: add `postgres-up` / `postgres-down` targets and make `dev-backend` and `test-backend` depend on `postgres-up` (with `pg_isready` wait)
- [ ] 1.5 Document the local Docker requirement (and native Postgres 16 install as fallback) in `README.md`

## 2. Configuration

- [ ] 2.1 Add `database_url: str` to `app/config.py` with dev default `postgresql://atelier:atelier@localhost:5432/atelier_marie`
- [ ] 2.2 Add `database_pool_min_size: int = 2` and `database_pool_max_size: int = 10` to config
- [ ] 2.3 Extend the `validate_production_config` model_validator to require `DATABASE_URL` in `ENVIRONMENT=production`
- [ ] 2.4 Remove `database_path` from `Settings` (and any lingering `SQLITE_PATH` references)
- [ ] 2.5 Ensure `DATABASE_URL` is scrubbed from log records (custom log filter or explicit exclusion at startup logging)

## 3. Alembic Setup

- [ ] 3.1 Run `alembic init migrations` and commit `alembic.ini` + `migrations/` skeleton
- [ ] 3.2 Configure `migrations/env.py` to read `DATABASE_URL` from `app.config.get_settings()` and use `psycopg` (sync) driver for migrations
- [ ] 3.3 Author revision `0001_initial.py` capturing the full current schema in Postgres form: products, users, sessions, cart_items, orders, order_items, reactions, reaction_toggle_log, comments — with `BOOLEAN`, `TIMESTAMPTZ`, `BIGINT`, `JSONB`, `CHECK` constraints, and all existing indexes
- [ ] 3.4 In `0001_initial.py`, add generated `search_en` and `search_bg` `tsvector` columns to `products` with `setweight(...)` composition
- [ ] 3.5 In `0001_initial.py`, create `idx_products_search_en` and `idx_products_search_bg` as GIN indexes; convert `idx_products_is_active` to a partial index `WHERE is_active = TRUE`; add `idx_orders_status_open` partial index
- [ ] 3.6 Verify `alembic upgrade head` and `alembic downgrade base` both run cleanly against an empty Postgres 16 DB

## 4. Database Layer Rewrite

- [ ] 4.1 Rewrite `app/database.py`: remove `_SCHEMA_SQL`, `_migrate_existing_schema`, `init_db`, `get_db`, `cleanup_expired_sessions`; introduce `init_pool(dsn, min_size, max_size)`, `close_pool()`, `get_pool()` returning the module-level `asyncpg.Pool`
- [ ] 4.2 Reimplement `cleanup_expired_sessions()` as an async function running `DELETE FROM sessions WHERE expires_at < NOW()`
- [ ] 4.3 Update `app/main.py` lifespan: startup calls `init_pool(settings.database_url, ...)`, verifies Alembic head matches (log WARNING in dev / ERROR-exit in prod on mismatch), starts the hourly cleanup task; shutdown cancels the task and awaits `close_pool()`
- [ ] 4.4 Delete or simplify `app/utils/row_access.py` (asyncpg.Record supports dict-style access already)
- [ ] 4.5 Confirm no `import sqlite3` remains under `app/` via `grep -R "sqlite3" app/`

## 5. Service Layer Query Rewrite (one commit per service)

- [ ] 5.1 `app/services/product_service.py`: convert all queries to asyncpg, replace `?` placeholders with `$N`, switch search to `tsvector` + `plainto_tsquery` + `ts_rank_cd`, honor `locale` to pick `search_en` / `search_bg`, apply category/in-stock/`is_active` filters in SQL, keep LIMIT/OFFSET at SQL level
- [ ] 5.2 `app/services/cart_service.py`: convert to asyncpg; validate stock via a plain `SELECT stock FROM products WHERE id = $1` on add; return 409 on `stock = 0`
- [ ] 5.3 `app/services/order_service.py`: rewrite checkout — open `async with pool.acquire() as conn: async with conn.transaction():`, `SELECT ... FOR UPDATE ORDER BY id ASC` for all cart products, validate stock, `executemany` decrement, `INSERT` order + order_items, `DELETE FROM cart_items WHERE session_id = $1`; catch `UniqueViolationError`, `CheckViolationError`, `DeadlockDetectedError` with `from` chaining
- [ ] 5.4 `app/services/order_service.py`: implement single-retry loop on `DeadlockDetectedError` (`40P01`); raise `RetryableError` if retry also fails
- [ ] 5.5 `app/services/auth_service.py`: convert to asyncpg; session `SELECT/INSERT/UPDATE` use `TIMESTAMPTZ` (`NOW()`, `NOW() + INTERVAL '30 days'`) instead of `datetime('now')` strings
- [ ] 5.6 `app/services/admin_service.py`: rewrite listing queries; convert CSV import to batch-existence check (`WHERE id = ANY($1::text[])`) and `INSERT ... ON CONFLICT (id) DO UPDATE SET ...` upsert; per-row errors captured without aborting the batch
- [ ] 5.7 `app/services/comment_service.py`: convert to asyncpg
- [ ] 5.8 `app/services/reaction_service.py`: convert to asyncpg; keep the toggle-log rate-limit query semantics

## 6. Middleware & Dependencies

- [ ] 6.1 `app/middleware/session.py`: rewrite session lookup / creation using `async with pool.acquire()` and `TIMESTAMPTZ` semantics; keep the "eager creation" behavior and `request.state.session_is_new` flag
- [ ] 6.2 `app/dependencies/auth.py` and `app/dependencies/session.py`: adjust for async Postgres calls (they already used awaits, but confirm no lingering `sqlite3.Row` assumptions)
- [ ] 6.3 `app/exceptions.py`: add mapping for `asyncpg.exceptions.UniqueViolationError` → 409, `PostgresConnectionError` → 503, add `DatabaseUnavailableError` and `RetryableError` custom exceptions

## 7. Full-Text Search Cleanup

- [ ] 7.1 Delete the `_PRODUCT_FTS_RESET_SQL` and FTS5 trigger blocks (already gone with the `app/database.py` rewrite — confirm)
- [ ] 7.2 `grep -RE "products_fts|MATCH|fts5" app/` returns nothing
- [ ] 7.3 Product search integration test verifies English stemming ("candle" matches "candles") and Bulgarian simple config behavior

## 8. Data Migration Tool (One-Shot)

- [ ] 8.1 Create `scripts/migrate_sqlite_to_postgres.py`: reads an existing `atelier_marie.db`, runs `alembic upgrade head` against target Postgres, streams rows table-by-table via `INSERT` respecting FK order
- [ ] 8.2 Convert timestamp strings to Python `datetime` before insert; convert integer bool flags to `bool`; validate `delivery_details` JSON blobs and log/skip malformed rows
- [ ] 8.3 Print per-table row-count summary at the end; document usage in README under "Migrating an existing dev DB"

## 9. Test Infrastructure

- [ ] 9.1 Add a `tests/conftest.py` session-scoped fixture that creates `atelier_test_template` DB, runs `alembic upgrade head`, marks it as template (`ALTER DATABASE ... IS_TEMPLATE TRUE`), drops it on session teardown
- [ ] 9.2 Add a module-scoped `app` fixture that clones the template into `test_<workerid>_<modname>` via `CREATE DATABASE ... TEMPLATE ...`, opens the pool against it, tears down at module end
- [ ] 9.3 Add an autouse function-scoped fixture that runs `TRUNCATE products, users, sessions, cart_items, orders, order_items, reactions, reaction_toggle_log, comments RESTART IDENTITY CASCADE` between tests
- [ ] 9.4 Rewrite `make_session()` and `seed_products()` helpers to use asyncpg
- [ ] 9.5 Rewrite `admin_client` fixture (Bearer auth stays; only the underlying connection changes)
- [ ] 9.6 Rewrite `tests/realapp/conftest.py` similarly (real middleware, real pool)
- [ ] 9.7 Update `FakeSessionMiddleware` to no longer touch the DB (already the intent — confirm no asyncpg leaks)
- [ ] 9.8 Ensure xdist worker isolation: each worker gets its own template-clone naming space (`gw0`, `gw1`, …)
- [ ] 9.9 Verify `make test-backend` passes green with `-n auto`; measure and note the new wall-time in the PR description

## 10. New / Updated Tests

- [ ] 10.1 `tests/test_migrations.py`: verifies `alembic upgrade head` followed by `alembic downgrade base` runs clean
- [ ] 10.2 `tests/test_checkout_concurrency.py`: exercises two concurrent checkouts for the last unit — asserts exactly one wins, other gets 409, stock ends at 0
- [ ] 10.3 `tests/test_product_search.py`: covers English stemming, Bulgarian simple tokenization, operator-character safety, category+stock filter combination
- [ ] 10.4 `tests/test_admin_csv_import.py`: adds an upsert case (existing SKU) and a malformed-row-doesn't-abort-batch case
- [ ] 10.5 `tests/test_session_cleanup.py`: seeds expired sessions, runs cleanup, asserts rows deleted and cascade-removed cart_items
- [ ] 10.6 `tests/test_database.py`: pool acquire/release, pool exhaustion timeout → 503

## 11. Deployment Documentation

- [ ] 11.1 Add a `docs/DEPLOYMENT.md` (or extend README) covering: self-hosted Postgres on the VPS (install, `pg_hba.conf`, `postgresql.conf` tuning defaults — `shared_buffers`, `effective_cache_size`, `max_connections`), and a managed alternative (Neon/Supabase) — both driven by the same `DATABASE_URL`
- [ ] 11.2 Document backup strategy: nightly `pg_dump` to Backblaze B2 (or the equivalent object store), plus `pgbackrest` as a heavier alternative
- [ ] 11.3 Document the deploy sequence: `alembic upgrade head` runs BEFORE the app restart, never at app startup
- [ ] 11.4 Update `CLAUDE.md`: replace "SQLite (WAL mode)" with "PostgreSQL 16"; update Application Structure section (no more `_SCHEMA_SQL`, mention `migrations/`); adjust the Key Design Decisions section

## 12. Cleanup & Merge

- [ ] 12.1 Delete `app/utils/row_access.py` (or its remnants) and remove imports
- [ ] 12.2 Remove any lingering references to `atelier_marie.db` from the codebase (except the one-shot migration script)
- [ ] 12.3 Confirm `openspec/changes/deferred/analytics-sandbox` is untouched (Layer 2 still deferred)
- [ ] 12.4 Run `make lint` and `make test` end-to-end green
- [ ] 12.5 Update the openspec `product-service`, `checkout-flow`, and related archived specs by running `/opsx:archive` after merge
