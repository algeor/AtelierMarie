## Context

AtelierMarie has a fully operational backend: event ingestion (POST /v1/events → JSONL → DuckDB), session lifecycle management (in-memory cache + batch flush), identity linking, and ML recommendations. The backend exposes a well-defined contract for browser clients: events arrive as JSON batches with an X-Session-ID header, and session state is communicated back via X-Session-Expired / X-Session-Rotated response headers.

No frontend code exists. The SDK is the first JavaScript deliverable — a standalone ES module that any frontend (React, Vue, vanilla) can import to start emitting behavioral events.

**Current state:**
- Backend: FastAPI + DuckDB + JSONL pipeline, fully deployed
- Frontend: Nothing — no tracker, no SDK, no JavaScript
- Contract: POST /v1/events accepts `{ events: [...] }` with X-Session-ID header
- Session headers: X-Session-Expired (true), X-Session-Rotated (new-uuid) on responses

**Constraints:**
- Zero budget — no Segment, no Amplitude, no third-party analytics
- SDK must be zero-dependency (no axios, no lodash)
- Bundle must be <5KB minified
- Must not block main thread (all I/O async)
- Backend is on free-tier VPS — must minimize HTTP request volume
- Must work without cookies (client generates session UUID)

## Goals / Non-Goals

**Goals:**
- Provide a drop-in tracker that any JavaScript app can use with 3 lines of code
- Handle session lifecycle entirely client-side, responding to server signals
- Batch events to reduce HTTP requests (protect free-tier VPS from request floods)
- Guarantee delivery on page close via sendBeacon
- Enable safe retries via client-generated event_id (server deduplicates)
- Gate all tracking behind explicit consent (GDPR)
- Degrade gracefully when localStorage is unavailable

**Non-Goals:**
- Offline queue (events lost if network unavailable — acceptable for e-commerce)
- npm publish or package registry distribution (self-hosted for now)
- TypeScript source (plain JS — types can be added via .d.ts later)
- Auto-capture (page views, clicks) — all tracking is explicit via track() calls
- Server-side rendering support (SDK is browser-only)
- Multi-tab coordination (each tab manages its own flush independently)
- A/B testing or feature flags integration

## Decisions

### 1. Single-file architecture (no module split)

**Decision:** The entire SDK ships as one file (`sdk/src/atelier-tracker.js`) — session logic, queue, transport, and consent are all in one module.

**Alternatives considered:**
- *Multi-file split (session.js, transport.js, consent.js, queue.js)*: Standard for large libraries, but this is ~100-150 lines total. Four files with 25-40 lines each adds import complexity and build requirements without meaningful separation of concerns. Rejected.
- *Class-per-concern with barrel export*: Over-engineered for the scope. Rejected.

**Rationale:** At this size, a single file IS the right architecture. The module boundary is the SDK itself. Internal organization is via well-named functions and clear code sections. When it grows past ~300 lines, split then — not before.

### 2. Client always generates event_id

**Decision:** Every call to `track()` assigns `event_id = crypto.randomUUID()` immediately. The ID travels with the event through the queue, batch, and any retries.

**Alternatives considered:**
- *Server generates event_id*: The backend already supports this (generates UUID4 if client omits). But then retries create duplicate events because the server sees each attempt as new. Rejected for SDK use.
- *Client generates only on retry*: Complicates the queue — must track which events have been attempted. Simpler to always assign upfront. Rejected.

**Rationale:** Client-generated event_id is the foundation of retry safety. The server's INSERT OR IGNORE on the primary key means the same event can be sent 3 times with identical result. The server's fallback generation remains for non-SDK clients (curl, testing).

### 3. Batch-first with sendBeacon fallback

**Decision:** Normal delivery uses `fetch()` with batched payloads. On `visibilitychange` → `hidden`, switch to `navigator.sendBeacon()` for the final flush.

**Alternatives considered:**
- *Always sendBeacon*: Limited to 64KB payload, no response inspection (can't read X-Session-Expired headers), no retry capability. Rejected as primary transport.
- *fetch with keepalive flag*: `fetch(url, {keepalive: true})` survives page unload in some browsers, but browser support is inconsistent and payload limit is 64KB. sendBeacon is more reliable for fire-and-forget. Rejected.
- *Image pixel fallback*: Only supports GET with limited payload. Legacy pattern. Rejected.

**Rationale:** fetch() for normal operation gives us response header inspection (session rotation), retry capability, and proper error handling. sendBeacon for the final flush guarantees delivery when fetch would be cancelled by page unload.

### 4. In-memory queue with configurable flush triggers

**Decision:** Events accumulate in a plain Array. Flush triggers: batch size reached (default 10), timer fires (default 5000ms), page hidden, or manual `tracker.flush()`.

**Alternatives considered:**
- *Immediate send per event*: 1 HTTP request per user action. On a free VPS handling multiple users, this creates 100+ RPS easily. Rejected.
- *localStorage queue*: Survives refresh but adds JSON.parse/stringify overhead on every track() call and creates multi-tab contention. Over-complicated for MVP. Rejected.
- *Web Worker queue*: Moves batching off main thread, but adds complexity (message passing, Worker lifecycle) for negligible benefit — Array.push is already <1μs. Rejected.

**Rationale:** In-memory Array is the simplest possible queue. Push is O(1). Flush is a single splice + POST. No serialization overhead until flush time. Events lost on hard crash (browser kill) — acceptable; the server's 60-second batch to DuckDB means even successfully-delivered events aren't queryable instantly.

### 5. Consent as a boolean gate, not a separate module

**Decision:** Consent is an `enabled` boolean on the tracker instance. When `requireConsent: true` (default), the tracker starts disabled. `grantConsent()` sets enabled=true and persists to localStorage. All `track()` calls short-circuit with an early return when disabled.

**Alternatives considered:**
- *Conditional initialization*: Don't create tracker until consent given. Simpler for the app developer but loses the ability to call `tracker.track()` optimistically (events silently dropped pre-consent vs. "tracker is undefined" errors). Rejected.
- *Event buffering pre-consent*: Queue events before consent, flush on grant. GDPR-questionable — even holding events in memory without consent may violate purpose limitation. Rejected.

**Rationale:** A boolean gate is ~5 lines of code, is unambiguous (no events = no events), and is the safest GDPR interpretation. The app calls `track()` freely; the tracker handles the gate internally.

### 6. Session rotation driven by server response headers

**Decision:** After every `fetch()` response, the SDK inspects headers. On `X-Session-Expired: true`, rotate locally (new UUID + session_start event). On `X-Session-Rotated: <id>`, adopt the server-provided UUID. Client-side idle/age detection is a secondary signal (server is the backstop).

**Alternatives considered:**
- *Client-only expiry*: Client tracks idle time and session age, rotates autonomously. Risk: client clock manipulation or bugs create sessions that never expire. Server has no voice. Rejected as sole mechanism.
- *Server sets session via cookie*: Requires cookie support, breaks the "no cookies" design. Rejected.

**Rationale:** Server is the authority on session state. Client rotation is best-effort UX (avoid sending events the server will reject). The dual approach gives you defense in depth: server enforces, client anticipates.

### 7. esbuild for minification (single devDependency)

**Decision:** `esbuild --bundle --minify --format=esm` produces the dist build. No rollup, no webpack, no babel.

**Alternatives considered:**
- *Rollup + terser*: Standard for library authors, but two dependencies and config files for a single-file bundle. Rejected.
- *No build step (ship source)*: Possible since it's one file, but unminified is ~4KB vs ~2KB minified. Minification matters for a tracking pixel use case. Rejected.
- *Manual terser CLI*: Works, but esbuild is faster and handles both bundling (if we split later) and minification. Rejected.

**Rationale:** esbuild is a single `npm install --save-dev esbuild` and a one-line script in package.json. Future-proof if the single file eventually splits.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **localStorage unavailable** (private browsing, storage full) | Fallback to in-memory-only mode. Session ID regenerated each page load — acceptable degradation. Events still tracked for the page session. |
| **sendBeacon payload >64KB** (huge batch on tab close) | Enforce max batch size. If queue exceeds limit on unload, send multiple beacons or truncate oldest. Unlikely at 10-event flush interval. |
| **crypto.randomUUID unavailable** (older browsers) | Only affects Chrome <92, Firefox <95, Safari <15.4. Polyfill with `URL.createObjectURL(new Blob()).slice(-36)` or similar. Alternatively: document as browser requirement and don't polyfill. |
| **CORS blocks requests** | Backend must set Access-Control-Allow-Origin, Allow-Headers (X-Session-ID, Content-Type). Already assumed in backend design. Document CORS setup in README. |
| **Double-flush on visibilitychange** (timer fires + visibility fires) | Clear timer on visibility flush. Queue is empty after flush, so second attempt is a no-op regardless. |
| **Session_id divergence** (client rotates, server doesn't know yet) | Acceptable. Server creates new session record on first event with unknown session_id. By design, sessions are client-initiated. |
| **Events lost on network failure** (no offline queue) | Accepted trade-off. E-commerce browsing while offline is not a real use case. Retry (3x) covers transient failures. |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  BROWSER                                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  AtelierTracker                                          │    │
│  │                                                         │    │
│  │  ┌──────────┐   ┌─────────────┐   ┌───────────────┐    │    │
│  │  │ Consent  │   │  Session    │   │  Identity     │    │    │
│  │  │ Gate     │   │  Manager    │   │  (user_id)    │    │    │
│  │  │          │   │             │   │               │    │    │
│  │  │ enabled? ├──▶│ get/rotate  │   │ set/clear     │    │    │
│  │  │ grant()  │   │ localStorage│   │ userId        │    │    │
│  │  │ revoke() │   │ expiry check│   │               │    │    │
│  │  └──────────┘   └──────┬──────┘   └───────┬───────┘    │    │
│  │                         │                  │            │    │
│  │       track(type, data) │                  │            │    │
│  │            │            │                  │            │    │
│  │            ▼            ▼                  ▼            │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Event Queue (Array)                             │    │    │
│  │  │  [{event_id, event_type, session_id, user_id,   │    │    │
│  │  │    product_id, metadata, timestamp}, ...]        │    │    │
│  │  └────────────────────────┬────────────────────────┘    │    │
│  │                           │                             │    │
│  │           Flush triggers: │                             │    │
│  │           • queue.length >= 10                          │    │
│  │           • setInterval(5000ms)                         │    │
│  │           • visibilitychange → hidden                   │    │
│  │           • tracker.flush()                             │    │
│  │                           │                             │    │
│  │                           ▼                             │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Transport                                       │    │
│  │  │                                                 │    │
│  │  │  Normal: fetch(POST /v1/events)                 │    │
│  │  │    → Inspect response headers                   │    │
│  │  │    → X-Session-Expired? → rotate()              │    │
│  │  │    → X-Session-Rotated? → adopt(id)             │    │
│  │  │    → 429/5xx? → retry (1s, 2s, 4s)             │    │
│  │  │                                                 │    │
│  │  │  On unload: sendBeacon(POST /v1/events)         │    │
│  │  │    → Fire-and-forget, no response available     │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  BACKEND (existing — no changes)                                  │
│                                                                  │
│  POST /v1/events                                                 │
│    Headers: X-Session-ID, Content-Type: application/json         │
│    Body: { events: [{event_id, event_type, ...}, ...] }          │
│    Response: 202 + X-Session-Expired / X-Session-Rotated         │
│                                                                  │
│  → JSONL buffer → DuckDB batch load (60s)                        │
└──────────────────────────────────────────────────────────────────┘
```

## Open Questions

- **sendBeacon content type**: `sendBeacon()` with a Blob allows setting Content-Type to application/json. Verify CORS preflight behavior — does the backend handle OPTIONS for sendBeacon requests? (Likely yes, but worth testing.)
- **Timer cleanup**: Should the SDK expose a `destroy()` method that clears the flush interval and removes event listeners? Useful for SPAs that unmount tracker components.
