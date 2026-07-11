## Why

The cart system (Day 3) allows customers to add products and manage quantities, but there is no way to actually place an order. Without checkout, the store cannot process purchases or generate revenue. This is the core transactional capability that makes the e-commerce platform functional — converting browsing intent into committed orders with stock decrements and price snapshots.

## What Changes

- Implement `app/services/order_service.py` with atomic checkout, order retrieval, and status management
- Replace the 501 stub in `app/routes/orders.py` with full CRUD endpoints
- Add admin order management routes to `app/routes/admin.py` (list all orders, update status)
- Implement the order state machine with strictly validated transitions (pending → confirmed → shipped → delivered; cancel from pending/confirmed only)
- Atomic checkout transaction: validate stock → snapshot prices → decrement stock → clear cart → create order
- Stock restoration on cancellation
- Order access control: session-owner or authenticated user can view their own orders

## Capabilities

### New Capabilities
- `checkout-flow`: Atomic conversion of cart to order — stock validation, price snapshotting, stock decrement, cart clearing in a single transaction
- `order-management`: Order CRUD (create via checkout, list own orders, get detail), state machine transitions, access control
- `admin-orders`: Admin-only order listing (all orders, filtered/paginated) and status updates

### Modified Capabilities

## Impact

- **New file:** `app/services/order_service.py` — all business logic for orders
- **Modified:** `app/routes/orders.py` — replace stub with real endpoints
- **Modified:** `app/routes/admin.py` — add order management endpoints
- **Database:** Uses existing `orders` and `order_items` tables (already defined in schema)
- **Dependencies:** Requires working session middleware and products in DB (cart_items must exist). No new pip dependencies.
- **API surface:** `POST /v1/orders`, `GET /v1/orders`, `GET /v1/orders/{id}`, `GET /v1/admin/orders`, `GET /v1/admin/orders/{id}`, `PATCH /v1/admin/orders/{id}/status`
