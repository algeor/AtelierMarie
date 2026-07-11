## ADDED Requirements

### Requirement: Google OAuth sign-in
The system SHALL support Google Sign-In via POST /auth/google accepting a Google ID token. On valid token, the system SHALL create or retrieve the user record (google_id, email, name, avatar_url) and return a session token.

#### Scenario: New user signs in with Google
- **WHEN** a client sends POST /auth/google with a valid Google ID token for a new user
- **THEN** a user record is created and a session token is returned with HTTP 200

#### Scenario: Existing user signs in with Google
- **WHEN** a client sends POST /auth/google with a valid Google ID token for an existing user
- **THEN** the existing user record is retrieved and a session token is returned

#### Scenario: Invalid Google token rejected
- **WHEN** a client sends POST /auth/google with an invalid or expired token
- **THEN** the API returns HTTP 401 with message "Invalid authentication token"

### Requirement: Session identity linking on login
The system SHALL link the current anonymous session_id to the authenticated user_id in the session_identity table when Google login occurs. All prior events with that session_id SHALL be retroactively associated with the user_id.

#### Scenario: Anonymous session linked to user on login
- **WHEN** a user with session_id "abc-123" authenticates via Google and receives user_id 42
- **THEN** the session_identity record for "abc-123" is updated with user_id 42

#### Scenario: Prior events retroactively linked
- **WHEN** session "abc-123" has 5 events with null user_id, and the user logs in as user_id 42
- **THEN** those 5 events are updated in DuckDB to include user_id 42

### Requirement: Anonymous session generation
The system SHALL generate a UUID v4 session_id for every new visitor and persist it in both localStorage and an HTTP-only cookie. The session_id SHALL be sent with every API request.

#### Scenario: New visitor receives session ID
- **WHEN** a new visitor loads the site with no existing session
- **THEN** a UUID v4 session_id is generated, stored in localStorage and cookie, and included in subsequent API calls

#### Scenario: Existing session persists across page loads
- **WHEN** a returning visitor loads the site with existing session_id in localStorage
- **THEN** the existing session_id is reused for all API calls

### Requirement: Logout clears session association
The system SHALL expose POST /auth/logout that clears the user's authentication token while preserving the session_id for continued anonymous tracking.

#### Scenario: Logout clears auth but keeps session
- **WHEN** an authenticated user calls POST /auth/logout
- **THEN** the auth token is invalidated but the session_id continues to function for anonymous tracking

### Requirement: Get current user
The system SHALL expose GET /auth/me that returns the current user's profile (id, email, name, avatar_url) if authenticated, or HTTP 401 if not.

#### Scenario: Authenticated user gets profile
- **WHEN** an authenticated user calls GET /auth/me
- **THEN** the API returns their profile with id, email, name, avatar_url

#### Scenario: Unauthenticated request returns 401
- **WHEN** an unauthenticated client calls GET /auth/me
- **THEN** the API returns HTTP 401

### Requirement: Anonymous browsing and purchasing
The system SHALL allow complete e-commerce functionality (browse, add to cart, checkout) without requiring authentication. Orders placed anonymously SHALL use session_id as the identifier.

#### Scenario: Anonymous user completes checkout
- **WHEN** a user with no authentication adds items to cart and checks out
- **THEN** the order is created with user_id NULL and the session_id recorded
