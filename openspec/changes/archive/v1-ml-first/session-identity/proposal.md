## Why

The event ingestion pipeline captures behavior but has no concept of *who* is behaving. Every ML feature downstream (recommendations, conversion tracking, user profiles) requires linking events to sessions and sessions to users. Without a session & identity layer, the platform cannot distinguish returning visitors from new ones, cannot attribute anonymous browsing to a user after login, and cannot build cross-session user profiles for personalization.

The system must work without cookies (header-based session IDs for SPA/mobile compatibility), handle anonymous-first tracking (most visitors never log in), and resolve identity retroactively via read-time JOINs rather than risky event backfilling.

## What Changes

- Add a `session_identity` bridge table in DuckDB linking session_ids to user_ids (nullable)
- Implement FastAPI middleware that validates `X-Session-ID` headers, upserts session records, and communicates session expiry via response headers
- Create session lifecycle management: 30-min idle timeout, 24-hour hard cap, forced rotation on logout
- Add `POST /v1/sessions/link` endpoint for binding authenticated users to their session (called post-OAuth)
- Add `GET /v1/sessions/{session_id}/status` endpoint for querying session state
- Build a background expiry batch job (runs every 5 min) that marks expired sessions and synthesizes `session_end` events into the JSONL buffer
- Create internal analytics helpers for read-time identity resolution (`get_user_events`, `get_user_sessions`, etc.)

## Capabilities

### New Capabilities

- `session-tracking`: Middleware-based session lifecycle management — header validation, session_identity upserts, expiry detection, and rotation signaling via response headers
- `identity-linking`: Session-to-user binding via link endpoint, read-time JOIN resolution for retroactive attribution, and edge case handling (logout, shared device, multi-device, re-login)
- `session-expiry`: Background batch job for server-side session expiry detection, marking expired sessions, and synthesizing session_end events

### Modified Capabilities

<!-- No existing capabilities to modify — session_id is already a field in events but was not managed until now -->

## Impact

- **DuckDB schema**: New `session_identity` table added alongside `events`
- **Middleware**: New middleware added to FastAPI app (runs on all requests)
- **New endpoints**: `/v1/sessions/link`, `/v1/sessions/{session_id}/status`
- **Event pipeline integration**: Expiry job writes `session_end` events to the same JSONL buffer, uses separate `.session-expiry.lock`
- **Response headers**: All `/v1/events` responses gain `X-Session-Expired` header when applicable
- **New directory**: `app/middleware/`, `app/services/`, `app/jobs/` packages
- **Background process**: Additional asyncio task alongside the batch loader
- **Performance constraint**: Session validation on event ingestion must stay under 1ms (in-memory cache path)
