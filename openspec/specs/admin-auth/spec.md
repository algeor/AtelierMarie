## ADDED Requirements

### Requirement: Dual admin authentication with explicit precedence
The system SHALL provide a `require_admin` dependency that grants admin access if EITHER (a) the request has a valid JWT cookie with `is_admin=true` (verified against DB), OR (b) the request has an `Authorization: Bearer <key>` header matching the configured `admin_api_key`. Credential evaluation follows a defined precedence order.

#### Scenario: Precedence order
- **WHEN** the `require_admin` dependency evaluates credentials
- **THEN** it checks in order: (1) JWT cookie — if valid and DB-confirmed admin, grant (identity = authenticated user). (2) If JWT valid but not admin, return 403 (JWT establishes identity — API key cannot escalate privileges). (3) If no valid JWT, check API key — if valid, grant (identity = synthetic "api-key-admin"). (4) If no valid JWT and no valid key, return 401.

#### Scenario: Admin via JWT cookie
- **WHEN** a request to an admin endpoint includes a valid JWT with `is_admin=true` (confirmed by DB check)
- **THEN** the `require_admin` dependency succeeds and returns the admin user identity

#### Scenario: Admin via API key
- **WHEN** a request to an admin endpoint includes `Authorization: Bearer <key>` matching `settings.admin_api_key`
- **THEN** the `require_admin` dependency succeeds and returns a synthetic admin identity

#### Scenario: Non-admin JWT rejected
- **WHEN** a request to an admin endpoint includes a valid JWT with `is_admin=false` and no valid API key header
- **THEN** the system returns 403 Forbidden

#### Scenario: Invalid API key rejected
- **WHEN** a request to an admin endpoint has an `Authorization: Bearer <key>` that does NOT match `settings.admin_api_key` and no valid admin JWT
- **THEN** the system returns 403 Forbidden

#### Scenario: No credentials at all
- **WHEN** a request to an admin endpoint has no JWT cookie and no Authorization header
- **THEN** the system returns 401 Unauthorized

### Requirement: API key comparison is constant-time
The system SHALL compare the provided API key with the configured key using `hmac.compare_digest()` to prevent timing attacks.

#### Scenario: Timing-safe comparison
- **WHEN** the system checks an API key against `settings.admin_api_key`
- **THEN** the comparison uses `hmac.compare_digest()` (not `==`)

### Requirement: Empty API key disables key auth
The system SHALL NOT accept API key authentication when `admin_api_key` is empty string (the default). Only JWT auth works when no API key is configured. The empty-key check MUST be evaluated BEFORE calling `hmac.compare_digest()` to prevent an empty Authorization header from matching an empty configured key.

#### Scenario: Empty API key config
- **WHEN** `settings.admin_api_key` is `""` (empty) and a request sends `Authorization: Bearer <anything>`
- **THEN** the API key check SHALL always fail (short-circuit before `compare_digest` — never compare against empty string)
