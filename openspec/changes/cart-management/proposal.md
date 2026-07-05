# Cart Management — Proposal

## Why

A luxury e-commerce UX requires cart persistence across tabs, browser restarts, and devices (after login). Client-only cart is fragile — server-side state keyed by session_id gives reliable cart recovery, multi-tab sync, and enables server-side stock validation before checkout. The cart also feeds add_to_cart/remove_from_cart events into the ML pipeline.

## What Changes

- New `cart_items` table in SQLite (session_id, product_id, quantity, added_at)
- GET /v1/cart — return cart contents with product details and totals
- POST /v1/cart/items — add item to cart (validate stock, increment if exists)
- PATCH /v1/cart/items/{product_id} — update quantity (0 = remove)
- DELETE /v1/cart/items/{product_id} — remove item
- POST /v1/cart/checkout — atomic checkout (validate stock, create order, decrement stock, emit purchase event, clear cart)
- Cart events emitted to event pipeline (add_to_cart, remove_from_cart)

## Capabilities

### `cart-state` (new)

Server-side cart CRUD keyed by session_id with stock validation.

### `cart-checkout` (new)

Atomic cart-to-order conversion with stock decrement, event emission, and cart clearing.

## Impact

- New SQLite table (`cart_items`)
- 5 new endpoints under /v1/cart
- **Depends on**:
  - product-catalog (stock validation)
  - session-identity (session_id)
  - event-ingestion-pipeline (event emission)
  - orders-checkout (order creation)
