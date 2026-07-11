## Context

AtelierMarie has a working skeleton: FastAPI app factory, SQLite database with full schema (products, sessions, cart_items, orders, order_items, users), session middleware that creates cookies and DB rows on first request, and Pydantic models for all request/response shapes. The cart route returns 501 stubs. The session middleware handles new visitors but does NOT validate returning sessions against the DB, does NOT implement sliding expiry, and does NOT handle expired/deleted sessions.

The `product-catalog` spec (Day 2) is defined but not yet implemented — cart service will query the products table directly. The cart depends on products existing in the DB but not on the product service layer.

**Existing code state:**
- `app/database.py`: Schema with `sessions` table (id, user_id, created_at, expires_at) and `cart_items` (session_id FK, product_id FK, quantity, added_at, PK on session_id+product_id)
- `app/middleware/session.py`: Creates new sessions (INSERT + cookie), but no validation of returning sessions
- `app/models/cart.py`: `CartItemResponse`, `CartResponse`, `AddToCartRequest`, `UpdateCartItemRequest` already defined
- `app/config.py`: `session_cookie_name`, `session_max_age` settings present

## Goals / Non-Goals

**Goals:**
- Harden session middleware: validate, expire, and rotate sessions properly
- Implement full cart CRUD with stock validation and quantity limits
- Keep all responses under 50ms (session overhead <2ms, cart operations <50ms)
- Maintain anonymous-first UX: full cart works without any login
- Establish the service-layer pattern (`app/services/`) for reuse by orders/auth

**Non-Goals:**
- Cart merging across sessions on login (future — tracked in archived spec)
- Wishlists or saved-for-later
- Checkout flow (Day 4 — orders-checkout spec)
- Shipping calculation or tax
- Session cleanup cron job implementation (deferred — schema supports CASCADE for when it's added)
- Product service implementation (Day 2 spec — cart queries products table directly)
- Rate limiting implementation (noted as future hardening; Nginx-level for MVP)

## Decisions

### 1. Session validation on every request (Option A: DB check)

**Decision:** On each request with an existing cookie, validate in this strict order:
1. UUID v4 format check (regex — no DB hit for garbage values)
2. DB lookup: `SELECT id, expires_at, created_at FROM sessions WHERE id = ?`
3. Absolute lifetime check: reject if `created_at + 180 days < now`
4. Sliding expiry check: reject if `expires_at < now`
5. Sliding expiry update: ONLY if all above pass AND `expires_at` is within 7 days of now

If any check fails (row missing, expired, or past absolute lifetime), treat as invalid — generate new session, replace cookie. No writes occur for sessions that fail validation.

**Alternatives considered:**
- *Trust the cookie blindly (current behavior):* No security or expiry. Rejected.
- *JWT-based session tokens:* Avoids DB lookup but can't invalidate/rotate server-side. Rejected — we need rotation on logout.
- *In-memory cache of valid session IDs:* Faster but adds complexity and stale-cache risk for negligible gain at this scale. Rejected.

**Rationale:** SQLite read by PK is <1ms. At MVP scale (~100 concurrent users), this adds negligible overhead. Simplicity wins. The UUID format check (regex, no DB) short-circuits malformed cookies before they hit the database.

### 2. Sliding expiry with 7-day threshold (not every request)

**Decision:** Only update `expires_at = now + 30 days` when the current value is within 7 days of expiring. This means active users still never expire, but the write only happens once per ~23-day window instead of on every single request.

**Why threshold from day one:**
- Eliminates write amplification as a DoS vector (attacker flooding requests can't force a write per request)
- Reduces SQLite write load from O(requests) to O(active_sessions / 23_days)
- Still guarantees no active user ever expires (worst case: user returns on day 29, gets extended)
- Health checks and monitoring probes never trigger writes

**Alternatives considered:**
- *UPDATE on every request:* Simple but write amplification is a DoS vector and unnecessary load. Rejected.
- *No sliding expiry (fixed 30 days from creation):* Punishes loyal customers who visit weekly. Rejected.

**Cookie header behavior:** The `Set-Cookie` header SHALL be set on every response (with the current session_id and remaining max-age) regardless of whether the DB `expires_at` was updated. This decouples the observable cookie behavior from the internal write threshold, preventing a side-channel where an attacker with a stolen cookie could infer victim activity patterns from the presence/absence of Set-Cookie.

### 3. Cart service as pure functions with explicit DB connection

**Decision:** `cart_service.py` exports free functions that accept a `sqlite3.Connection` parameter. No class, no internal state. Functions return dataclass/named-tuple results (not raw dicts) to carry metadata alongside cart data.

```python
@dataclass
class AddItemResult:
    cart: CartData
    created: bool  # True if new item, False if quantity incremented

def get_cart(conn: sqlite3.Connection, session_id: str) -> CartData: ...
def add_item(conn: sqlite3.Connection, session_id: str, product_id: str, quantity: int) -> AddItemResult: ...
def update_quantity(conn: sqlite3.Connection, session_id: str, product_id: str, quantity: int) -> CartData: ...
def remove_item(conn: sqlite3.Connection, session_id: str, product_id: str) -> CartData: ...
```

**Transaction boundaries:** Functions that perform read-then-write sequences (`add_item`, `update_quantity`) SHALL operate within an explicit `BEGIN IMMEDIATE` transaction to prevent TOCTOU races on stock/quantity checks. `get_cart` (read-only) and `remove_item` (single DELETE, no prior read dependency) do not require explicit transaction management. The route layer does NOT manage transactions — each service function is self-contained.

**Rationale:** Matches the patterns described in CLAUDE.md (services are testable without HTTP, take explicit parameters). Easy to test with in-memory SQLite. The `AddItemResult` lets the route layer select 201 (new item) vs 200 (quantity bump) without a separate existence check.

### 4. Stock validation on add (not reservation)

**Decision:** On `add_item`, check `products.stock >= (existing_cart_quantity + new_quantity)`. If insufficient, raise `InsufficientStockError` with `available` field (total stock, not "remaining after cart" — frontend computes max addable). On `update_quantity`, check `products.stock >= new_absolute_quantity` (the quantity is being SET, not incremented — comparison is against the absolute new value). Stock is NOT reserved — only decremented atomically at checkout.

**Important:** Stock validation on cart-add is best-effort and advisory. Multiple sessions may simultaneously hold items that exceed total stock. The atomic `CHECK (stock >= 0)` constraint enforced within the checkout transaction is the authoritative guard. The cart-add check exists to give users immediate feedback, not to guarantee availability.

**Rationale:** Reservation adds timeout complexity and phantom-stock issues. The core-ecommerce design doc explicitly states: "Stock is not reserved on cart add — only decremented at checkout."

### 5. Quantity limits enforced at service level (Pydantic bound intentionally wider)

**Decision:**
- Max 10 per item (configurable via settings)
- Max 20 distinct items per cart
- Update to quantity 0 → remove the item (DELETE row)
- Custom exceptions: `QuantityLimitError`, `CartFullError`

The Pydantic model `AddToCartRequest` uses `le=99` (not `le=10`) because the per-item limit is configurable and may vary by product in the future. The service layer is the authoritative enforcement point. The Pydantic bound prevents obviously insane values while allowing the business rule to be the tighter constraint.

### 6. CHECK constraints and CASCADE in SQLite as safety net

**Decision:** Add `CHECK (stock >= 0)` to products table, `CHECK (quantity >= 1)` to cart_items, and `ON DELETE CASCADE` on `cart_items.session_id` FK. These are defense-in-depth — service logic should prevent violations, but the DB constraint catches bugs. The CASCADE ensures session cleanup (future) automatically removes orphaned cart items.

**Note on schema migration:** `CREATE TABLE IF NOT EXISTS` won't add constraints to existing tables. Since we're pre-launch with no production data, the schema in `database.py` can be modified directly. Post-launch, this would require a migration.

### 7. Cart response always includes product details (unpaginated by design)

**Decision:** `GET /v1/cart` JOINs products to return full `ProductResponse` embedded in each `CartItemResponse`. Inactive products are excluded from `items` and reported in `unavailable_items` with product_id, product_name, and reason.

The endpoint is intentionally unpaginated: the 20-item distinct cap guarantees a bounded response (max 20 products × ~500 bytes each ≈ 10KB). If the max-items limit is ever raised above 50, pagination should be reconsidered.

**Rationale:** The frontend needs product name, price, image to render the cart. A single JOIN avoids N+1 requests.

### 8. Session middleware skips non-application paths

**Decision:** The middleware maintains a skip-list of path prefixes (`/health`, `/metrics`, `/docs`, `/openapi.json`) that bypass all session logic. These paths do not create sessions, do not set cookies, and do not trigger expiry updates. This prevents monitoring probes from polluting the sessions table.

**Matching semantics:** Exact match for leaf paths (`/health`, `/docs`, `/openapi.json`) and prefix-with-trailing-slash match for directory paths (`/docs/`, `/metrics/`). A request to `/health-records` would NOT match `/health` — only the exact path `/health` matches. Note: `/docs` appears in both lists (exact-match for the Swagger UI root and prefix for sub-paths like `/docs/oauth2-redirect`). This prevents accidental bypass if future routes share a prefix.

### 9. Absolute session lifetime cap (180 days)

**Decision:** Sessions have a hard maximum lifetime of 180 days from `created_at`, regardless of sliding expiry. This limits the exposure window if a cookie is stolen. Combined with session rotation on login/logout, an attacker has at most 180 days to use a stolen cookie.

### 10. Session rotation on login (fixation prevention)

**Decision:** When a user successfully authenticates via Google OAuth, the session ID is rotated: new UUID generated, `cart_items` rows migrated to the new session_id, `user_id` linked, old session row deleted, new cookie set. This is in addition to the already-planned rotation on logout.

**Atomicity:** The entire rotation MUST execute within a single `BEGIN IMMEDIATE ... COMMIT` transaction. The sequence within the transaction is: (1) INSERT new session row, (2) UPDATE cart_items SET session_id = new WHERE session_id = old, (3) DELETE old session row. The UPDATE must precede the DELETE to avoid FK violations regardless of CASCADE presence. If any step fails, the transaction rolls back and the old session remains valid.

**Concurrent request window:** During the brief period between server-side rotation and the client receiving the new cookie, concurrent in-flight requests on the old session_id (e.g., browser pre-fetches, parallel XHR) will find the old session deleted and be treated as first-time visits (new empty session). This is acceptable because: (1) the OAuth callback response carries the new cookie so subsequent requests use it, (2) the window is sub-millisecond in SQLite, (3) implementers should handle `sqlite3.IntegrityError` gracefully on cart writes after rotation rather than crashing.

**Rationale:** Prevents session fixation attacks where an attacker plants a known session cookie and waits for the victim to authenticate.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Threshold expiry (7-day window)** → user who visits on day 29 and then disappears for 30 days | They get 30 more days from the threshold update. Worst case: session lives 37 days from last non-threshold visit. Acceptable. |
| **No stock reservation** → user adds to cart, checks out 10 min later, item sold out | Clear error at checkout ("Item X no longer available — 2 remaining"). User sees stock count on product page. Acceptable UX for low-volume store. |
| **Cart items reference deactivated products** | GET /cart reports them in `unavailable_items` with product_name and reason. Checkout rejects with specific error per unavailable item. |
| **Session table grows unbounded** | `ON DELETE CASCADE` ensures cart_items are cleaned when sessions are deleted. Cleanup job (deferred) runs `DELETE WHERE expires_at < datetime('now')`. At MVP traffic, table stays small for years. |
| **Concurrent add + checkout race** | `CHECK (stock >= 0)` catches the edge case at DB level. Checkout uses a single atomic transaction; if any stock constraint fails, the ENTIRE transaction rolls back. |
| **Session fixation via planted cookie** | Session rotation on login migrates cart but invalidates the old session ID. Attacker's known cookie becomes useless. |
| **Stock-locking DoS (many sessions soft-lock stock)** | Stock is not reserved, so "soft-locking" doesn't actually prevent legitimate purchases — checkout is atomic and only the CHECK constraint gates it. Rate limiting at Nginx level (future) further mitigates. |
| **Absolute lifetime cap forces re-auth** | 180 days is generous. Users who visit more than once per 6 months will need to re-authenticate. Acceptable for security. |

## Open Questions

None — all decisions align with the core-ecommerce design doc, IMPLEMENTATION_PLAN.md Day 3 spec, and address all review council findings.

## Resolved Conflicts

**Cart endpoint paths:** ARCHITECTURE.md originally defined `POST /v1/cart/items`, `PATCH /v1/cart/items/{product_id}`, `DELETE /v1/cart/items/{product_id}`. The implemented code stub and this spec use the shorter `POST /v1/cart`, `PATCH /v1/cart/{product_id}`, `DELETE /v1/cart/{product_id}`. ARCHITECTURE.md has been updated to match — the `/items` sub-resource added unnecessary nesting for a single-resource endpoint that only ever operates on items.
