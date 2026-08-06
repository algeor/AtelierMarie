## ADDED Requirements

### Requirement: App database uses Postgres connection URLs
The backend SHALL use Postgres as the only supported application database and SHALL configure it through `DATABASE_URL`.

#### Scenario: Development database URL is used
- **WHEN** the app starts in development with `DATABASE_URL` set to a Postgres URL
- **THEN** the database layer opens psycopg connections to that Postgres database
- **AND** no SQLite database file is created or opened

#### Scenario: Production rejects missing database URL
- **WHEN** `ENVIRONMENT=production` is set and `DATABASE_URL` is missing or empty
- **THEN** startup fails with a clear configuration validation error

#### Scenario: SQLite path is rejected
- **WHEN** `DATABASE_URL` is set to a SQLite path or SQLite URL
- **THEN** startup fails with a clear error that SQLite is no longer supported

### Requirement: Alembic owns application schema versioning
The backend SHALL use Alembic migrations as the authoritative mechanism for creating and changing the app database schema.

#### Scenario: Fresh database upgrade
- **WHEN** a developer runs `alembic upgrade head` against an empty Postgres database
- **THEN** all application tables, constraints, indexes, triggers, and structural seed rows are created
- **AND** `alembic_version` records the exact current head revision id from the Alembic revision graph

#### Scenario: Migration scripts declare revision chain
- **WHEN** a new Alembic migration script is added
- **THEN** it declares a stable `revision` id
- **AND** it declares the correct `down_revision` for the previous migration in the chain
- **AND** migration ordering does not depend on filename or timestamp sorting

#### Scenario: App starts with current schema
- **WHEN** the app starts against a Postgres database whose current Alembic revision matches the script-directory head revision
- **THEN** startup completes without attempting to create tables directly

#### Scenario: App rejects stale schema
- **WHEN** the app starts against a Postgres database whose Alembic revision is missing, behind head, or diverged from the script-directory revision graph
- **THEN** startup fails with a clear instruction to run Alembic migrations

### Requirement: Initial Postgres migration preserves current domain schema
The initial Postgres migration SHALL represent the current fresh application schema and preserve domain constraints needed by existing behavior.

#### Scenario: Constraint parity
- **WHEN** the initial migration is applied
- **THEN** product price, stock, cart quantity, order status, payment status, inventory, return, contact, courier, content, and accounting constraints are enforced by Postgres

#### Scenario: Index parity
- **WHEN** the initial migration is applied
- **THEN** indexes required by product listing, cart lookup, order/admin filters, payment reconciliation, courier polling, inventory, accounting, and content ordering exist in Postgres

#### Scenario: Structural seed data exists
- **WHEN** the initial migration is applied to an empty database
- **THEN** singleton/default rows needed for settings, taxonomy, FAQ, legal pages, cookies, banner, about content, delivery, Econt, and inventory setup exist or are created by migration-managed seed steps

### Requirement: Database connection context commits and rolls back transactions
The database layer SHALL provide a connection context for service code that commits successful units of work and rolls back failed units of work.

#### Scenario: Successful unit of work commits
- **WHEN** service code exits the database context without raising an exception
- **THEN** the transaction is committed and the connection is returned or closed cleanly

#### Scenario: Failed unit of work rolls back
- **WHEN** service code raises an exception inside the database context
- **THEN** the transaction is rolled back and the exception is propagated

#### Scenario: Rows support keyed access
- **WHEN** service code fetches a row from Postgres
- **THEN** fields can be read by column name in the same service transformations that previously consumed SQLite rows

#### Scenario: Integrity errors map to expected domain handling
- **WHEN** a Postgres unique, foreign-key, or check constraint violation occurs in a service that previously handled `sqlite3.IntegrityError`
- **THEN** the service maps the psycopg error to the same domain-level response or exception behavior expected by existing API tests

### Requirement: Postgres access does not block the event loop
The backend SHALL avoid running synchronous Postgres network I/O directly on FastAPI's event loop.

#### Scenario: Async route performs database work
- **WHEN** an async route needs to execute synchronous database service code
- **THEN** the database work runs behind a threadpool boundary or the endpoint is converted to a sync handler managed by FastAPI's threadpool

#### Scenario: Database pool is used
- **WHEN** multiple requests need database connections
- **THEN** connections are acquired from a configured psycopg connection pool and returned after commit or rollback

### Requirement: Public timestamp and flag shapes remain stable
The Postgres port SHALL preserve API-visible timestamp and 0/1 flag behavior unless an owning API contract is deliberately changed and tested.

#### Scenario: Timestamp row is returned by Postgres
- **WHEN** an API response includes a timestamp loaded from a Postgres `timestamptz` column
- **THEN** the response serializes it in the expected public format for existing frontend and API consumers

#### Scenario: Existing integer flag column is migrated
- **WHEN** a SQLite column represented a boolean as `0` or `1`
- **THEN** the initial Postgres schema preserves compatible `0`/`1` semantics or updates all dependent code and tests in the same change

### Requirement: Local Docker Compose provides Postgres
The local Compose stack SHALL include a Postgres service for development and smoke testing.

#### Scenario: Compose database starts
- **WHEN** a developer starts the Compose stack
- **THEN** Postgres starts with a persistent named volume, healthcheck, database name, user, and password suitable for local development

#### Scenario: Backend waits for database health
- **WHEN** the backend service starts through Compose
- **THEN** it depends on the Postgres service being healthy before attempting database connections

### Requirement: Migration execution is explicit and repeatable
Local and deployed environments SHALL have an explicit command or service for applying Alembic migrations before backend startup depends on schema state.

#### Scenario: Local migration command runs
- **WHEN** a developer runs the documented local migration command against the Compose Postgres service
- **THEN** Alembic upgrades the database to head without requiring the backend to create tables at startup

#### Scenario: Backend starts before migrations are applied
- **WHEN** the backend starts against a database that has not run Alembic migrations
- **THEN** startup fails with a clear migration error instead of partially initializing schema

### Requirement: Operational scripts use the Postgres database layer
Operational scripts and browser smoke setup SHALL use `DATABASE_URL` and migrated Postgres schema instead of opening SQLite files directly.

#### Scenario: Seed products script runs
- **WHEN** a developer runs the product seeding script after migrations are applied
- **THEN** it connects through the Postgres database layer and seeds products idempotently

#### Scenario: Browser smoke setup starts servers
- **WHEN** the browser smoke script starts backend and frontend servers itself
- **THEN** it provisions or reuses a migrated Postgres test database and passes `DATABASE_URL` to the backend
