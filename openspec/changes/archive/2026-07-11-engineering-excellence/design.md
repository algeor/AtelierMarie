## Context

AtelierMarie is a luxury candle e-commerce platform (FastAPI + SQLite backend, Next.js 14 frontend) with solid architectural foundations. Three independent reviews identified systematic gaps that cluster into: test infrastructure performance (294 tests bottlenecked by per-test DB/app setup), operational hardening (bare exceptions, no observability, race conditions, injection vectors), and code quality debt (N+1 queries, duplication, lint violations). The codebase is small (~30 Python modules, ~50 frontend files) making this the ideal time to address all three before they compound in production.

**Current state:**
- Every test spins up a fresh `init_db()` + `create_app()` + real session middleware DB round-trip
- 5+ bare `except Exception:` blocks across critical paths
- No request tracing or structured logging
- JWKS cache accessed without locks; checkout has TOCTOU race condition
- FTS5 search accepts raw user input including operators
- N+1 query patterns (41 queries per page-load in order listing)
- 46 ruff lint violations; duplicated validators, constants, and UI patterns

## Goals / Non-Goals

**Goals:**
- Reduce test wall-clock time by ~10× via module-scoped fixtures and mocked middleware
- Every exception caught specifically, logged with context, and chained properly
- Any request traceable end-to-end via correlation ID (structured logging)
- Concurrent access to shared state is thread-safe
- External service failures degrade gracefully (circuit breaker)
- FTS5 input sanitized; all queries meet <200ms target
- Zero ruff violations; single-source-of-truth for all duplicated code
- Full backward compatibility — no API changes, all tests pass

**Non-Goals:**
- Full APM/metrics integration (Prometheus, Datadog)
- Distributed tracing (OpenTelemetry spans) — overkill for single-VPS
- Retry logic for SQLite operations — WAL mode handles this
- Changing production APIs, database schema, or service layer pattern
- Switching test frameworks or reducing coverage
- Introducing an ORM

## Decisions

### 1. Test infrastructure: Module-scoped fixtures with per-test cleanup

**Choice:** `scope="module"` for `app`, `client`, and `db` fixtures. Each test cleans up via `DELETE FROM` tables in FK-safe order.

**Why:** `init_db()` + `create_app()` runs 18 times (per file) instead of 294 times (per test). Isolation maintained via autouse cleanup fixture.

**Alternative:** SAVEPOINT/ROLLBACK per test. Rejected — impossible because `get_db()` creates new connections that auto-commit.

### 2. Mock session middleware for route tests

**Choice:** `FakeSessionMiddleware` (no-op `BaseHTTPMiddleware`) stamps `request.state.session_id` without DB or cookie logic. Session tests keep real middleware.

**Why:** Real middleware does a full DB round-trip per request. In route tests we test route/service behavior, not session creation. Session tests validate the real middleware independently.

### 3. Structured logging: `structlog` with JSON output + Request-ID via contextvars

**Choice:** `structlog` with JSON renderer (production) / colored console (dev). A `RequestIdMiddleware` generates UUID4 per request, stores it in a `contextvar`. All logs automatically include the request ID.

**Why not stdlib logging?** Requires manual `extra={}` dict management. **Why contextvars over request.state?** Services don't have access to the request object.

### 4. Circuit breaker: Simple in-process implementation

**Choice:** Lightweight `CircuitBreaker` class (~50 lines): CLOSED → OPEN → HALF_OPEN. 3 failures in 30s → open for 60s → half-open allows 1 probe.

**Why no library?** We have exactly one external call (Google OAuth). A 50-line class is simpler than a dependency for a single use site.

### 5. FTS5 sanitization: Quote-wrap user tokens

**Choice:** Split input on whitespace, wrap each token in double quotes, rejoin. Prevents operator interpretation while preserving multi-word search.

**Why not a blocklist?** Blocklists are fragile — FTS5 has many operators. Quoting is a positive-security model.

### 6. Stock race condition: `BEGIN IMMEDIATE`

**Choice:** Checkout transaction uses `BEGIN IMMEDIATE` to acquire write lock at start. SQLite returns `SQLITE_BUSY` immediately if another transaction holds the lock.

**Why?** Prevents TOCTOU where two checkouts read same stock, both decrement.

### 7. JWKS cache: `threading.Lock` with double-checked locking

**Choice:** Add `threading.Lock` to `_JwksCache`. Check staleness outside lock, re-check inside before fetching.

**Why not asyncio.Lock?** JWKS cache accessed from sync code paths (JWT validation in dependencies).

### 8. Batch order-item fetch: `WHERE order_id IN (...)`

**Choice:** Replace per-order `_fetch_order_with_items` loop with a single batch query + Python grouping. Two queries (orders + items) instead of N+1.

**Why not JOINs?** Duplicate order rows per item complicate pagination. Two queries is simpler.

### 9. Push FTS5 filters into SQL

**Choice:** `SELECT ... WHERE id IN (SELECT rowid FROM products_fts WHERE ... MATCH ?) AND category = ? AND stock > 0 LIMIT ? OFFSET ?`

**Why:** Eliminates fetching all FTS5 results into Python memory for post-filtering.

### 10. Validator mixin for product models

**Choice:** `_ProductFieldValidators` mixin class with shared `@field_validator` methods. Both Create and Update request models inherit it.

**Why not standalone functions?** Pydantic v2 field validators must live on a class.

### 11. `useMemo` for React context values

**Choice:** Wrap context `value` objects in `useMemo` with explicit dependency arrays in AuthContext and CartContext.

**Why not useReducer?** State shape is fine; the issue is reference stability.

### 12. Shared constants: Single `app/constants.py` module

**Choice:** All cross-module constants (`SQLITE_DT_FMT`, pagination limits, price bounds, session expiry) in one file. Module-specific constants stay local.

**Rule:** If a value appears in 2+ files, it moves to `constants.py`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Module-scoped test fixtures allow test-order coupling | Autouse `_clean_tables` fixture deletes rows after every test in FK-safe order |
| `structlog` adds a dependency | Lightweight, well-maintained, no C extensions. Pin version. |
| Circuit breaker could lock out logins during transient outage | 60s cooldown is short; half-open probes recovery. Admin still has API key auth. |
| FTS5 quoting changes search behavior | No power users — literal search is correct for a candle shop. |
| `BEGIN IMMEDIATE` increases lock contention | Single-VPS, <100 concurrent users, lock hold <10ms. WAL handles readers. |
| Large `IN (...)` clause for order items | Bounded by pagination (max 100 orders per page). |
| Mock middleware drift vs real middleware | Session tests still test real middleware; any regression surfaces there. |
| `useMemo` dependency arrays may be incomplete | Enable exhaustive-deps ESLint rule. |

## Migration Plan

All changes are additive/internal — no API contract changes, no data migrations, no schema changes.

**Phase A — Test infrastructure** (independent of production code):
Module-scoped fixtures, mock middleware, shared helpers. Existing tests refactored.

**Phase B — Foundation** (production code, non-breaking):
`app/constants.py`, `structlog` + request-ID middleware, shared validators/helpers.

**Phase C — Hardening sweep** (file-by-file):
Replace bare excepts, add service-layer logging, FTS5 sanitization, JWKS lock, BEGIN IMMEDIATE, circuit breaker.

**Phase D — Performance & quality**:
Batch queries, push SQL filters, frontend memoization, hook extraction, deduplication.

**Phase E — Linting**:
`ruff check --fix && ruff format`. Run full test suite after.

**Rollback:** Revert commits. No database changes, no external dependencies beyond `structlog`.
