## 1. Database Schema Updates

- [x] 1.1 Add `CHECK (stock >= 0)` constraint to the `products` table in `app/database.py`
- [x] 1.2 Add `CHECK (quantity >= 1)` constraint to the `cart_items` table in `app/database.py`
- [x] 1.3 Add `ON DELETE CASCADE` to `cart_items.session_id` FK (so session cleanup removes orphaned cart items)
- [x] 1.4 Add index on `cart_items(session_id)` for fast cart lookups
- [x] 1.5 Add `session_absolute_max_age` (180 days in seconds) and `session_expiry_threshold` (7 days in seconds) to `app/config.py`
- [x] 1.6 Add `cart_max_quantity_per_item: int = 10` and `cart_max_distinct_items: int = 20` to `app/config.py`
- [x] 1.7 Add `session_skip_paths: list[str] = ["/health", "/metrics", "/docs", "/openapi.json"]` to `app/config.py`
- [x] 1.8 Add `session_cookie_secure: bool = True` to `app/config.py` (overridden to `False` in dev `.env`)

## 2. Session Middleware Hardening

- [x] 2.1 Add UUID v4 format validation (regex) — reject malformed cookies without DB hit (treat as first-time visit)
- [x] 2.2 Add path-exclusion logic: skip session processing for paths matching `session_skip_paths` config. Use exact match for leaf paths (`/health`, `/docs`, `/openapi.json`) and prefix-with-trailing-slash for directory paths (`/docs/`, `/metrics/`). A request to `/health-records` must NOT match `/health`. Replace the existing hard-coded `_SESSION_SKIP_PATHS = frozenset({"/v1/health"})` with the config-driven list. Note: health check should be at `/health` (non-versioned), not `/v1/health` — update or add the route accordingly.
- [x] 2.3 Add DB validation for returning sessions: query `sessions` table by cookie value, check row exists
- [x] 2.4 Add expiry check: if `expires_at < now`, treat as invalid and create new session
- [x] 2.5 Add absolute lifetime check: if `created_at + session_absolute_max_age < now`, treat as expired
- [x] 2.6 Implement sliding expiry with threshold: only UPDATE `expires_at` when current value is within `session_expiry_threshold` of now
- [x] 2.7 Replace cookie when session is invalid/expired/malformed (set new cookie on response with correct attributes: HttpOnly, Secure in production, SameSite=Lax)

## 3. Session Rotation on Login

- [x] 3.1 Implement session rotation helper within a single `BEGIN IMMEDIATE` transaction: (1) INSERT new session row with user_id, (2) UPDATE `cart_items` SET session_id = new WHERE session_id = old, (3) DELETE old session row. Ensure UPDATE precedes DELETE to avoid FK violations regardless of CASCADE.
- [x] 3.2 Wire rotation into auth callback (to be fully connected in Day 5 auth spec, but the helper function is implemented now)

## 4. Cart Service Layer

- [x] 4.1 Create `app/services/__init__.py`
- [x] 4.2 Create `app/services/cart_service.py` with custom exceptions (`InsufficientStockError`, `QuantityLimitError`, `CartFullError`, `ProductNotFoundError`, `CartItemNotFoundError`)
- [x] 4.3 Create `AddItemResult` dataclass with `cart: CartData` and `created: bool` fields
- [x] 4.4 Create `UnavailableItem` model with `product_id: str`, `product_name: str`, `reason: str` fields
- [x] 4.5 Implement `get_cart(conn, session_id)` — JOIN cart_items + products, filter inactive into `unavailable_items` (with product_name + reason), compute totals, return structured data
- [x] 4.6 Implement `add_item(conn, session_id, product_id, quantity)` — validate product exists/active, check stock (existing_qty + new_qty vs products.stock), check limits, INSERT or UPDATE quantity, return `AddItemResult` with `created` flag
- [x] 4.7 Implement `update_quantity(conn, session_id, product_id, quantity)` — validate item exists, MUST check quantity=0 BEFORE any SQL (if zero → DELETE row, never UPDATE with 0 which violates CHECK constraint), check stock (absolute new qty vs products.stock), check per-item limit
- [x] 4.8 Implement `remove_item(conn, session_id, product_id)` — validate item exists, DELETE row

## 5. Cart Routes

- [x] 5.1 Replace stub in `app/routes/cart.py` with real router
- [x] 5.2 Add `product_id` path parameter validation: `Path(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=100)`
- [x] 5.3 Implement `GET /v1/cart` — call `get_cart`, return `CartResponse`
- [x] 5.4 Implement `POST /v1/cart` — parse `AddToCartRequest`, call `add_item`, return 201 if `result.created` else 200, with `CartResponse`
- [x] 5.5 Implement `PATCH /v1/cart/{product_id}` — parse `UpdateCartItemRequest`, call `update_quantity`, return 200 with `CartResponse`
- [x] 5.6 Implement `DELETE /v1/cart/{product_id}` — call `remove_item`, return 200 with `CartResponse`
- [x] 5.7 Map service exceptions to HTTP responses (404, 409, 422) with consistent error format `{"error": {"code": "...", "message": "...", "details": {...}}}`

## 6. Cart Model Alignment

- [x] 6.1 Rename `total` → `total_cents` in `CartResponse` (aligns with core-ecommerce spec and CLAUDE.md naming convention)
- [x] 6.2 Add `unavailable_items: list[UnavailableItem] = []` field to `CartResponse` (with product_id, product_name, reason — not just opaque IDs)
- [x] 6.3 Create `UnavailableItem` Pydantic model in `app/models/cart.py`
- [x] 6.4 Update `AddToCartRequest.quantity` from `le=10` to `le=99` — Pydantic bound is intentionally wider than the configurable service-layer limit (see design Decision 5). Similarly update `UpdateCartItemRequest.quantity` from `le=10` to `le=99`.

## 7. Tests — Session Middleware

- [x] 7.1 Test: no cookie → new session created, cookie set with correct attributes (HttpOnly, SameSite, max_age)
- [x] 7.2 Test: valid session → request proceeds, `request.state.session_id` set correctly
- [x] 7.3 Test: valid session near expiry → `expires_at` updated in DB (assert new value > old value)
- [x] 7.4 Test: valid session far from expiry → `expires_at` NOT updated (no unnecessary write)
- [x] 7.5 Test: expired session → new session created, old cookie replaced with new cookie (verify attributes: HttpOnly, SameSite=Lax, max_age)
- [x] 7.6 Test: unknown cookie → new session created, cookie replaced (verify attributes: HttpOnly, SameSite=Lax, max_age)
- [x] 7.7 Test: malformed cookie (not UUID format) → new session created without DB query (use mock/spy on DB execute to assert NO SELECT issued for the malformed value)
- [x] 7.8 Test: oversized cookie value → treated as absent, new session created (verify attributes: HttpOnly, SameSite=Lax, max_age)
- [x] 7.9 Test: session past absolute lifetime (created_at > 180 days ago) → treated as expired
- [x] 7.10 Test: health check path (`/health`) → no session created, no cookie set
- [x] 7.10a Test: path-exclusion negative case — request to `/health-records` → session IS created, cookie IS set (must NOT match `/health` exclusion). Request to `/docs/swagger` → session NOT created (matches `/docs/` prefix match).
- [x] 7.11 Test: session rotation helper — add 3 items with quantities (2, 5, 1), rotate session, verify all cart_items migrated with identical product_ids and quantities, old session deleted, new session has user_id
- [x] 7.12 Test: DB failure during session middleware (mock `sqlite3.connect` raising `OperationalError`) → 500 response with generic JSON error `{"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}`, no traceback in body or headers. Verify downstream route handler is NOT invoked (use a mock route that sets a flag; assert flag is not set).

## 8. Tests — Cart Service

- [x] 8.1 Create test fixtures: products in DB (with varying stock levels, including inactive), session in DB
- [x] 8.2 Test `get_cart` — empty cart, cart with items (verify `total_cents` arithmetic: price_cents × quantity summed correctly), cart with inactive product in `unavailable_items` (with product_name)
- [x] 8.3 Test `add_item` — new item (created=True), increment existing (created=False), product not found, product inactive
- [x] 8.4 Test `add_item` stock validation — sufficient stock, insufficient stock on new add, insufficient with existing cart quantity (existing_qty=3, add 4, stock=5 → fail)
- [x] 8.5 Test `add_item` quantity limits — per-item limit exceeded (existing qty 8, add 4 → total 12 → fail), cart full (20 distinct + new → fail), existing item when cart full (should succeed)
- [x] 8.6 Test `update_quantity` — valid update, update to zero removes, exceeds stock (absolute qty comparison), exceeds per-item limit, item not in cart
- [x] 8.7 Test `remove_item` — existing item removed, non-existent item raises error
- [x] 8.8 Test `total_cents` computation: add product A (price_cents=2500, qty=2) + product B (price_cents=1800, qty=3) → assert total_cents = 10400
- [x] 8.9 Test concurrent stock depletion: use two threads sharing a file-based SQLite DB (not in-memory), each calling `add_item` for the same product where stock=1. Use `BEGIN IMMEDIATE` in the service to demonstrate that either transaction isolation serializes the operations (second thread sees updated state) or the `CHECK (stock >= 0)` at checkout catches it. Assert stock never goes negative. Note: this tests the logical behavior under contention, not a true race — SQLite serializes writes.
- [x] 8.10 Test product deactivated after cart add: add while active, set is_active=0, call get_cart → product appears in `unavailable_items` not in `items`
- [x] 8.11 Test boundary values: `add_item` with existing qty 7 + add 3 = 10 (at limit) succeeds; existing qty 10 + add 1 = 11 fails with `QUANTITY_LIMIT_EXCEEDED`; `update_quantity` to exactly 10 succeeds; qty 11 fails. Cart with 19 distinct items, adding 20th succeeds; adding 21st fails.
- [x] 8.12 Test `add_item` with quantity=0 raises error at service level (service does not rely solely on Pydantic for this validation)
- [x] 8.13 Test concurrent per-item quantity limit: use two threads sharing a file-based SQLite DB, same session, same product (stock=20, limit=10). Each thread calls `add_item` with qty=6. With `BEGIN IMMEDIATE`, one thread succeeds (qty=6) and the other either succeeds (total=12 → fail with `QuantityLimitError`) or serializes correctly (6+6=12 > 10 → second call rejected). Verify final quantity never exceeds 10.

## 9. Tests — Cart Routes

- [x] 9.1 Test `GET /v1/cart` — 200 empty cart, 200 with items, 200 with `unavailable_items` populated (verify response contains `product_id`, `product_name`, `reason` keys with `reason == "deactivated"` and correct product_name)
- [x] 9.2 Test `POST /v1/cart` — 201 new item, 200 existing item, 404 bad product, 409 stock, 422 limits. For 409: assert body matches `{"error": {"code": "INSUFFICIENT_STOCK", "message": <str>, "details": {"product_id": <str>, "requested": <int>, "available": <int>}}}`. For 422 limits: assert body matches `{"error": {"code": "QUANTITY_LIMIT_EXCEEDED"|"CART_FULL", "message": <str>, "details": {"max_quantity": 10}|{"max_items": 20}}}`.
- [x] 9.3 Test `PATCH /v1/cart/{product_id}` — 200 update, 200 remove (qty 0), 404 not in cart, 409 stock (assert same nested error structure as 9.2), 422 limit
- [x] 9.4 Test `DELETE /v1/cart/{product_id}` — 200 removed, 404 not in cart
- [x] 9.5 Test Pydantic validation: POST with invalid product_id format → 422, quantity=0 on add → 422, quantity=100 on add → 422 (Pydantic le=99), quantity=-1 on update → 422, missing required fields → 422
- [x] 9.6 Test path parameter validation: PATCH/DELETE with uppercase product_id → 422, oversized product_id → 422
- [x] 9.7 Test cart isolation between sessions: create two sessions (manual cookie manipulation), add different items to each, verify `GET /v1/cart` returns only the correct session's items

## 10. Integration Verification

- [x] 10.1 Verify end-to-end: create session → add item → view cart → update quantity → remove item
- [x] 10.2 Verify session expiry + cart: expired session gets new session, old cart items are orphaned (not visible to new session). Assert: (a) new session's `GET /v1/cart` returns empty, (b) old session row still exists in DB with `expires_at < now`, (c) old cart_items rows still present — middleware does NOT delete expired sessions.
- [x] 10.3 Verify session rotation: add items → rotate session → cart items still visible under new session
- [x] 10.4 Verify ON DELETE CASCADE: delete session row → verify cart_items rows also deleted
- [x] 10.5 Run full test suite (`pytest`) and confirm all pass with ≥80% coverage on new code
