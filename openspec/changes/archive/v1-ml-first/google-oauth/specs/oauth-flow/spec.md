## ADDED Requirements

### Requirement: Login endpoint returns Google OAuth redirect URL
The system SHALL expose `GET /v1/auth/google/login` which generates a Google OAuth 2.0 authorization URL and returns it as JSON. The endpoint SHALL generate a cryptographically random state token for CSRF protection, store it in memory with a 10-minute TTL alongside the requesting session's session_id, and include it in the authorization URL.

#### Scenario: Successful login initiation
- **WHEN** `GET /v1/auth/google/login` is called with header `X-Session-ID: <valid-uuid>`
- **THEN** the response is HTTP 200 with body `{"redirect_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=openid+email+profile&state=<token>&access_type=offline"}` AND the state token is stored in memory with the session_id and a 10-minute expiry

#### Scenario: Login without session_id
- **WHEN** `GET /v1/auth/google/login` is called without an `X-Session-ID` header
- **THEN** the response is HTTP 400 with body `{"detail": "X-Session-ID header required for login"}`

#### Scenario: State token uniqueness
- **WHEN** multiple login requests are made concurrently
- **THEN** each generates a unique state token (minimum 32 bytes of randomness, URL-safe base64 encoded)

### Requirement: Callback endpoint exchanges code and authenticates user
The system SHALL expose `GET /v1/auth/google/callback` which handles the OAuth redirect from Google. It SHALL validate the state token, exchange the authorization code for tokens, verify the Google ID token, create or update the user record, link the session, and return a JWT.

#### Scenario: Successful callback with new user
- **WHEN** `GET /v1/auth/google/callback?code=<auth-code>&state=<valid-state>` is called AND the state token exists and has not expired AND the code exchange with Google succeeds AND the ID token is valid
- **THEN** a new user record is created in SQLite AND `POST /v1/sessions/link` is called with the stashed session_id and new user_id AND the response is HTTP 200 with body `{"token": "<jwt>", "user": {"id": <int>, "email": "...", "name": "...", "avatar_url": "..."}}`

#### Scenario: Successful callback with returning user
- **WHEN** the callback completes successfully AND the google_id already exists in the users table
- **THEN** the existing user record is updated (name, avatar_url, last_login_at) AND the same user_id is used for session linking AND a new JWT is issued

#### Scenario: Invalid state token (CSRF protection)
- **WHEN** `GET /v1/auth/google/callback?code=<code>&state=<invalid-or-expired>` is called AND the state token is not found in the state store
- **THEN** the response is HTTP 400 with body `{"detail": "Invalid or expired state token. Please retry login."}`

#### Scenario: State token consumed (single-use)
- **WHEN** the callback successfully validates a state token
- **THEN** the state token is removed from the store (cannot be reused)

#### Scenario: Google token exchange failure
- **WHEN** the state is valid but the code exchange with Google returns an error (invalid code, expired code)
- **THEN** the response is HTTP 400 with body `{"detail": "Failed to exchange authorization code with Google"}`

#### Scenario: Google ID token verification failure
- **WHEN** the code exchange succeeds but the ID token fails RS256 signature verification or claim validation (wrong iss, wrong aud, expired)
- **THEN** the response is HTTP 401 with body `{"detail": "Google ID token verification failed"}`

#### Scenario: Session link conflict (409 from session-identity)
- **WHEN** the callback attempts to link the session but `POST /v1/sessions/link` returns 409 (session belongs to different user)
- **THEN** the response is HTTP 409 with body `{"detail": "Session already linked to a different user. Please logout first."}`

### Requirement: Google ID token verified via JWKS (RS256)
The system SHALL verify Google's ID token by validating the RS256 signature using Google's public keys (JWKS), and checking claims: `iss` (accounts.google.com or https://accounts.google.com), `aud` (must match client_id), and `exp` (not expired).

#### Scenario: Valid ID token with cached JWKS
- **WHEN** an ID token is verified AND Google's JWKS is cached (fetched within last 6 hours)
- **THEN** the token is verified using the cached keys without a network call to Google

#### Scenario: JWKS cache expired
- **WHEN** an ID token needs verification AND the JWKS cache is older than 6 hours
- **THEN** the system fetches fresh keys from `https://www.googleapis.com/oauth2/v3/certs` AND caches them AND verifies the token

#### Scenario: Verification fails with cached keys — fallback refetch
- **WHEN** RS256 verification fails with cached keys (possible key rotation)
- **THEN** the system refetches JWKS once AND retries verification AND only returns failure if the second attempt also fails

#### Scenario: Google JWKS endpoint unreachable
- **WHEN** the JWKS fetch fails (network error, timeout) AND no cached keys exist
- **THEN** the ID token verification fails with HTTP 503 `{"detail": "Unable to verify Google credentials. Please retry."}`

#### Scenario: Google JWKS endpoint unreachable but stale cache exists
- **WHEN** the JWKS refresh attempt fails (network error, timeout)
- **AND** stale keys exist in cache (older than 6 hours)
- **THEN** the stale keys are used for verification (with a warning logged)
- **AND** retry of the refresh is attempted on the next verification request

### Requirement: State tokens expire and are cleaned up
The system SHALL automatically discard state tokens older than 10 minutes. Expired tokens SHALL NOT be accepted in callback requests. The system SHALL periodically clean expired entries to prevent unbounded memory growth.

#### Scenario: State token used within TTL
- **WHEN** the callback arrives within 10 minutes of login initiation
- **THEN** the state token is valid and the flow proceeds

#### Scenario: State token expired
- **WHEN** the callback arrives more than 10 minutes after login initiation
- **THEN** the state token is not found (or explicitly expired) AND the response is HTTP 400 with body `{"detail": "Invalid or expired state token. Please retry login."}`

#### Scenario: Cleanup prevents memory leak
- **WHEN** the state store is checked periodically (on each access or via background sweep)
- **THEN** entries with `expires_at < now()` are removed from the store

### Requirement: OAuth scopes request openid, email, and profile
The system SHALL request exactly the scopes `openid email profile` from Google. These scopes provide the ID token with email, name, and profile picture claims needed for user record creation.

#### Scenario: Scopes included in authorization URL
- **WHEN** the login endpoint builds the Google authorization URL
- **THEN** the URL includes `scope=openid+email+profile` (or space-separated equivalent)
