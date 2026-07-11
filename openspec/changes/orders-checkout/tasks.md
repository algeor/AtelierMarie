## 1. Order Service — Core

- [x] 1.0 Create `require_session` FastAPI dependency in `app/routes/orders.py` (or a shared deps module): `def require_session(request: Request) -> str` — returns `request.state.session_id` or raises `HTTPException(status_code=503, detail="Service unavailable")` if None. All order routes use `session_id: Annotated[str, Depends(require_session)]`.
- [x] 1.1 Create `app/services/__init__.py` (empty module init)
- [x] 1.2 Create `app/services/order_service.py` with base exception class and custom exceptions:
  - `OrderServiceError(Exception)` — base class for all order service errors
  - `EmptyCartError(OrderServiceError)` — raised when cart has no items
  - `InsufficientStockError(OrderServiceError)` — attributes: `product_id: str`, `requested: int`, `available: int`
  - `ProductUnavailableError(OrderServiceError)` — attributes: `product_id: str`, `product_name: str`
  - `InvalidStateTransitionError(OrderServiceError)` — attributes: `order_id: str`, `current_status: str`, `requested_status: str`
  - `OrderNotFoundError(OrderServiceError)` — attributes: `order_id: str`
- [x] 1.3 Implement `checkout(conn, session_id, customer_email, customer_name, shipping_address, notes, user_id=None)` — validate cart not empty, validate all products active and in stock (batch-validate ALL items, return all failures in one response), INSERT order (UUID v4) with user_id set from the session's user_id, INSERT order_items (snapshot names + prices), compute total_cents server-side as sum(price_cents × quantity), UPDATE stock, DELETE cart_items WHERE session_id = ? AND product_id IN (...) (only items included in the order), return order data. All operations run within a single `get_db()` context manager — no explicit BEGIN/COMMIT (the context manager owns transaction boundaries). On IntegrityError during stock decrement UPDATE, raise InsufficientStockError immediately (other IntegrityErrors e.g. from INSERT should propagate as-is).
- [x] 1.4 Implement `get_order(conn, order_id, session_id, user_id=None)` — fetch order + items, enforce access control (session_id match OR user_id match), raise OrderNotFoundError for non-existent or unauthorized (never expose 403 — always 404). Also implement `get_order_admin(conn, order_id)` — fetch order + items without ownership check (admin auth enforced at route level).
- [x] 1.5 Implement `list_orders(conn, session_id, user_id=None, page=1, limit=20)` — paginated query filtered by session_id OR user_id, sorted by created_at DESC. Also implement `list_orders_admin(conn, status: OrderStatus | None = None, page=1, limit=20)` — returns all orders with optional status filter, no ownership check (admin auth enforced at route level).
- [x] 1.6 Implement `update_status(conn, order_id, new_status: OrderStatus)` — validate transition against VALID_TRANSITIONS dict, UPDATE status + updated_at, restore stock on cancellation (from both pending and confirmed states), log admin action (structured log with order_id, old_status, new_status). Uses `OrderStatus` literal type (not bare str) to enforce valid status values at the function boundary.

## 2. Order Routes — Customer-Facing

- [x] 2.1 Replace all stubs in `app/routes/orders.py` with real router using `Depends()` for session — implement only POST, GET list, GET detail. Use synchronous route functions (`def`, NOT `async def`) since service functions perform blocking SQLite I/O — FastAPI auto-runs sync routes in a threadpool.
- [x] 2.1b DELETE the `PATCH /{order_id}/status` stub from the customer-facing orders router (status updates are admin-only via admin router)
- [x] 2.2 Implement `POST /v1/orders` — destructure Pydantic model into primitives, read user_id from the session DB row (`SELECT user_id FROM sessions WHERE id = ?` using middleware-validated session_id), pass user_id to checkout service, handle exceptions → appropriate HTTP codes (400 empty cart, 409 stock/unavailable, 422 validation). Reject requests where session_id is None with 503 (DB unavailable).
- [x] 2.3 Implement `GET /v1/orders` — read user_id from session DB row (same as 2.2), call list_orders with session_id and user_id, return OrderListResponse
- [x] 2.4 Implement `GET /v1/orders/{order_id}` — call get_order, return OrderResponse or 404

## 3. Admin Order Routes

- [x] 3.1 Add `GET /v1/admin/orders` to admin router — call `list_orders_admin` with optional `?status=` filter (validate against OrderStatus literal, return 422 for invalid values), require admin auth. Use sync `def` (not `async def`).
- [x] 3.2 Add `GET /v1/admin/orders/{order_id}` to admin router — call `get_order_admin` (no ownership check), full order detail including items, customer info, shipping_address, notes; require admin auth
- [x] 3.3 Add `PATCH /v1/admin/orders/{order_id}/status` to admin router — call update_status, handle InvalidStateTransitionError → 422, OrderNotFoundError → 404, require admin auth

## 4. Tests — Checkout Flow

- [x] 4.1 Create `tests/test_order_service.py` — unit tests for order_service functions with in-memory SQLite
- [x] 4.2 Test: successful checkout creates order, snapshots prices, decrements stock, clears cart, and total_cents equals sum(price_cents × quantity) for all items
- [x] 4.3 Test: checkout with empty cart raises EmptyCartError
- [x] 4.4 Test: checkout with insufficient stock raises InsufficientStockError with available quantity; explicitly assert cart_items rows are unchanged AND product stock values are unchanged after failure
- [x] 4.5 Test: checkout with deactivated product raises ProductUnavailableError; explicitly assert cart_items rows are unchanged AND product stock values are unchanged after failure
- [x] 4.5b Test: checkout with MULTIPLE failing items (e.g., two products out of stock) returns ALL failures in the error, not just the first one (batch validation behavior)
- [x] 4.6 Test: checkout that would make stock negative triggers IntegrityError → InsufficientStockError (CHECK constraint defense-in-depth, no retry)
- [x] 4.7 Test: product price change after checkout does not affect existing order item prices (snapshot immutability)
- [x] 4.8 Test: created order ID matches UUID v4 format
- [x] 4.9 Test: total_cents is computed server-side as sum of (price_cents × quantity) across all items
- [x] 4.10 Test: two sessions each holding the last unit in their carts — call checkout for both sequentially, assert exactly one succeeds (returns order) and the other raises InsufficientStockError; product stock ends at 0

## 5. Tests — Order Management

- [x] 5.1 Test: list_orders returns only orders belonging to session/user (including orders from multiple sessions linked to the same user_id), sorted by created_at DESC
- [x] 5.2 Test: get_order returns full order with items for owner; raises OrderNotFoundError (not a permission error) for non-owner, ensuring 404 translation
- [x] 5.3 Test: get_order with authenticated user_id finds orders from any of their sessions
- [x] 5.4 Test: list_orders pagination edge cases — page beyond last returns empty list with correct total; limit=0 or negative values are rejected

## 6. Tests — State Machine & Admin

- [x] 6.1 Test: all valid state transitions succeed (pending→confirmed, pending→cancelled, confirmed→shipped, confirmed→cancelled, shipped→delivered) and updated_at is refreshed after each transition (insert order with a known past updated_at, transition, assert updated_at changed)
- [x] 6.2 Test: all invalid transitions raise InvalidStateTransitionError — exhaustively test: pending→shipped, pending→delivered, confirmed→pending, confirmed→delivered, shipped→pending, shipped→confirmed, shipped→cancelled, delivered→{any status}, cancelled→{any status}
- [x] 6.3 Test: cancellation from pending state restores stock for all order items
- [x] 6.4 Test: cancellation of order with deactivated product still restores stock
- [x] 6.5 Test: cancellation from confirmed state also restores stock
- [x] 6.6 Test: double-cancellation prevention — cancel an already-cancelled order raises InvalidStateTransitionError and stock is NOT double-incremented
- [x] 6.7 Test: checkout from authenticated session sets user_id on order; list_orders from a new session with same user_id returns the order. Prerequisites: the route reads user_id from `sessions.user_id` and passes it to checkout; this test verifies the full chain.
- [x] 6.8 Test: update_status emits structured log containing order_id, old_status, and new_status (verify with caplog fixture)
- [x] 6.9 Test: backfill user_id on login — when a user authenticates, orders WHERE session_id = current AND user_id IS NULL get user_id set (this test validates the backfill query)

## 7. Tests — Route Integration

- [x] 7.1 Create `tests/test_order_routes.py` — integration tests with TestClient. For admin-authenticated scenarios, use `app.dependency_overrides[require_admin] = lambda: None` to bypass the admin check in tests.
- [x] 7.2 Test: POST /v1/orders returns 201 with order data on success
- [x] 7.3 Test: POST /v1/orders returns 400 on empty cart, 409 on stock issues
- [x] 7.4 Test: POST /v1/orders returns 422 for invalid email, overly long customer_name/shipping_address/notes
- [x] 7.5 Test: GET /v1/orders returns paginated list for session owner
- [x] 7.5b Test: GET /v1/orders cross-session isolation — orders from session A are not visible to session B
- [x] 7.6 Test: GET /v1/orders/{id} returns 404 for non-owner (not 403)
- [x] 7.7 Test: PATCH /v1/admin/orders/{id}/status returns 422 on invalid transition (uses dependency_overrides for admin auth)
- [x] 7.8 Test: admin routes return 403 for non-admin sessions (no override — verify the guard works)
- [x] 7.9 Test: GET /v1/admin/orders returns all orders paginated; with ?status= filter returns only matching orders; combined filter+pagination returns correct subset and total
- [x] 7.10 Test: GET /v1/admin/orders?status=invalid returns 422
- [x] 7.11 Test: GET /v1/admin/orders/{id} returns full order detail for admin, 403 for non-admin
- [x] 7.12 Test: POST /v1/orders with Content-Type application/x-www-form-urlencoded returns 422 (CSRF protection via JSON Content-Type enforcement)
