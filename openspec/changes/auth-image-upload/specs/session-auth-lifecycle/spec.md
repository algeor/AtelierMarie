## ADDED Requirements

### Requirement: Session rotation on logout
The system SHALL create a new session (fresh UUID) on logout, clear the old session's `user_id`, and replace the session cookie. This prevents session fixation attacks.

#### Scenario: Logout rotates session
- **WHEN** an authenticated user sends `POST /v1/auth/logout`
- **THEN** the system:
  1. Sets `user_id=NULL` on the current session row
  2. Creates a new session row with a fresh UUID
  3. Sets the session cookie to the new session ID
  4. Includes `X-Session-Rotated: true` response header (opaque indicator; does NOT expose the new session ID value)
  5. Returns 200

#### Scenario: Cart is NOT transferred on logout
- **WHEN** a user logs out and a new session is created
- **THEN** `cart_items` remain associated with the OLD session_id (the new session starts with an empty cart)

#### Scenario: Abandoned cart cleanup
- **WHEN** the old session expires (30 days) and is deleted by `cleanup_expired_sessions()`
- **THEN** the associated `cart_items` are cascade-deleted (standard abandoned cart cleanup). If longer cart persistence is needed in the future, cart items should be migrated to user_id association.

#### Scenario: Frontend detects rotation
- **WHEN** the frontend receives a response with `X-Session-Rotated` header
- **THEN** the frontend can update its local session reference (for optimistic UI)

### Requirement: Login links session to user
The system SHALL set `sessions.user_id` to the authenticated user's ID on successful OAuth callback. The session_id itself does NOT change on login.

#### Scenario: Session linked on login
- **WHEN** the OAuth callback completes successfully for a user
- **THEN** the system updates the current session row: `SET user_id = <user_id>`

#### Scenario: Cart preserved on login
- **WHEN** a user logs in and their session is linked
- **THEN** `cart_items` remain associated with the same `session_id` (cart is preserved)

#### Scenario: Previous orders visible via backfill
- **WHEN** a user logs in and their session is linked
- **THEN** the system backfills `UPDATE orders SET user_id = <user_id> WHERE session_id = <session_id> AND user_id IS NULL`, permanently attaching anonymous orders to the user identity (survives session rotation)

#### Scenario: Backfill limited to current session
- **WHEN** a user has placed orders in previous sessions (before a logout rotation)
- **THEN** those orders are NOT backfilled — only orders from the current session are linked. There is no mechanism to retroactively link orders from old sessions without a user_id. This is an accepted limitation.

#### Scenario: Backfill security assumption
- **WHEN** the backfill query runs during OAuth callback
- **THEN** the `session_id` used MUST be the same `session_id` present in the verified OAuth state token (from login initiation). Authorization relies on UUID4 unguessability of session IDs — an attacker cannot guess a victim's session_id to claim their orders. This is documented as an accepted security boundary for the threat model (small family business, ~50 orders/month).

### Requirement: Logout for unauthenticated user is no-op
The system SHALL handle logout gracefully even if the user has no JWT or is already logged out.

#### Scenario: Unauthenticated logout
- **WHEN** a request to `POST /v1/auth/logout` has no valid JWT cookie but HAS a valid session cookie
- **THEN** the system still rotates the session (fresh UUID) and returns 200 (no error)

#### Scenario: Logout without valid session cookie
- **WHEN** a request to `POST /v1/auth/logout` has no valid JWT cookie and no valid session cookie (e.g., expired or missing)
- **THEN** the middleware will have created a new session (eagerly, before the route handler runs) and set `request.state.session_is_new = True`. The logout route detects this flag and returns 200 without rotating (no meaningful session to rotate — prevents session exhaustion via repeated unauthenticated POSTs). The middleware-created session remains valid for subsequent requests.

### Requirement: Session middleware exposes freshness flag
The session middleware SHALL set `request.state.session_is_new` to indicate whether the session was just created by the middleware for this request (True) or was an existing session from the cookie (False). This allows route handlers to distinguish "no prior session" from "returning session."

#### Scenario: New session flagged
- **WHEN** the session middleware creates a new session row because no valid session cookie was present
- **THEN** `request.state.session_is_new` is set to `True`

#### Scenario: Existing session flagged
- **WHEN** the session middleware finds a valid, non-expired session from the cookie
- **THEN** `request.state.session_is_new` is set to `False`
