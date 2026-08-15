## Context

The current storefront, cart, checkout, and order management flows use `products.stock` as both the source of truth for physical on-hand inventory and the rule for whether a customer is allowed to purchase. Checkout fully rejects shortages, decrements stock for the full ordered quantity, and has no separate fulfillment state for “paid, accepted, but still waiting to be crafted”. Admin shipment flow likewise assumes every confirmed order is physically ready once payment and tracking are in place.

This change introduces crafted-later ordering across the catalog. Customers pay upfront, orders may mix on-hand and not-yet-crafted quantities, and the atelier ships only when the complete order is ready. The design must preserve the existing inventory model enough to fit the current codebase, while stopping the system from treating shortages as hard checkout failures.

## Goals / Non-Goals

**Goals:**
- Accept checkout for active products even when on-hand stock is insufficient.
- Reserve currently available finished goods at checkout so existing stock cannot be oversold.
- Record order-level and item-level production shortfalls explicitly.
- Block shipment until the outstanding shortfall is allocated and the full order is ready.
- Expose customer-facing availability messaging that distinguishes “available now” from “crafted later”.
- Keep cancellation and inventory restoration correct for both already-reserved and not-yet-allocated quantities.

**Non-Goals:**
- Building a full production planning or workshop scheduling system.
- Automatically linking production batches to orders or auto-allocating fresh stock in the background.
- Supporting partial shipment or split shipments for one order.
- Reworking the entire ledger-managed inventory model away from its current stock cache approach.

## Decisions

### 1. Represent production waiting with a separate fulfillment field, not a new order status
Orders keep the existing customer-visible lifecycle (`pending`, `confirmed`, `shipped`, etc.) and gain a separate `fulfillment_status` field with values `ready` and `awaiting_production`.

Rationale:
- This minimizes disruption across existing order history, timeline UI, and admin payment flows.
- The shortage problem is about fulfillment readiness, not payment/order existence.
- Shipment can be blocked by fulfillment readiness without inventing many new status transitions.

Alternatives considered:
- Add a new order status such as `awaiting_production`: rejected because it would force a broader rewrite of timeline, transitions, filters, and tests for little extra value.
- Infer readiness from stock on the fly: rejected because readiness must be snapshotted per order, not guessed from mutable catalog stock.

### 2. Reserve only the available quantity at checkout
For each order item, checkout computes:
- `allocated_quantity`: units immediately reserved from on-hand stock
- `backordered_quantity`: units still needing production

Checkout decrements stock only for `allocated_quantity`. If any line has `backordered_quantity > 0`, the order gets `fulfillment_status = 'awaiting_production'`; otherwise it starts as `ready`.

Rationale:
- This prevents overselling currently available finished goods.
- It avoids pretending not-yet-crafted items already exist in inventory.
- It gives cancellation an exact quantity to restore.

Alternatives considered:
- Allow product stock to go negative: rejected because it destroys the meaning of on-hand stock and conflicts with the current DB constraint and admin tooling.
- Reserve nothing until production completes: rejected because it would oversell the stock that does already exist.

### 3. Track shortfall directly on `order_items`
`order_items` gain `allocated_quantity` and `backordered_quantity`. Admin and customer responses derive item-level readiness from these fields.

Rationale:
- Order items already hold the commercial snapshot; adding fulfillment snapshot data here keeps one row as the source of truth for both pricing and fulfillment.
- Order-level readiness can be derived and audited from the sum of line shortages.

Alternatives considered:
- Separate allocation table: rejected as unnecessary complexity for the current scale.
- Store only order-level shortage metadata: rejected because admin needs item-level detail to know what still needs crafting.

### 4. Add an explicit admin “mark ready” step before shipment
New admin action: mark order fulfillment ready. It is only valid for orders in `awaiting_production`. The action checks that every outstanding `backordered_quantity` is now available in current stock, reserves those units, sets each line’s `backordered_quantity` to `0`, increments `allocated_quantity`, and flips the order to `fulfillment_status = 'ready'`.

Shipment remains blocked unless `fulfillment_status = 'ready'`.

Rationale:
- It fits the business rule that orders ship only when complete.
- It avoids hidden auto-allocation logic and keeps the atelier in control of when crafted stock is committed to a specific order.

Alternatives considered:
- Auto-allocate stock when inventory rises: rejected because the current system has no reliable event pipeline for that, and implicit reservation would be hard to reason about.
- Allow shipping with outstanding backordered lines: rejected by business requirement.

### 5. Keep “all products orderable” as a derived global rule
There is no per-product allow-backorder flag. For active products, `can_order` is always true. Public APIs expose derived fields such as `availability_status` and `available_now` so UI stops using raw `stock == 0` as “not buyable”.

Rationale:
- The business decision applies to the full catalog.
- Avoids unnecessary product configuration and migration overhead.

Alternatives considered:
- Product-level toggle: rejected because it adds complexity without matching the chosen business rule.

### 6. Keep `in_stock` filtering semantics unchanged
`GET /v1/products?in_stock=true` continues to mean `stock > 0`, even though out-of-stock items remain orderable.

Rationale:
- Existing filtering behavior stays useful for customers who want items available immediately.
- This avoids renaming query params or breaking current UI and tests more than necessary.

### 7. Apply minimal ledger-managed changes
For ledger-managed products, checkout records sale-issue movement only for the immediately allocated quantity. When admin marks the order ready, the newly available quantity is reserved then via the same inventory path.

Rationale:
- Keeps current accounting/inventory integration mostly intact.
- Limits the blast radius in the ledger/COGS system.

Alternatives considered:
- Introduce a brand-new inventory reservation movement type: rejected for this change because it would cascade into valuation, COGS, and admin analytics work far beyond the requirement.

## Risks / Trade-offs

- [Risk] Reserving only part of an order means admin must perform an extra readiness action before shipping. → Mitigation: add explicit admin UI, readiness badges, and clear shipment blocking.
- [Risk] Ledger-managed semantics still use sale-issue as the reservation mechanism for allocated quantity. → Mitigation: limit it to actually allocated units and keep backordered quantity out of that path until ready.
- [Risk] Customers may misunderstand “available later” as immediate availability. → Mitigation: add storefront and confirmation copy that states orders may be crafted after purchase and ship when complete.
- [Risk] Cancellation logic becomes quantity-sensitive. → Mitigation: restore only `allocated_quantity`, not ordered quantity, and cover with service/integration tests.

## Migration Plan

1. Add schema columns for order/item fulfillment tracking with defaults that classify legacy orders as `ready` and legacy line items as fully allocated.
2. Deploy backend that writes and reads the new fields while preserving current public contracts.
3. Deploy frontend updates that consume the new availability and fulfillment fields.
4. Verify legacy orders remain visible and shippable without manual data repair.

Rollback:
- Frontend can roll back independently because old UI paths ignore the new fields.
- Backend rollback is safe only before new checkout writes depend on the columns; after rollout, schema rollback should be avoided without a data migration plan.

## Open Questions

- None for initial implementation. The user already confirmed: all products are eligible, payment is upfront, and mixed-availability orders ship only when complete.
