## ADDED Requirements

### Requirement: JWT issued on successful authentication
The system SHALL issue a JWT (JSON Web Token) on successful OAuth callback. The JWT payload SHALL contain `user_id` (integer), `session_id` (string, the session that initiated login), and `exp` (expiration timestamp, 7 days from issuance). The token SHALL be signed with HS256 using the `ATELIER_JWT_SECRET` environment variable.

#### Scenario: JWT issued after login
- **WHEN** the OAuth callback completes successfully and a user is authenticated
- **THEN** a JWT is returned in the response body with payload `{"user_id": <int>, "session_id": "<uuid>", "exp": <unix-timestamp-7-days-from-now>}` signed with HS256

#### Scenario: JWT contains correct session_id
- **WHEN** a user initiates login with session S1 and completes OAuth
- **THEN** the issued JWT's `session_id` claim equals S1 (recovered from the state store, not from a request header)

#### Scenario: JWT secret not configured
- **WHEN** the application starts and `ATELIER_JWT_SECRET` is not set or is empty
- **THEN** the application SHALL fail to start with a clear error message indicating the missing configuration

### Requirement: JWT validation checks signature, expiry, and session active status
The system SHALL validate incoming JWTs by: (1) verifying the HS256 signature using `ATELIER_JWT_SECRET`, (2) checking the `exp` claim has not passed, and (3) confirming the `session_id` in the payload is still active in the session cache. All three checks MUST pass for the token to be considered valid.

#### Scenario: Valid JWT with active session
- **WHEN** a request includes `Authorization: Bearer <jwt>` AND the signature is valid AND `exp` has not passed AND the session_id is active in the session cache
- **THEN** the user is considered authenticated and `user_id` is extracted from the payload

#### Scenario: Expired JWT
- **WHEN** a request includes a JWT where `exp` is in the past
- **THEN** the token is rejected with HTTP 401 `{"detail": "Token expired"}`

#### Scenario: Invalid signature (tampered or wrong secret)
- **WHEN** a request includes a JWT that fails HS256 signature verification
- **THEN** the token is rejected with HTTP 401 `{"detail": "Invalid token"}`

#### Scenario: Valid JWT but session rotated (logout)
- **WHEN** a request includes a JWT with a valid signature and non-expired `exp` BUT the `session_id` in the payload corresponds to an expired/rotated session
- **THEN** the token is rejected with HTTP 401 `{"detail": "Session expired"}`

#### Scenario: Malformed Authorization header
- **WHEN** a request includes an `Authorization` header that is not in the format `Bearer <token>`
- **THEN** the token is rejected with HTTP 401 `{"detail": "Invalid token"}`

### Requirement: Required auth dependency returns 401 if no valid token
The system SHALL provide a FastAPI dependency `get_current_user` that extracts and validates the JWT from the `Authorization: Bearer` header. If no token is present or validation fails, it SHALL return HTTP 401.

#### Scenario: Authenticated request to protected endpoint
- **WHEN** a request to an endpoint using `get_current_user` includes a valid JWT
- **THEN** the dependency resolves to the authenticated User object (id, email, name, avatar_url)

#### Scenario: No token on protected endpoint
- **WHEN** a request to an endpoint using `get_current_user` has no `Authorization` header
- **THEN** the response is HTTP 401 with body `{"detail": "Not authenticated"}`

#### Scenario: Invalid token on protected endpoint
- **WHEN** a request to an endpoint using `get_current_user` has an invalid or expired JWT
- **THEN** the response is HTTP 401 with appropriate error detail

### Requirement: Optional auth dependency returns None if no token
The system SHALL provide a FastAPI dependency `get_current_user_optional` that extracts and validates the JWT if present. If no `Authorization` header exists, it SHALL return `None` (allowing anonymous access). If a token IS present but invalid, it SHALL still return `None` (graceful degradation, not 401).

#### Scenario: Authenticated request on optional endpoint
- **WHEN** a request to an endpoint using `get_current_user_optional` includes a valid JWT
- **THEN** the dependency resolves to the authenticated User object

#### Scenario: Anonymous request on optional endpoint
- **WHEN** a request to an endpoint using `get_current_user_optional` has no `Authorization` header
- **THEN** the dependency resolves to `None` and the request proceeds normally

#### Scenario: Invalid token on optional endpoint (graceful degradation)
- **WHEN** a request to an endpoint using `get_current_user_optional` has an invalid or expired JWT
- **THEN** the dependency resolves to `None` (treats as anonymous, does NOT return 401)

### Requirement: Logout invalidates session and returns rotation header
The system SHALL expose `POST /v1/auth/logout` which requires a valid JWT. On successful logout, it SHALL: (1) mark the current session as expired via the session rotation service, (2) return the new anonymous session_id via `X-Session-Rotated` response header, and (3) confirm logout in the response body.

#### Scenario: Successful logout
- **WHEN** `POST /v1/auth/logout` is called with a valid JWT for user U1 with session S1
- **THEN** session S1 is rotated (marked expired, session_end event synthesized) AND the response is HTTP 200 with body `{"logged_out": true}` AND header `X-Session-Rotated: <new-session-uuid>`

#### Scenario: Logout without valid token
- **WHEN** `POST /v1/auth/logout` is called without a valid JWT
- **THEN** the response is HTTP 401 `{"detail": "Not authenticated"}`

#### Scenario: JWT invalidated after logout
- **WHEN** a user logs out and then makes a request with the old JWT
- **THEN** the JWT validation fails because session_id S1 is now expired AND the response is HTTP 401 `{"detail": "Session expired"}`
