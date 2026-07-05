## ADDED Requirements

### Requirement: Package configuration exists
The project SHALL have a `pyproject.toml` that declares all production and development dependencies with pinned minimum versions, and configures ruff and pytest.

#### Scenario: Fresh install
- **WHEN** a developer runs `pip install -e ".[dev]"`
- **THEN** all production and development dependencies are installed successfully

#### Scenario: Tool configuration
- **WHEN** a developer runs `ruff check .` or `pytest`
- **THEN** the tools use configuration from `pyproject.toml` without additional config files

### Requirement: Application starts successfully
The application SHALL start via `uvicorn app.main:app` and respond to HTTP requests within 2 seconds of launch.

#### Scenario: Clean startup
- **WHEN** the application starts with default configuration (no env vars set)
- **THEN** the server binds to port 8000 and initializes the database without errors

#### Scenario: Health endpoint available
- **WHEN** a client sends `GET /v1/health`
- **THEN** the response status is 200 and the body contains `{"status": "ok"}`

### Requirement: Configuration is environment-driven
The application SHALL read all configuration from environment variables with sensible development defaults. Missing required production config SHALL cause a startup failure with a clear error message.

#### Scenario: Default development config
- **WHEN** the app starts with no environment variables set
- **THEN** it uses `./atelier_marie.db` as the database path and a development JWT secret

#### Scenario: Production config override
- **WHEN** `DATABASE_PATH`, `JWT_SECRET`, and `GOOGLE_CLIENT_ID` are set as environment variables
- **THEN** the application uses those values instead of defaults

#### Scenario: Missing production config in production mode
- **WHEN** `ENVIRONMENT=production` is set but `JWT_SECRET` is not provided
- **THEN** the application refuses to start with a validation error

### Requirement: Database initializes with WAL mode
The database layer SHALL open SQLite connections with WAL mode and foreign keys enabled, and SHALL create all required tables on first startup.

#### Scenario: First-time database creation
- **WHEN** the configured database path does not exist
- **THEN** the application creates the database file, enables WAL mode, enables foreign keys, and creates all schema tables

#### Scenario: Existing database reuse
- **WHEN** the configured database path already exists with valid schema
- **THEN** the application opens it without error and does not drop or recreate tables

#### Scenario: WAL mode active
- **WHEN** any database connection is opened
- **THEN** `PRAGMA journal_mode` returns `wal` and `PRAGMA foreign_keys` returns `1`

### Requirement: Session middleware assigns identity
The application SHALL assign a session cookie to every request that lacks one, providing anonymous identity for cart and checkout flows.

#### Scenario: New visitor gets session
- **WHEN** a request arrives without a session cookie
- **THEN** the response includes a `Set-Cookie` header with a UUID v4 session ID, HTTPOnly flag, SameSite=Lax, and a 30-day expiry

#### Scenario: Existing session preserved
- **WHEN** a request arrives with a valid session cookie
- **THEN** the session ID is available on `request.state.session_id` and no new cookie is set

### Requirement: Test infrastructure supports isolation
The test suite SHALL provide fixtures that give each test its own database instance, preventing cross-test pollution.

#### Scenario: Isolated test database
- **WHEN** a test function uses the `client` fixture
- **THEN** it receives an HTTP test client backed by a fresh, empty database with schema initialized

#### Scenario: Parallel test safety
- **WHEN** two tests run in parallel using the `client` fixture
- **THEN** each operates on a separate database file and neither sees the other's data
