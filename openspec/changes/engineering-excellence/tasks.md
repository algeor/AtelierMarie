<!-- Execution model: Wave 1 is sequential (foundation). Wave 2 runs 5 agents in parallel. Wave 3 verifies. -->

## Wave 1 — Foundation + Test Infrastructure (Sequential)

> Execute in order. Creates shared infrastructure that Wave 2 depends on.

### 1.1 Linting Cleanup

- [ ] 1.1.1 Run `ruff check --fix .` to auto-fix I001 (unsorted imports) and W292 (missing EOF newline)
- [ ] 1.1.2 Run `ruff format .` to reformat all files with formatting violations
- [ ] 1.1.3 Manually wrap remaining E501 lines (long strings, docstrings, inline dicts) to ≤100 chars
- [ ] 1.1.4 Verify `ruff check .` and `ruff format --check .` both pass with zero violations

### 1.2 Constants & Dependencies

- [ ] 1.2.1 Create `app/constants.py` with all shared constants: `SQLITE_DATETIME_FORMAT`, `SESSION_MAX_AGE_DAYS`, `SESSION_ABSOLUTE_LIFETIME_DAYS`, `SESSION_SLIDING_THRESHOLD_DAYS`, `MAX_PAGE`, `MAX_LIMIT`, `MAX_PRICE_CENTS`, `MAX_STOCK`
- [ ] 1.2.2 Add `structlog` to pyproject.toml dependencies
- [ ] 1.2.3 Replace inline magic numbers in `app/config.py`, `app/middleware/session.py`, and service files with imports from `app/constants.py`

### 1.3 Test Infrastructure — Core Fixtures

- [ ] 1.3.1 Add `monkeypatch_module` fixture (module-scoped `pytest.MonkeyPatch`)
- [ ] 1.3.2 Add `FakeSessionMiddleware` class that stamps `request.state.session_id` without DB
- [ ] 1.3.3 Rewrite `app` fixture to module scope with `tmp_path_factory` and `FakeSessionMiddleware`
- [ ] 1.3.4 Add `_clean_tables` autouse function-scoped fixture (DELETE in FK-safe order after each test)
- [ ] 1.3.5 Rewrite `client` fixture to module scope (shares module-scoped app)
- [ ] 1.3.6 Rewrite `db` fixture to module scope (raw connection to module-scoped DB file)

### 1.4 Test Infrastructure — Shared Helpers

- [ ] 1.4.1 Add `make_session(conn, session_id=None)` helper function
- [ ] 1.4.2 Add `seed_products(conn, products=None)` helper with DEFAULT_PRODUCTS list
- [ ] 1.4.3 Add module-scoped `admin_client` fixture (AsyncClient with Bearer auth header)
- [ ] 1.4.4 Add module-scoped `service_db` fixture for service-layer tests (raw connection, no app)

### 1.5 Migrate Service Tests

- [ ] 1.5.1 Refactor `test_product_service.py` — use `service_db` + `seed_products()` + `_clean_tables`
- [ ] 1.5.2 Refactor `test_cart_service.py` — replace `cart_db` with `service_db` + helpers
- [ ] 1.5.3 Refactor `test_order_service.py` — replace local `conn` fixture with `service_db` + helpers

### 1.6 Migrate Route Tests

- [ ] 1.6.1 Refactor `test_product_routes.py` — use module-scoped `app`/`client`, remove local `_products` fixture
- [ ] 1.6.2 Refactor `test_cart_routes.py` — use module-scoped `client`, replace `_seed_products` with `seed_products()`
- [ ] 1.6.3 Refactor `test_order_routes.py` — remove `order_app`/`order_client`/`order_session_id`, use shared fixtures + helpers
- [ ] 1.6.4 Refactor `test_admin_routes.py` — remove local `admin_app`/`admin_client`, use shared `admin_client`
- [ ] 1.6.5 Refactor `test_day6_admin_dashboard.py` — remove duplicated fixtures, use shared fixtures
- [ ] 1.6.6 Refactor `test_integration.py` — use module-scoped fixtures + helpers
- [ ] 1.6.7 Refactor `test_routers.py` — use module-scoped `client`

### 1.7 Migrate Remaining Tests

- [ ] 1.7.1 Refactor `test_database.py` — use `service_db` fixture
- [ ] 1.7.2 Refactor `test_database_constraints.py` — use `service_db` fixture
- [ ] 1.7.3 Refactor `test_auth.py` — use module-scoped app + helpers for user/session setup
- [ ] 1.7.4 Refactor `test_health.py` — use module-scoped `client`
- [ ] 1.7.5 Refactor `test_lifespan.py` — keep function-scoped (tests app startup/shutdown directly)

### 1.8 Session Tests (Preserve)

- [ ] 1.8.1 Verify `test_session.py` still uses function-scoped real middleware (add comment header)
- [ ] 1.8.2 Verify `test_session_hardened.py` still uses function-scoped real middleware (add comment header)

### 1.9 Wave 1 Gate

- [ ] 1.9.1 Run `pytest` — all existing tests pass
- [ ] 1.9.2 Confirm test wall-clock time ≥5× faster than baseline

---

## Wave 2 — Parallel Production Changes (5 independent agents)

> All agents run simultaneously. Each touches distinct files. Depends on Wave 1 completing.

### Agent A: Structured Logging + Error Handling

> Files: `app/logging_config.py` (new), `app/middleware/request_id.py` (new), `app/main.py`, `app/database.py`, `app/middleware/session.py`, `app/services/cart_service.py`, `app/services/auth_service.py`, `app/routes/admin.py`

- [ ] A.1 Create `app/logging_config.py` — structlog configuration (JSON prod, colored dev, request_id processor)
- [ ] A.2 Create `app/middleware/request_id.py` — RequestIdMiddleware (UUID4 per request, reads `X-Request-ID`, contextvar, response header)
- [ ] A.3 Wire request-ID middleware into `app/main.py` (before session middleware)
- [ ] A.4 Initialize structlog in app lifespan (based on `settings.environment`)
- [ ] A.5 Replace `import logging` / `logging.getLogger()` with `structlog.get_logger()` across codebase
- [ ] A.6 Replace bare `except Exception:` in `app/database.py` — catch `sqlite3.IntegrityError`, `sqlite3.OperationalError` separately
- [ ] A.7 Replace bare `except Exception:` in `app/middleware/session.py` — specific DB error catches
- [ ] A.8 Replace bare `except Exception:` in `app/services/cart_service.py` — specific catches, chain with `from e`
- [ ] A.9 Replace bare `except Exception:` in `app/services/auth_service.py` — catch `httpx.HTTPError`, `jwt.PyJWTError` separately
- [ ] A.10 Fix CSV import error handling in `app/routes/admin.py` — specific catches
- [ ] A.11 Add structured logging to all catch blocks (operation context, entity IDs, exc_type)

### Agent B: Concurrency + Sanitization + Resilience

> Files: `app/services/auth_service.py` (JWKS lock only), `app/services/order_service.py` (checkout), `app/services/product_service.py` (FTS5 + search rewrite), `app/utils/circuit_breaker.py` (new), `app/routes/admin.py` (CSV bounds + health endpoint)

- [ ] B.1 Add `threading.Lock` to `_JwksCache` with double-checked locking pattern
- [ ] B.2 Change checkout in `order_service.py` to use `BEGIN IMMEDIATE`
- [ ] B.3 Fix background task lifecycle in `app/main.py` — cancel + await with 5s timeout, catch `CancelledError`
- [ ] B.4 Create FTS5 sanitization helper — quote-wrap each token, handle empty/whitespace input
- [ ] B.5 Apply sanitization to `search_products()` before FTS5 query
- [ ] B.6 Rewrite `search_products()` to push category/stock filters + LIMIT/OFFSET into SQL (not in-memory)
- [ ] B.7 Add pagination clamping to `list_products()`, `list_orders()` — cap page at MAX_PAGE, limit at MAX_LIMIT
- [ ] B.8 Add `MAX_PRICE_CENTS` and `MAX_STOCK` validation to CSV import
- [ ] B.9 Create defensive row-access helper for service-layer transformations
- [ ] B.10 Create `app/utils/circuit_breaker.py` — CLOSED/OPEN/HALF_OPEN states (3 failures/30s → open 60s)
- [ ] B.11 Integrate circuit breaker wrapping Google OAuth HTTP calls (token exchange, JWKS fetch)
- [ ] B.12 Add `GET /v1/admin/health/oauth` admin endpoint exposing circuit breaker state
- [ ] B.13 HTTP 4xx from Google does NOT count toward failure threshold (only 5xx and timeouts)

### Agent C: Backend Deduplication + Query Optimization

> Files: `app/models/products.py`, `app/routes/auth.py`, `app/routes/orders.py`, `app/routes/products.py`, `app/services/order_service.py` (list_orders only), `app/dependencies/session.py` (new)

- [ ] C.1 Create `_ProductFieldValidators` mixin in `app/models/products.py` with shared validators
- [ ] C.2 Refactor `CreateProductRequest` and `UpdateProductRequest` to inherit mixin
- [ ] C.3 Create `_unauthorized(message)` helper in `app/routes/auth.py`, replace inline JSONResponse blocks
- [ ] C.4 Create `get_session_user_id` FastAPI dependency in `app/dependencies/session.py`
- [ ] C.5 Refactor `app/routes/orders.py` to use `get_session_user_id` dependency
- [ ] C.6 Extract `_build_field_map(data)` helper in `product_service.py` for upsert/update
- [ ] C.7 Remove redundant `limit = min(limit, 100)` from `app/routes/products.py` and `app/routes/admin.py`
- [ ] C.8 Refactor list endpoints to use `PaginationParams` from `app/models/common.py`
- [ ] C.9 Refactor `list_orders` to batch-fetch order items with `WHERE order_id IN (...)`
- [ ] C.10 Refactor `list_orders_admin` similarly
- [ ] C.11 Refactor CSV import to pre-fetch existing product IDs in one batch query
- [ ] C.12 Convert order route handlers from `def` to `async def`

### Agent D: Frontend (Performance + Deduplication + Conventions)

> Files: `frontend/contexts/`, `frontend/hooks/` (new), `frontend/lib/constants.ts`, `frontend/components/`, `frontend/app/checkout/`, `frontend/app/account/`

- [ ] D.1 Wrap AuthContext provider `value` in `useMemo` with appropriate dependency array
- [ ] D.2 Wrap CartContext provider `value` in `useMemo` with appropriate dependency array
- [ ] D.3 Refactor `AdminProvider` to consume `useAuth()` instead of calling `getCurrentUser()`
- [ ] D.4 Create `frontend/hooks/useAddToCart.ts` — idle→loading→success→reset state machine
- [ ] D.5 Refactor `AddToCartButton` to use `useAddToCart` hook
- [ ] D.6 Refactor `AddToCartSection` to use `useAddToCart` hook
- [ ] D.7 Create `ORDER_STATUS_STYLES` constant in `frontend/lib/constants.ts`
- [ ] D.8 Refactor `OrderStatusBadge` and admin orders to use shared constant
- [ ] D.9 Replace inline button classes with `Button` component in orders/account/callback pages
- [ ] D.10 Replace raw `<img>` with `next/image` in `UserMenu.tsx` (+ configure remotePatterns)
- [ ] D.11 Replace raw `<img>` with `next/image` in `app/account/page.tsx`
- [ ] D.12 Refactor `StatusTimeline.tsx` to use `cn()` utility
- [ ] D.13 Replace hand-rolled inputs in checkout with `Input` component
- [ ] D.14 Add rollback logic to CartContext — store prev state, revert on API failure

### Agent E: New Hardening Tests

> Files: `tests/test_sanitization.py`, `tests/test_circuit_breaker.py`, `tests/test_pagination.py`, `tests/test_concurrency.py`, `tests/test_request_id.py` (all new)

- [ ] E.1 Write tests for FTS5 sanitization (operators, wildcards, empty input, normal queries)
- [ ] E.2 Write tests for circuit breaker state transitions (CLOSED→OPEN→HALF_OPEN→CLOSED, timeout counting, 4xx exclusion)
- [ ] E.3 Write tests for pagination clamping (extreme values, boundary values, normal values)
- [ ] E.4 Write test for BEGIN IMMEDIATE race condition (simulate concurrent checkout)
- [ ] E.5 Write test for JWKS cache thread safety (concurrent access during refresh)
- [ ] E.6 Write test for background task graceful shutdown
- [ ] E.7 Write tests for CSV import value bounds (extreme price, negative stock, boundary values)
- [ ] E.8 Write test for request-ID middleware (generation, passthrough, invalid header)

---

## Wave 3 — Verification (Sequential, after all Wave 2 agents complete)

- [ ] 3.1 Resolve any merge conflicts between agents (see conflict matrix in design.md)
- [ ] 3.2 Run `ruff check . && ruff format --check .` — zero violations
- [ ] 3.3 Run full `pytest` — all tests pass (fast, thanks to Wave 1)
- [ ] 3.4 Run frontend tests — `cd frontend && npx vitest run`
- [ ] 3.5 Smoke test: `uvicorn app.main:app` starts without import errors