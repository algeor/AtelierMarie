## ADDED Requirements

### Requirement: Login redirect to Google OAuth
The system SHALL provide a `GET /v1/auth/login` endpoint that redirects the user to Google's OAuth 2.0 authorization URL with appropriate scopes (`openid email profile`), a signed state token (containing session_id, nonce, and timestamp), and the configured redirect URI.

#### Scenario: User initiates login
- **WHEN** an unauthenticated user visits `GET /v1/auth/login`
- **THEN** the system redirects (302) to `https://accounts.google.com/o/oauth2/v2/auth` with `client_id`, `redirect_uri`, `response_type=code`, `scope=openid email profile`, and a signed `state` parameter

#### Scenario: State token is signed and time-limited
- **WHEN** the system generates the OAuth state parameter
- **THEN** the state SHALL be a JWT signed with the app's `jwt_secret` (HS256), containing `type: "oauth_state"`, `session_id`, a random `nonce`, `code_verifier` (for PKCE), optional `return_to` path, and an `iat` timestamp, with a 10-minute expiry. Verification MUST specify `algorithms=["HS256"]` to prevent algorithm confusion. The `type` claim prevents token confusion with auth JWTs.

#### Scenario: PKCE protects authorization code exchange (RFC 7636)
- **WHEN** the system initiates the OAuth flow
- **THEN** it SHALL:
  1. Generate a `code_verifier` (43-128 characters, cryptographically random, URL-safe: `[A-Za-z0-9._~-]`)
  2. Compute `code_challenge = base64url(SHA256(code_verifier))` (no padding)
  3. Include `code_challenge` and `code_challenge_method=S256` in the authorization URL
  4. Store the `code_verifier` in the signed state token (tamper-proof)
  5. Include the `code_verifier` in the token exchange POST to Google's token endpoint

### Requirement: OAuth callback processes authorization code
The system SHALL provide a `GET /v1/auth/callback` endpoint that validates the state token, exchanges the authorization code for tokens via Google's token endpoint, and verifies the ID token using Google's JWKS.

#### Scenario: Successful OAuth callback
- **WHEN** Google redirects to `/v1/auth/callback` with valid `code` and `state` parameters
- **THEN** the system exchanges the code for tokens at `https://oauth2.googleapis.com/token`, verifies the ID token signature (RS256 via JWKS), and extracts user claims (sub, email, name, picture)

#### Scenario: Token exchange and JWKS fetch have timeouts
- **WHEN** the system makes HTTP calls to Google (token exchange at `oauth2.googleapis.com/token` or JWKS fetch at `googleapis.com/oauth2/v3/certs`)
- **THEN** all httpx requests SHALL use a 10-second timeout (`httpx.Timeout(10.0)`). On timeout, token exchange returns 400 `"token_exchange_failed"`; JWKS fetch falls back to stale cache or raises 503 per the JWKS cache failure scenarios.

#### Scenario: Invalid state token rejected
- **WHEN** the callback receives a `state` parameter that fails validation
- **THEN** the system SHALL validate in this order: (1) signature verification with `algorithms=["HS256"]`, (2) expiry check (>10 min), (3) `type` claim equals `"oauth_state"`, (4) `session_id` matches `request.state.session_id`. Failure at any step returns 400 with error `"invalid_state"`.

#### Scenario: State session_id binding verified against current request
- **WHEN** the callback's state token contains a `session_id` that does not match `request.state.session_id` from the current session cookie
- **THEN** the system SHALL return 400 with error `"invalid_state"` (prevents cross-session CSRF)

#### Scenario: Invalid authorization code
- **WHEN** the code exchange with Google fails (invalid or expired code)
- **THEN** the system SHALL return 400 with error `"token_exchange_failed"`

### Requirement: Google JWKS cached with TTL
The system SHALL cache Google's public keys (JWKS) in memory with a 6-hour TTL. Keys are re-fetched when the cache expires or when no matching `kid` is found.

#### Scenario: Cache hit
- **WHEN** verifying an ID token and the matching `kid` exists in cache with age < 6 hours
- **THEN** the system uses the cached key without network call

#### Scenario: Cache miss triggers refresh
- **WHEN** verifying an ID token and no matching `kid` exists in cache or cache is expired
- **THEN** the system fetches fresh keys from `https://www.googleapis.com/oauth2/v3/certs` and updates the cache

#### Scenario: JWKS fetch failure with existing cache
- **WHEN** the JWKS refresh fails (network error, Google outage) but previously cached keys exist
- **THEN** the system continues using the stale cached keys (Google rotates infrequently; stale keys are likely still valid)

#### Scenario: JWKS fetch failure with empty cache
- **WHEN** the JWKS refresh fails and no cached keys exist at all
- **THEN** login attempts fail with 503 `"authentication_service_unavailable"` (fail closed — do not skip verification)

### Requirement: Email verification required
The system SHALL reject Google ID tokens where the `email_verified` claim is `false`. Only fully verified Google accounts can authenticate.

#### Scenario: Unverified email rejected
- **WHEN** the Google ID token has `email_verified=false`
- **THEN** the system SHALL return 400 with error `"email_not_verified"`

### Requirement: Redirect URI from config only
The system SHALL use `settings.google_redirect_uri` as the exact redirect_uri in the OAuth flow. It MUST NOT be dynamically constructed from Host headers or query parameters. The post-login redirect destination MUST be a hardcoded frontend URL (e.g., `/` or from config), never from a user-supplied parameter.

#### Scenario: Redirect URI is static
- **WHEN** the system constructs the OAuth authorization URL or exchanges a code
- **THEN** the `redirect_uri` parameter is exactly `settings.google_redirect_uri` (no dynamic construction)

#### Scenario: Post-login redirect is safe
- **WHEN** the OAuth callback completes successfully
- **THEN** the system redirects to a configurable frontend base URL from `settings.frontend_url` (e.g., `http://localhost:3000` in dev, `https://atelier-marie.com` in prod). If a `return_to` path was encoded in the state token, it is appended — but ONLY if it starts with `/` and does NOT start with `//` (prevents protocol-relative open redirect via `//evil.com`). If no `return_to` or it fails validation, redirects to `/`.

### Requirement: User upsert on OAuth callback
The system SHALL create or update a user row on each successful OAuth login. The user is identified by `google_id`. On first login, a new row is inserted. On subsequent logins, `name`, `avatar_url`, and `last_login_at` are updated.

#### Scenario: New user created
- **WHEN** the OAuth callback succeeds and no user with the given `google_id` exists
- **THEN** the system inserts a new user row with `id` (UUID), `google_id`, `email`, `name`, `avatar_url`, `is_admin=0`, `last_login_at=now`

#### Scenario: Existing user updated
- **WHEN** the OAuth callback succeeds and a user with the given `google_id` already exists
- **THEN** the system updates `name`, `avatar_url`, and `last_login_at` for the existing user

### Requirement: First-user-is-admin bootstrap
The system SHALL automatically promote the first user to register via OAuth to admin status. The count check and insert MUST occur within a single transaction to prevent race conditions. This eliminates the need for manual database edits to set up the store.

#### Scenario: First user becomes admin
- **WHEN** the OAuth callback creates a new user AND the `users` table was previously empty (zero rows)
- **THEN** the newly created user SHALL have `is_admin=1`

#### Scenario: Subsequent users are not admin
- **WHEN** the OAuth callback creates a new user AND other users already exist
- **THEN** the newly created user SHALL have `is_admin=0`

#### Scenario: Concurrent first-login race prevented
- **WHEN** two users complete OAuth simultaneously and both see zero users in the table
- **THEN** only one SHALL be promoted to admin (the count check and insert are atomic within a single SQLite transaction). This relies on SQLite's single-writer serialization (BEGIN IMMEDIATE acquires a RESERVED lock). If migrating to a multi-writer DB, use `INSERT ... WHERE NOT EXISTS (SELECT 1 FROM users)` with a unique constraint.
