# Cart Management — Design

## Context

The platform has products stored in SQLite, sessions tracked via the X-Session-ID header, and events flowing to DuckDB. We need cart persistence that works for anonymous users without requiring authentication.

## Goals

- Instant UI feedback (frontend does optimistic updates, server is source of truth)
- Stock validation on add
- Atomic checkout (all-or-nothing order creation)
- Cart events emitted for ML pipeline consumption

## Non-Goals

- Wishlists or saved-for-later functionality
- Cart expiry/cleanup (MVP — carts persist indefinitely)
- Cart merging on login (future scope)
- Quantity limits per product
- Shipping calculation

## Decisions

### 1. Cart in SQLite

Same `atelier.db` as products/orders. Foreign key to products table. Atomic checkout transaction spans cart_items + orders + order_items + stock decrement in a single transaction.

### 2. Session-keyed, not user-keyed

Anonymous users have carts. When a user logs in, the cart stays associated with the session. Cart merge across sessions is future scope.

### 3. Optimistic UI pattern

Frontend updates UI instantly on add/remove/quantity change, then syncs to server in the background. Server response confirms or corrects (e.g., stock insufficient → server returns actual available quantity).

### 4. Checkout reads from server cart

POST /v1/cart/checkout takes no request body. Server reads cart_items for the session, validates stock, and creates the order. This eliminates client-server cart drift at the critical moment of purchase.

### 5. Fire-and-forget event emission

add_to_cart and remove_from_cart events are emitted to the JSONL buffer post-mutation. If event write fails, the cart operation still succeeds. Cart functionality is never blocked by the event pipeline.

### 6. Cart-to-order delegation

Checkout creates the order using the same service layer as orders-checkout, just sourcing items from cart_items instead of the request body.

## Risks

- **Deleted/deactivated products in cart** — Cart items may reference products that are later deactivated or deleted. Handled gracefully: GET /v1/cart filters out inactive products (with a flag), checkout rejects with a clear error identifying unavailable items.
- **Unbounded cart rows** — No cart expiry means abandoned carts accumulate indefinitely. Acceptable for MVP traffic levels. A cleanup job (e.g., remove carts older than 30 days) can be added later.
