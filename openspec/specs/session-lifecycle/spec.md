## MODIFIED Requirements

### Requirement: Session cookie assigned on first visit
The system SHALL assign a session cookie (`session_id`) to every visitor on their first request. The cookie SHALL be UUID v4, HttpOnly, Secure (controlled by `session_cookie_secure` config setting, defaulting to `True`), SameSite=Lax, with a 30-day max-age. A corresponding row SHALL be inserted into the `sessions` table with `expires_at` set to 30 days from now. Session time constants SHALL be defined as named constants in `app/constants.py` (not inline arithmetic).

#### Scenario: First-time visitor receives session cookie
- **WHEN** a request arrives with no `session_id` cookie
- **THEN** the system generates a UUID v4, inserts a session row with `expires_at = now + SESSION_MAX_AGE_SECONDS`, sets the cookie on the response (HttpOnly, Secure in production, SameSite=Lax), and sets `request.state.session_id` to the new ID

#### Scenario: Session constants are defined centrally
- **WHEN** any module needs session lifetime values
- **THEN** it imports `SESSION_MAX_AGE_DAYS`, `SESSION_ABSOLUTE_LIFETIME_DAYS`, `SESSION_SLIDING_THRESHOLD_DAYS` from `app.constants` — never uses inline `30 * 24 * 60 * 60`

## ADDED Requirements

### Requirement: Background cleanup task is properly lifecycle-managed
The session cleanup background task SHALL be cancelled with proper awaiting on application shutdown. The shutdown sequence SHALL: (1) cancel the task, (2) await it with a 5-second timeout, (3) catch and log `CancelledError` at INFO level, (4) if the timeout expires, log at WARNING and proceed with shutdown. The task SHALL NOT leave pending asyncio warnings.

#### Scenario: Graceful shutdown completes cleanup task
- **WHEN** the application shuts down while the cleanup task is sleeping between cycles
- **THEN** the task is cancelled, the `CancelledError` is caught within 5 seconds, and shutdown proceeds without asyncio warnings

#### Scenario: Cleanup task mid-deletion is given time to finish
- **WHEN** the application shuts down while the cleanup task is actively deleting expired sessions
- **THEN** the current database operation completes (or rolls back) before the task exits
