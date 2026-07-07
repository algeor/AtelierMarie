## ADDED Requirements

### Requirement: Session cookie assigned on first visit
The system SHALL assign a session cookie (`session_id`) to every visitor on their first request. The cookie SHALL be UUID v4, HttpOnly, Secure (controlled by `session_cookie_secure` config setting, defaulting to `True`), SameSite=Lax, with a 30-day max-age. A corresponding row SHALL be inserted into the `sessions` table with `expires_at` set to 30 days from now.

#### Scenario: First-time visitor receives session cookie
- **WHEN** a request arrives with no `session_id` cookie
- **THEN** the system generates a UUID v4, inserts a session row with `expires_at = now + 30 days`, sets the cookie on the response (HttpOnly, Secure in production, SameSite=Lax), and sets `request.state.session_id` to the new ID

### Requirement: Session cookie format validated before DB lookup
The middleware SHALL validate that the incoming cookie value matches UUID v4 format (`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`) before performing a database lookup. Non-conforming values (arbitrary strings, oversized payloads, null bytes) SHALL be treated as absent — a new session is created and the invalid cookie is replaced.

#### Scenario: Malformed cookie value rejected without DB query
- **WHEN** a request arrives with a `session_id` cookie value of `"not-a-uuid"` or `"'; DROP TABLE sessions;--"`
- **THEN** the system does NOT query the database, generates a new session (new UUID, new DB row), replaces the cookie, and sets `request.state.session_id` to the new ID

#### Scenario: Oversized cookie value rejected without DB query
- **WHEN** a request arrives with a `session_id` cookie value longer than 36 characters
- **THEN** the system does NOT query the database and treats it as a first-time visit

### Requirement: Returning session validated against database
The system SHALL validate the session cookie on every request by checking — in this strict order — that: (1) the session ID exists in the `sessions` table, (2) `created_at + 180 days >= now` (absolute lifetime), and (3) `expires_at >= now`. If any check fails, the session SHALL be treated as a first-time visit (new session created, old cookie replaced). No writes (including sliding expiry updates) SHALL occur for sessions that fail validation.

#### Scenario: Valid returning session
- **WHEN** a request arrives with a `session_id` cookie that exists in the DB and has `expires_at >= now`
- **THEN** the system sets `request.state.session_id` to that session ID and proceeds with the request

#### Scenario: Expired session replaced
- **WHEN** a request arrives with a `session_id` cookie whose DB row has `expires_at < now`
- **THEN** the system generates a new session (new UUID, new DB row), replaces the cookie, and sets `request.state.session_id` to the new ID. The expired session row is NOT deleted by the middleware (deferred to a separate cleanup job).

#### Scenario: Unknown session cookie replaced
- **WHEN** a request arrives with a `session_id` cookie that does not exist in the `sessions` table
- **THEN** the system generates a new session (new UUID, new DB row), replaces the cookie, and sets `request.state.session_id` to the new ID

### Requirement: Sliding expiry extends session on activity (with threshold optimization)
The system SHALL update `sessions.expires_at` to `now + 30 days` only when the current `expires_at` is within 7 days of expiring. This ensures active users never expire while minimizing unnecessary writes. The `Set-Cookie` header SHALL be set on every response for valid sessions (with the current session_id and remaining max-age), regardless of whether the DB was updated. This prevents a timing side-channel where cookie header presence could leak session activity patterns.

#### Scenario: Session near expiry gets extended
- **WHEN** a valid session is used and its `expires_at` is within 7 days from now
- **THEN** the system updates `expires_at` to `now + 30 days` in the sessions table

#### Scenario: Session far from expiry skips update
- **WHEN** a valid session is used and its `expires_at` is more than 7 days from now
- **THEN** the system does NOT update `expires_at` (no write to DB)

#### Scenario: Session expires after 30 days of inactivity
- **WHEN** a session has not been used for more than 30 days
- **THEN** the next request with that session cookie SHALL be treated as a first-time visit (new session created)

### Requirement: Absolute session lifetime cap
The system SHALL enforce a maximum absolute session lifetime of 180 days from `created_at`, regardless of sliding expiry. Sessions older than 180 days SHALL be treated as expired even if `expires_at` is still in the future.

#### Scenario: Session exceeds absolute lifetime
- **WHEN** a request arrives with a session whose `created_at` is more than 180 days ago
- **THEN** the system treats it as expired — generates a new session, replaces the cookie

#### Scenario: Active session within absolute lifetime continues normally
- **WHEN** a request arrives with a session whose `created_at` is 90 days ago and `expires_at` is in the future
- **THEN** the session is valid and proceeds normally

### Requirement: Session rotation on login (fixation prevention)
Upon successful authentication (Google OAuth callback), the system SHALL rotate the session ID within a single `BEGIN IMMEDIATE` transaction: (1) INSERT new session row with new UUID and user_id, (2) UPDATE `cart_items` rows to the new session_id, (3) DELETE the old session row. The new cookie SHALL be set on the response. This prevents session fixation attacks.

#### Scenario: Session rotated on authentication
- **WHEN** a user successfully completes Google OAuth login with session ID "old-uuid"
- **THEN** within a single transaction: creates new session "new-uuid" with user_id, migrates cart_items from "old-uuid" to "new-uuid", deletes "old-uuid", and sets the new cookie

#### Scenario: Cart preserved across session rotation
- **WHEN** a user has 3 items in their cart (with quantities 2, 5, 1) and logs in
- **THEN** all 3 items remain in the cart under the new session ID with identical quantities and product_ids

### Requirement: Session middleware skips non-application paths
The session middleware SHALL skip processing for paths that are not application routes (e.g., `/health`, `/metrics`, `/docs`, `/openapi.json`). These paths SHALL NOT trigger session creation, validation, or expiry updates. Matching uses exact-match for leaf paths (`/health`, `/docs`, `/openapi.json`) and prefix-with-trailing-slash for directory paths (`/docs/`, `/metrics/`). A request to `/health-records` does NOT match `/health`. Note: `/docs` appears in BOTH the exact-match list (for the Swagger UI root) and as a prefix (`/docs/`) for sub-paths like `/docs/oauth2-redirect`.

#### Scenario: Health check does not create a session
- **WHEN** a request arrives at `GET /health` with no session cookie
- **THEN** the system does NOT create a session row, does NOT set a cookie, and the request proceeds without `request.state.session_id`

#### Scenario: Monitoring probe does not extend session expiry
- **WHEN** a request arrives at `GET /health` with a valid session cookie
- **THEN** the system does NOT update `expires_at` for that session

### Requirement: Session ID always available to downstream handlers
The system SHALL guarantee that `request.state.session_id` is set to a valid, non-expired session ID for every application request that passes through the middleware. Downstream code (routes, services) SHALL be able to rely on this without additional validation.

#### Scenario: Route handler accesses session ID
- **WHEN** any route handler reads `request.state.session_id`
- **THEN** the value is a valid UUID that exists in the sessions table with `expires_at >= now`
