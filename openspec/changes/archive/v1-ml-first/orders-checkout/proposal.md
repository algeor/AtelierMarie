## Why

AtelierMarie needs to capture purchases as transactional records to serve as the business source of truth (refunds, status tracking, order history) while simultaneously feeding purchase events into the ML analytics layer. Without an orders system, the platform has no way to close the loop between product browsing and actual conversions — the strongest signal for collaborative filtering and recommendation quality.

## What Changes

- New `orders` and `order_items` SQLite tables with full status lifecycle
- `POST /v1/orders` — direct order creation endpoint (accepts items in request body for programmatic/API use)
- `GET /v1/orders` — paginated order history for authenticated users
- `GET /v1/orders/{id}` — order detail with items (auth or session-match for anonymous)
- `PATCH /v1/orders/{id}/status` — admin-only status transitions with state machine validation
- Purchase event emission to JSONL buffer after order commit (fire-and-forget)
- Anonymous checkout support (user_id nullable, session_id always required)
- Price snapshot at purchase time (`price_at_purchase` per item, immutable)
- Order status state machine: pending → confirmed → shipped → delivered, with cancel/refund branches
- `payment_method` enum field on orders (MVP: "cod" only, extensible for future methods)
- Integration with cart-management: `POST /v1/cart/checkout` delegates to order creation service (items sourced from server cart)

## Capabilities

### New Capabilities
- `order-checkout`: Order creation (checkout) with atomic SQLite transaction, product validation, price snapshotting, and purchase event emission
- `order-management`: Order retrieval (detail + list), status state machine, admin status updates, access control (owner or session-match)

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **Database**: Two new SQLite tables (`orders`, `order_items`) with foreign keys to `users` and `products`
- **API**: New `/v1/orders` route group (4 endpoints)
- **Event pipeline**: New `purchase` event type emitted post-checkout, flows through existing JSONL → DuckDB path
- **Auth**: Uses existing `get_current_user` and `get_current_user_optional` dependencies
- **Product catalog**: Read dependency — validates product existence/active status and reads current price
- **Session system**: Orders always linked to session_id for anonymous support
