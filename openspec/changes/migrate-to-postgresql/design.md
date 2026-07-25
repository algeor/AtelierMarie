## Context

AtelierMarie's Layer 1 (production e-commerce) currently uses SQLite in WAL mode as the system of record. The schema lives in `app/database.py` and is materialized at startup via `_SCHEMA_SQL` with `CREATE TABLE IF NOT EXISTS`, plus an ad-hoc `_migrate_existing_schema()` that patches older dev databases in place. Product search uses two SQLite FTS5 virtual tables (`products_fts_en`, `products_fts_bg`) kept in sync via triggers. Sessions, orders, cart items, reactions, and comments all sit in the same file.

This has worked well for local development and single-process testing. It stops working the moment we care about production:

- **Concurrent writes**: SQLite's WAL is single-writer. Two customers checking out simultaneously serialize at the DB, and the current stock decrement in checkout has no explicit row lock — it relies on the CHECK constraint as the last line of defense. That's correct but coarse.
- **Deploys**: `db.sqlite3` is pinned to a single VM's local disk. Moving between VPS providers, running blue/green deploys, or attaching a read replica requires bespoke rsync scripting.
- **Backups**: A hot `.sqlite` file is trivial to copy wrong (WAL/SHM sidecars), and PITR isn't a thing.
- **Managed hosting**: Every cheap production host (Hetzner, Oracle, Fly, Render) supports Postgres natively; none supports SQLite as a first-class managed service.

Constraints that shape the design:
- **No production data exists yet.** This migration is happening on a dev DB only, so we don't need online migration tooling — a one-shot copy script is enough.
- **Layer 2 (analytics/ML) is not yet implemented.** DuckDB is still the planned analytics store; that decision is untouched.
- **The service layer is already testable-without-HTTP.** Services take explicit parameters, so swapping the DB driver ripples through queries but not through business logic shape.
- **Prices are `int` cents, product IDs are text (SKU/slug).** These are stable choices; the migration must preserve them.

Stakeholders: solo dev (owner), single small VPS in production, low-to-moderate traffic (family candle business).

## Goals / Non-Goals

**Goals:**
- Replace SQLite with PostgreSQL 16 as the sole Layer 1 datastore, no dual-write period.
- Introduce **Alembic** for versioned schema management; retire startup-time `CREATE TABLE IF NOT EXISTS`.
- Use **asyncpg** with a connection pool for all runtime queries (Uvicorn is already async).
- Reimplement product full-text search on Postgres `tsvector` + GIN, preserving the bilingual (English + Bulgarian) split.
- Close the concurrent-checkout race with explicit `SELECT ... FOR UPDATE` on stock rows inside the checkout transaction.
- Make local dev frictionless via `docker-compose up postgres` and a Make target that waits for readiness.
- Keep the test suite fast: parallel-safe Postgres test DBs per xdist worker, cleaned via `TRUNCATE`.
- Preserve the two-layer cardinal rule: nothing in this migration introduces a Layer 2 import from Layer 1.
- Provide a one-shot `scripts/migrate_sqlite_to_postgres.py` for anyone with a local SQLite dev DB.

**Non-Goals:**
- Zero-downtime or online migration. Production has no data.
- Multi-region or read-replica topology. Single-writer Postgres is more than enough for this store.
- Rewriting the service layer or repository pattern. Query changes only.
- Migrating Layer 2 (there's nothing to migrate).
- Switching ORMs — we've never used one and won't start now. Raw SQL with `asyncpg` stays the norm.
- Introducing PgBouncer in v1. Single-app Uvicorn on one box doesn't need it. Revisit if/when we scale out.

## Decisions

### Driver: `asyncpg` (not `psycopg`, not SQLAlchemy)

FastAPI + Uvicorn is async top-to-bottom, and `asyncpg` is the fastest async Postgres driver in the ecosystem (roughly 2–3× `psycopg` async in benchmarks, and it avoids the sync-through-thread bridge). Our services already `await` where relevant.

Alembic itself uses a sync driver — we install `psycopg[binary]` **only** for Alembic's offline/online migration runs (invoked from CLI or a one-shot on startup). Runtime traffic goes through `asyncpg`. That's a well-worn split.

**Alternatives considered:**
- **`psycopg` (v3) async**: perfectly usable, better SQL feature coverage (COPY streaming API is nicer), but slower and no compelling reason given how simple our queries are.
- **SQLAlchemy Core / ORM**: introduces query-builder mental overhead we don't have today. Our current code uses raw parameterized SQL and it's fine. Adding SQLAlchemy would be a bigger change than the DB swap itself.
- **Databases (encode/databases)**: unmaintained, don't touch.

### Schema management: Alembic

The `_migrate_existing_schema()` in `app/database.py` is a smell — it detects pre-bilingual schemas and patches them in place. That approach breaks the moment we go to Postgres, and it can't do rollbacks. Alembic is the boring correct answer: versioned revisions in `migrations/versions/`, `alembic upgrade head` on deploy, `alembic downgrade -1` for rollback.

- Initial revision (`0001_initial.py`) captures the entire current schema translated to Postgres. Hand-written (Alembic autogenerate against a mismatched SQLite schema is worse than useless).
- Startup no longer creates tables. `app/main.py` lifespan runs `alembic upgrade head` in a subprocess (or via the `alembic.command` API) if `ENVIRONMENT=development`; production runs it as a separate deploy step.

**Alternatives considered:**
- **Yoyo / dbmate / raw SQL files in a directory**: simpler but no rollback, no autogenerate, no Python integration. Alembic is standard enough that any future contributor recognizes it.
- **Keep the `IF NOT EXISTS` bootstrap**: doesn't survive column type changes or FTS→tsvector transitions.

### Connection pooling: `asyncpg.create_pool` at app lifespan

- Pool opened in `app/main.py` lifespan `startup`, closed on `shutdown`.
- Held in a module-level `_pool` variable in `app/database.py`, exposed via `get_pool()`.
- Default `min_size=2`, `max_size=10`. For a single-VPS deployment with ~4 GB RAM Postgres running `max_connections=100` (default), this is very safe.
- Every service acquires per-operation: `async with pool.acquire() as conn: ...`. Transactions via `async with conn.transaction():`.
- Configurable via env: `DATABASE_POOL_MIN_SIZE`, `DATABASE_POOL_MAX_SIZE`.

**Alternatives considered:**
- **PgBouncer in transaction mode**: correct at scale but overkill for one app process. Adds a moving part and complicates local dev. Revisit if we ever run >1 backend replica.
- **Per-request connections (no pool)**: 5–10 ms of TLS handshake per request is unacceptable when p99 targets are <200 ms.

### Full-text search: `tsvector` + GIN, per-language

The current setup has two FTS5 virtual tables (English, Bulgarian) with sync triggers. Postgres has direct analogs: **generated `tsvector` columns** plus **GIN indexes**.

Schema (relevant columns on `products`):
```sql
search_en tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(name_en, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description_en, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(category, '')), 'C')
) STORED,
search_bg tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(name_bg, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(description_bg, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(category, '')), 'C')
) STORED,
```
Then `CREATE INDEX ... USING GIN (search_en)` and same for `search_bg`. Generated columns mean **no triggers to maintain** — Postgres re-computes on write. This is a strict improvement over the trigger-driven FTS5 approach.

Bulgarian gets `'simple'` config (lowercase, split on whitespace) because Postgres ships no Bulgarian stemmer out of the box and adding `pg_snowball` variants isn't worth the operational cost for a small catalog. English gets `'english'` for stemming + stop-words.

Queries use `plainto_tsquery(...)` for user input (safe, escapes operators) and `ts_rank_cd` for ranking:
```sql
SELECT * FROM products
WHERE search_en @@ plainto_tsquery('english', $1)
ORDER BY ts_rank_cd(search_en, plainto_tsquery('english', $1)) DESC
LIMIT $2 OFFSET $3;
```

**Alternatives considered:**
- **pg_trgm** (trigram similarity): fuzzy but no stemming, worse for real text queries. Could layer on top for typo tolerance later.
- **External search (Meilisearch, Typesense)**: massive overkill; adds a whole service to babysit.
- **Keep FTS5 via a Postgres extension**: doesn't exist. Would need to keep SQLite for search alone, which is worse than either pure option.

### Concurrent checkout: `SELECT ... FOR UPDATE`

In SQLite WAL, the CHECK constraint on `stock >= 0` prevents over-selling but can raise late (at COMMIT). In Postgres, we do it properly:

```python
async with conn.transaction():
    rows = await conn.fetch(
        "SELECT id, stock, price_cents FROM products "
        "WHERE id = ANY($1::text[]) FOR UPDATE",
        product_ids,
    )
    # verify all requested quantities <= stock, else raise InsufficientStockError
    await conn.executemany(
        "UPDATE products SET stock = stock - $2 WHERE id = $1",
        [(pid, qty) for pid, qty in ...],
    )
    # insert order, order_items
```

Row locks release on transaction end. Two concurrent checkouts serialize on the same product row and one loses cleanly. The `CHECK (stock >= 0)` constraint stays — it's the belt to the row-lock's suspenders.

### Session cleanup: SQL-native

Current implementation queries `datetime('now')` string against `expires_at TEXT`. In Postgres we'll store `expires_at` as `TIMESTAMPTZ` and cleanup is a plain `DELETE FROM sessions WHERE expires_at < NOW()` on a partial index:
```sql
CREATE INDEX idx_sessions_expires_at ON sessions (expires_at);
```
The hourly background task in `app/main.py` stays; only the query changes.

### Timestamps: `TIMESTAMPTZ`, everywhere

SQLite stored timestamps as `TEXT NOT NULL DEFAULT (datetime('now'))` (UTC by convention). Postgres has `TIMESTAMPTZ` (stored as UTC, aware). We migrate to `TIMESTAMPTZ NOT NULL DEFAULT NOW()`. Application code that parses/formats strings needs one pass to switch to `datetime` objects — asyncpg returns `datetime.datetime` directly.

### Booleans: real `BOOLEAN`, not `INTEGER`

SQLite has no bool, so `is_admin`, `is_active`, `is_featured`, `translation_stale_*` are all `INTEGER NOT NULL DEFAULT 0/1`. In Postgres these become `BOOLEAN NOT NULL DEFAULT FALSE/TRUE`. Pydantic models already expose them as `bool`, so this is a driver-layer change with no API impact.

### Money: `BIGINT` (still cents)

`price_cents INTEGER` stays, upgraded to `BIGINT` in Postgres. Cents-as-int is non-negotiable. `NUMERIC` is not used for money here — it's slower, invites float-adjacent thinking, and we don't need it.

### JSON blobs: `JSONB`

`delivery_details TEXT` (JSON blob for DeliveryOffice / DeliveryDoor) becomes `JSONB`. Same read/write shape in Python (asyncpg handles dict ↔ JSONB natively), but now indexable and queryable if we ever want reporting on delivery methods.

### Testing: Postgres per xdist worker, `TRUNCATE` for isolation

The in-memory SQLite test fixture won't map. New model:

- `tests/conftest.py` creates a **template database** once per test session (schema migrated via Alembic).
- Each xdist worker gets its own DB via `CREATE DATABASE <name> TEMPLATE <template>` (fast; Postgres copies template files).
- Function-scoped autouse fixture `TRUNCATE ... RESTART IDENTITY CASCADE` on all tables between tests.
- CI + local dev run against a `docker-compose` Postgres. `DATABASE_URL` env var overrides for CI.

`tests/realapp/` gets the same fixture (still exercises real middleware + real pool).

**Alternatives considered:**
- **`pytest-postgresql`**: cute but adds a dependency for something we can do in ~30 lines of conftest.
- **Transactional rollback per test** (`BEGIN` in setup, `ROLLBACK` in teardown): elegant but breaks anything that uses `SAVEPOINT` internally or opens its own transaction (checkout does). `TRUNCATE` is boring and correct.

### Row access: retire `app/utils/row_access.py`

The current utility exists because `sqlite3.Row` is subscript-by-int-or-name but not full dict. `asyncpg.Record` supports both `record['col']` and `record.get('col', default)` when wrapped, and is directly iterable as items. We can drop the helper or reduce it to a one-line `dict(record)` cast wherever code currently does dict access. Small cleanup, done in the same PR.

### Local dev: `docker-compose.yml` at repo root

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: atelier
      POSTGRES_PASSWORD: atelier
      POSTGRES_DB: atelier_marie
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "atelier"]
      interval: 2s
volumes:
  pgdata:
```

`make dev-backend` gains a dependency on a `postgres-up` target that runs compose and waits for `pg_isready`. Docs mention native install as an alternative for users allergic to Docker.

## Risks / Trade-offs

- **[Alembic learning curve for future contributors]** → Migration is standard enough (autogenerate + review, `alembic upgrade head` on deploy) and the README section walks through the three commands anyone needs. Non-blocker.

- **[Bulgarian FTS quality drop vs. English]** → Postgres has no Bulgarian stemmer; we use `'simple'` config. Real difference in practice: substring matches on inflected Bulgarian words won't match unless the query and product use the same form. Mitigation: (a) the current SQLite FTS5 also doesn't stem Bulgarian, so we're not regressing, (b) if it hurts, add pg_trgm + `%` operator as a secondary matcher.

- **[Deadlocks under `SELECT ... FOR UPDATE` if products locked in inconsistent order]** → Mitigation: always lock products in `ORDER BY id ASC` inside checkout. Documented in `checkout_service.py`.

- **[Local dev now requires Docker or native Postgres]** → Yes, and this is a real friction step for anyone used to "clone and run". Mitigation: `make dev-backend` runs `docker compose up -d postgres` transparently; if compose isn't installed, error message points at the Postgres 16 install instructions. Loss of the "zero-deps SQLite" story is genuine but unavoidable for the goal.

- **[Test suite gets slower]** → In-memory SQLite is astonishingly fast. Postgres + TRUNCATE per test is not. Expect the backend test suite wall time to roughly double. Mitigation: keep `pytest-xdist` parallelism, use `UNLOGGED` tables for the test template DB (10–30% faster writes, safe because we don't care about test-DB durability), fsync=off on the docker-compose Postgres.

- **[Alembic + asyncpg dual-driver footprint]** → Two Postgres drivers in `requirements.txt` is mildly annoying. Mitigation: `psycopg[binary]` is only imported by Alembic scripts, never by app code. Enforced with a `ruff` rule (or code review discipline) that bans `import psycopg` outside `migrations/`.

- **[JSON schema for `delivery_details` becomes stricter under JSONB]** → JSONB requires valid JSON at write time (TEXT didn't). If any dev DB has malformed rows, the migration script fails on those rows. Mitigation: the one-shot migration script validates + logs bad rows and skips them; production has no data so this only matters for local dev DBs.

- **[Rollback path for a bad Alembic revision]** → `alembic downgrade -1` works but destructive migrations (dropping columns) lose data. Mitigation: for any migration that drops data, the revision file includes a comment explaining the recovery step, and we tag the pre-migration DB with `pg_dump` in the deploy script.

## Migration Plan

Not a hot cutover — production has zero data. This is a code-and-schema swap.

1. **PR 1: infrastructure only** — Add `docker-compose.yml`, `alembic.ini`, `migrations/` skeleton with the initial revision, `asyncpg` + `alembic` + `psycopg[binary]` to `requirements.txt`. No app code changes. Merge to main.
2. **PR 2: `app/database.py` rewrite** — asyncpg pool, `get_pool()` accessor, lifespan startup/shutdown, remove `_SCHEMA_SQL` and `_migrate_existing_schema()`. Update `app/config.py` (`DATABASE_URL` replaces `SQLITE_PATH`). Ship with a flag so the app still boots against SQLite temporarily if needed (single feature-flag env var `DB_BACKEND=sqlite|postgres`, defaults to postgres).
3. **PR 3: service layer** — Rewrite queries in each service module (`product_service`, `cart_service`, `order_service`, `auth_service`, `admin_service`, `comment_service`, `reaction_service`). One service per commit to keep review manageable.
4. **PR 4: FTS migration** — Replace FTS5 usage in `product_service.search_products()` with the tsvector query. Drop the FTS5-specific rebuild code from `database.py`.
5. **PR 5: tests** — Rewrite `tests/conftest.py` and `tests/realapp/conftest.py` for per-worker Postgres DBs. Delete the SQLite-specific fixtures. Verify `make test-backend` runs clean and parallel.
6. **PR 6: cleanup** — Remove the `DB_BACKEND` flag, retire the SQLite-only code paths, delete `app/utils/row_access.py`. Delete `scripts/migrate_sqlite_to_postgres.py` (or keep it in `scripts/one-shot/`).

**Rollback**: PRs 1–5 are individually revertible; the final SQLite deletion is PR 6. As long as PR 6 hasn't merged, `DB_BACKEND=sqlite` puts us back on the old driver.

## Open Questions

- **Do we adopt PgBouncer at deploy time or defer?** Deferring for v1 unless we start hitting connection saturation. Revisit if/when we run multiple backend replicas.
- **Do we back Alembic migrations with tests?** Probably yes — a `test_migrations.py` that runs `upgrade head` then `downgrade base` catches broken downgrades. Add in PR 5 if not blocked on complexity.
- **`pg_trgm` for typo-tolerant search?** Not now. Ship the tsvector baseline, revisit if search quality complaints show up.
- **Managed vs. self-hosted Postgres in production?** Independent of this design. Deployment docs will describe both shapes with the same `DATABASE_URL`; no code changes either way.
