## ADDED Requirements

### Requirement: Idle timeout expiry (30 minutes)
The system SHALL mark a session as expired when the session's `last_seen` timestamp is more than 30 minutes in the past. Expiry detection SHALL be performed by the background batch job, not inline on requests.

#### Scenario: Session idle for 31 minutes
- **WHEN** the expiry batch job runs and finds a session with `last_seen` = 31 minutes ago and `is_expired = False`
- **THEN** the session is marked `is_expired = True` in both the cache and DuckDB

#### Scenario: Session idle for 29 minutes
- **WHEN** the expiry batch job runs and finds a session with `last_seen` = 29 minutes ago and `is_expired = False`
- **THEN** the session remains `is_expired = False`

### Requirement: Hard cap expiry (24 hours)
The system SHALL mark a session as expired when the session's `first_seen` timestamp is more than 24 hours in the past, regardless of activity. This prevents indefinite sessions.

#### Scenario: Session active for 25 hours
- **WHEN** the expiry batch job runs and finds a session with `first_seen` = 25 hours ago and `is_expired = False` (even if `last_seen` is recent)
- **THEN** the session is marked `is_expired = True`

#### Scenario: Session active for 23 hours with recent activity
- **WHEN** the expiry batch job runs and finds a session with `first_seen` = 23 hours ago and `last_seen` = 1 minute ago
- **THEN** the session remains `is_expired = False`

### Requirement: Session_end event synthesis on expiry
The system SHALL synthesize a `session_end` event for each session it marks as expired. The event SHALL be appended to the JSONL buffer using the same `O_APPEND` writer as the event API. The synthesized event SHALL include the session_id, event_type "session_end", and a server_timestamp of the expiry detection time.

#### Scenario: Session expires — event synthesized
- **WHEN** the expiry job marks session "abc-123" as expired
- **THEN** a `session_end` event with `session_id = "abc-123"` and `event_type = "session_end"` is appended to the current day's JSONL buffer file

#### Scenario: Already-expired session not re-processed
- **WHEN** the expiry job runs and finds a session with `is_expired = True`
- **THEN** no additional `session_end` event is synthesized (idempotent)

### Requirement: Expiry batch job runs every 5 minutes
The system SHALL run the session expiry batch job as an asyncio background task, executing every 5 minutes. The job SHALL acquire the shared `.batch.lock` file lock before writing to DuckDB.

#### Scenario: Batch job acquires lock and runs
- **WHEN** the expiry job timer fires and `.batch.lock` is available
- **THEN** the job acquires the lock, flushes dirty cache entries to DuckDB, marks expired sessions, synthesizes events, and releases the lock

#### Scenario: Batch job cannot acquire lock
- **WHEN** the expiry job timer fires but `.batch.lock` is held by the event batch loader
- **THEN** the job skips this cycle and retries at the next 5-minute interval

### Requirement: Expired sessions accept events gracefully
The system SHALL continue to accept events for expired sessions. The middleware SHALL NOT reject requests based on session expiry status. Expiry is communicated to the client via the `X-Session-Expired: true` response header, leaving rotation as a client responsibility.

#### Scenario: Event arrives on expired session
- **WHEN** `POST /v1/events` is called with a session_id that is expired
- **THEN** the event is accepted (HTTP 202) AND the response includes `X-Session-Expired: true` AND `last_seen` is still updated in the cache

### Requirement: Expired sessions evicted from cache after flush
The system SHALL remove expired sessions from the in-memory cache after they have been successfully flushed to DuckDB. This prevents unbounded memory growth.

#### Scenario: Expired session evicted after flush
- **WHEN** the batch job flushes session "abc-123" (marked expired) to DuckDB
- **THEN** session "abc-123" is removed from the in-memory cache

#### Scenario: Query for evicted session falls through to DuckDB
- **WHEN** `GET /v1/sessions/{session_id}/status` is called for a session that was evicted from cache
- **THEN** the system queries DuckDB for the session and returns its persisted state
