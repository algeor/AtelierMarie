## ADDED Requirements

### Requirement: Admin endpoints require API key authentication
The system SHALL require a valid API key in the `Authorization: Bearer <key>` header for all requests to `/v1/admin/*` routes. The valid key SHALL be read from the `ATELIER_ADMIN_API_KEY` environment variable.

#### Scenario: Valid API key grants access
- **WHEN** a request to `/v1/admin/products` includes header `Authorization: Bearer <valid-key>`
- **THEN** system processes the request normally

#### Scenario: Missing Authorization header
- **WHEN** a request to `/v1/admin/products` has no Authorization header
- **THEN** system returns 401 Unauthorized with `{"detail": "Missing API key"}`

#### Scenario: Invalid API key
- **WHEN** a request to `/v1/admin/products` includes header `Authorization: Bearer wrong-key`
- **THEN** system returns 401 Unauthorized with `{"detail": "Invalid API key"}`

#### Scenario: Malformed Authorization header
- **WHEN** a request to `/v1/admin/products` includes header `Authorization: Basic abc123` (wrong scheme)
- **THEN** system returns 401 Unauthorized with `{"detail": "Missing API key"}`

### Requirement: Public endpoints do not require authentication
The system SHALL NOT check for or require any authentication on `/v1/products` routes.

#### Scenario: Public access without credentials
- **WHEN** a request to `/v1/products` has no Authorization header
- **THEN** system returns 200 OK with product data

#### Scenario: Public access with credentials (ignored)
- **WHEN** a request to `/v1/products` includes an Authorization header
- **THEN** system ignores the header and returns 200 OK with product data

### Requirement: API key not configured returns server error
The system SHALL fail gracefully if `ATELIER_ADMIN_API_KEY` is not set in the environment at startup.

#### Scenario: Missing env var at startup
- **WHEN** the application starts without `ATELIER_ADMIN_API_KEY` environment variable
- **THEN** system SHALL refuse to start (or log a fatal error) indicating the admin key must be configured
