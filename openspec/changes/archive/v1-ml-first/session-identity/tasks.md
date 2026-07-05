## 1. Schema & Models

- [ ] 1.1 Create DuckDB `session_identity` table schema (session_id VARCHAR PK, user_id VARCHAR nullable, first_seen TIMESTAMPTZ, last_seen TIMESTAMPTZ, is_expired BOOLEAN)
- [ ] 1.2 Create Pydantic models in `app/models/sessions.py` (SessionLink request, SessionLinkResponse, SessionStatus response)
- [ ] 1.3 Add session-related settings to pydantic-settings config (idle_timeout_minutes=30, hard_cap_hours=24, expiry_interval_seconds=300)

## 2. In-Memory Session Cache

- [ ] 2.1 Create `app/services/session_cache.py` with SessionCache class (dict-based, thread-safe)
- [ ] 2.2 Implement cache operations: get, upsert (create-or-update-last_seen), set_user_id, mark_expired, get_dirty_entries
- [ ] 2.3 Implement cache rebuild from DuckDB on startup (load active sessions only)
- [ ] 2.4 Implement cache flush to DuckDB (batch UPSERT of dirty entries)
- [ ] 2.5 Implement expired session eviction after successful flush

## 3. Session Middleware

- [ ] 3.1 Create `app/middleware/session.py` with SessionMiddleware class
- [ ] 3.2 Implement X-Session-ID header extraction and UUID v4 validation
- [ ] 3.3 Implement path-based enforcement (400 for event/session endpoints, pass-through for others)
- [ ] 3.4 Implement session cache upsert on valid requests (update last_seen)
- [ ] 3.5 Implement X-Session-Expired response header injection for expired sessions
- [ ] 3.6 Register middleware in FastAPI app lifespan/startup

## 4. Session Link Endpoint

- [ ] 4.1 Create `app/api/v1/sessions.py` router with POST /v1/sessions/link
- [ ] 4.2 Implement link logic: set user_id in cache, 409 on different-user conflict, 404 on unknown session
- [ ] 4.3 Create GET /v1/sessions/{session_id}/status endpoint (read from cache, fallback to DuckDB)
- [ ] 4.4 Register sessions router in the FastAPI app

## 5. Session Expiry Batch Job

- [ ] 5.1 Create `app/jobs/session_expiry.py` with expiry detection logic
- [ ] 5.2 Implement idle timeout detection (last_seen > 30 min ago)
- [ ] 5.3 Implement hard cap detection (first_seen > 24 hours ago)
- [ ] 5.4 Implement session_end event synthesis (append to JSONL buffer via O_APPEND writer)
- [ ] 5.5 Implement shared .batch.lock acquisition (non-blocking, skip on contention)
- [ ] 5.6 Implement DuckDB flush within the expiry job (dirty cache → session_identity table)
- [ ] 5.7 Implement expired session cache eviction post-flush
- [ ] 5.8 Wire expiry job as asyncio background task in FastAPI lifespan (5-min interval)

## 6. Logout & Session Rotation

- [ ] 6.1 Implement logout handler in session_service (mark expired, synthesize session_end, generate new UUID)
- [ ] 6.2 Add X-Session-Rotated response header support to middleware/endpoint layer
- [ ] 6.3 Ensure old session retains user_id after rotation (historical attribution preserved)

## 7. Analytics Helpers

- [ ] 7.1 Create `app/services/session_analytics.py` with internal query functions
- [ ] 7.2 Implement get_session_events(session_id) — DuckDB query
- [ ] 7.3 Implement get_user_sessions(user_id) — DuckDB query on session_identity
- [ ] 7.4 Implement get_user_events(user_id) — read-time JOIN query
- [ ] 7.5 Implement is_session_expired(session_id) — cache check with DuckDB fallback

## 8. Integration & Startup

- [ ] 8.1 Add session_identity table creation to DuckDB initialization (app startup)
- [ ] 8.2 Wire cache rebuild into FastAPI lifespan startup
- [ ] 8.3 Wire cache flush into FastAPI lifespan shutdown (graceful)
- [ ] 8.4 Add session cache stats to /health endpoint (active count, expired count)

## 9. Tests

- [ ] 9.1 Unit tests for SessionCache (upsert, expiry, dirty tracking, eviction)
- [ ] 9.2 Unit tests for session middleware (header validation, path enforcement, expiry header)
- [ ] 9.3 Unit tests for link endpoint (success, idempotent, 409 conflict, 404 unknown)
- [ ] 9.4 Unit tests for expiry job (idle timeout, hard cap, event synthesis, lock skip)
- [ ] 9.5 Integration test: full session lifecycle (new session → events → link → logout → rotation)
- [ ] 9.6 Integration test: shared device scenario (user A logout → user B login)
- [ ] 9.7 Integration test: multi-device identity resolution
