## MODIFIED Requirements

### Requirement: Application starts successfully
The application SHALL start via `uvicorn app.main:app` and respond to HTTP requests within 2 seconds of launch when configured with a reachable migrated Postgres database.

#### Scenario: Clean startup
- **WHEN** the application starts with a valid `DATABASE_URL` pointing at a Postgres database at Alembic head
- **THEN** the server binds to port 8000 and verifies database connectivity without creating SQLite files or running inline DDL

#### Scenario: Health endpoint available
- **WHEN** a client sends `GET /v1/health`
- **THEN** the response status is 200 and the body contains `{"status": "ok"}`

#### Scenario: Routers registered at startup
- **WHEN** the application starts
- **THEN** routers are registered for /v1/products, /v1/cart, /v1/orders, /v1/auth, and /v1/admin prefixes

#### Scenario: CORS middleware active
- **WHEN** a cross-origin request arrives from a configured origin
- **THEN** appropriate CORS headers are included in the response

### Requirement: Configuration is environment-driven
The application SHALL read all configuration from environment variables with sensible development defaults. Missing required production config SHALL cause a startup failure with a clear error message.

#### Scenario: Default development config
- **WHEN** the app starts in development with no database override and the documented local Postgres service is reachable
- **THEN** it uses a local-development Postgres `DATABASE_URL`, a development JWT secret, `./static` as the static file path, and `["http://localhost:3000"]` as default CORS origins

#### Scenario: Production config override
- **WHEN** `DATABASE_URL`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `CORS_ORIGINS`, and `STATIC_FILE_PATH` are set as environment variables
- **THEN** the application uses those values instead of defaults

#### Scenario: Missing production config in production mode
- **WHEN** `ENVIRONMENT=production` is set but `JWT_SECRET` or `DATABASE_URL` is not provided
- **THEN** the application refuses to start with a validation error

#### Scenario: CORS origins configured
- **WHEN** `CORS_ORIGINS` is set to a comma-separated list of URLs
- **THEN** the application allows cross-origin requests only from those origins

## REMOVED Requirements

### Requirement: Database initializes with WAL mode
**Reason**: SQLite WAL mode and startup DDL are removed because Postgres is now the only app database and Alembic owns schema creation.
**Migration**: Use `DATABASE_URL` for Postgres connectivity and run `alembic upgrade head` before app startup.

## ADDED Requirements

### Requirement: Database schema is migration-managed
The application SHALL rely on Alembic-managed Postgres schema state instead of creating or mutating app tables during normal startup.

#### Scenario: Startup does not run DDL
- **WHEN** the app starts against a migrated Postgres database
- **THEN** startup verifies connectivity and migration version
- **AND** does not execute `CREATE TABLE IF NOT EXISTS` or SQLite compatibility migrations

#### Scenario: Missing schema gives actionable failure
- **WHEN** the app starts against an empty Postgres database without Alembic migrations applied
- **THEN** startup fails with an error that names the missing migration state and the migration command to run
