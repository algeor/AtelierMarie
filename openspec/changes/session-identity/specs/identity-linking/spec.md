## ADDED Requirements

### Requirement: Link session to user
The system SHALL expose `POST /v1/sessions/link` which binds a session_id to a user_id. The session's `user_id` field in the cache (and eventually DuckDB) SHALL be set to the provided user_id. This is called after successful OAuth authentication.

#### Scenario: Link anonymous session to user
- **WHEN** `POST /v1/sessions/link` is called with `{"session_id": "<uuid>", "user_id": "user123"}` and the session currently has `user_id = null`
- **THEN** the response is HTTP 200 with body `{"linked": true, "previous_user_id": null}` AND the session's user_id is set to "user123"

#### Scenario: Idempotent re-link same user
- **WHEN** `POST /v1/sessions/link` is called with `{"session_id": "<uuid>", "user_id": "user123"}` and the session is already linked to "user123"
- **THEN** the response is HTTP 200 with body `{"linked": true, "previous_user_id": "user123"}` (no-op, idempotent)

#### Scenario: Conflict — link to different user
- **WHEN** `POST /v1/sessions/link` is called with `{"session_id": "<uuid>", "user_id": "userB"}` and the session is already linked to "userA"
- **THEN** the response is HTTP 409 with body `{"detail": "Session already linked to a different user. Logout first to rotate session."}`

#### Scenario: Link unknown session
- **WHEN** `POST /v1/sessions/link` is called with a session_id not in the cache or DuckDB
- **THEN** the response is HTTP 404 with body `{"detail": "Session not found. Send at least one event first."}`

### Requirement: Read-time identity resolution via JOIN
The system SHALL provide internal query helpers that resolve user identity at read time by JOINing the `events` table with `session_identity` on `session_id`. Historical events SHALL NOT be modified when a session is linked to a user.

#### Scenario: Get all events for a user (cross-session)
- **WHEN** `get_user_events(user_id)` is called for a user with sessions S1 and S2
- **THEN** all events from both S1 and S2 are returned, ordered by `server_timestamp`

#### Scenario: Get all sessions for a user
- **WHEN** `get_user_sessions(user_id)` is called
- **THEN** all `session_identity` rows where `user_id` matches are returned

#### Scenario: Get events for a single session
- **WHEN** `get_session_events(session_id)` is called
- **THEN** all events with that `session_id` are returned from DuckDB, ordered by `server_timestamp`

### Requirement: Logout forces session rotation
The system SHALL handle logout by: (1) marking the current session as expired, (2) synthesizing a `session_end` event for the session, (3) generating a new session_id (UUID v4), and (4) returning the new session_id via `X-Session-Rotated` response header. The old session's `user_id` SHALL be preserved for historical attribution.

#### Scenario: User logs out
- **WHEN** a logout action is triggered for a session linked to "user123"
- **THEN** the current session is marked `is_expired = True` AND a `session_end` event is synthesized AND the response includes `X-Session-Rotated: <new-uuid>` header AND the old session retains `user_id = "user123"`

#### Scenario: Old session after logout
- **WHEN** events are queried for "user123" after logout
- **THEN** events from the old (now-expired) session are still attributed to "user123" via the read-time JOIN

### Requirement: Shared device isolation
The system SHALL prevent identity leakage on shared devices by ensuring that after logout+rotation, the new session starts as anonymous. A session linked to user A SHALL never be re-linked to user B without a 409 rejection.

#### Scenario: Shared device — user A logs out, user B logs in
- **WHEN** user A logs out (session S1 rotated to S2) and user B later logs in on the same device
- **THEN** S1 remains attributed to user A AND S2 is linked to user B AND there is no identity leakage between the two users

#### Scenario: Attempted re-link without logout
- **WHEN** user B tries to link session S1 (still linked to user A) without user A logging out first
- **THEN** the system returns HTTP 409 Conflict

### Requirement: Multi-device identity resolution
The system SHALL support the same user having multiple concurrent sessions (one per device). All sessions linked to a user_id SHALL be included in cross-session queries.

#### Scenario: Same user on phone and laptop
- **WHEN** "user123" has session S1 (phone) and session S2 (laptop), both linked
- **THEN** `get_user_events("user123")` returns events from both S1 and S2 AND `get_user_sessions("user123")` returns both sessions
