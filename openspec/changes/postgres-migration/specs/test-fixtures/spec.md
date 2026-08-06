## MODIFIED Requirements

### Requirement: Module-scoped app fixture initializes DB once per file
The shared `conftest.py` SHALL provide a module-scoped `app` fixture that connects to the pytest worker's migrated Postgres test database and calls `create_app()` exactly once per test module. All tests in that module share the same app instance and worker-isolated database state.

#### Scenario: Two tests in same module share app
- **WHEN** `test_a` and `test_b` both request the `app` fixture in the same file
- **THEN** app creation for that module happens exactly once
- **AND** the worker database has already been migrated once before the app fixture yields
- **AND** both tests operate on the same pytest-worker Postgres database

#### Scenario: Different modules get isolated databases
- **WHEN** `test_file_a.py` and `test_file_b.py` both use the module-scoped `app` fixture
- **THEN** per-test cleanup prevents row leakage between modules in the same worker
- **AND** modules in different pytest workers use different Postgres databases

### Requirement: Service tests use module-scoped connection
Service-layer tests (`test_*_service.py`) SHALL use a module-scoped Postgres connection fixture. The connection is created once against migrated schema, and tests call helper functions to seed data as needed.

#### Scenario: Service test gets raw connection
- **WHEN** `test_cart_service.py` requests the `service_db` fixture
- **THEN** it receives a psycopg-backed connection with keyed row access
- **AND** the schema has already been migrated by Alembic

### Requirement: Session test files remain function-scoped
The files `test_session.py` and `test_session_hardened.py` SHALL continue using function-scoped fixtures with the real `SessionMiddleware`. They MUST NOT use `FakeSessionMiddleware` or module-scoped app fixtures.

#### Scenario: Session tests still test real middleware
- **WHEN** `test_session.py` runs
- **THEN** each test gets isolated Postgres database state and real `SessionMiddleware`
- **AND** session creation, validation, expiry, and rotation are tested against actual middleware logic

## ADDED Requirements

### Requirement: Postgres test isolation is safe under pytest-xdist
The test infrastructure SHALL isolate Postgres state with one migrated test database per pytest-xdist worker and foreign-key-safe cleanup between tests.

#### Scenario: Parallel workers use isolated database state
- **WHEN** two pytest-xdist workers run backend tests at the same time
- **THEN** each worker operates against a separate Postgres database
- **AND** cleanup in one worker does not delete rows used by another worker

#### Scenario: Alembic migrations run before tests use schema
- **WHEN** a test fixture creates a fresh worker Postgres database
- **THEN** Alembic migrations are applied before the fixture yields clients or connections

### Requirement: SQLite-specific tests are removed or rewritten
Tests SHALL assert Postgres-backed behavior and schema state instead of SQLite implementation details.

#### Scenario: SQLite PRAGMA assertion is encountered
- **WHEN** a test currently asserts `PRAGMA` output, SQLite FTS shadow tables, `sqlite_master`, or SQLite migration behavior
- **THEN** it is rewritten to assert equivalent Postgres behavior or removed if the behavior no longer applies
