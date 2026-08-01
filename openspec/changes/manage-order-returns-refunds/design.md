## Context

The current app has basic order states (`pending`, `confirmed`, `shipped`, `delivered`, `cancelled`) and basic payment states (`pending`, `paid`, `cod_pending`, `failed`, `refunded`). Checkout decrements stock and cancellation restores stock. Speedy tracking can surface courier statuses, but tracking does not drive the order state machine. Econt currently has pricing and office data, but no tracked fulfillment/trace source in this branch. Stripe checkout and webhook audit handling exist, but admin `mark_refunded` is local status-only and the app does not initiate Stripe refunds.

Real operations need more detail: customers abandon card payment, do not collect courier-office orders, refuse delivery, return delivered goods, or receive parcels damaged/lost by the courier. These must be handled without mixing fulfillment, payment, courier evidence, stock, and accounting records.

Econt has two relevant official API surfaces:

- EE `LabelService` under `https://ee.econt.com/services/Shipments/`, already used for price calculation through `LabelService.createLabel` with `mode=calculate`. Its shipment schema includes return/reject instruction fields such as `returnParcelDestination`, `daysUntilReturn`, `returnParcelPaymentSide`, `rejectAction`, `executeIfNotTaken`, and tracking/status fields such as `shortDeliveryStatusEn`, `trackingEvents`, `returnShipmentURL`, `previousShipmentNumber`, `nextShipments`, and COD fields `cdCollected*`/`cdPaid*`.
- Econt Delivery `OrdersService` under `https://delivery.econt.com/services/`, with `updateOrder`, `createAWB`, `getTrace`, and `deleteLabel`. The historical `econt` branch already modeled this as a thin client plus fulfillment service, but that source is not present in the current branch.

Econt office fulfillment also requires Econt's native office `code`. The current normalized `data/econt_offices.json` exposes only internal ids like `econt-1053`, while official Econt nomenclature distinguishes `id` and `code`.

## Goals / Non-Goals

**Goals:**

- Keep order, payment, courier, stock, and accounting state separate.
- Add admin-controlled return/uncollected workflows for COD and card orders.
- Add real Stripe refund initiation with idempotency and webhook confirmation.
- Add return and refund audit records that support accounting follow-up.
- Add abandoned card payment review so admins can call the customer before cancelling or converting to payment on delivery.
- Add scheduled courier status polling so return/uncollected/delivery evidence is discovered without waiting for courier push notifications.
- Add Econt-specific trace/return/COD evidence handling based on the official Econt APIs.
- Preserve Econt office codes so Econt office orders can be fulfilled and returned correctly.
- Support manual courier claim recordkeeping for lost/damaged shipments.
- Prevent automatic courier scans from refunding, restocking, or closing orders.
- Keep public Terms and FAQ content consistent with the operational return/refund rules.

**Non-Goals:**

- No exchange workflow. A return and a new purchase are two separate processes.
- No courier claim API integration. Admins enter claim ID/status/amount manually.
- No full accounting ledger, invoicing, VAT engine, or payout import in this change.
- No automatic restock based only on courier tracking.
- No automatic refund based only on courier tracking.

## Decisions

### Separate return cases from orders

Add `order_returns` and `order_return_events` instead of storing every return/refund/courier field on `orders`.

Rationale: an order can have operational history and audit details that outgrow a single status column. Separate records preserve the simple order state while allowing reason, source, inspection, courier claim, fees, notes, and admin actor data.

Alternative considered: add many nullable columns to `orders`. Rejected because it mixes current fulfillment state with historical return-case details and makes future partial returns harder.

### Use small order states plus reason codes

Extend order statuses with `return_in_transit` and `returned`. Use return reasons such as `not_picked_up`, `refused_delivery`, `customer_return`, `wrong_address`, `unreachable_customer`, `damaged_by_courier`, `lost_by_courier`, and `merchant_error`.

Rationale: `returned` is the physical outcome. The reason explains why. This avoids adding a separate terminal order status for every courier/customer scenario.

Alternative considered: add `uncollected`, `refused`, `damaged`, and `lost` as order statuses. Rejected because those are reasons or issue classes, not distinct fulfillment states.

### Add explicit payment review and refund states

Add payment states for `review_required`, `refund_pending`, `partially_refunded`, and dispute outcomes. `review_required` is used for abandoned card payments that need an admin callback before cancellation or COD conversion.

Rationale: `failed` means payment failed or was abandoned; it does not capture that the order still needs customer contact. Refund states must also distinguish requested refunds from confirmed refunds.

Alternative considered: keep using `failed` for abandoned checkout and rely on notes. Rejected because it would allow missed callbacks and weak filtering.

### Stripe refunds are initiated by admin action and confirmed by webhook

Admin refund action validates the order, creates a Stripe refund with an idempotency key, writes a `payment_refunds` row, and sets payment status to `refund_pending`. Stripe refund webhook/event processing finalizes `refunded`, `partially_refunded`, or review-needed failure state.

Rationale: Stripe is the payment source of truth for card refunds. Local status must not claim money was refunded before provider confirmation.

Alternative considered: keep manual mark-refunded only. Rejected because it creates reconciliation risk and cannot prove the refund happened.

### Courier tracking creates review signals only

Speedy/Econt returned or failed tracking statuses create admin review/audit entries and update display courier status, but do not update order status, payment status, refund state, or stock automatically.

Rationale: courier scans are evidence, not policy decisions. Admin must decide refund amount, restock, courier fees, and customer communication.

Alternative considered: auto-mark returned/uncollected from courier scan. Rejected because it risks wrong refunds and premature restocks.

### Poll courier status instead of depending on notifications

Implement courier polling as an async idempotent service called directly from an async FastAPI background loop. The courier poller MUST NOT use worker threads or `asyncio.to_thread`; provider clients used by the poller must be async. Poll only active shipments with tracking/shipment identifiers. Store last poll time, next poll time, attempt count, lease expiry, normalized status, raw redacted payload, and admin-safe error details.

Rationale: Speedy/Econt push notifications are not guaranteed to be configured or reliable, and this workflow must discover uncollected/refused/returned parcels. The app already has async in-process lifespan loops; the courier poller should follow that shape but remain async-only because courier calls are network I/O and should not consume threadpool capacity. Durable leases prevent duplicate polling across multiple workers.

Alternative considered: wait for courier notifications/webhooks only. Rejected because missed webhooks would hide uncollected orders. Alternative considered: external cron only. Rejected as the only path because local/dev and simple deployments already run background loops. Alternative considered: wrapping synchronous poll work in `asyncio.to_thread`. Rejected because the requirement is async-only and the provider work is naturally async HTTP I/O.

Polling remains evidence collection. It must not refund, restock, mark COD settled, close return cases, or force order/payment transitions by itself.

### Econt is not just a manual fallback

Add a first-class Econt return-signal path. When credentials and shipment numbers are available, Econt orders should refresh trace/status through Econt Delivery `OrdersService.getTrace` or the EE shipment status response used by the active fulfillment implementation. Normalize `Is returning to sender`, `Returned to sender`, and tracking event types such as `failed_delivery`, `is_returning_to_sender`, and `returned_to_sender` into admin review signals.

Rationale: Econt exposes enough status, return-shipment, and COD evidence to support the same review workflow as Speedy. Treating Econt only as manual import would leave uncollected Econt office orders under-specified.

Alternative considered: keep Econt manual until later. Rejected because the official APIs and historical branch show the integration shape clearly enough to specify now.

### Econt office code must be preserved

Extend office data and checkout delivery snapshots with the native Econt office `code` separately from internal `office_id`.

Rationale: Econt's official docs identify offices by `code` for label and return destinations. Internal ids like `econt-1053` are not enough to create reliable labels or return instructions.

Alternative considered: derive the code later from office id. Rejected because existing normalized data may not carry enough information and stale/manual orders need explicit repair paths.

### Econt return/reject instructions are configured, not implicit

When creating Econt labels, include configured return/reject instruction fields for unclaimed or refused parcels, such as days until return, return destination, return payment side, and reject action/payment side.

Rationale: uncollected office orders are central to this change. Econt has first-class fields for unclaimed/rejected shipments, so the app should not depend on unclear courier defaults.

Alternative considered: record only after the courier returns the parcel. Rejected because label-time instructions affect what the courier will do when a parcel is refused or unclaimed.

### Customer policy copy follows operational truth

Update Terms as the detailed public policy source for returns, refunds, uncollected/refused courier parcels, return shipping, inspection/restock timing, card refunds, payment-on-delivery cases, and courier damaged/lost parcels. FAQ should stay short: answer the common uncollected/refused parcel question and link to the Terms returns section for the full policy.

Rationale: admins need operational flexibility for review, refund amount, return fees, stock inspection, and courier claim handling. Public copy must not promise automatic refunds, automatic restocks, or courier-status-driven outcomes.

Alternative considered: put the full policy in FAQ. Rejected because FAQ should remain practical and brief while Terms carries the detailed legal and policy language.

### Port the econt branch selectively

The `econt` branch is a strong base for Econt fulfillment, but it should be ported selectively rather than merged wholesale. Its useful pieces are Econt settings, office-code preservation, redaction helpers, courier metadata columns, `order_courier_events`, admin fulfillment endpoints, label/AWB actions, trace refresh, and the admin Econt fulfillment panel.

Required adjustments when porting:

- Convert `EcontDeliveryClient` from synchronous `httpx.Client` to async `httpx.AsyncClient` for all courier polling/trace paths.
- Do not use worker threads or `asyncio.to_thread` for courier polling.
- Remove or disable `auto_delivered_on_trace`; trace refresh and scheduled polling create evidence/review signals only.
- Treat `auto_confirm_on_label` as unsafe by default. Label creation must not bypass abandoned-payment review or admin confirmation rules.
- Extend Econt models beyond the branch's thin `EcontShipmentStatus` so return/COD evidence is typed: `shortDeliveryStatusEn`, tracking event type, `returnShipmentURL`, `previousShipmentNumber`, `nextShipments`, `lastProcessedInstruction`, `cdCollected*`, and `cdPaid*`.
- Reconcile the two Econt API families: current pricing uses EE `LabelService.createLabel` with `mode=calculate`; the branch uses Delivery `OrdersService` for fulfillment. Keep a provider abstraction so status evidence is normalized independent of API family.
- Merge with the current payment integration instead of replacing it. The `econt` branch is older in some areas and must not remove Stripe/payment settings, admin payment review, analytics, or unrelated frontend changes from `extras`.

Porting order:

1. Office code and Econt settings/redaction.
2. Courier metadata and `order_courier_events` schema, extended with polling fields/leases.
3. Async Econt client and fulfillment mapping.
4. Admin Econt panel/endpoints, adjusted for current payment/order states.
5. Async trace polling and return/COD evidence normalization.
6. Return/refund/admin workflows on top of the Econt evidence layer.

### Coordinate with parallel Speedy admin parity work

`speedy-admin-parity` is being implemented in parallel, so this change should keep shared admin surfaces conservative. Return/refund controls should live on the existing order detail and report endpoints unless a broader admin layout change is already owned by the Speedy parity change.

Rationale: both changes touch admin courier operations. Avoiding broad sidebar/navigation rewrites and treating Speedy tracking integration as evidence-only reduces merge risk while preserving the return/refund workflow.

Alternative considered: fold Speedy admin parity UI work into this change. Rejected because it would mix two active scopes and make it harder to review courier parity separately from return/refund accounting behavior.

### Stock returns only after physical inspection

Cancellation before shipping restores stock. Shipped/delivered returns do not restore stock until admin marks the item received and chooses a restock decision.

Rationale: physical inventory may be damaged, lost, or incomplete even if courier status says returned.

Alternative considered: restore stock when courier reports returned. Rejected because it can oversell damaged or missing products.

### Abandoned card payment becomes callback review

When card payment is abandoned/expired, the order remains unshippable and enters payment review. Admin calls the customer. If the customer confirms, admin may convert the order to payment on delivery. If not confirmed, admin cancels or lets reservation expiry release stock.

Rationale: this preserves sales opportunity without shipping unpaid orders.

Alternative considered: automatically cancel abandoned card orders. Rejected because the business wants manual customer recovery.

## Risks / Trade-offs

- Schema change touches constrained status fields -> migrate with explicit CHECK updates and compatibility tests.
- Refund webhook timing can race admin actions -> use idempotency keys, event deduplication, and total-refunded validation.
- Partial refunds may need line-level data -> start with order-level refund amount, but design tables so line-level allocation can be added.
- Admin workflow can become too broad -> phase implementation and keep the first UI focused on return review, receive/inspect, refund, and close.
- Accounting expectations may exceed the app -> provide reconciliation records/exports, but do not present this as a full ledger.
- Courier statuses differ between providers -> normalize only to review signals and keep raw payloads in audit details.
- Polling in multiple app workers could duplicate calls -> use database leases and batch limits per order/provider.
- Polling too aggressively could hit courier rate limits -> configure interval, batch size, and backoff; poll only active shipments.
- Econt has two API families with overlapping concepts -> isolate the active client behind an Econt fulfillment/trace service and store normalized evidence independent of API family.
- Econt office codes are missing from current normalized data -> update normalization and provide an admin repair path for old orders.

## Migration Plan

1. Add new status values, return/refund/settlement tables, and nullable fields without changing existing rows.
2. Backfill existing paid/refunded/failed data into payment rows only where needed for consistency.
3. Add backend services and tests for return cases, refund records, and guarded transitions.
4. Add admin API/actions and UI controls behind existing admin auth.
5. Add Stripe refund creation and webhook finalization.
6. Add courier status polling service with leases, backoff, batch limits, and manual refresh support.
7. Add courier review-signal creation for Speedy and Econt, with Econt trace refresh guarded by credentials and shipment number availability.
8. Preserve Econt office codes in office data and checkout/order snapshots; provide repair path for older Econt orders without code.
9. Update Terms and FAQ copy, localized in English and Bulgarian, after operational policy wording is finalized.
10. Add reconciliation exports/reports after operational data is captured.

Rollback: keep migrations additive where possible. If UI/API rollout is paused, existing orders continue using current statuses and new tables remain unused.

## Open Questions

- For card-paid uncollected orders, should refunds include shipping or product amount only?
- Should partial refunds initially be order-level amounts only, or must they allocate to order items in phase 1?
- Should lost/damaged shipments use a dedicated `shipment_issue` status, or remain return cases with reason codes?
- Should COD uncollected use payment status `failed`, `uncollected`, or a COD-specific settlement state?
- How should custom/personalized product return warnings be represented in product/order item data?
