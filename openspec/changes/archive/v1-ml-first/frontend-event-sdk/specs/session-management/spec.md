## ADDED Requirements

### Requirement: Session ID generation
The SDK SHALL generate a session_id using `crypto.randomUUID()` on first initialization when no existing session is found in localStorage.

#### Scenario: First visit (no existing session)
- **WHEN** the tracker initializes and localStorage does not contain `atelier_session_id`
- **THEN** the SDK generates a new UUID v4 via `crypto.randomUUID()`, stores it in localStorage under `atelier_session_id`, and stores the current timestamp under `atelier_session_start`

#### Scenario: Returning visit (existing session)
- **WHEN** the tracker initializes and localStorage contains a valid `atelier_session_id`
- **THEN** the SDK uses the existing session_id without generating a new one

#### Scenario: localStorage unavailable
- **WHEN** the tracker initializes and localStorage is not accessible (private browsing, storage full, disabled)
- **THEN** the SDK generates a new UUID in memory for the page session and operates without persistence (session lost on page reload)

### Requirement: Session rotation on server expiry signal
The SDK SHALL rotate the session when the server responds with `X-Session-Expired: true`.

#### Scenario: Server signals session expired
- **WHEN** a fetch response includes header `X-Session-Expired: true`
- **THEN** the SDK generates a new session_id, stores it in localStorage, stores a new session start timestamp, and enqueues a `session_start` event with the new session_id

#### Scenario: Session end event for expired session
- **WHEN** the SDK rotates a session due to X-Session-Expired
- **THEN** the SDK attempts to send a `session_end` event with the OLD session_id via sendBeacon (best-effort, fire-and-forget)

### Requirement: Session adoption on server rotation
The SDK SHALL adopt a server-provided session_id when the server responds with `X-Session-Rotated: <uuid>`.

#### Scenario: Server forces rotation (logout flow)
- **WHEN** a fetch response includes header `X-Session-Rotated: <new-uuid>`
- **THEN** the SDK replaces the current session_id with the server-provided UUID, updates localStorage, and enqueues a `session_start` event with the new session_id

### Requirement: Client-side idle expiry detection
The SDK SHALL detect when a session has been idle for more than 30 minutes and rotate the session proactively.

#### Scenario: User returns after 30+ minutes of inactivity
- **WHEN** `tracker.track()` is called and `Date.now() - lastActivityTimestamp > 30 * 60 * 1000`
- **THEN** the SDK rotates the session (new UUID, session_start event) before queuing the new event

#### Scenario: User returns within 30 minutes
- **WHEN** `tracker.track()` is called and the idle time is less than 30 minutes
- **THEN** the SDK updates lastActivityTimestamp and queues the event on the current session

### Requirement: Client-side age cap expiry
The SDK SHALL detect when a session exceeds 24 hours of age and rotate the session.

#### Scenario: Session older than 24 hours
- **WHEN** `tracker.track()` is called and `Date.now() - sessionStartTimestamp > 24 * 60 * 60 * 1000`
- **THEN** the SDK rotates the session (new UUID, session_start event) before queuing the new event

### Requirement: Session ID sent on all requests
The SDK SHALL include the current session_id as the `X-Session-ID` header on every request to the backend.

#### Scenario: Event batch sent with session header
- **WHEN** the SDK flushes events via fetch or sendBeacon
- **THEN** the request includes the header `X-Session-ID: <current-session-id>`
