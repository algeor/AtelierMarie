## Context

AtelierMarie has a working event ingestion pipeline: POST /v1/events → JSONL buffer → DuckDB batch load. Events carry a `session_id` field but the system currently does nothing with it — no lifecycle management, no identity resolution, no expiry. The platform needs a session & identity layer to bridge anonymous browsing and personalized ML features.

**Current state:**
- Events table in DuckDB with `session_id` (VARCHAR) and `user_id` (nullable VARCHAR) columns
- No session validation or tracking
- No mechanism to link anonymous sessions to authenticated users
- JSONL writer + batch loader running with file-lock concurrency pattern

**Constraints:**
- Zero budget — no Redis, no external session stores
- DuckDB single-writer model (file lock for writes)
- Must not add >1ms latency to event ingestion hot path
- Must integrate with existing JSONL buffer and batch loader patterns
- Client generates session_id (no server-side cookies)

## Goals / Non-Goals

**Goals:**
- Track session lifecycle (first_seen, last_seen, expiry) in DuckDB
- Validate session_id format (UUID v4) on event ingestion without blocking latency
- Link anonymous sessions to authenticated users via a bridge table
- Resolve historical attribution at read-time via JOIN (not backfill)
- Handle edge cases: logout rotation, shared devices, multi-device, re-login
- Communicate session state to clients via response headers
- Detect and mark expired sessions server-side (30-min idle / 24-hour hard cap)

**Non-Goals:**
- Server-side session_id generation or cookie management
- Real-time session state (DuckDB batch delay is acceptable for session_identity updates)
- User authentication/OAuth implementation (that's a separate system; this provides the link endpoint)
- Client SDK or frontend session logic
- Session replay or debugging tools
- Rate limiting or abuse detection based on sessions

## Decisions

### 1. In-memory write-through cache for session state

**Decision:** Maintain an in-memory dict (`{session_id: SessionRecord}`) populated on first access, flushed to DuckDB by the expiry batch job. The middleware reads/updates only the cache on the hot path.

**Alternatives considered:**
- *DuckDB read on every request*: Single-writer model makes this impossible without read-only connection. Even read-only adds 1-5ms per query. Rejected — violates <1ms constraint.
- *SQLite as session cache*: Adds cross-database complexity and WAL contention for a write-heavy access pattern. Rejected.
- *LRU dict with periodic sync*: Closest to what we chose, but LRU eviction could lose session state. Use unbounded dict (sessions are small, ~200 bytes each; 100K sessions = ~20MB).

**Rationale:** The cache is the source of truth for `last_seen` (updated every request). The batch job is responsible for persisting to DuckDB periodically. On cold start, cache is rebuilt from DuckDB. Session data is tiny — even 100K concurrent sessions fit comfortably in memory on free-tier VPS (512MB+ RAM).

**Trade-off:** Process crash loses `last_seen` updates since last flush. Acceptable — expiry is approximate by nature (30-min window).

### 2. Middleware with path-based enforcement

**Decision:** A single middleware runs on all requests. Behavior varies by path:
- `/v1/events/*`: Require valid `X-Session-ID`, return 400 if missing/invalid
- `/v1/sessions/*`: Require valid `X-Session-ID`
- All other paths (`/v1/products/*`, `/health`): Ignore missing session_id, pass through

**Alternatives considered:**
- *Dependency injection per route*: More granular but duplicates validation logic across every event handler. Rejected.
- *Two middlewares (validator + tracker)*: Separation of concerns but doubles middleware overhead. Rejected — they're tightly coupled.

**Rationale:** Single middleware, path-conditional logic. Simple, testable, minimal overhead on non-session paths.

### 3. Read-time JOIN for identity resolution (not event backfill)

**Decision:** When a session is linked to a user_id, the `session_identity` table is updated. Historical events are NOT modified. Attribution is resolved at query time:

```sql
SELECT e.* FROM events e
JOIN session_identity si ON e.session_id = si.session_id
WHERE si.user_id = ?
```

**Alternatives considered:**
- *Backfill events with user_id*: Requires updating potentially thousands of rows in DuckDB (batch operation), risks corrupting event history, and violates single-writer constraints during link. Rejected.
- *Materialized view*: DuckDB doesn't support incremental materialized views. Full rebuild is expensive. Rejected.

**Rationale:** Events are immutable facts. Identity is a lens. The JOIN is fast (session_id indexed in both tables). This pattern composes cleanly — a user's "identity" can even be revised (e.g., account merge) without touching events.

### 4. Forced session rotation on logout via response header

**Decision:** On logout, the server marks the current session as expired, synthesizes a `session_end` event, and returns `X-Session-Rotated: <new-uuid>` header. The client MUST start using the new session_id.

**Alternatives considered:**
- *Client-initiated rotation*: Client generates new session_id on logout. Risk: client bug could reuse old session_id, leaking identity to next user. Rejected.
- *Server generates but doesn't force*: Suggests via header but allows old session. Half-measure — still leaks if client ignores. Rejected.

**Rationale:** Server generates the rotation UUID because it atomically closes the old session. 409 Conflict on re-link-to-different-user is the backstop — even if the client ignores the rotation header, the old session can never be claimed by another user.

### 5. Shared file lock for all DuckDB writers

**Decision:** The session expiry job acquires `app/data/.batch.lock` — the same unified lock used by the event batch loader. This serializes all DuckDB writes through a single lock.

**Rationale:** DuckDB is single-writer. All jobs that write to DuckDB (event batch loader, session expiry flush, analytics compute) must coordinate via the same lock. The expiry job acquires `.batch.lock`, runs its DuckDB operations (mark expired + flush dirty cache to `session_identity`), then releases. It also appends synthesized `session_end` events to the JSONL buffer (which is lock-free via `O_APPEND`).

**Note:** The analytics layer also shares `.batch.lock` with a blocking wait strategy (it waits for the lock rather than skipping), since analytics compute runs on a longer interval and must complete its write. The event loader and session expiry job both use non-blocking try with skip/retry semantics.

### 6. Session_identity upsert batched (not per-request)

**Decision:** The in-memory cache collects `last_seen` updates. The batch job (or a dedicated sync within it) flushes all dirty cache entries to DuckDB in a single batch UPSERT. New sessions are also batch-inserted.

**Rationale:** Upserting session_identity on every request would require DuckDB write access per request — impossible with single-writer model and unacceptable for latency. Batching is consistent with the event pipeline philosophy: fast writes to buffer (cache), periodic batch persist to DuckDB.

**Flush cadence:** Piggybacked on the expiry job (every 5 minutes). Session state in DuckDB may lag up to 5 minutes behind reality. Acceptable for analytics/ML use cases.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Process crash loses in-memory cache** → last_seen updates lost since last flush | Expiry is approximate (30-min window); losing 5 min of last_seen is negligible. On restart, cache rebuilds from DuckDB (slightly stale). |
| **Unbounded cache growth** → memory pressure on long-running process | Expired sessions evicted from cache after flush. Active session count bounded by real traffic (free-tier = low volume). Monitor via /health endpoint. |
| **Shared .batch.lock** → expiry job and event loader contend | Both are fast (<5s). 5-min intervals mean overlap is unlikely. If it occurs, one waits — acceptable. |
| **Client ignores X-Session-Expired header** → events arrive on expired session | Graceful handling: events accepted, session stays expired, session_end already synthesized. No data loss, just slightly messy session boundary. |
| **409 Conflict on link to different user** → legitimate shared-device scenario blocked | By design. User must logout first (rotates session). If 409 occurs, client should prompt logout-then-login flow. |
| **DuckDB cold-start rebuild** → slow startup with many sessions | `SELECT * FROM session_identity WHERE is_expired = FALSE` — only loads active sessions. Expired sessions not needed in cache. |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Session Middleware                                                  │    │
│  │  ┌───────────┐    ┌──────────────────────────────────────────┐      │    │
│  │  │ Request   │    │  In-Memory Session Cache                  │      │    │
│  │  │ X-Session │───▶│  {session_id: {user_id, first_seen,      │      │    │
│  │  │ -ID header│    │   last_seen, is_expired}}                 │      │    │
│  │  └───────────┘    └──────────────────┬───────────────────────┘      │    │
│  │       │                              │                               │    │
│  │       │ 400 if missing               │ Updates last_seen             │    │
│  │       │ (event endpoints)            │ Sets X-Session-Expired        │    │
│  └───────┼──────────────────────────────┼──────────────────────────────┘    │
│           │                              │                                   │
│           ▼                              ▼                                   │
│  ┌────────────────┐        ┌─────────────────────────────┐                  │
│  │ POST /v1/events│        │ POST /v1/sessions/link      │                  │
│  │ (existing)     │        │ → cache.user_id = req.uid   │                  │
│  └───────┬────────┘        │ → 409 if different user     │                  │
│          │                  └─────────────────────────────┘                  │
│          ▼                                                                   │
│  ┌────────────────┐                                                         │
│  │  JSONL Buffer  │◀─── session_end events (from expiry job)                │
│  │  buffer/*.jsonl│                                                         │
│  └───────┬────────┘                                                         │
│          │                                                                   │
│          ▼                   ┌─────────────────────────────────────────┐    │
│  ┌────────────────┐         │  Session Expiry Job (every 5 min)       │    │
│  │  .batch.lock   │◀────────│  1. Acquire .batch.lock                 │    │
│  │  (shared)      │         │  2. Flush dirty cache → session_identity│    │
│  └───────┬────────┘         │  3. Mark expired (idle>30m, age>24h)    │    │
│          │                   │  4. Synthesize session_end → JSONL      │    │
│          ▼                   │  5. Release lock                        │    │
│  ┌──────────────────────┐   └─────────────────────────────────────────┘    │
│  │  DuckDB              │                                                   │
│  │  ┌────────────────┐  │                                                   │
│  │  │ events         │  │   Read-time JOIN for identity resolution:         │
│  │  │ (session_id,.. │  │   SELECT e.* FROM events e                        │
│  │  └────────────────┘  │   JOIN session_identity si                        │
│  │  ┌────────────────┐  │     ON e.session_id = si.session_id               │
│  │  │session_identity│  │   WHERE si.user_id = ?                            │
│  │  │ (bridge table) │  │                                                   │
│  │  └────────────────┘  │                                                   │
│  └──────────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Open Questions

- **Cache persistence on graceful shutdown**: Should the lifespan shutdown hook flush the cache to DuckDB? (Leaning yes — prevents 5-min data gap on restart.)
- **Session count in /health**: Should the health endpoint report active session count from the cache? (Leaning yes — useful for monitoring.)
