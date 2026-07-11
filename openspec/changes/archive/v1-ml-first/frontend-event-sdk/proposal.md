## Why

The AtelierMarie backend has a complete event ingestion pipeline (POST /v1/events → JSONL buffer → DuckDB batch load), session/identity management, and ML recommendations — but no way for browsers to actually send events reliably. Without a frontend SDK, every frontend integration must re-implement session management, event batching, retry logic, and consent gating. A lightweight, framework-agnostic JavaScript tracker closes the loop between user behavior and the ML platform.

## What Changes

- **New: Browser event tracker** — ES module (~100-150 lines, zero dependencies) that queues events in-memory and flushes to POST /v1/events in batches
- **New: Client-side session management** — Generates and rotates session UUIDs in localStorage, responds to server expiry/rotation headers (X-Session-Expired, X-Session-Rotated)
- **New: Reliable delivery** — Batch flush (10 events / 5s timer), exponential retry with client-generated event_id for idempotency, sendBeacon on tab close
- **New: Consent gate** — All tracking gated behind explicit opt-in (GDPR compliance). No events emitted without `grantConsent()`
- **New: Identity integration** — `setUserId()` / `clearUserId()` for post-login attribution
- **New: SDK package** — `sdk/` directory with source, minified build (<5KB), README, and package.json

## Capabilities

### New Capabilities
- `session-management`: Client-side session UUID generation, localStorage persistence, rotation on server signal (X-Session-Expired / X-Session-Rotated), idle/age expiry detection
- `event-delivery`: In-memory event queue, batch flush triggers (count/timer/visibility/manual), POST /v1/events transport, sendBeacon fallback on page unload
- `retry-reliability`: Client-generated event_id (crypto.randomUUID), exponential backoff (1s/2s/4s), max 3 retries, server-side dedup via INSERT OR IGNORE
- `consent-gate`: Opt-in gating of all track() calls, localStorage-persisted consent state, grant/revoke API, GDPR compliance

### Modified Capabilities
<!-- No existing specs are modified — this is a new client-side component that consumes existing backend APIs -->

## Impact

- **New directory**: `sdk/` at project root (JavaScript, separate from Python backend)
- **APIs consumed**: POST /v1/events (existing), response headers X-Session-ID / X-Session-Expired / X-Session-Rotated (existing)
- **No backend changes required** — SDK is a pure consumer of existing endpoints
- **Browser requirements**: Chrome 80+, Firefox 78+, Safari 14+, Edge 80+ (crypto.randomUUID, sendBeacon, localStorage)
- **Build tooling**: esbuild (single devDependency) for minification
- **Distribution**: Self-hosted script tag (npm publish deferred to follow-up)
