## Why

The core e-commerce APIs (products, cart, orders, auth) are functionally complete as specs, but the codebase still has 501 stubs. Before implementation proceeds further, we need the "last-mile" polish that makes the API production-ready: a dashboard endpoint for admin overview, consistent pagination on all list endpoints, a standard error response envelope, robust input validation for edge cases, rate limiting at the reverse proxy layer, and clear API documentation. These are not new features — they're the hardening and consistency layer that makes the existing features shippable.

## What Changes

- **New endpoint: `GET /v1/admin/dashboard`** — returns aggregate stats (total orders, total revenue in cents, product count, orders by status) via simple SQLite aggregate queries. Target <200ms.
- **Pagination enforcement** — all list endpoints (`/v1/products`, `/v1/orders`, `/v1/admin/orders`) use the shared `PaginationParams` pattern (page/limit) and return `{<entity_plural>, total, page, limit}` envelope with entity-specific keys.
- **Consistent error response format** — all error responses use the existing `ErrorResponse` envelope (`{error: {code, message, details}}`). Unify FastAPI's default validation errors (422) and custom service exceptions into this format.
- **Input validation hardening** — reject empty-string product names/IDs, negative `price_cents`, zero/negative quantities, quantities exceeding per-item limits, strings exceeding sane max lengths. Pydantic validators + custom exception handlers.
- **Nginx rate limiting configuration** — `limit_req_zone` rules for `/v1/auth/` (5 req/min per IP) and `/v1/orders` POST (10 req/min per session). Config file only — no Python code.
- **API documentation polish** — add `summary`, `description`, `response_model`, `responses` kwargs to all route decorators. Tag grouping for FastAPI auto-docs (Swagger/ReDoc).

## Capabilities

### New Capabilities
- `admin-dashboard`: Admin stats endpoint returning order/revenue/product aggregates from SQLite
- `error-handling`: Consistent error envelope, custom exception handlers, validation error formatting
- `input-validation`: Edge-case hardening for all write endpoints (empty strings, bounds, lengths)
- `rate-limiting`: Nginx rate limiting configuration for auth and checkout endpoints
- `api-docs`: OpenAPI documentation polish (descriptions, tags, response examples)

### Modified Capabilities

_(No existing spec-level requirements are changing — these are new cross-cutting concerns.)_

## Impact

- **Code:** `app/routes/admin.py` (new dashboard endpoint), `app/main.py` (exception handlers), all `app/models/*.py` (Pydantic field validators/constraints), all `app/routes/*.py` (decorator kwargs for docs)
- **Config:** `deploy/nginx-rate-limit.conf` (new file, included in main nginx config)
- **Dependencies:** None new — uses existing FastAPI, Pydantic, SQLite
- **APIs:** No breaking changes. Existing error responses gain the standard envelope (previously already using it in stubs). Pagination parameters are additive (defaults apply if omitted).
