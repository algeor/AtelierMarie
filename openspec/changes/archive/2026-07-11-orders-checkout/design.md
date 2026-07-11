## Context

AtelierMarie has a working skeleton: FastAPI app factory, SQLite database with full schema (products, sessions, cart_items, orders, order_items, users), session middleware that creates cookies and DB rows on first request, and Pydantic models for all request/response shapes. The orders route currently returns 501 stubs. The `session-cart` spec (Day 3) established the service-layer pattern with free functions accepting `sqlite3.Connection`.

The `orders` and `order_items` tables already exist in `app/database.py` schema. Pydantic models (`OrderResponse`, `OrderItemResponse`, `OrderListResponse`, `CreateOrderRequest`, `UpdateOrderStatusRequest`) are already defined in `app/models/orders.py`. The `OrderStatus` type literal is defined as `"pending" | "confirmed" | "shipped" | "delivered" | "cancelled"`.

The cart service (when implemented) will populate `cart_items` rows that the checkout flow reads. The order service queries `cart_items` and `products` tables directly — it does not import from a cart service module.

## Goals / Non-Goals

**Goals:**
- Implement atomic checkout that converts a cart into a committed order in a single transaction
- Enforce the order state machine (valid transitions only, 422 on invalid)
- Restore stock on cancellation
- Provide order retrieval for both customers (own orders) and admins (all orders)
- Keep all operations under 200ms (checkout is the most complex at ~150ms)
- Establish clear access control: session-owner sees own orders, admin sees all

**Non-Goals:**
- Payment processing (orders go to "pending" status — payment is out of band for MVP)
- Email notifications on order status change (future enhancement)
- Shipping cost calculation or tax (flat rate or free shipping for MVP)
- Order editing after placement (immutable once created)
- Bulk order operations
- Cart service implementation (separate spec — order service reads cart_items directly)
- Customer self-cancellation via a dedicated endpoint (deferred — the core-ecommerce design doc allows "Admin or Customer" for pending→cancelled, but for MVP only admins cancel orders; customer-facing cancel will be a future spec)
- Admin audit trail / order status history table (future enhancement — for MVP, admin actions are logged via application logs only)

## Decisions

### 1. Order service as pure functions with explicit DB connection

**Decision:** Same pattern as session-cart spec — `order_service.py` exports free functions accepting `sqlite3.Connection` and explicit parameters.

```python
def checkout(
    conn: sqlite3.Connection,
    session_id: str,
    customer_email: str,
    customer_name: str | None = None,
    shipping_address: str | None = None,
    notes: str | None = None,
    user_id: str | None = None,  # from sessions.user_id — set on authenticated sessions
) -> OrderData: ...
def get_order(conn: sqlite3.Connection, order_id: str, session_id: str, user_id: str | None = None) -> OrderData: ...
def get_order_admin(conn: sqlite3.Connection, order_id: str) -> OrderData: ...
def list_orders(conn: sqlite3.Connection, session_id: str, user_id: str | None = None, page: int = 1, limit: int = 20) -> OrderListData: ...
def list_orders_admin(conn: sqlite3.Connection, status: OrderStatus | None = None, page: int = 1, limit: int = 20) -> OrderListData: ...
def update_status(conn: sqlite3.Connection, order_id: str, new_status: OrderStatus) -> OrderData: ...
```

**Rationale:** Consistent with the service-layer pattern established in Day 3. Testable with in-memory SQLite. Service functions accept explicit primitives (not Pydantic models) so they can be called from CLI tools, background jobs, or tests without constructing HTTP-layer objects. Routes destructure the Pydantic model before calling the service.

`get_order` enforces ownership (session_id OR user_id match), returning `OrderNotFoundError` for non-owners. `get_order_admin` is a separate function with no ownership check — admin authorization is enforced at the route level via `require_admin`. This avoids "skip security" boolean flags in the service layer.

`list_orders` query logic: when `user_id` is None, filter by `session_id` only (`WHERE session_id = ?`). When `user_id` is provided, filter by `user_id` only (`WHERE user_id = ?`) — this captures all sessions for that user including the current one. Never combine with OR to avoid the NULL pitfall.

`list_orders_admin` is a separate function for the admin list-all-orders endpoint. It returns ALL orders with optional status filter. Admin authorization is enforced at the route level — this function has no ownership logic.

**user_id source:** `user_id` MUST be read from `sessions.user_id` in the database (set only via completed OAuth flow). NEVER accept user_id from client headers, query parameters, or unvalidated tokens. Route implementation: `SELECT user_id FROM sessions WHERE id = ?` using the middleware-validated `session_id`. The route reads it from the session DB row and passes it as an explicit parameter to service functions.

**Return types:** `OrderData` and `OrderListData` are `TypedDict` classes defined in `order_service.py`. They represent the service-layer return shape (plain dicts with typed keys). Routes convert them to HTTP responses via `OrderResponse.model_validate(order_data)`. This decouples the service layer from Pydantic HTTP models.

```python
class OrderItemData(TypedDict):
    product_id: str
    product_name: str
    price_cents: int
    quantity: int

class OrderData(TypedDict):
    id: str
    session_id: str
    user_id: str | None
    status: str
    total_cents: int
    customer_email: str
    customer_name: str | None
    shipping_address: str | None
    notes: str | None
    created_at: str
    updated_at: str
    items: list[OrderItemData]

class OrderListData(TypedDict):
    items: list[OrderData]
    total: int
    page: int
    limit: int
```

### 2. Single transaction for checkout (no two-phase commit)

**Decision:** The entire checkout (validate → insert order → insert items → decrement stock → clear cart) runs within a single `get_db()` context manager call. The context manager provides implicit transaction atomicity (commit on success, rollback on exception). No explicit `BEGIN`/`COMMIT` in service code — the context manager owns transaction boundaries.

**Alternatives considered:**
- *Two-phase (reserve stock, then commit):* Over-engineered for single-SQLite, single-server. Rejected.
- *Optimistic (check stock, insert, hope for the best):* Relies entirely on CHECK constraint. Rejected — better to validate explicitly and give clear error messages.
- *Explicit BEGIN/COMMIT in service:* Conflicts with `get_db()` which already calls `conn.commit()` on successful exit and `conn.rollback()` on exception. Double transaction management causes confusion.

**Rationale:** SQLite's single-writer serialization makes this safe. The `CHECK (stock >= 0)` constraint is the last-resort safety net, but the service validates first for good error messages. The `get_db()` context manager guarantees atomicity without manual transaction statements.

### 3. UUID v4 for order IDs

**Decision:** Generate order IDs as UUID v4 strings (e.g., `550e8400-e29b-41d4-a716-446655440000`).

**Alternatives considered:**
- *Sequential integer:* Leaks order volume, guessable. Rejected.
- *Short hash (nanoid):* Shorter but higher collision risk. Rejected for simplicity.

**Rationale:** Consistent with session IDs. Unguessable. No coordination needed.

### 4. Access control via session_id matching

**Decision:** A customer can view an order if `orders.session_id` matches their current session OR if `orders.user_id` matches their authenticated user ID. Admin bypasses this check.

**Rationale:** Anonymous-first design — unregistered users can still view their orders in the same browser session. Logged-in users can see orders from any session linked to their account.

### 5. State machine validation in service layer (not DB triggers)

**Decision:** Valid transitions are defined as a Python dict. The service checks the transition before executing the UPDATE. Invalid transitions raise `InvalidStateTransitionError`.

```python
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}
```

**Alternatives considered:**
- *SQLite trigger checking old/new status:* Harder to test, opaque error messages. Rejected.
- *DB-level CHECK constraint on status column:* Can only validate the value itself, not transitions. Not applicable.

**Rationale:** Python validation gives clear error messages and is trivially testable.

### 6. Stock restoration on cancellation is synchronous

**Decision:** When an order is cancelled, `UPDATE products SET stock = stock + quantity` for each order item runs in the same transaction as the status update. Stock restoration only applies to cancellations from `pending` or `confirmed` states. Since `shipped` and `delivered` are not cancellable (no valid transition to `cancelled`), stock is never restored for orders that have progressed past `confirmed`.

**Rationale:** At this scale, no risk of the stock update being slow. Keeping it transactional ensures consistency — if the stock update fails, the cancellation rolls back.

### 7. Price snapshot is immutable

**Decision:** `order_items.price_cents` and `order_items.product_name` are copied from the products table at checkout time and never updated. Even if the product price changes later, existing orders retain the purchase-time price.

**Rationale:** This is stated in the architecture doc as a key design decision. Essential for accounting accuracy.

### 8. total_cents is always server-computed

**Decision:** The `total_cents` field on an order is computed server-side as `sum(product.price_cents × cart_item.quantity)` for all items at checkout time. No client-provided total is accepted — `CreateOrderRequest` intentionally has no `total_cents` field.

**Rationale:** Prevents financial manipulation. The server is the sole source of truth for order totals.

### 9. Session expiry relies on middleware validation

**Decision:** The order service does NOT re-validate session expiry. It trusts that the session middleware (Day 3 spec) has already validated the session cookie, rejected expired sessions, and set `request.state.session_id` to a known-valid session. If the middleware passes a session_id, it's valid.

**Rationale:** Separation of concerns. Session lifecycle is the middleware's responsibility. The order service only checks access control (session_id match or user_id match), not session validity.

### 10. CSRF protection via JSON Content-Type enforcement

**Decision:** State-changing endpoints (`POST /v1/orders`, `PATCH /v1/admin/orders/{id}/status`) require `Content-Type: application/json`. Combined with `SameSite=Lax` cookies, this prevents cross-origin form-based CSRF because browsers cannot send JSON bodies from plain HTML forms without CORS preflight.

**Rationale:** Standard API-level CSRF mitigation. No additional CSRF token needed for JSON APIs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Race condition: two checkouts for last item** | `CHECK (stock >= 0)` constraint catches it at DB level. On `IntegrityError`, the service rolls back and returns 409 immediately (no retry). The explicit stock check before the transaction handles the common case with a clear error message; the CHECK constraint is defense-in-depth for the true race. |
| **Large carts slow down checkout** | Max 20 items per cart (enforced by cart service). 20 INSERTs + 20 UPDATEs in a single transaction is still <100ms on SQLite. |
| **Cancelled order stock restoration after product deactivated** | Stock is still restored (product row exists, just `is_active=0`). The stock number is correct even if product isn't shown. |
| **Session expiry between cart-add and checkout** | Session middleware creates a new session on expired cookie. The old cart_items are orphaned (acceptable — periodic cleanup). Customer sees empty cart, starts fresh. |
| **Admin status updates have no undo** | Terminal states (delivered, cancelled) are irreversible by design. Admin UI should confirm before transitioning. |
| **Checkout abuse / rate limiting** | Nginx rate-limits `POST /v1/orders` to 5 req/session/minute (configured in deploy phase). SQLite single-writer serializes writes, so flood attempts cause queueing, not corruption. |
| **Admin action accountability** | For MVP, admin actions are logged at application level (standard structured logging with admin identity, action, order_id, old/new status). A dedicated `order_status_history` table is deferred to a future spec. |
| **Anonymous user loses session → loses order access** | Anonymous users who lose their session cookie (browser reset, cookie expiry, session rotation on login/logout) lose access to orders placed under that session (user_id is NULL). Acceptable for MVP — order confirmation email (future feature) is the recovery mechanism. Consider: when a user logs in, backfill `user_id` on orders matching the current session_id. |
| **Double-submit on checkout** | After successful checkout the cart is empty, so a quick retry returns 400 (empty cart). Acceptable for MVP — no data corruption. Frontend should clear local cart state on 201 to prevent double-submit attempts. |
| **Pre-login orders invisible after login** | When user_id is provided, list_orders query is `WHERE user_id = ?`. Orders placed anonymously on the same session (before login) have user_id = NULL and become invisible. Fix for MVP: when a user authenticates via OAuth, backfill user_id on existing orders WHERE session_id = current_session AND user_id IS NULL. This is a REQUIRED step in the OAuth login flow, not a "consider." |
| **Session middleware DB error → None session_id** | On sqlite3.Error, middleware sets session_id = None and continues. Routes MUST guard against None session_id by returning 503 (Service Unavailable). Implement as a FastAPI dependency: `def require_session(request: Request) -> str` that raises HTTPException(503) if session_id is None. All order routes depend on this. |

## Open Questions

None — all decisions align with the core-ecommerce design doc, ARCHITECTURE.md, and IMPLEMENTATION_PLAN.md Day 4 spec.

## Spec Errata (resolved via code review)

| # | Issue | Resolution |
|---|-------|-----------|
| 1 | checkout() missing user_id parameter | Added `user_id: str \| None = None` — read from sessions.user_id |
| 2 | Explicit BEGIN/COMMIT conflicts with get_db() auto-commit | Removed — get_db() context manager owns transaction boundaries |
| 3 | No list_orders_admin function for admin route | Added `list_orders_admin(conn, status, page, limit)` |
| 4 | user_id source unspecified (IDOR risk) | Mandated: read from sessions.user_id in DB, never from client |
| 5 | async def + blocking SQLite stalls event loop | Changed to sync `def` routes — FastAPI threadpools them |
| 6 | Fail-fast vs validate-all contradiction | Resolved: batch-validate all items, return all failures |
| 7 | No sliding window session expiry | Implemented UPDATE expires_at on each valid request |
| 8 | update_status accepts str not OrderStatus | Changed to `new_status: OrderStatus` literal type |
| 9 | Exception classes lack attributes | Specified attributes on all custom exceptions |
| 10 | OrderData/OrderListData undefined | Defined as TypedDict in service module |
| 11 | Admin auth untestable | Added dependency_overrides guidance for tests |
| 12 | CSRF enforcement has no test | Added test 7.12 for Content-Type rejection |
