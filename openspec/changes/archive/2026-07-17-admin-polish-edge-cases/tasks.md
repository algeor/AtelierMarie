# Tasks (Revised 2026-07-16)

> **Revision note:** The original tasks assumed pre-implementation 501 stubs. The codebase is now well past that: services, exception handlers, admin dashboard, pagination, and Nginx config all exist in some form. Tasks below are rescoped to close the remaining *behavioral* gaps between what exists and what the specs require, without demanding a wholesale refactor of exception hierarchies that would touch every service. Where reality already satisfies the spec, the task is marked "verify" and closes on inspection.

## 1. Error Handling — reconcile existing handlers with spec

- [x] 1.1 **Verify existing exception handlers cover the spec's behavioral contract.**
  `app/exceptions.py` already registers handlers for `RequestValidationError`, `StarletteHTTPException`, the catch-all `Exception`, and the cart-service exceptions (`ProductNotFoundError`, `CartItemNotFoundError`, `InsufficientStockError`, `QuantityLimitError`, `CartFullError`) — all emit the `{error: {code, message, details}}` envelope. Inspect each handler's response shape against `specs/error-handling/spec.md` scenarios; note any that fail the scenarios and address them in subsequent tasks. No code change if all scenarios pass.
- [x] 1.2 **Register handlers for the order-service exceptions currently caught inline in routes.** `app/routes/admin.py` and `app/routes/orders.py` catch `OrderNotFoundError` / `InvalidStateTransitionError` with per-route `try/except` blocks returning `JSONResponse`. Register global handlers for these in `app/exceptions.py` (matching the pattern used for cart exceptions), then remove the per-route try/except blocks. Ordering: register before removing the inline handlers so tests never see a raw 500.
- [x] 1.3 **Verify the `HTTPException` handler honours dict-detail passthrough.** Current handler stringifies dict details unconditionally. Update it to implement the spec rule: if `detail` is a dict with both `code` and `message` keys, extract them into the envelope (remaining keys → `details`); otherwise fall back to status-derived code with the dict/string in `message`/`details`.
- [x] 1.4 **Verify the catch-all `Exception` handler does not leak internals.** Current handler already logs via `logger.exception()` and returns a static safe payload — verify by test only, no code change expected.
- [x] 1.5 **Skip `ServiceError` base-class refactor.** The spec envisions a single `ServiceError` base class with a single handler. The codebase has independent exception classes per service (`cart_service`, `order_service`, `product_service`, etc.) and dedicated handlers per class. Migrating everything is out of scope for a "polish" change — it would touch every service and every route. Document the divergence in `openspec/changes/admin-polish-edge-cases/design.md` (add a "Post-implementation reality" section) and defer the consolidation to a future change if it's still wanted.
- [x] 1.6 **Write tests for the reconciled handlers.** Cover: validation error → 422 envelope with field details; `HTTPException(status_code=403, detail="…")` → 403 with `FORBIDDEN` code; `HTTPException(status_code=409, detail={"code": "X", "message": "Y", "extra": 1})` → 409 with envelope + `details.extra`; `OrderNotFoundError` raised in a route → 404 envelope (handler, not per-route catch); unhandled `RuntimeError` → 500 with no leaked traceback / message / class name.
- [x] 1.7 **Verify `admin_api_key` length check.** Already at `app/config.py:84-86`. Add a test to `tests/test_config.py` asserting `Settings(environment="production", admin_api_key="short", jwt_secret="…secure…", …)` raises `ValueError` containing "32 characters".

## 2. Input Validation Hardening — verify + tighten

- [x] 2.1 **Verify product model constraints.** `CreateProductRequest` and `UpdateProductRequest` already have `Field(min_length=1, max_length=200)` for names, `pattern=PRODUCT_ID_PATTERN` on ID, `gt=0` and `le=99_999_99` on `price_cents`, `max_length=5000` on descriptions, `max_length=100` on category, `ge=0, le=MAX_STOCK` (99999) on stock, and strip-whitespace validators on text fields. Spec asks for `stock ≤ 1_000_000` — the code caps at 99_999 (`MAX_STOCK`), which is stricter. Keep the stricter cap; note the divergence in a comment on the constant.
- [x] 2.2 **Verify strip-whitespace validators on product name/description fields.** Existing `strip_and_reject_blank` validator uses `mode="before"` but does not type-guard: passing an int as `name_en` would raise a `TypeError` inside `.strip()` before Pydantic can produce a clean 422. Add `if not isinstance(v, str): return v` guard at the top of `strip_and_reject_blank` in both `CreateProductRequest` and `UpdateProductRequest`.
- [x] 2.3 **Tighten cart quantity bounds from 99 to 10.** `AddToCartRequest.quantity` and `UpdateCartItemRequest.quantity` currently have `le=99`. Change to `le=10` in both (matches `cart_max_quantity_per_item` in `app/config.py`). Add `min_length=1, max_length=100` to `AddToCartRequest.product_id`.
- [x] 2.4 **Verify order model constraints.** `CreateOrderRequest` has `max_length` on `customer_name` (200), `shipping_address` (1000), `notes` (2000). `customer_email` is `EmailStr` — add explicit `Field(..., max_length=320)` for OpenAPI docs. Add `min_length=1` and a strip-whitespace validator on `customer_name` so `"   "` is rejected.
- [x] 2.5 **Verify pagination params.** `app/models/common.py` already has `page: ge=1`, `limit: ge=1, le=100`. No change.
- [x] 2.6 **Write tests for the tightened validators.** Focus only on the *changed* behaviour: (a) `AddToCartRequest(product_id=…, quantity=11)` → `ValidationError` (was previously accepted); (b) `CreateProductRequest(name_en=123, …)` → `ValidationError` with a clean type error (not TypeError from `.strip()`); (c) `CreateOrderRequest(customer_name="   ", customer_email="a@b.com")` → `ValidationError`. Skip re-testing already-passing constraints — those are covered by existing `tests/test_models_*.py`.
- [x] 2.7 **Tighten cart_items DB CHECK constraint from 99 to 10.** In `app/database.py` `_SCHEMA_SQL`, change `CHECK (quantity >= 1 AND quantity <= 99)` on `cart_items` to `<= 10`. Note: existing databases created before this change keep the older constraint (schema is created with `IF NOT EXISTS`; no migration runs). Add a comment above the constraint documenting this. Add a test that a fresh in-memory DB rejects a direct SQL INSERT of `quantity=11`. Do **not** tighten the `order_items` CHECK — orders are historical and may have snapshot quantities up to the old limit.

## 3. Admin Dashboard — verify existing implementation

- [x] 3.1 **Verify `app/services/admin_service.py` exists** with `get_dashboard_stats()` returning `{products: {total, active}, orders: {total, revenue_cents, by_status}, low_stock_count}`. This shape differs from the spec (which asked for a flat structure with `total_orders`, `total_revenue_cents`, `orders_by_status`, `carts_with_items`, `computed_at`), but the frontend has been built against the current shape. Keep the existing shape; document the divergence in `design.md`. The spec's `carts_with_items` and `computed_at` fields are not currently exposed — decide whether they're worth adding.

  **Decision (2026-07-17):** Keep the existing nested shape as-is. `carts_with_items` and `computed_at` deferred — capture in a future additive-only change if the fields prove useful.

  **Decision needed** — see "Open items" below.
- [x] 3.2 **Verify `DashboardResponse` model.** Already present in `app/models/admin.py` matching the actual service shape (`ProductStats`, `OrderStats`, `low_stock_count`). No change unless 3.1's decision adds fields.
- [x] 3.3 **Verify `GET /v1/admin/dashboard` endpoint.** Exists at `app/routes/admin.py:457`. Add `Cache-Control: no-store` response header (currently missing — the spec requires it).
- [x] 3.4 **Verify DB indexes.** `idx_orders_status` and `idx_cart_items_session_id` (note: existing index has `_id` suffix, spec called it `idx_cart_items_session`) both already exist in `_SCHEMA_SQL`. No change.
- [x] 3.5 **Write test for the missing Cache-Control header** on `GET /v1/admin/dashboard`. Existing dashboard tests likely already cover empty-DB, auth, and status aggregation — verify and only add tests for gaps.

## 4. Pagination Standardization — verify + add `calculate_offset` helper

- [x] 4.1 **Verify list routes accept `page`/`limit`.** All admin/products/orders list routes use `Query(default=1, ge=1)` / `Query(default=20, ge=1, le=100)` inline. Spec suggested extracting to `PageParam`/`LimitParam` from `common.py` — these types are already defined but not used. **Do not** refactor existing routes to switch to them (churn without behaviour change). Note the divergence.
- [x] 4.2 **Verify list response envelopes.** `ProductListResponse` uses `products`, `ProductAdminListResponse` uses `products`, `OrderListResponse` uses `items` (inconsistent — orders use `items`, not `orders`). The frontend TypeScript types were built against these existing keys — do **not** rename `items → orders` without a coordinated frontend change. Note the divergence.
- [x] 4.3 **Add `calculate_offset(page: int, limit: int) -> int` helper** to `app/models/common.py`. Update at least one service that computes `offset = (page - 1) * limit` inline to use the helper as a demonstration; leave others alone unless the change is trivial.
- [x] 4.4 **Write a test for `calculate_offset`** covering `page=1 → 0`, `page=2, limit=20 → 20`. Pagination-parameter validation tests already exist for existing routes.

## 5. API Documentation Polish — verify existing coverage

- [x] 5.1 **Verify `FastAPI()` app metadata.** `app/main.py` already sets `title`, `description`, `version="0.1.0"`. No change.
- [x] 5.2–5.6 **Verify `summary`/`description` on route decorators.** Spot-check `app/routes/products.py`, `cart.py`, `orders.py`, `auth.py`, `admin.py`. Admin routes have full summaries already. For any router file where >50% of routes lack `summary`, add them. **Do not** touch routes that already have adequate docs. Report which files needed additions.

  **Applied:** Added `summary=` to all 4 routes in `cart.py` and all 4 in `auth.py` (both were at 0% before). `products.py`, `orders.py`, `admin.py`, `comments.py`, `reactions.py` were already at 100%.
- [x] 5.7 **Add `responses={404/409/422: {"model": ErrorResponse}}`** to routes that raise those errors and currently lack the kwarg. Scope: admin routes only (largest surface, most auditor value). Skip cart/product routes unless trivial.
- [x] 5.8 **Verify `response_model` on success routes.** Most already have it. Spot-check and add for any misses.

  **Verified:** products/orders/comments/reactions/cart at 100%; admin at 93% (13/14); auth deliberately uses `JSONResponse` for OAuth flows. Acceptable.
- [x] 5.9 **Manual smoke check** — `make dev-backend`, hit `/v1/docs`, confirm groups render.

## 6. Nginx Rate Limiting — reconcile existing config

- [x] 6.1 **Reconcile `deploy/nginx-ratelimit.conf` with spec.** Existing file uses `$binary_remote_addr` (IP) for all zones with `rate=5r/s` (auth), `2r/s` (checkout), `30r/s` (api_general). Spec wants: auth `5r/m`, checkout session-cookie-keyed with `map` fallback + IP backstop `30r/m`, admin `30r/m`. Update the zones to match the spec's per-minute rates and add the `map $cookie_session_id …` block. Preserve existing file name (`nginx-ratelimit.conf`) unless the spec truly requires the exact `nginx-rate-limit.conf` spelling — the include instruction is what matters, not the filename.
- [x] 6.2 **Add location-level `limit_req` directives** with correct `nodelay` policy: `nodelay` on auth and admin, no `nodelay` on checkout.
- [x] 6.3 **Add custom 429 JSON response** via `error_page 429 @rate_limited;` returning the standard error envelope. Static `Retry-After: 60` header.
- [x] 6.4 **Document deployment usage.** Create or update `deploy/README.md` explaining: `include` directive placement, admin API key generation, `set_real_ip_from` / `real_ip_header` behind a proxy.

## 7. Integration Verification

- [x] 7.1 Run `make test-backend`. All tests pass.

  **588 passed** after fixing `test_patch_cart_limit_422` to expect `VALIDATION_ERROR` (Pydantic `le=10` now catches over-limit quantities before the service raises `QUANTITY_LIMIT_EXCEEDED` — both 422; semantic meaning preserved).
- [x] 7.2 Manual: start server, load `/v1/docs`, confirm docs render.
- [x] 7.3 Manual/curl: send an invalid request, confirm response matches `ErrorResponse` schema.

  **Verified 2026-07-17:** `curl` to an unrouted `/v1/*` path returned `{"error":{"code":"NOT_FOUND","message":"Not Found","details":null}}` — all four envelope fields match the `ErrorResponse` contract in `app/models/common.py`.

## Open items (decisions the applier should surface, not silently resolve)

1. **Task 3.1 — dashboard shape.** Keep the existing nested shape (`products`/`orders`/`low_stock_count`) or add the spec's fields (`carts_with_items`, `computed_at`)? Adding fields is additive/safe; renaming would break the frontend. Recommendation: additive only.
2. **Task 4.2 — `OrderListResponse` uses `items` not `orders`.** Rename requires frontend coordination. Recommendation: leave alone, note in design.md.
3. **Task 1.5 — `ServiceError` base class refactor.** The spec's cleanest architecture. Deferring keeps the diff small; the cost is a per-exception handler registration pattern that's harder to extend. Recommendation: defer, capture in a follow-up change if desired.
