## 1. Error Handling Foundation

- [ ] 1.1 Define `ServiceError` base exception class in `app/exceptions.py` with class-level `status_code: int = 500`, `error_code: str = "INTERNAL_ERROR"` and instance-level `message: str`, `details: dict | None` set via `__init__(self, message: str, details: dict | None = None)`. All service exceptions inherit from it: ProductNotFoundError (404/NOT_FOUND), InsufficientStockError (409/INSUFFICIENT_STOCK), InvalidStateTransitionError (422/INVALID_STATE_TRANSITION), CartFullError (409/CART_FULL), QuantityLimitError (422/QUANTITY_LIMIT_EXCEEDED), OrderNotFoundError (404/NOT_FOUND), AuthenticationError (401/UNAUTHORIZED)
- [ ] 1.2 Register custom exception handler for `RequestValidationError` in `app/main.py` that formats Pydantic errors into `ErrorResponse` envelope with `details.fields` array. Parse `error['loc']` to include source location (body/query/path) in each field error for client clarity.
- [ ] 1.3 Register custom exception handler for `HTTPException` in `app/main.py` that wraps into `ErrorResponse` envelope. Rule: if `detail` is a dict with BOTH `code`+`message` keys, extract into envelope (remaining keys → `details`); if dict lacks those keys, derive code from status via `http.HTTPStatus(status_code).phrase.upper().replace(' ', '_')`, use generic message, put entire dict in `details`; if `detail` is a string, use status-derived code and string as message
- [ ] 1.4 Register single exception handler for `ServiceError` base class that reads `status_code`, `error_code`, `message`, `details` from the exception instance
- [ ] 1.5 Register catch-all exception handler for unhandled exceptions: (1) Log the full exception with traceback at ERROR level via `logger.exception()`, (2) Return 500 with safe `{"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred", "details": null}}`. Response MUST NOT contain exception details; server logs MUST contain them.
- [ ] 1.6 Write tests for all exception handlers (validation error, HTTP exception with string detail, HTTP exception with dict detail, service exception, unhandled exception). For the unhandled exception test, assert that the response body does NOT contain the original exception message, class name, or traceback lines. Also verify that `ProductNotFoundError` (ServiceError subclass) routes to the ServiceError handler (returns 404), not the generic Exception catch-all (500).
- [ ] 1.7 Verify existing `admin_api_key` length check in `app/config.py` (already implemented at lines 51-55). Add test to `tests/test_config.py` asserting that `Settings(environment="production", admin_api_key="short", ...)` raises ValueError containing "32 characters".

## 2. Input Validation Hardening

- [ ] 2.1 Update `app/models/products.py`: add `Field()` constraints — `name` (min_length=1, max_length=200, already present), `id` (min_length=3, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$" — tightens existing min_length=1; safe pre-production, verified no test fixtures use IDs shorter than 3 chars), `price_cents` (already has gt=0; add upper bound le=9999999), `description` (max_length=5000, already present), `category` (max_length=100), `stock` (ge=0, le=1000000)
- [ ] 2.2 Add `@field_validator("name", mode="before")` to `CreateProductRequest` AND `UpdateProductRequest` that type-guards before stripping: `if isinstance(value, str): return value.strip(); return value`. This lets Pydantic handle type errors naturally while stripping whitespace for valid strings. Then `min_length=1` catches empty/whitespace-only results. Do NOT add to response models.
- [ ] 2.3 Update `app/models/cart.py`: `AddToCartRequest.quantity` (ge=1, le=10 — already correct), `UpdateCartItemRequest.quantity` (ge=0, le=10 — already correct), `product_id` (min_length=1, max_length=100). Note: Pydantic models already have le=10; the DB constraint (le=99) is fixed in task 2.7.
- [ ] 2.4 Update `app/models/orders.py`: add `Field()` constraints — `customer_email: EmailStr = Field(..., max_length=320)` (EmailStr already validates format; explicit max_length for OpenAPI docs and defense-in-depth), `customer_name` (min_length=1, max_length=200 — reject empty/whitespace if provided), `shipping_address` (max_length=1000), `notes` (max_length=2000). Apply whitespace-stripping validator to `customer_name`.
- [ ] 2.5 Verify `app/models/common.py` pagination params already have ge/le constraints (page≥1, limit 1-100)
- [ ] 2.6 Write tests for validation edge cases: empty strings, whitespace-only (tabs, newlines, mixed Unicode whitespace), negative values, boundary values (N-1/N/N+1 for all max_length fields: name 199/200/201, description 4999/5000/5001, product_id 3-char accepted/2-char rejected, price_cents 9999999 accepted/10000000 rejected, stock 1000000 accepted/1000001 rejected), oversized strings, quantity 0 on update (remove semantic), consecutive-hyphen slugs rejected, non-string types passed to name validator (int, null, array → 422 not 500)
- [ ] 2.7 Update `app/database.py` cart_items CHECK constraint from `CHECK (quantity >= 1 AND quantity <= 99)` to `CHECK (quantity >= 1 AND quantity <= 10)` to align with Pydantic validation (defense-in-depth). Add test verifying direct SQL INSERT with quantity=11 is rejected by DB.

## 3. Admin Dashboard Endpoint

- [ ] 3.1 Create `app/services/admin_service.py` with `get_dashboard_stats(conn)` function that runs aggregate queries. Use `COALESCE(SUM(total_cents), 0)` to handle empty tables. Revenue/count excludes cancelled; orders_by_status includes all statuses.
- [ ] 3.2 Create `DashboardResponse` Pydantic model in `app/models/admin.py` with fields: `total_orders: int`, `total_revenue_cents: int`, `total_products: int`, `carts_with_items: int`, `orders_by_status: dict[OrderStatus, int] = Field(default_factory=dict)` (use OrderStatus Literal as key type for type safety), `computed_at: str` (ISO 8601 timestamp)
- [ ] 3.3 Rename existing `GET /v1/admin/stats` stub to `GET /v1/admin/dashboard` in `app/routes/admin.py`. Update `tests/test_routers.py` to reference `/v1/admin/dashboard`. Implement with `require_admin` dependency, calling the admin service. Add `Cache-Control: no-store` response header (prevents caching; admin always sees fresh stats).
- [ ] 3.4 Add indexes to `app/database.py` schema: `CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)` and `CREATE INDEX IF NOT EXISTS idx_cart_items_session ON cart_items(session_id)`
- [ ] 3.5 Write tests for dashboard: empty DB (returns zeros/empty dict), normal data (multiple orders per status aggregate correctly), cancelled orders excluded from revenue but counted in orders_by_status, all orders cancelled (revenue=0, total_orders=0), unauthenticated → 401, non-admin authenticated → 403, admin API key accepted → 200, Cache-Control header present on success response

## 4. Pagination Standardization

- [ ] 4.1 Ensure all list routes accept `page` and `limit` query params using the shared `PageParam`/`LimitParam` types from `app/models/common.py`
- [ ] 4.2 Ensure all list response models follow `{<entity_plural>: [...], total: int, page: int, limit: int}` pattern (entity-specific keys: `products`, `orders`, etc. — matching existing TypeScript types)
- [ ] 4.3 Add `calculate_offset(page: int, limit: int) -> int` helper to `app/models/common.py` (near `PaginationParams`): returns `(page - 1) * limit`. Used by all services for consistent pagination offset.
- [ ] 4.4 Write tests verifying pagination params are validated (page=0 → 422, limit=101 → 422), page beyond available data returns empty items array (not 404), and response shape is correct with entity-specific keys

## 5. API Documentation Polish

- [ ] 5.1 Verify existing `FastAPI()` title/description in `app/main.py` (already configured). Keep `version="0.1.0"` (do not bump to 1.0.0 until production launch). Optionally expand description.
- [ ] 5.2 Verify router-level tags in `app/main.py` use consistent casing (currently lowercase: "products", "cart", etc.). Do NOT add per-route `tags=` (redundant with router-level). Add `summary` and `description` to all product route decorators.
- [ ] 5.3 Add `summary`, `description` to all cart route decorators (no per-route tags needed)
- [ ] 5.4 Add `summary`, `description` to all order route decorators (no per-route tags needed)
- [ ] 5.5 Add `summary`, `description` to all auth route decorators (no per-route tags needed)
- [ ] 5.6 Add `summary`, `description` to all admin route decorators (no per-route tags needed)
- [ ] 5.7 Add `responses={...}` kwarg to all routes documenting error status codes with `ErrorResponse` model
- [ ] 5.8 Add `response_model` to all route decorators for success responses
- [ ] 5.9 Verify `/docs` renders correctly with all tags, descriptions, and response schemas

## 6. Nginx Rate Limiting Configuration

- [ ] 6.1 Create `deploy/nginx-rate-limit.conf` with `limit_req_zone` for: auth (5r/m per IP, burst=5 nodelay), checkout (10r/m per session cookie using `map $cookie_session_id $rate_limit_key { "" $binary_remote_addr; default $cookie_session_id; }` — cookieless requests fall back to IP-based limiting instead of sharing one bucket), checkout IP backstop (30r/m per IP), admin (30r/m per IP, burst=10)
- [ ] 6.2 Add location-specific `limit_req` directives: `nodelay` for auth (instant retries expected), NO `nodelay` for checkout (gradual consumption — prevents 11 instant orders from one session), `nodelay` for admin
- [ ] 6.3 Configure custom 429 response: `error_page 429 @rate_limited;` with named location that sets `default_type application/json;`, `add_header Retry-After 60;`, and returns static JSON `{"error":{"code":"RATE_LIMITED","message":"Too many requests. Retry after 60 seconds.","details":null}}`
- [ ] 6.4 Document in `deploy/README.md`: (1) how to include nginx-rate-limit.conf in the main Nginx server block, (2) admin API key must be ≥32 characters (already enforced by config.py) — generate with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`, (3) if behind a reverse proxy/load balancer, configure `set_real_ip_from` and `real_ip_header X-Forwarded-For` so rate limiting uses the real client IP

## 7. Integration Verification

- [ ] 7.1 Run full test suite — all existing tests still pass
- [ ] 7.2 Manual smoke test: start server, hit `/docs`, verify API docs render with all groups and descriptions
- [ ] 7.3 Verify error responses from invalid requests match the `ErrorResponse` schema exactly
