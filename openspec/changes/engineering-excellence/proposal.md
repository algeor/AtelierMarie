## Why

The codebase has solid architecture but accumulates three categories of technical debt that compound if left unaddressed: (1) a test suite that's unacceptably slow due to per-test DB/app setup, (2) operational gaps — bare exceptions, missing observability, race conditions, injection vectors — that shouldn't ship to production, and (3) code quality issues — N+1 queries, duplication, lint violations, unmemoized contexts — that will degrade performance and maintainability. Tackling all three now, while the codebase is small, prevents compounding debt before it reaches production.

## What Changes

### Test Infrastructure
- Introduce a **no-op session middleware** for route tests (stamps `session_id` without DB round-trip)
- Lift `app`/`client` fixtures to **module scope** (init once per file, not per test)
- Consolidate duplicated fixtures into shared `conftest.py` helpers (`make_session()`, `seed_products()`, `admin_client`)
- Service-layer tests get module-scoped DB with per-test cleanup (DELETE rows)

### Operational Hardening
- Replace bare `except Exception:` with specific types + proper chaining (`from e`)
- Add **structured logging** with request-ID correlation (structlog)
- Fix **FTS5 injection** by escaping user input operators
- Add `threading.Lock` to JWKS cache for thread safety
- Use **BEGIN IMMEDIATE** in checkout to prevent stock race conditions
- Implement **circuit breaker** for Google OAuth (3 failures/30s → open 60s)
- Properly await background task cancellation on shutdown
- Extract constants to `app/constants.py`

### Code Quality
- **Backend queries**: Batch-fetch order items (fix N+1), push filters into FTS5 SQL, batch CSV import lookups
- **Backend deduplication**: Shared constants, validator mixins, response helpers, `get_session_user_id` dependency
- **Frontend performance**: Memoize AuthContext/CartContext values, remove duplicate `getCurrentUser()` in AdminProvider
- **Frontend deduplication**: Extract `useAddToCart` hook, unify status color maps, replace inline styling with components
- **Linting**: Auto-fix all 46 ruff violations and reformat

## Capabilities

### New Capabilities
- `test-fixtures`: Module-scoped app/DB fixtures, mock session middleware, reusable seed helpers, admin/client factories
- `structured-logging`: Request-ID middleware, structured log formatter, service-layer logging at critical paths
- `error-handling-hardening`: Specific exception catches, proper chaining, contextual messages across all services
- `concurrency-safety`: Thread-safe JWKS cache, BEGIN IMMEDIATE transactions, async task lifecycle
- `input-sanitization`: FTS5 query escaping, pagination caps, CSV import bounds
- `external-call-resilience`: Circuit breaker for Google OAuth, timeout retry with backoff
- `backend-query-optimization`: Fix N+1 in order listing, push filters into SQL, batch CSV lookups
- `backend-deduplication`: Extract shared constants, validator mixins, response helpers, FastAPI dependencies
- `frontend-performance`: Memoize context values, remove duplicate fetches
- `frontend-deduplication`: Extract hooks, unify color maps, replace inline styling with shared components
- `linting-cleanup`: Auto-fix ruff violations and reformat all Python files

### Modified Capabilities
- `session-lifecycle`: Background cleanup task properly awaited on shutdown; session constants extracted
- `product-service`: FTS5 search input escaped; row access made defensive
- `checkout-flow`: Stock decrement uses BEGIN IMMEDIATE; exception handling made specific

## Impact

- **Backend**: All files in `app/services/`, `app/routes/`, `app/middleware/`, `app/main.py`, `app/database.py`; new `app/constants.py`, `app/middleware/request_id.py`, `app/utils/circuit_breaker.py`
- **Frontend**: Contexts, components (cart, orders, auth), checkout/orders/admin pages
- **Test infrastructure**: `conftest.py` (major rewrite), all 16 test files except session middleware tests
- **New dependency**: `structlog`
- **APIs**: No breaking changes — error responses may include more detail but shape unchanged
- **Risk**: Module-scoped test fixtures require per-test cleanup; mitigated by explicit cleanup in autouse fixtures
