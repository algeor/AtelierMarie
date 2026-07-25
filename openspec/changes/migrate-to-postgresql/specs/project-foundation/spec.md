## MODIFIED Requirements

### Requirement: Configuration is environment-driven
The application SHALL read all configuration from environment variables with sensible development defaults. Missing required production config SHALL cause a startup failure with a clear error message. Database connectivity SHALL be configured via a `DATABASE_URL` Postgres DSN — the prior `DATABASE_PATH` / `SQLITE_PATH` settings SHALL NOT exist.

#### Scenario: Default development config
- **WHEN** the app starts with no environment variables set
- **THEN** it uses `postgresql://atelier:atelier@localhost:5432/atelier_marie` as the default `DATABASE_URL`, a development JWT secret, `./static` as the static file path, and `["http://localhost:3000"]` as default CORS origins

#### Scenario: Production config override
- **WHEN** `DATABASE_URL`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `CORS_ORIGINS`, and `STATIC_FILE_PATH` are set as environment variables
- **THEN** the application uses those values instead of defaults

#### Scenario: Missing production config in production mode
- **WHEN** `ENVIRONMENT=production` is set but `JWT_SECRET` is not provided
- **THEN** the application refuses to start with a validation error

#### Scenario: Missing DATABASE_URL in production
- **WHEN** `ENVIRONMENT=production` is set but `DATABASE_URL` is not provided
- **THEN** the application refuses to start with a validation error naming `DATABASE_URL` as missing

#### Scenario: CORS origins configured
- **WHEN** `CORS_ORIGINS` is set to a comma-separated list of URLs
- **THEN** the application allows cross-origin requests only from those origins

### Requirement: Database connectivity uses PostgreSQL with connection pooling
The database layer SHALL open an `asyncpg` connection pool at application startup and close it at shutdown. Schema SHALL be managed exclusively by Alembic migrations run outside the application startup path. The application SHALL NOT create, alter, or drop tables at startup.

#### Scenario: First-time database provisioning
- **WHEN** the deployment pipeline runs `alembic upgrade head` against an empty Postgres database
- **THEN** all schema tables are created with their constraints, indexes, generated tsvector columns, and default values from the head revision

#### Scenario: Existing database reuse
- **WHEN** the application starts and the `alembic_version` in the DB matches the code's expected head
- **THEN** the app opens the connection pool, executes a `SELECT 1` health probe, and begins serving traffic — no schema statements are executed

#### Scenario: Connection pool active
- **WHEN** the application is running and any service function needs a connection
- **THEN** it acquires from the pool via `pool.acquire()`, executes its work, and releases; pool size respects `DATABASE_POOL_MIN_SIZE` and `DATABASE_POOL_MAX_SIZE`
