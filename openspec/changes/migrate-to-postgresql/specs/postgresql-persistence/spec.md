## ADDED Requirements

### Requirement: Runtime uses PostgreSQL 16 via asyncpg
The application SHALL connect to PostgreSQL 16 (or newer) as its sole Layer 1 datastore for all runtime read and write traffic. The connection driver SHALL be `asyncpg`. The application SHALL NOT open SQLite connections for any Layer 1 operation.

#### Scenario: Application boots against Postgres
- **WHEN** the application starts with `DATABASE_URL` pointing at a reachable Postgres 16 instance
- **THEN** the app opens an `asyncpg` connection pool during lifespan startup, executes a lightweight `SELECT 1` health probe, and begins serving requests
- **AND** no `sqlite3` module is imported by any code under `app/` at runtime

#### Scenario: Application refuses to start against unreachable Postgres
- **WHEN** the application starts with a `DATABASE_URL` that cannot be reached (DNS failure, wrong port, credentials rejected)
- **THEN** the lifespan startup logs an ERROR with the connection failure reason and the process exits non-zero within 10 seconds

### Requirement: Connection pool sized via configuration
The application SHALL manage database connections through an `asyncpg` connection pool created at application startup and closed at application shutdown. Pool minimum and maximum size SHALL be configurable via environment variables `DATABASE_POOL_MIN_SIZE` (default 2) and `DATABASE_POOL_MAX_SIZE` (default 10).

#### Scenario: Pool acquired per operation
- **WHEN** a service function needs to run a query
- **THEN** it acquires a connection from the pool via `async with pool.acquire() as conn:` and releases it when the block exits
- **AND** no service function opens a raw `asyncpg.connect()` outside the pool

#### Scenario: Pool respects configured limits
- **WHEN** `DATABASE_POOL_MAX_SIZE=5` is set and 6 concurrent requests all need a connection
- **THEN** at most 5 connections are open simultaneously and the 6th request waits until a connection is released

#### Scenario: Pool closed cleanly on shutdown
- **WHEN** the application receives a shutdown signal
- **THEN** the lifespan `shutdown` handler awaits `pool.close()` before the process exits and no `asyncpg` "connection was garbage collected" warnings appear

### Requirement: Configuration replaces SQLite path with Postgres URL
The application configuration SHALL expose `DATABASE_URL` (a Postgres DSN, e.g., `postgresql://user:pass@host:5432/dbname`) as a required setting in production and a defaulted setting in development. The prior `database_path` / `SQLITE_PATH` settings SHALL NOT exist.

#### Scenario: Development default
- **WHEN** the application starts in `ENVIRONMENT=development` with no `DATABASE_URL` set
- **THEN** it uses `postgresql://atelier:atelier@localhost:5432/atelier_marie` as the default

#### Scenario: Production requires explicit DATABASE_URL
- **WHEN** the application starts in `ENVIRONMENT=production` with no `DATABASE_URL` set
- **THEN** the pydantic settings validator raises a startup error naming `DATABASE_URL` as missing

#### Scenario: DATABASE_URL is not logged
- **WHEN** any log entry is emitted at startup
- **THEN** the full `DATABASE_URL` (including password) does NOT appear in any log record — only host and database name may be logged for diagnostics

### Requirement: Schema managed by Alembic
The database schema SHALL be defined and evolved through Alembic migration revisions stored in `migrations/versions/`. The application SHALL NOT create or alter tables at startup. Deploying a new schema version SHALL be a distinct step from starting the application.

#### Scenario: Fresh database migrated to head
- **WHEN** an operator runs `alembic upgrade head` against an empty Postgres database
- **THEN** all tables (`products`, `users`, `sessions`, `cart_items`, `orders`, `order_items`, `reactions`, `reaction_toggle_log`, `comments`) are created with the constraints, indexes, and default values specified in the current head revision
- **AND** the `alembic_version` table records the head revision ID

#### Scenario: Application refuses to run against outdated schema
- **WHEN** the application starts and the DB's `alembic_version` does not match the code's expected head revision
- **THEN** the lifespan startup logs a WARNING (development) or ERROR and exits (production) — never proceeds against a schema mismatch

#### Scenario: Downgrade path exists
- **WHEN** an operator runs `alembic downgrade -1`
- **THEN** the previous revision's schema is restored (subject to any documented data-loss caveats in the revision file's docstring)

#### Scenario: Startup does not create tables
- **WHEN** the application starts against an empty database
- **THEN** it does NOT run `CREATE TABLE` statements — it fails the schema-version check and refuses to boot until Alembic runs

### Requirement: Column types map correctly from SQLite semantics
The Alembic-managed schema SHALL translate the prior SQLite column types to their idiomatic Postgres equivalents: `INTEGER` boolean flags become `BOOLEAN`, `TEXT` timestamps become `TIMESTAMPTZ`, `TEXT` JSON blobs become `JSONB`, and money fields (`price_cents`, `total_cents`) become `BIGINT` (still integer cents, never `NUMERIC` or `FLOAT`).

#### Scenario: Boolean flags are real booleans
- **WHEN** an admin queries a product's `is_active`, `is_featured`, `translation_stale_en`, `translation_stale_bg`
- **THEN** the values returned by asyncpg are Python `bool` objects, not integers

#### Scenario: Timestamps returned as datetime
- **WHEN** any service reads a `created_at`, `updated_at`, or `expires_at` column
- **THEN** asyncpg returns a timezone-aware `datetime.datetime` object (UTC)

#### Scenario: Delivery details are JSONB
- **WHEN** an order with structured `delivery_details` is written
- **THEN** the column type is `JSONB` and asyncpg serializes the Python dict on write and returns a dict on read — no manual `json.dumps` / `json.loads` at the service layer

#### Scenario: Prices remain integer cents
- **WHEN** a product's `price_cents` is read
- **THEN** it is a Python `int` and the column type is `BIGINT` with the same non-negative constraints as before

### Requirement: Concurrent stock decrement uses row locks
The checkout transaction SHALL acquire row-level locks on all affected product rows via `SELECT ... FOR UPDATE` before validating and decrementing stock. Products SHALL be locked in ascending `id` order to prevent deadlocks between concurrent checkouts.

#### Scenario: Two concurrent checkouts for the last unit
- **WHEN** two concurrent transactions each attempt to check out the last unit of product X
- **THEN** the first transaction acquires the row lock, decrements stock to 0, and commits
- **AND** the second transaction blocks on the row lock, then upon acquisition sees `stock = 0`, rolls back, and its request receives HTTP 409 (`InsufficientStockError`)
- **AND** product X's final stock is 0, never negative

#### Scenario: Checkout locks products in deterministic order
- **WHEN** a checkout involves products with ids `zzz-candle` and `aaa-candle`
- **THEN** the `SELECT ... FOR UPDATE` clause orders the ids ascending (`aaa-candle` locked before `zzz-candle`) so two concurrent multi-product checkouts cannot deadlock

#### Scenario: Row locks release on transaction end
- **WHEN** a checkout transaction commits or rolls back
- **THEN** all `FOR UPDATE` locks acquired within that transaction are released and unrelated read queries on those products are unblocked

### Requirement: Stock non-negativity enforced at DB level
The `products` table SHALL retain a `CHECK (stock >= 0)` constraint as the last line of defense against negative stock even when application-level guards fail.

#### Scenario: Direct UPDATE attempting negative stock is rejected
- **WHEN** any SQL statement attempts to set a product's `stock` below zero
- **THEN** Postgres raises a `check_violation` error (SQLSTATE `23514`) and the statement fails
- **AND** the surrounding transaction rolls back

### Requirement: Expired sessions cleaned by SQL-native delete
The session cleanup task SHALL delete expired sessions using `DELETE FROM sessions WHERE expires_at < NOW()` against a `TIMESTAMPTZ expires_at` column with an index on `expires_at`. The task SHALL continue to run hourly during application lifetime.

#### Scenario: Hourly cleanup deletes expired rows
- **WHEN** the background cleanup task fires
- **THEN** it executes a single `DELETE FROM sessions WHERE expires_at < NOW()` query and logs the number of rows deleted at INFO level

#### Scenario: Cleanup uses the index
- **WHEN** `EXPLAIN` is run on the cleanup query against a table with many expired sessions
- **THEN** the query plan uses an index scan on `idx_sessions_expires_at`, not a sequential scan

#### Scenario: Cleanup cascades to cart items
- **WHEN** a session row is deleted by cleanup
- **THEN** the associated `cart_items` rows are removed via `ON DELETE CASCADE` and no orphaned cart rows remain

### Requirement: Postgres error taxonomy maps to service exceptions
The service layer SHALL translate Postgres error codes into the existing custom exception hierarchy. Specifically: unique-violation (`23505`) SHALL raise `DuplicateError`, check-violation (`23514`) on stock SHALL raise `InsufficientStockError` (as a defense-in-depth backup to the pre-check), foreign-key-violation (`23503`) SHALL raise the appropriate not-found error, and deadlock-detected (`40P01`) SHALL be caught and either retried once or converted to a transient `RetryableError`.

#### Scenario: Duplicate product SKU raises DuplicateError
- **WHEN** the admin CSV import tries to insert a product with an `id` that already exists via an `INSERT` (not `UPSERT`)
- **THEN** asyncpg raises a `UniqueViolationError` (SQLSTATE `23505`), the service catches it and raises `DuplicateError(entity="product", id=...)` with `from` chaining

#### Scenario: Deadlock is retried once
- **WHEN** a checkout transaction receives SQLSTATE `40P01` (deadlock detected)
- **THEN** the service retries the entire transaction one time; if the retry also fails, `RetryableError` is raised and the route returns HTTP 409

### Requirement: Layer 1 code has no SQLite imports post-cutover
After migration completes, no module under `app/` SHALL import from the `sqlite3` standard library module. The `app/utils/row_access.py` helper SHALL be either deleted or reduced to a plain `dict(record)` cast that does not depend on `sqlite3.Row`.

#### Scenario: Grep for sqlite3 in app returns nothing
- **WHEN** `grep -R "^import sqlite3\|^from sqlite3" app/` is run
- **THEN** it produces no matches

#### Scenario: One-shot migration script may import sqlite3
- **WHEN** `grep -R "^import sqlite3\|^from sqlite3" scripts/` is run
- **THEN** matches are permitted only in `scripts/migrate_sqlite_to_postgres.py` (the one-shot dev-DB copier)
