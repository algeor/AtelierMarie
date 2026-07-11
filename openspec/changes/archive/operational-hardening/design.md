## Context

AtelierMarie is a luxury candle e-commerce platform built with FastAPI + SQLite (backend) and Next.js (frontend). The architecture follows a strict two-layer model: Layer 1 (production e-commerce) must be rock-solid; Layer 2 (analytics/ML) is optional and crash-tolerant.

The codebase has solid structural foundations — service pattern, Pydantic validation, typed Python, clear module boundaries. However, a seniority audit revealed systematic gaps in operational hardening: error handling is broad and context-free, observability is nearly absent, concurrency safety is ignored, and external call resilience doesn't exist. These gaps cluster around production survivability rather than correctness.

**Current state:**
- 5+ bare `except Exception:` blocks across critical paths (checkout, auth, DB operations)
- No request tracing — impossible to correlate logs across a request lifecycle
- Global mutable state accessed without locks (JWKS cache)
- Stock decrement vulnerable to TOCTOU race condition
- FTS5 search accepts raw user input including operators
- Background tasks cancelled without awaiting completion

## Goals / Non-Goals

**Goals:**
- Every exception in the codebase is caught specifically, logged with context, and chained properly
- Any production request can be traced end-to-end via correlation ID
- Concurrent access to shared state is thread-safe
- External service failures degrade gracefully instead of cascading
- User input to FTS5 is sanitized against operator injection
- All magic numbers extracted to named constants
- Frontend state remains consistent when API calls fail

**Non-Goals:**
- Full APM/metrics integration (Prometheus, Datadog) — out of scope, future work
- Distributed tracing (OpenTelemetry spans) — overkill for single-VPS deployment
- Retry logic for SQLite operations — WAL mode handles this; retries would mask bugs
- Refactoring the service layer pattern itself — it's sound
- Adding a proper ORM — SQLite direct access is intentional and performant
- Changing the error response shape — existing `{error: {code, message, details}}` is fine

## Decisions

### 1. Structured logging: `structlog` with JSON output

**Decision:** Use `structlog` configured with JSON renderer for production and colored console for development.

**Why not stdlib `logging`?** stdlib requires manual `extra={}` dict management, doesn't bind context automatically, and JSON formatting needs a separate library anyway. `structlog` gives us context binding (attach `request_id` once, it appears in all subsequent logs) with zero runtime overhead difference.

**Why not `loguru`?** `loguru` is opinionated about output format and doesn't integrate cleanly with FastAPI's existing uvicorn logger. `structlog` wraps stdlib loggers, so uvicorn/SQLite logs get the same request-ID enrichment.

### 2. Request-ID propagation via middleware + contextvars

**Decision:** A new `RequestIdMiddleware` generates a UUID4 per request (or reads `X-Request-ID` header if present), stores it in a `contextvar`, and `structlog` processors automatically include it.

**Why contextvars over `request.state`?** Services don't have access to the request object. With contextvars, any code in the call stack gets the request ID without threading it through function parameters.

### 3. Circuit breaker: Simple in-process implementation (no library)

**Decision:** A lightweight `CircuitBreaker` class (~50 lines) with three states: CLOSED → OPEN → HALF_OPEN. Tracks failure count and last failure time.

**Why not `pybreaker` or `tenacity`?** We have exactly one external call (Google OAuth). A full library adds a dependency for a single use site. The implementation is trivial: track consecutive failures, trip after N failures in M seconds, half-open after cooldown.

**Parameters:** 3 failures in 30s → open for 60s → half-open allows 1 probe request.

### 4. FTS5 sanitization: Quote-wrap user tokens

**Decision:** Split user input on whitespace, wrap each token in double quotes, rejoin. This prevents FTS5 operator interpretation while preserving multi-word search.

**Why not a blocklist of operators?** Blocklists are fragile — FTS5 has many operators (`NEAR`, `*`, `^`, column filters). Quoting is a positive-security model: only literal text matches are possible.

**Example:** `lavender OR *` → `"lavender" "OR" "*"` (searches for literal words).

### 5. Stock race condition: `BEGIN IMMEDIATE` + retry

**Decision:** The checkout transaction uses `BEGIN IMMEDIATE` to acquire a write lock at transaction start (not at first write statement). If another transaction holds the lock, SQLite returns `SQLITE_BUSY` immediately rather than silently queuing.

**Why not `SERIALIZABLE` isolation?** SQLite doesn't support isolation levels in the PostgreSQL sense. `BEGIN IMMEDIATE` is the correct SQLite mechanism for "I intend to write — lock now."

### 6. JWKS cache: `threading.Lock` with double-checked locking

**Decision:** Add a `threading.Lock` to `_JwksCache`. Use double-checked locking pattern: check staleness outside lock, re-check inside lock before fetching.

**Why not `asyncio.Lock`?** The JWKS cache is accessed from sync code paths (JWT validation in dependencies). An asyncio lock would require making the entire validation chain async. A threading lock is simpler and correct for the use case.

### 7. Constants extraction: Single `app/constants.py` module

**Decision:** All cross-module constants (datetime format, pagination limits, price bounds) live in one file. Module-specific constants (like a regex pattern used only in session middleware) stay in their module.

**Rule:** If a value appears in 2+ files, it moves to `constants.py`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `structlog` adds a dependency | Lightweight (no C extensions), well-maintained, 10k+ GitHub stars. Pin version. |
| Request-ID middleware adds latency | UUID4 generation is ~1μs. Negligible vs 200ms response target. |
| Circuit breaker could lock out logins during transient Google outage | 60s cooldown is short; half-open state probes recovery. Admin can still auth via API key. |
| FTS5 quoting changes search behavior for power users | We have no power users — this is a candle shop. Literal search is correct behavior. |
| `BEGIN IMMEDIATE` increases lock contention under high concurrency | Single-VPS deployment with <100 concurrent users. Lock hold time is <10ms (just stock decrement). SQLite WAL handles readers during write lock. |
| Double-checked locking is subtle | Pattern is well-established. Add a comment explaining the invariant. Test with concurrent access in CI. |

## Migration Plan

This change is purely additive/internal — no API contract changes, no data migrations.

1. **Phase 1** — Foundation: Add `structlog`, `app/constants.py`, request-ID middleware. All existing code continues working.
2. **Phase 2** — Error handling sweep: Replace bare excepts file-by-file. Each file is independently deployable.
3. **Phase 3** — Concurrency fixes: JWKS lock, BEGIN IMMEDIATE. Both are backward-compatible.
4. **Phase 4** — Resilience: Circuit breaker for OAuth. Degraded path (error message) already exists.
5. **Phase 5** — Frontend: CartContext rollback. Independent of backend changes.

**Rollback:** Revert the commit. No database changes, no config changes, no external service dependencies.

## Open Questions

- Should structured logs go to stdout (let systemd/journald handle rotation) or to a file with rotation? **Leaning:** stdout — simpler, matches 12-factor app principles, systemd already captures it.
- Should the circuit breaker state be observable via admin API endpoint? **Leaning:** Yes, cheap to add, useful for debugging "why can't anyone log in?"
