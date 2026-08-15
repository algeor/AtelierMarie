## 1. Schema and shared models

- [x] 1.1 Add database fields for order fulfillment status and order-item allocated/backordered quantities, with legacy-safe defaults.
- [x] 1.2 Extend backend Pydantic models and frontend TypeScript types with crafted-later availability and fulfillment fields.

## 2. Backend fulfillment logic

- [x] 2.1 Update product/cart services to stop treating raw stock as a universal blocker for active products.
- [x] 2.2 Update checkout to allocate available stock, persist backordered quantities, and set order fulfillment status.
- [x] 2.3 Add admin fulfillment-ready logic that allocates outstanding quantities when stock becomes available.
- [x] 2.4 Block shipment while fulfillment status is awaiting production and restore only allocated quantities on cancellation.

## 3. Storefront and admin UI

- [x] 3.1 Update storefront product and cart UI to support crafted-later ordering and messaging.
- [x] 3.2 Update checkout and confirmation UI to explain upfront payment plus ship-when-complete behavior.
- [x] 3.3 Update admin order detail/actions to show fulfillment readiness and allow marking orders ready.

## 4. Verification

- [x] 4.1 Update backend tests for cart, checkout, order lifecycle, and inventory integration.
- [x] 4.2 Update frontend tests and mock API for crafted-later availability and fulfillment behavior.
- [x] 4.3 Run targeted backend and frontend test suites covering the changed flows.
