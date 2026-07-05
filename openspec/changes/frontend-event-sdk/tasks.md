## 1. Project Setup

- [ ] 1.1 Create `sdk/` directory with `package.json` (name: @atelier/tracker, type: module, no dependencies, esbuild as devDependency)
- [ ] 1.2 Add build script to package.json: `esbuild src/atelier-tracker.js --bundle --minify --format=esm --outfile=dist/atelier-tracker.min.js`
- [ ] 1.3 Create `sdk/src/` and `sdk/dist/` directories

## 2. Core Tracker Implementation

- [ ] 2.1 Implement `AtelierTracker.init(config)` factory — accepts endpoint, batchSize (default 10), flushInterval (default 5000), maxRetries (default 3), requireConsent (default true), debug (default false)
- [ ] 2.2 Implement localStorage helper with in-memory fallback (try/catch around getItem/setItem/removeItem)
- [ ] 2.3 Implement consent gate — `grantConsent()`, `revokeConsent()`, enabled boolean, localStorage persistence under `atelier_consent`
- [ ] 2.4 Implement session management — `getSessionId()`, `rotateSession()`, localStorage keys `atelier_session_id` / `atelier_session_start`, idle detection (30min), age cap (24h)
- [ ] 2.5 Implement `track(eventType, data)` — consent check, session expiry check, event_id generation (crypto.randomUUID), build event object, push to queue, trigger size-based flush
- [ ] 2.6 Implement `setUserId(id)` and `clearUserId()` — stores user_id on instance for inclusion in subsequent events

## 3. Event Queue & Flush

- [ ] 3.1 Implement in-memory event queue (Array) with flush triggers: batchSize reached, manual flush()
- [ ] 3.2 Implement flush timer (setInterval at flushInterval ms) — skip flush if queue empty, clear timer on visibility-hidden flush
- [ ] 3.3 Implement `flush()` method — splice queue, POST /v1/events with JSON body `{ events: [...] }`, include X-Session-ID header
- [ ] 3.4 Implement concurrent flush guard — prevent double-flush of same events when timer fires during in-flight request

## 4. Transport & Reliability

- [ ] 4.1 Implement fetch transport — POST /v1/events, Content-Type: application/json, parse response for session headers (X-Session-Expired, X-Session-Rotated)
- [ ] 4.2 Implement retry with exponential backoff — on 5xx or 429, retry up to maxRetries with delays 1s, 2s, 4s; on 4xx (not 429) drop batch; on 202 clear
- [ ] 4.3 Implement session header response handling — call rotateSession() on X-Session-Expired, adopt server UUID on X-Session-Rotated
- [ ] 4.4 Implement sendBeacon fallback — on visibilitychange → hidden, flush queue via sendBeacon with JSON Blob (Content-Type: application/json)

## 5. Build & Distribution

- [ ] 5.1 Build `sdk/dist/atelier-tracker.js` (ES module, unbundled copy for readability)
- [ ] 5.2 Build `sdk/dist/atelier-tracker.min.js` (esbuild minified, verify <5KB)
- [ ] 5.3 Add exports field to package.json pointing to dist/atelier-tracker.js

## 6. Documentation

- [ ] 6.1 Write `sdk/README.md` — installation (script tag + ES module import), initialization, tracking API, consent flow, session behavior, configuration options, browser support

## 7. Testing

- [ ] 7.1 Unit tests for session management — generation, rotation, idle/age expiry, localStorage fallback
- [ ] 7.2 Unit tests for consent gate — grant/revoke, persistence, pre-consent track() no-op
- [ ] 7.3 Unit tests for event queue — batch size flush, timer flush, manual flush, empty queue skip
- [ ] 7.4 Unit tests for retry — exponential backoff timing, max retries, event_id preservation across retries, 4xx vs 5xx handling
- [ ] 7.5 Integration test — tracker.track() → verify POST /v1/events received with correct payload structure (against local backend)
