## Why

Atelier Marie needs to accept orders even when finished goods are not currently on hand, because products can be crafted after purchase and shipped once ready. The current flow treats stock shortages as hard failures, which blocks sales and gives the team no first-class way to distinguish ready-to-ship orders from paid orders waiting on production.

## What Changes

- Allow checkout to accept product shortages for active products instead of rejecting the order with `INSUFFICIENT_STOCK`.
- Add explicit order fulfillment states and data that distinguish paid orders waiting for production from orders that are fully ready to ship.
- Change stock handling so checkout records shortages/backorder intent without pretending finished goods were already issued from inventory.
- Update product, cart, checkout, confirmation, and admin surfaces to show “order now, ships when complete” messaging instead of treating `stock == 0` as universally unavailable.
- Preserve the business rule that mixed-availability orders ship only when the full order is ready.

## Capabilities

### New Capabilities
- `crafted-later-fulfillment`: Production-aware fulfillment state and readiness tracking for orders that can be accepted before all items are physically available.

### Modified Capabilities
- `order-management`: Order lifecycle, cancellation, and fulfillment transitions must support production-waiting orders.
- `checkout-flow`: Checkout must create orders for active products even when on-hand stock is insufficient, with upfront payment and ship-when-complete behavior.
- `product-public-api`: Public product responses must expose orderability/availability semantics beyond raw stock.
- `cart-management`: Cart validation must stop using raw stock as a universal add/update blocker for active products.
- `cart-ui`: Cart interactions and copy must support crafted-later ordering rather than disabling out-of-stock items.
- `product-detail`: Product detail must show crafted-later purchase behavior and lead-time messaging instead of only “Out of Stock”.
- `order-confirmation-ui`: Confirmation must explain that crafted-later orders are accepted and ship when the full order is ready.
- `admin-orders`: Admin order detail and workflow must surface production-waiting readiness and prevent premature shipment.
- `api-models`: Public and admin API contracts must include the new fulfillment/availability fields.

## Impact

- Backend: order models, order service, cart service, product service, admin order workflows, migrations, and validation logic.
- Frontend: cart context/components, product cards/detail, checkout, confirmation, admin order detail, and localized copy.
- Data model: new order/product fields and adjusted inventory/fulfillment bookkeeping.
- Tests: order, cart, product, checkout, admin, integration, and mock API coverage.
