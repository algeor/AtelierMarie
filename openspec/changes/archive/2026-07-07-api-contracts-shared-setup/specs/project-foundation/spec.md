## MODIFIED Requirements

### Requirement: Configuration is environment-driven
The application SHALL read all configuration from environment variables with sensible development defaults. Missing required production config SHALL cause a startup failure with a clear error message.

#### Scenario: Default development config
- **WHEN** the app starts with no environment variables set
- **THEN** it uses `./atelier_marie.db` as the database path, a development JWT secret, `./static` as the static file path, and `["http://localhost:3000"]` as default CORS origins

#### Scenario: Production config override
- **WHEN** `DATABASE_PATH`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `CORS_ORIGINS`, and `STATIC_FILE_PATH` are set as environment variables
- **THEN** the application uses those values instead of defaults

#### Scenario: Missing production config in production mode
- **WHEN** `ENVIRONMENT=production` is set but `JWT_SECRET` is not provided
- **THEN** the application refuses to start with a validation error

#### Scenario: CORS origins configured
- **WHEN** `CORS_ORIGINS` is set to a comma-separated list of URLs
- **THEN** the application allows cross-origin requests only from those origins

### Requirement: Application starts successfully
The application SHALL start via `uvicorn app.main:app` and respond to HTTP requests within 2 seconds of launch.

#### Scenario: Clean startup
- **WHEN** the application starts with default configuration (no env vars set)
- **THEN** the server binds to port 8000 and initializes the database without errors

#### Scenario: Health endpoint available
- **WHEN** a client sends `GET /v1/health`
- **THEN** the response status is 200 and the body contains `{"status": "ok"}`

#### Scenario: Routers registered at startup
- **WHEN** the application starts
- **THEN** routers are registered for /v1/products, /v1/cart, /v1/orders, /v1/auth, and /v1/admin prefixes

#### Scenario: CORS middleware active
- **WHEN** a cross-origin request arrives from a configured origin
- **THEN** appropriate CORS headers are included in the response

## ADDED Requirements

### Requirement: Models package provides importable schemas
The application SHALL have an `app/models/` package that exports all Pydantic request and response schemas. Importing `from app.models.<domain> import <Schema>` SHALL work for any defined model.

#### Scenario: Models importable
- **WHEN** a developer imports `from app.models.products import ProductResponse`
- **THEN** the import succeeds and the class is a valid Pydantic BaseModel subclass

#### Scenario: All domains covered
- **WHEN** `app/models/` is inspected
- **THEN** it contains modules for: products, cart, orders, users, auth, common
