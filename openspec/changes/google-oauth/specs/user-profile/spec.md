## ADDED Requirements

### Requirement: Users table stores Google OAuth profiles
The system SHALL maintain a `users` table in SQLite with columns: `id` (INTEGER PRIMARY KEY AUTOINCREMENT), `google_id` (TEXT UNIQUE NOT NULL), `email` (TEXT UNIQUE NOT NULL), `name` (TEXT), `avatar_url` (TEXT), `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP), `last_login_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP). The table SHALL be created during application startup alongside the products table.

#### Scenario: Users table created on startup
- **WHEN** the application starts and the SQLite database exists
- **THEN** the `users` table is created if it does not already exist (CREATE TABLE IF NOT EXISTS)

#### Scenario: Users table schema enforces uniqueness
- **WHEN** an attempt is made to insert a duplicate `google_id` or `email`
- **THEN** the database rejects the insert with a UNIQUE constraint violation

### Requirement: Create or update user on OAuth login (upsert on google_id)
The system SHALL create a new user record if the `google_id` does not exist, or update the existing record's `name`, `avatar_url`, and `last_login_at` fields if it does. This handles both first-time and returning users in a single operation.

#### Scenario: First-time Google user
- **WHEN** OAuth callback extracts google_id "g123", email "user@gmail.com", name "User Name", picture "https://..." AND no user with google_id "g123" exists
- **THEN** a new row is inserted with all fields populated AND the new user's `id` (autoincrement) is returned

#### Scenario: Returning Google user with updated profile
- **WHEN** OAuth callback extracts google_id "g123" with a new name "New Name" and new picture URL AND a user with google_id "g123" already exists
- **THEN** the existing user's `name` and `avatar_url` are updated AND `last_login_at` is set to current timestamp AND the existing `id` and `email` are preserved

#### Scenario: Returning user — email unchanged
- **WHEN** a returning user logs in and their Google email has not changed
- **THEN** the `email` field is not modified (avoids unnecessary writes)

#### Scenario: Google email change detected
- **WHEN** a returning user's Google profile returns a different email than stored
- **THEN** the `email` field is updated to the new value (Google guarantees email verification)

### Requirement: Profile endpoint returns current user info
The system SHALL expose `GET /v1/auth/me` which requires authentication (uses `get_current_user` dependency). It SHALL return the authenticated user's profile information.

#### Scenario: Authenticated user requests profile
- **WHEN** `GET /v1/auth/me` is called with a valid JWT for user with id=1
- **THEN** the response is HTTP 200 with body `{"id": 1, "email": "user@gmail.com", "name": "User Name", "avatar_url": "https://..."}`

#### Scenario: Unauthenticated request to profile
- **WHEN** `GET /v1/auth/me` is called without a valid JWT
- **THEN** the response is HTTP 401 `{"detail": "Not authenticated"}`

### Requirement: User lookup by ID for internal use
The system SHALL provide an internal service function `get_user_by_id(user_id: int) -> Optional[User]` for use by other system components (e.g., order attribution, event enrichment). This is NOT an HTTP endpoint.

#### Scenario: Lookup existing user
- **WHEN** `get_user_by_id(1)` is called and user with id=1 exists
- **THEN** a User object is returned with all fields populated

#### Scenario: Lookup non-existent user
- **WHEN** `get_user_by_id(999)` is called and no user with id=999 exists
- **THEN** `None` is returned