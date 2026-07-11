## ADDED Requirements

### Requirement: JWT issued on successful login
The system SHALL issue a JWT cookie upon successful OAuth callback. The JWT contains `user_id`, `email`, `is_admin`, `session_id`, `iss`, and `aud` claims. It is signed with HS256 using the configured `jwt_secret`.

#### Scenario: JWT cookie set after login
- **WHEN** the OAuth callback successfully authenticates a user
- **THEN** the system sets a cookie named `atelier_auth` containing a JWT with claims `{user_id, email, is_admin, session_id, iss: "atelier-marie", aud: "atelier-marie-web", exp}`, signed HS256, with HttpOnly=true, Secure=true, SameSite=Lax, Path=/, max-age=settings.jwt_expiry_hours * 3600 (default: 604800s / 7 days)

#### Scenario: JWT expiry is configurable
- **WHEN** a JWT is issued
- **THEN** the `exp` claim SHALL be set to current time + `settings.jwt_expiry_hours` hours (default: 168 hours / 7 days)

### Requirement: JWT validation on protected routes
The system SHALL provide a `get_current_user` dependency that extracts and validates the JWT from the `atelier_auth` cookie. Validation checks signature, algorithm, issuer, audience, expiry, session existence, and session user_id match.

#### Scenario: Valid JWT accepted
- **WHEN** a request includes a valid `atelier_auth` cookie with correct signature, non-expired token, valid `iss`/`aud` claims, and matching session row in DB
- **THEN** the dependency returns the authenticated `UserResponse`

#### Scenario: Expired JWT rejected
- **WHEN** a request includes a JWT cookie with `exp` in the past
- **THEN** the dependency returns None (unauthenticated) and does NOT raise an error (allows anonymous access)

#### Scenario: Invalid signature rejected
- **WHEN** a request includes a JWT cookie with invalid signature
- **THEN** the dependency returns None (treats as unauthenticated)

#### Scenario: Wrong algorithm rejected
- **WHEN** a request includes a JWT with an algorithm header other than HS256 (e.g., `none`, `RS256`)
- **THEN** the dependency rejects the token (verification MUST specify `algorithms=["HS256"]` to prevent algorithm confusion attacks)

#### Scenario: Invalid issuer or audience rejected
- **WHEN** a request includes a JWT with `iss` not equal to `"atelier-marie"` or `aud` not equal to `"atelier-marie-web"`
- **THEN** the dependency returns None (prevents cross-application token reuse)

#### Scenario: Session no longer exists
- **WHEN** a request includes a valid JWT but the `session_id` claim does not match any active session row
- **THEN** the dependency returns None (session was rotated or expired)

#### Scenario: Session user_id mismatch after logout
- **WHEN** a request includes a valid JWT but the session row's `user_id` is NULL or does not match the JWT's `user_id` claim (e.g., after logout NULLed user_id)
- **THEN** the dependency returns None (JWT is effectively invalidated by logout)

### Requirement: Admin privilege verified from DB on admin requests
The `require_admin` dependency SHALL verify the user's `is_admin` flag against the database (not just the JWT claim) to ensure revoked admin access takes effect immediately. The `is_admin` claim in the JWT is informational only (for frontend UI hints like showing admin menus) — it is NEVER trusted for authorization decisions.

#### Scenario: Admin revoked mid-session
- **WHEN** a request has a valid JWT with `is_admin=true` but the user's DB row has `is_admin=0`
- **THEN** the `require_admin` dependency SHALL return 403 Forbidden (DB is authoritative, not the JWT claim)

### Requirement: Current user endpoint
The system SHALL provide `GET /v1/auth/me` that returns the authenticated user's profile or 401 if not logged in.

#### Scenario: Authenticated user
- **WHEN** a request to `GET /v1/auth/me` includes a valid JWT cookie
- **THEN** the system returns 200 with `UserResponse` (id, email, name, avatar_url, is_admin)

#### Scenario: Unauthenticated user
- **WHEN** a request to `GET /v1/auth/me` has no valid JWT cookie
- **THEN** the system returns 401 with error `"not_authenticated"`

### Requirement: JWT cleared on logout
The system SHALL provide `POST /v1/auth/logout` that clears the JWT cookie and rotates the session.

#### Scenario: Logout clears cookie
- **WHEN** an authenticated user sends `POST /v1/auth/logout`
- **THEN** the system sets the `atelier_auth` cookie with max-age=0 (effectively deleting it) and returns 200

### Requirement: JWT cookie security attributes
The `atelier_auth` cookie SHALL have `Secure=true` in production environments. In development, `Secure=false` is acceptable for localhost-only access (matching the session cookie pattern in `session.py`).
