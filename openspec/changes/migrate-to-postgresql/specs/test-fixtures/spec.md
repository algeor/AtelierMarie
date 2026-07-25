## MODIFIED Requirements

### Requirement: Module-scoped app fixture initializes DB once per file
The shared `conftest.py` SHALL provide a module-scoped `app` fixture that creates a per-worker PostgreSQL database (cloned from a session-scoped template DB migrated to head via Alembic) and calls `create_app()` exactly once per test module. All tests in that module share the same app instance and Postgres database.

#### Scenario: Two tests in same module share app
- **WHEN** `test_a` and `test_b` both request the `app` fixture in the same file
- **THEN** `create_app()` is called exactly once and both tests operate against the same per-worker Postgres database

#### Scenario: Different modules get isolated databases
- **WHEN** `test_file_a.py` and `test_file_b.py` both use the module-scoped `app` fixture on the same xdist worker
- **THEN** each module gets a distinct database cloned from the template (`CREATE DATABASE test_<worker>_<mod> TEMPLATE atelier_test_template`) and neither sees the other's data

#### Scenario: Parallel xdist workers do not collide
- **WHEN** pytest-xdist runs the suite with `-n auto`
- **THEN** each worker maintains its own set of test databases keyed by worker id (`gw0`, `gw1`, ...) and no worker touches another worker's database

### Requirement: Per-test cleanup deletes all rows between tests
The shared `conftest.py` SHALL provide an autouse function-scoped fixture that truncates all data tables between tests using a single `TRUNCATE ... RESTART IDENTITY CASCADE` statement. This restores an empty schema without dropping tables.

#### Scenario: Test data does not leak to next test
- **WHEN** `test_a` inserts a product and completes
- **AND** `test_b` queries products
- **THEN** `test_b` sees zero products (truncate ran between them)

#### Scenario: Truncate cascades FK-safely
- **WHEN** cleanup runs after a test that created orders with order_items, sessions with cart_items, and products with reactions
- **THEN** `TRUNCATE ... CASCADE` clears all dependent tables in one statement without FK violations

#### Scenario: Sequences reset between tests
- **WHEN** a test uses any auto-increment sequence and cleanup runs
- **THEN** the sequence is restarted at 1 so subsequent tests see predictable IDs

### Requirement: Service tests use module-scoped Postgres connection
Service-layer tests (`test_*_service.py`) SHALL use a module-scoped `asyncpg.Connection` (or pool) fixture bound to the per-worker test database. Tests call helper functions to seed data as needed.

#### Scenario: Service test gets asyncpg connection
- **WHEN** `test_cart_service.py` requests the `service_db` fixture
- **THEN** it receives an `asyncpg` connection (or pool acquire) against the module's test database with the schema already migrated to head

## ADDED Requirements

### Requirement: Session-scoped Postgres template database exists
The test suite SHALL create exactly one template database per test session (named `atelier_test_template` or similar) whose schema is migrated to the current Alembic head. Per-module test databases SHALL be cloned from this template via `CREATE DATABASE ... TEMPLATE ...` to avoid re-running Alembic for every module.

#### Scenario: Template built once
- **WHEN** the test session starts
- **THEN** a session-scoped fixture creates the template DB, runs `alembic upgrade head` against it, and marks it as a valid template (`ALTER DATABASE ... IS_TEMPLATE TRUE`)

#### Scenario: Template reused across modules
- **WHEN** two test modules request the `app` fixture in the same test session
- **THEN** each clones from the template via `CREATE DATABASE ... TEMPLATE atelier_test_template` — Alembic runs zero additional times

#### Scenario: Template dropped at session end
- **WHEN** the test session finishes
- **THEN** the template database is dropped so re-runs start clean

### Requirement: Test Postgres tuned for speed over durability
The docker-compose Postgres used for local development and CI SHALL be configured with `fsync=off`, `synchronous_commit=off`, and `full_page_writes=off`. Test data is disposable; these settings materially reduce test suite wall time.

#### Scenario: Local test compose disables fsync
- **WHEN** `docker compose up postgres` is used for `make test-backend`
- **THEN** the Postgres process runs with `fsync=off` and related durability settings disabled
- **AND** the same compose profile is NOT used for production deployment
