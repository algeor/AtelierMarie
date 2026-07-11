## 1. Foundation — Constants & Dependencies

- [ ] 1.1 Create `app/constants.py` with all shared constants: `SQLITE_DATETIME_FORMAT`, `SESSION_MAX_AGE_DAYS`, `SESSION_ABSOLUTE_LIFETIME_DAYS`, `SESSION_SLIDING_THRESHOLD_DAYS`, `MAX_PAGE`, `MAX_LIMIT`, `MAX_PRICE_CENTS`, `MAX_STOCK`
- [ ] 1.2 Add `structlog` to `requirements.txt` / pyproject dependencies
- [ ] 1.3 Replace inline magic numbers in `app/config.py`, `app/middleware/session.py`, and service files with imports from `app/constants.py`

## 2. Structured Logging Infrastructure

- [ ] 2.1 Create `app/logging_config.py` with structlog configuration (JSON renderer for production, colored console for dev, automatic request_id binding via processors)
- [ ] 2.2 Create `app/middleware/request_id.py` — RequestIdMiddleware that generates UUID4 per request (or reads valid `X-Request-ID` header), stores in contextvar, adds to response header
- [ ] 2.3 Wire request-ID middleware into `app/main.py` (before session middleware)
- [ ] 2.4 Initialize structlog in app lifespan (call logging config based on `settings.environment`)
- [ ] 2.5 Replace all `import logging` / `logging.getLogger()` calls with `import structlog` / `structlog.get_logger()` across the codebase

## 3. Error Handling Hardening

- [ ] 3.1 Audit and replace bare `except Exception:` in `app/database.py` — catch `sqlite3.IntegrityError` and `sqlite3.OperationalError` separately with contextual logging
- [ ] 3.2 Replace bare `except Exception:` in `app/middleware/session.py` — specific catches for DB errors, log with session context
- [ ] 3.3 Replace bare `except Exception:` in `app/main.py` background task — catch `asyncio.CancelledError` explicitly, log other errors
- [ ] 3.4 Replace bare `except Exception:` in `app/services/cart_service.py` — catch specific DB errors, chain with `from e`
- [ ] 3.5 Replace bare `except Exception:` in `app/services/auth_service.py` — catch `httpx.HTTPError`, `jwt.PyJWTError`, etc. separately
- [ ] 3.6 Fix CSV import error handling in `app/routes/admin.py` — catch `sqlite3.IntegrityError` and `ValueError` specifically, let unexpected errors propagate
- [ ] 3.7 Add structured logging to all service-layer catch blocks (operation context, entity IDs, exc_type)

## 4. Concurrency Safety

- [ ] 4.1 Add `threading.Lock` to `_JwksCache` in `app/services/auth_service.py` with double-checked locking pattern
- [ ] 4.2 Change checkout transaction in `app/services/order_service.py` to use `BEGIN IMMEDIATE` instead of implicit begin
- [ ] 4.3 Fix background task lifecycle in `app/main.py` — await cancellation with 5s timeout, catch `CancelledError`, log at INFO

## 5. Input Sanitization & Defensive Access

- [ ] 5.1 Create FTS5 sanitization helper in `app/services/product_service.py` — quote-wrap each token, handle empty/whitespace input
- [ ] 5.2 Apply sanitization to `search_products()` before FTS5 query execution
- [ ] 5.3 Add pagination clamping to `list_products()`, `list_orders()`, and any other paginated service functions — cap page at `MAX_PAGE`, limit at `MAX_LIMIT`
- [ ] 5.4 Add `MAX_PRICE_CENTS` and `MAX_STOCK` validation to CSV import in `app/routes/admin.py`
- [ ] 5.5 Create a defensive row-access helper (or use `.get()` with diagnostic error) in service-layer data transformations (`cart_service.py:163-177`)

## 6. External Call Resilience

- [ ] 6.1 Create `app/utils/circuit_breaker.py` — CircuitBreaker class with CLOSED/OPEN/HALF_OPEN states, configurable thresholds (3 failures / 30s → open for 60s)
- [ ] 6.2 Integrate circuit breaker into `app/services/auth_service.py` wrapping Google OAuth HTTP calls (token exchange, JWKS fetch)
- [ ] 6.3 Add `GET /v1/admin/health/oauth` endpoint exposing circuit breaker state (admin-only)
- [ ] 6.4 Ensure HTTP 4xx from Google does NOT count toward circuit breaker failure threshold (only 5xx and timeouts)

## 7. Frontend Fixes

- [ ] 7.1 Add rollback logic to `frontend/contexts/CartContext.tsx` — store previous state before optimistic update, revert on API failure

## 8. Testing

- [ ] 8.1 Write tests for FTS5 sanitization (operators, wildcards, empty input, normal queries)
- [ ] 8.2 Write tests for circuit breaker state transitions (CLOSED→OPEN→HALF_OPEN→CLOSED, timeout counting, 4xx exclusion)
- [ ] 8.3 Write tests for pagination clamping (extreme values, boundary values, normal values)
- [ ] 8.4 Write test for BEGIN IMMEDIATE race condition (simulate concurrent checkout)
- [ ] 8.5 Write test for JWKS cache thread safety (concurrent access during refresh)
- [ ] 8.6 Write test for background task graceful shutdown
- [ ] 8.7 Write tests for CSV import value bounds (extreme price, negative stock, boundary values)
- [ ] 8.8 Write test for request-ID middleware (generation, passthrough, invalid header)
