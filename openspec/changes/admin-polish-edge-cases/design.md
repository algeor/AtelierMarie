## Context

AtelierMarie's backend has its core domain specs defined (product-catalog, session-cart, orders-checkout, auth-image-upload) but all route handlers are still 501 stubs. Before implementing the full service layer, we need the cross-cutting concerns that make the API production-ready: admin dashboard stats, uniform pagination, consistent error handling, input validation hardening, rate limiting, and API documentation.

**Current state:**
- `app/models/common.py` already defines `ErrorResponse` (with `ErrorDetail`) and `PaginationParams`
- All route stubs return the error envelope format (`{error: {code, message, details}}`)
- `app/routes/admin.py` has a `GET /stats` stub
- Database schema has all tables needed for aggregate queries
- No custom exception handlers registered on the app
- No Pydantic field constraints beyond basic types
- No Nginx config exists yet in the repo

**Constraints:**
- All responses <200ms (dashboard is the most complex — simple `COUNT`/`SUM` on indexed tables)
- SQLite only — no background aggregation or materialized views needed at this scale
- No new Python dependencies
- Must not break existing stub responses (additive only)

## Goals / Non-Goals

**Goals:**
- Implement `GET /v1/admin/dashboard` with order/revenue/product aggregates
- Standardize pagination across all list endpoints with consistent response envelope
- Unify all error responses (FastAPI validation, HTTP exceptions, service exceptions) into `ErrorResponse` format
- Harden Pydantic models with field constraints (min/max lengths, value bounds)
- Provide Nginx rate limiting config for auth and checkout
- Polish FastAPI auto-docs with tags, descriptions, and response examples

**Non-Goals:**
- Real-time stats or WebSocket updates for dashboard
- Caching of dashboard queries (unnecessary at <1000 orders)
- Custom API documentation UI (FastAPI's built-in Swagger/ReDoc is sufficient)
- Client-side rate limiting or token bucket in Python (Nginx handles this)
- GraphQL or alternative API formats
- Metrics collection or observability (Layer 2 concern)

## Decisions

### 1. Dashboard endpoint uses raw SQL aggregates (no ORM, no pre-computation)

**Decision:** `GET /v1/admin/dashboard` executes 3-4 simple queries:
```sql
SELECT COUNT(*), COALESCE(SUM(total_cents), 0) FROM orders WHERE status != 'cancelled';
SELECT status, COUNT(*) FROM orders GROUP BY status;
SELECT COUNT(*) FROM products WHERE is_active = 1;
SELECT COUNT(DISTINCT session_id) FROM cart_items;
```

Note: The `cart_items` query counts all sessions with items (including expired sessions). The field is named `carts_with_items` rather than "active_carts" to avoid implying recency. At MVP scale this is acceptable; filtering by session expiry can be added later if needed.

**Alternatives considered:**
- *Pre-computed stats table updated by triggers:* Over-engineered for <1000 rows. Rejected.
- *DuckDB analytics:* This is Layer 1 — dashboard shows operational stats, not analytics. Rejected.

**Rationale:** These queries scan at most a few thousand rows. SQLite returns in <10ms. No caching or pre-computation needed. Keep it simple.

### 2. Custom exception handlers registered on the FastAPI app

**Decision:** Register exception handlers in `app/main.py` for:
- `RequestValidationError` → 422 with `ErrorResponse` envelope (field-level details)
- `HTTPException` → appropriate status with `ErrorResponse` envelope (rule: dict detail with BOTH `code`+`message` keys → extract into envelope, remaining keys → `details`; dict without those keys → derive code from status via `http.HTTPStatus(status_code).phrase.upper().replace(' ', '_')`, put dict in `details`; string detail → use status-derived code and string as message)
- `ServiceError` base class → single handler reads `status_code`, `error_code`, `message`, `details` from the exception instance

All service exceptions inherit from `ServiceError(Exception)` with attributes `status_code: int`, `error_code: str`, `message: str`, `details: dict | None`. This allows a single handler registration instead of one per exception type. Adding future exceptions doesn't require modifying the handler. Do NOT register separate handlers for subclasses — the base handler uses `isinstance` and catches all. Do NOT raise `ServiceError` directly — always raise a specific subclass.

Constructor pattern:
```python
class ServiceError(Exception):
    """Abstract base — do NOT raise directly. Always use a specific subclass."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

class ProductNotFoundError(ServiceError):
    status_code = 404
    error_code = "NOT_FOUND"
```
`status_code` and `error_code` are class-level defaults overridden per subclass; `message` and `details` are instance attributes set via `__init__`. The handler reads `exc.status_code` (finds class attribute) and `exc.message` (finds instance attribute).

**Alternatives considered:**
- *Middleware that catches all exceptions:* Too broad, loses status code context. Rejected.
- *Per-route try/except:* Repetitive, violates DRY. Rejected.
- *Individual handler per exception class:* Works but requires handler registration for every new exception. Rejected in favor of base class.

**Rationale:** FastAPI's exception handler system is designed for this. Register once, applies globally. Routes raise exceptions, handlers format them consistently.

### 3. Pydantic field constraints via `Field()` and custom validators

**Decision:** Add constraints directly to Pydantic model fields:
- `name: str = Field(..., min_length=1, max_length=200)` — no empty strings; whitespace-only rejected via `@field_validator("name", mode="before")` that strips whitespace (must type-guard: `if isinstance(value, str): return value.strip(); return value` — `mode="before"` runs before Pydantic's type validation, so `value` can be any type; non-string inputs are returned unchanged and will trigger Pydantic's type error). Apply to `CreateProductRequest`, `UpdateProductRequest`, and `CreateOrderRequest.customer_name`.
- `price_cents: int = Field(..., gt=0, le=9_999_999)` — positive (matching existing code's `gt=0`), max €99,999.99
- `quantity: int = Field(..., ge=1, le=10)` — for `AddToCartRequest`; `UpdateCartItemRequest` uses `ge=0` (0 = remove)
- `product_id: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-z0-9]+(-[a-z0-9]+)*$')` — slug format (no consecutive/trailing hyphens, matching existing code)
- `email: str = Field(..., max_length=320)` — RFC 5321 max

Note: `strip_whitespace` is NOT a `Field()` parameter in Pydantic 2 — it must be applied via `@field_validator` or `StringConstraints`.

**Alternatives considered:**
- *Custom validator functions for everything:* More code, less declarative. Rejected for simple bounds.
- *DB-level CHECK constraints only:* Late detection, opaque errors. Rejected as sole defense.

**Rationale:** Pydantic validates at the API boundary — earliest possible rejection with the best error messages. DB constraints remain as defense-in-depth.

### 4. Nginx rate limiting via `limit_req_zone` (not application-level)

**Decision:** Rate limiting lives in `deploy/nginx-rate-limit.conf`:
- Auth endpoints (`/v1/auth/`): 5 requests/minute per IP (`$binary_remote_addr`), `burst=5 nodelay` (allows up to 6 immediate requests: 1 current slot + 5 burst slots)
- Checkout (`POST /v1/orders`): 10 requests/minute per session cookie (`$cookie_session_id`) without `nodelay` (gradual consumption — prevents 11 instant orders) + IP backstop of 30 requests/minute per IP (catches clients rotating/omitting cookies)
- Admin endpoints (`/v1/admin/`): 30 requests/minute per IP (protects against compromised API keys)

Note: When `$cookie_session_id` is empty (cookieless requests), use a `map` directive to fall back to IP-based limiting (not a shared bucket): `map $cookie_session_id $rate_limit_key { "" $binary_remote_addr; default $cookie_session_id; }`. This prevents a single attacker from exhausting a shared bucket and blocking all new visitors. The IP backstop (30/min) is MANDATORY — session-based limiting without it is trivially bypassed by omitting the cookie.

Note: If deployed behind a reverse proxy/load balancer, `$binary_remote_addr` will be the proxy's IP. Configure `set_real_ip_from <proxy_ip_range>; real_ip_header X-Forwarded-For;` in Nginx to use the real client IP.

**Alternatives considered:**
- *Python middleware (slowapi/ratelimit):* Adds dependency, harder to tune, less performant. Rejected.
- *Per-IP only:* Session-based is better for checkout (family members on same IP). Mixed approach chosen.
- *Session-based only without IP backstop:* Trivially bypassed by omitting the cookie (middleware creates a fresh session each request). Rejected — IP backstop added.

**Rationale:** Nginx handles rate limiting at the edge with minimal overhead. Config-only change — no Python code affected. The layered approach (session + IP) prevents both accidental user overload and deliberate abuse.

### 5. API documentation via route decorator kwargs (no separate OpenAPI file)

**Decision:** Add to every route decorator:
- `summary="..."` (short title for the endpoint list)
- `description="..."` (longer explanation shown when expanded)
- `response_model=...` (already partially done)
- `responses={404: {"model": ErrorResponse}, ...}` (error response documentation)
- `tags=["Products"]` (grouping in Swagger UI)

App-level: `app = FastAPI(title="Atelier Marie", version="0.1.0", description="...")` (keep existing title and version; bump version on production launch)

**Rationale:** FastAPI generates OpenAPI spec from decorators. No maintenance burden — docs stay in sync with code automatically.

### 6. Pagination response envelope with entity-specific keys

**Decision:** All list endpoints return:
```json
{
  "<entity_plural>": [...],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

Where `<entity_plural>` is the entity name: `products`, `orders`, etc. Each entity has its own explicit response model (`ProductListResponse`, `OrderListResponse`).

**Alternatives considered:**
- *Generic `items` key:* Simpler but breaks existing TypeScript types defined on Day 1 (frontend uses `response.products`, `response.orders`). Rejected as a breaking change.
- *Generic `PaginatedResponse[T]`:* Pydantic 2 supports generic models, but entity-specific keys are clearer in API docs and match established contracts.

**Rationale:** The frontend TypeScript types and mock API were built against entity-specific keys on Day 1. Changing to `items` would require frontend coordination. Entity-specific keys are also more readable in raw API responses.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Dashboard stats slow on large order tables** | At MVP scale (<1000 orders), queries take <10ms. Add `CREATE INDEX idx_orders_status ON orders(status)` and `CREATE INDEX idx_cart_items_session ON cart_items(session_id)` for aggregate queries. Revisit if table exceeds 100k rows. |
| **Validation too strict rejects valid input** | Use generous bounds (200 chars for names, 10 for cart quantities). Real products won't hit these. Can loosen later without breaking clients. |
| **Rate limiting blocks legitimate burst** | Nginx `burst=10 nodelay` allows short bursts before enforcing. Auth limit (5/min) is very generous for a store with few users. |
| **Session-based rate limit bypass via cookie rotation** | IP backstop (30/min) prevents automated abuse. Cookieless requests share a single bucket (fail-closed). |
| **Error response format change breaks existing clients** | No existing clients — stubs already use this format. Additive change. |
| **API docs add noise to route files** | Keep descriptions to 1-2 sentences. Tags reduce visual complexity in Swagger UI. Worth it for onboarding and frontend integration. |
| **Stock disclosure in error details** | Intentional: frontend shows stock counts on product pages. The `available` field in INSUFFICIENT_STOCK errors enables "only N left" UX without extra API call. |
| **DB constraint misalignment (cart quantity)** | Database CHECK allows 99 but Pydantic allows 10. Fix: tighten DB constraint to match Pydantic (defense-in-depth). Pre-production only — no migration needed. |

## Open Questions

None — all decisions align with existing patterns in the codebase and the core-ecommerce design doc.
