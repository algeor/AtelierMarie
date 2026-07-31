## Why

The current order lifecycle stops at shipped, delivered, or cancelled, but real courier operations include abandoned card payments, uncollected parcels, refusals, damaged/lost shipments, refunds, and COD settlement gaps. This change gives admins a controlled workflow for those cases without letting courier scans silently refund, restock, or close orders.

## What Changes

- Add a manual admin-driven return/uncollected order workflow for shipped and delivered orders.
- Add return case records with reason, source, inspection/restock decision, courier fees, manual courier claim details, and audit events.
- Add payment refund records and real Stripe refund initiation for full and partial refunds.
- Add refund-related payment states such as refund pending, partially refunded, and refunded confirmation through provider events.
- Add abandoned card payment handling: do not ship, place in admin callback/review, and allow admin-confirmed conversion to payment on delivery.
- Add COD-specific handling for uncollected/refused orders and COD settlement reconciliation records.
- Add admin actions for marking uncollected/refused/return in transit, receiving and inspecting returns, issuing refunds, recording courier fees/claims, and recording COD settlement.
- Add courier signal handling so Speedy/Econt returned or failed statuses create admin review signals but do not automatically mutate order/payment/stock state.
- Add scheduled courier status polling so the app does not depend on courier push notifications/webhooks.
- Add Econt-specific handling for official trace/status data, return/reject instructions, unclaimed-parcel signals, COD collection/paid evidence, and native office codes.
- Explicitly exclude exchange workflows for now; returns and new purchases remain separate processes.

## Capabilities

### New Capabilities

- `order-returns-refunds`: Return cases, uncollected orders, refund records, stock inspection, courier claim recordkeeping, COD settlement records, and accounting-oriented reconciliation data.
- `courier-status-polling`: Scheduled and manual polling of active courier shipments with leases, backoff, event storage, and review-signal generation.
- `econt-return-signals`: Econt trace refresh, return/reject/unclaimed signal normalization, COD settlement evidence, native office-code requirements, and manual fallback behavior.

### Modified Capabilities

- `order-management`: Extend the order state machine and stock rules for return in transit, returned, and post-shipment return handling.
- `admin-orders`: Add admin actions, filters, and detail data for returns, uncollected orders, refunds, callback review, courier claims, and COD settlement.
- `checkout-flow`: Change abandoned card payment behavior so unpaid card orders require admin review/callback before any shipment and can be converted to payment on delivery only after customer confirmation.
- `courier-offices-data`: Preserve Econt native office codes in office data and checkout/order delivery snapshots so Econt fulfillment and return handling can address the correct office.
- `speedy-integration`: Treat returned/failed tracking statuses as admin review signals while preserving the rule that tracking remains read-only and does not drive order/payment/stock state automatically.

## Impact

- Backend models and database schema for orders, payments, return cases, refund records, audit events, courier claim fields, and COD settlement fields.
- Async background polling service/loop for active courier shipments, with no thread offloading in the courier poller.
- Admin order APIs and frontend views for return/refund/callback/claim/settlement actions.
- Stripe integration for refund creation, refund webhooks, idempotency, and double-refund protection.
- Speedy tracking handling plus Econt trace/status handling from Econt Delivery `OrdersService.getTrace` and/or EE `LabelService` shipment status responses.
- Stock adjustment logic for cancellation versus physical return inspection.
- Reports/exports used for accounting reconciliation of Stripe refunds, COD settlements, courier fees, return reasons, and inventory adjustments.
