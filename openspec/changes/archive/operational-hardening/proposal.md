## Why

The codebase has solid architecture (layer separation, service pattern, Pydantic validation) but lacks operational hardening — the defensive patterns that prevent production incidents. Bare exception catches hide root causes, missing observability makes debugging impossible, race conditions risk data corruption in checkout, and an FTS5 injection vector is a security hole. These are the gaps a senior reviewer would flag as "this shouldn't ship."

## What Changes

- Replace all bare `except Exception:` blocks with specific exception types, proper chaining (`from e`), and contextual logging
- Add structured logging with request-ID correlation across the entire request lifecycle
- Fix FTS5 query injection by escaping user input operators
- Add `threading.Lock` to the JWKS cache for thread safety
- Use `BEGIN IMMEDIATE` in checkout to prevent stock race conditions
- Properly await background task cancellation on shutdown
- Add circuit breaker / retry logic for Google OAuth external calls
- Add defensive data access patterns (safe row access, pagination caps, CSV validation bounds)
- Extract duplicated constants into `app/constants.py`
- Fix frontend optimistic update rollback in CartContext

## Capabilities

### New Capabilities
- `structured-logging`: Request-ID middleware, structured log formatter, service-layer logging at all critical paths
- `error-handling-hardening`: Specific exception catches, proper chaining, contextual error messages across all services
- `concurrency-safety`: Thread-safe JWKS cache, BEGIN IMMEDIATE transactions, proper async task lifecycle
- `input-sanitization`: FTS5 query escaping, pagination caps, CSV import value bounds
- `external-call-resilience`: Circuit breaker pattern for Google OAuth, timeout retry with backoff

### Modified Capabilities
- `session-lifecycle`: Background cleanup task properly awaited on shutdown; session constants extracted
- `product-service`: FTS5 search input escaped; row access made defensive
- `checkout-flow`: Stock decrement uses BEGIN IMMEDIATE; exception handling made specific

## Impact

- **Backend code**: All files in `app/services/`, `app/routes/`, `app/middleware/`, `app/main.py`, `app/database.py`
- **New files**: `app/constants.py`, `app/middleware/request_id.py`, `app/utils/circuit_breaker.py`
- **New dependency**: `structlog` (structured logging library)
- **Frontend**: `frontend/contexts/CartContext.tsx` (rollback logic)
- **APIs**: No breaking changes — error response bodies may include more detail but shape unchanged
- **Tests**: New tests for circuit breaker, FTS5 escaping, race condition scenarios
