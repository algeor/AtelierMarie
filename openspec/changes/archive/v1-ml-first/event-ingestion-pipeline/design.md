## Context

AtelierMarie is a fresh FastAPI project (Python 3.11) with no existing infrastructure beyond a hello-world endpoint. The platform needs to capture e-commerce behavioral events as the foundation for ML-powered recommendations, ranking, and analytics.

**Constraints:**
- Zero budget — no managed services (Kafka, Redis, SQS, etc.)
- Must deploy on free-tier VPS (Oracle Free, Fly.io, Render)
- DuckDB is the analytical store (single-writer model)
- Must handle concurrent requests without data loss
- Must survive process crashes without losing buffered events

**Current state:** Empty project. FastAPI + uvicorn installed. No database, no models, no endpoints beyond GET /.

## Goals / Non-Goals

**Goals:**
- Establish a crash-safe, concurrent-write-safe event ingestion pipeline
- Buffer events durably (survive process restarts) before loading to DuckDB
- Achieve sub-10ms write latency on the hot path (API → JSONL append)
- Support 50–300 RPS for event ingestion without contention
- Enable future multi-worker scaling without architectural changes
- Provide deduplication so client retries are safe
- Create a health check exposing pipeline status

**Non-Goals:**
- Real-time event availability in DuckDB (60-second batch delay is acceptable)
- Sub-second query freshness for ML features
- Multi-region or distributed deployment
- Event schema evolution or versioning (keep simple for now)
- Authentication or authorization on the events endpoint
- Frontend SDK implementation (backend only)

## Decisions

### 1. Buffered JSONL over direct DuckDB writes

**Decision:** Events are appended to JSONL files first, then batch-loaded into DuckDB on a 60-second timer.

**Alternatives considered:**
- *Direct DuckDB write per request*: Single-writer lock causes contention at >10 RPS. Rejected.
- *In-process asyncio queue → DuckDB*: Fast, but queue contents lost on crash. Rejected.
- *SQLite WAL as buffer*: Works, but adds second DB to manage and JSONL is simpler for DuckDB's `read_json` bulk loader. Rejected.

**Rationale:** JSONL append is effectively zero-latency (one syscall), crash-safe (data on disk before response), and DuckDB's `read_json` bulk loader is optimized for this exact pattern.

### 2. O_APPEND for concurrent write safety

**Decision:** JSONL files opened with `O_APPEND` flag + line-buffered mode. No application-level write lock.

**Rationale:** POSIX guarantees that `write()` with `O_APPEND` on regular files is atomic (seek+write is indivisible). Line-buffered mode ensures each `\n`-terminated line is a single `write()` syscall. This holds across threads (single worker) and across processes (multiple workers).

**Caveat:** If a process is killed mid-`write()`, the final partial line may be corrupt. The batch loader handles this with `ignore_errors=true`.

### 3. File-lock-guarded batch loader (multi-worker safe from day 1)

**Decision:** The batch loader runs as an `asyncio.create_task()` sleep loop in every worker's lifespan, BUT acquires an exclusive file lock (`fcntl.flock()` on `app/data/.batch.lock`) before performing any DuckDB writes. Only the worker that holds the lock runs the batch; all others skip silently.

This makes the system multi-worker safe from day 1 — no architecture change needed when adding `--workers N`.

**How it works:**
```
Worker 1 lifespan → batch_loader_loop():
    acquire flock(LOCK_EX | LOCK_NB) on .batch.lock
      → SUCCESS: run batch, release lock

Worker 2 lifespan → batch_loader_loop():
    acquire flock(LOCK_EX | LOCK_NB) on .batch.lock
      → EWOULDBLOCK: skip this cycle, sleep, try again next interval
```

**Alternatives considered:**
- *APScheduler*: Extra dependency, complex async integration. Rejected.
- *External cron job*: Operationally complex (two things to deploy). Rejected — unnecessary with file lock.
- *Single-worker assumption + defer*: Seems simpler but creates a known-broken state the moment you scale. Rejected.
- *PID-file leader election*: Stale PIDs cause issues on crash. File lock auto-releases on process death. Rejected.

**Rationale:** `fcntl.flock()` is kernel-managed — the lock is automatically released if the holding process dies (no stale locks). Non-blocking attempt (`LOCK_NB`) means losing workers don't wait, they just skip. Zero external dependencies. Works across uvicorn `--workers N` because workers are separate processes sharing a filesystem.

**Implementation detail:** The lock file lives at `app/data/.batch.lock` (same filesystem as buffer/archive, so no cross-device issues). Lock is held only during the batch operation (~1–5 seconds), not for the entire sleep interval.

**Note:** `.batch.lock` is a unified lock shared with multiple DuckDB writers: the session expiry flush and the analytics compute job also acquire this lock before writing. The event loader's usage is unchanged — it uses a non-blocking try (`LOCK_NB`) with a 1-second retry interval, skipping cycles when the lock is held by another job.

### 4. Transaction-per-file with INSERT OR IGNORE

**Decision:** Each JSONL file is loaded in a single DuckDB transaction. Deduplication uses `INSERT OR IGNORE` on the `event_id` primary key. File is moved to `archive/` only after commit.

**Rationale:**
- Transaction-per-file means a failed load leaves the file in `buffer/` for automatic retry (crash safety).
- `INSERT OR IGNORE` handles: (a) client retries sending same event_id, (b) replay if a file is accidentally loaded twice, (c) partial loads where some events from a prior attempt were committed.

### 5. Server-side event_id and timestamp as source of truth

**Decision:** Server generates `event_id` (UUID4) if client omits it. `server_timestamp` (UTC) is the canonical ordering field. Client-provided timestamp is preserved in `metadata.client_timestamp`.

**Rationale:** Client clocks are unreliable (timezone errors, skew, spoofing). Server-side generation ensures monotonic ordering within the server's clock domain and guarantees uniqueness for deduplication.

### 6. Date-partitioned JSONL files

**Decision:** Buffer files named `events_YYYY-MM-DD.jsonl`. One file per calendar day.

**Rationale:** Natural rotation boundary, easy to reason about retention, and the loader can process completed (yesterday's) files without racing the writer. Current-day files are also processed (writer flushes, loader uses `ignore_errors` for any trailing partial line).

### 7. Explicit DuckDB column types (not read_json_auto)

**Decision:** Use `read_json()` with explicit `columns` parameter instead of `read_json_auto()`.

**Rationale:** Schema inference fails when early data has many NULL fields (user_id, product_id). Explicit types prevent DuckDB from guessing VARCHAR vs INTEGER incorrectly.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Disk full on VPS** → writer fails, 503 returned | Health endpoint exposes buffer size. Future: alerting on file count. Writer catches OSError cleanly. |
| **Batch loader lag** → events not queryable for up to 60s | Acceptable for ML use cases. Not suitable for real-time dashboards (not a goal). |
| **Corrupt JSONL line from crash** → event lost | `ignore_errors=true` skips it. One event lost per crash is acceptable vs. complexity of write-ahead-log. |
| **Multiple workers attempt batch load simultaneously** → DuckDB write contention | File lock (`fcntl.flock`) ensures only one worker runs the loader at a time. Lock auto-releases on process death. |
| **DuckDB locked during batch load** → read queries timeout | Batch loads are fast (read_json is bulk). DuckDB WAL mode allows concurrent reads during write. |
| **Large batch request (1000 events)** → slow response | JSONL append is O(n) sequential writes, each ~1μs. 1000 events ≈ 1ms. Acceptable. |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     uvicorn --workers N                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Worker 1                                                       │    │
│  │  ┌──────────────────┐    ┌───────────────────────────────┐     │    │
│  │  │  POST /v1/events │    │  Batch Loader Loop (asyncio)  │     │    │
│  │  │  → writer.write  │    │  → flock(.batch.lock, LOCK_NB)│     │    │
│  │  └────────┬─────────┘    │  → GOT LOCK? Run batch.       │     │    │
│  │           │               │  → NO LOCK? Skip, sleep.     │     │    │
│  │           │               └──────────────┬────────────────┘     │    │
│  └───────────┼──────────────────────────────┼──────────────────────┘    │
│              │                               │                           │
│  ┌───────────┼──────────────────────────────┼──────────────────────┐    │
│  │  Worker 2 │                              │                      │    │
│  │  ┌────────▼─────────┐    ┌──────────────▼────────────────┐     │    │
│  │  │  POST /v1/events │    │  Batch Loader Loop (asyncio)  │     │    │
│  │  │  → writer.write  │    │  → flock(.batch.lock, LOCK_NB)│     │    │
│  │  └────────┬─────────┘    │  → GOT LOCK? Run batch.       │     │    │
│  │           │               │  → NO LOCK? Skip, sleep.     │     │    │
│  │           │               └──────────────┬────────────────┘     │    │
│  └───────────┼──────────────────────────────┼──────────────────────┘    │
│              │                               │                           │
│              ▼                               ▼                           │
│  ┌─────────────────────┐     ┌──────────────────────────────┐           │
│  │  buffer/            │     │  .batch.lock (fcntl.flock)   │           │
│  │  events_YYYY-MM-DD  │     │  Only 1 worker holds at a    │           │
│  │  .jsonl             │     │  time. Auto-release on death. │           │
│  └─────────────────────┘     └──────────────┬───────────────┘           │
│                                             │                           │
│                                             ▼                           │
│                               ┌──────────────────────────┐              │
│                               │  DuckDB (single writer)  │              │
│                               │  events table            │              │
│                               └──────────────────────────┘              │
│                                             ▲                           │
│  ┌──────────────────┐                       │                           │
│  │  GET /health     │──── read_only=True ───┘                           │
│  └──────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Open Questions

- **Archive retention**: 30-day retention was proposed. Should cleanup be part of this change or a separate follow-up?
- **Metrics endpoint**: Should `/v1/metrics` be Prometheus-compatible format or plain JSON? (Leaning JSON for simplicity.)
