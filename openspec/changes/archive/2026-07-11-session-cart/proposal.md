## Why

The skeleton app has session middleware that creates cookies and DB rows, but no sliding expiry, no expired-session handling, no format validation of incoming cookies, and no validation of returning sessions. The cart route is a stub returning 501. Without a working cart, there is no path to checkout — the entire purchase funnel is blocked. Session + Cart is the Day 3 critical path for Dev A.

## What Changes

- **Session middleware hardened:** Validate cookie format (UUID v4 regex before DB hit), validate returning sessions (exists in DB + not expired + within absolute lifetime), implement sliding 30-day expiry with 7-day threshold (only write when near expiry), reject/replace invalid cookies, skip non-application paths (health checks).
- **Session security:** Absolute 180-day lifetime cap, session rotation on login (fixation prevention), path-exclusion list for monitoring endpoints.
- **Cart service layer:** `get_cart`, `add_item`, `update_quantity`, `remove_item` — all keyed by session_id, with immediate stock validation (409 on insufficient), quantity limits (max 10/item, max 20 distinct items), and update-to-zero semantics (treated as remove).
- **Cart routes implemented:** Replace the 501 stub with real `GET /v1/cart`, `POST /v1/cart`, `PATCH /v1/cart/{product_id}`, `DELETE /v1/cart/{product_id}` endpoints. Path parameter validation on PATCH/DELETE.
- **Database constraints:** Add `CHECK (stock >= 0)` on products table, `CHECK (quantity >= 1)` on cart_items, `ON DELETE CASCADE` on cart_items.session_id FK.
- **Unavailable items reporting:** `GET /v1/cart` reports deactivated products with product_name and reason (not just opaque IDs).

## Capabilities

### New Capabilities
- `cart-management`: Shopping cart CRUD — add, update quantity, remove items, view cart with product details and computed totals. Stock validation on add, quantity limits enforced. Unavailable items reported with names. Path parameter validation.
- `session-lifecycle`: Session cookie format validation, DB validation, sliding expiry with threshold, absolute lifetime cap, login rotation, path exclusion. Ensures `request.state.session_id` always points to a valid, non-expired session row.

### Modified Capabilities
<!-- No existing specs to modify — these are new capabilities on a greenfield codebase. -->

## Impact

- **Code:** `app/middleware/session.py` (hardened with format check, threshold expiry, absolute cap, path exclusion), new `app/services/cart_service.py`, rewritten `app/routes/cart.py`, schema additions in `app/database.py` (CHECK constraints, ON DELETE CASCADE, index)
- **APIs:** `GET/POST/PATCH/DELETE /v1/cart` and `/v1/cart/{product_id}` — new functional endpoints replacing stubs
- **Models:** `CartResponse.total` → `total_cents` rename, new `UnavailableItem` model, `AddItemResult` dataclass in service
- **Dependencies:** None new (uses existing FastAPI, Pydantic, SQLite stack)
- **Config:** New settings: `session_absolute_max_age`, `session_expiry_threshold`, `cart_max_quantity_per_item`, `cart_max_distinct_items`, `session_skip_paths`, `session_cookie_secure`
- **Testing:** New test suite for cart service + route layer; session middleware tests expanded for format validation, expiry threshold, absolute cap, path exclusion, rotation on login
