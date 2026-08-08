# Order Returns, Uncollected Orders, and Refunds Plan

Last updated: 2026-08-01

Living planning note for courier uncollected orders, returns, refunds, stock handling, and accounting impact.

## Core Rule

Keep these states separate:

- Order state: where the goods are.
- Payment state: what happened to the money.
- Courier state: evidence from Speedy/Econt, not the final business decision.
- Stock state: physical inventory, restored only when appropriate.
- Accounting state: what must reconcile with Stripe, couriers, fees, and reports.

Courier tracking should create review signals. It should not silently refund, restock, or close an order.

## Conversation Context Captured

This note captures the payment/order review we did around the extras branch and the follow-up discussion about uncollected courier orders.

Questions covered:

- What does extras introduce on top of main for payments?
- Do the extra order/payment tables help accounting?
- What happens when Speedy/Econt orders are not collected?
- How should this work for COD and card payments?
- Can the app issue Stripe refunds?
- What scenarios are still missing?

## What Extras Introduces Over Main

The extras branch adds a stronger payment foundation, especially for card payments and admin payment review.

Important additions identified during review:

- Stripe Checkout support for card orders.
- Stripe retry checkout session support.
- Payment settings and Stripe configuration health checks.
- Payment rate limiting for Stripe session creation.
- Payment rows and payment events for audit/reconciliation.
- Stripe webhook handling for successful checkout, expired sessions, failed PaymentIntents, and refunded charges.
- Admin manual payment actions such as mark paid, mark collected, mark refunded, mark failed, mark review, and cancel.
- Frontend/admin payment status display and payment action controls.
- Order/payment email language for pending payments, cancellation, and refund messaging.

The key limitation: extras improves payment tracking, but it does not yet implement a real returns/refunds/courier-loss lifecycle.

## Current Payment Behavior Found

- COD orders start with payment_status cod_pending.
- COD delivered can become paid and collected_at is set.
- Card orders start pending.
- Stripe webhook can set card payments to paid.
- Admin mark_refunded currently changes local DB status only.
- The app does not currently call Stripe to create refunds.
- Stripe charge.refunded webhook is currently audit-only and does not update order/payment status.
- There is no refund_pending or partially_refunded payment status yet.
- There is no explicit payment_refunds table yet.

## Current Order Behavior Found

- Existing order statuses are pending, confirmed, shipped, delivered, cancelled.
- Current valid transitions are:
  - pending to confirmed or cancelled
  - confirmed to shipped or cancelled
  - shipped to delivered
  - delivered is terminal
  - cancelled is terminal
- Cancellation after shipped is not currently allowed.
- There is no returned, return_in_transit, uncollected, or shipment_issue state.
- courier_status exists on orders, but is display/evidence only.

## Current Courier Behavior Found

- Speedy has an admin tracking endpoint.
- Speedy tracking updates orders.courier_status.
- Speedy status normalization can detect delivered, out_for_delivery, returned, failed, and in_transit.
- Speedy tracking does not update order.status.
- Econt pricing exists in the current branch, but no tracked source file for Econt fulfillment/trace exists in this branch.
- Git history contains a separate `econt` branch/change with a fuller Econt delivery integration design.

## Current Stock Behavior Found

- Checkout decrements stock.
- Cancellation restores stock.
- Shipped orders cannot currently be cancelled through the normal transition path.
- Returned/uncollected stock handling is missing.
- Restocking should be tied to physical receipt and inspection, not courier status alone.

## Accounting Conclusion From Review

The added payment/order tables help accounting, but they are not a full accounting system.

They help with:

- payment provider audit trail,
- Stripe event history,
- current payment status,
- paid/collected/refunded markers,
- basic reconciliation investigation.

They do not fully cover:

- actual Stripe refund creation,
- refund amount records,
- partial refunds,
- courier return fees,
- COD settlement/payout reconciliation,
- Stripe payout IDs,
- courier claim tracking,
- inventory adjustment reasons,
- invoice/VAT ledger needs,
- accountant-ready exports.

## Current App Gaps

- Existing order statuses are too simple: pending, confirmed, shipped, delivered, cancelled.
- Existing payment statuses are too simple: pending, paid, cod_pending, failed, refunded.
- There is no returned, return in transit, refund pending, partial refund, dispute, or uncollected flow.
- Speedy tracking exists, but only updates courier status.
- Econt pricing exists, but no full tracking/return flow was identified.
- Admin can mark a payment refunded, but the app does not currently issue a Stripe refund.
- Stripe charge.refunded webhook is audit-only today.
- Checkout decrements stock.
- Cancellation restores stock.
- Returned/uncollected stock handling is missing.

## Recommended State Model

### Order Statuses

Use a small set of fulfillment states:

- pending
- confirmed
- shipped
- delivered
- cancelled
- return_in_transit
- returned

Avoid a separate order status for every reason. Prefer returned plus a reason code.

### Return Reasons

- not_picked_up
- refused_delivery
- customer_return
- wrong_address
- unreachable_customer
- damaged_by_courier
- lost_by_courier
- merchant_error
- other

### Payment Statuses

- pending
- paid
- cod_pending
- failed
- review_required
- refund_pending
- partially_refunded
- refunded
- dispute_open
- dispute_won
- dispute_lost

Disputes/chargebacks are separate from refunds.

## Recommended Tables

### order_returns

Track return cases separately instead of bloating orders.

Suggested fields:

- id
- order_id
- reason
- source: admin, speedy, econt, customer, stripe, system
- status: requested, return_in_transit, received, rejected, closed
- refund_amount_cents
- courier_return_fee_cents
- courier_claim_id
- courier_claim_status: none, filed, approved, rejected, paid
- courier_claim_amount_cents
- restock_decision: pending, restock, do_not_restock, partial
- returned_at
- received_at
- inspected_at
- notes
- created_by_admin_id
- created_at
- updated_at

### payment_refunds

Track Stripe and manual refunds explicitly.

Suggested fields:

- id
- order_id
- payment_id
- provider: stripe, manual, bank_transfer, cod_adjustment
- provider_refund_id
- amount_cents
- status: pending, succeeded, failed, cancelled
- reason
- idempotency_key
- failure_reason
- created_by_admin_id
- created_at
- confirmed_at

### order_return_events

Optional, but useful for audit.

Suggested fields:

- id
- order_return_id
- order_id
- event_type
- source
- payload_json
- created_by_admin_id
- created_at

## Stripe Refund Flow

The app should be able to issue Stripe refunds.

High-level backend flow:

```python
stripe.Refund.create(
    payment_intent=order["stripe_payment_intent_id"],
    amount=refund_amount_cents,  # omit for full refund
    reason="requested_by_customer",
    metadata={"order_id": order["id"]},
)
```

Recommended app behavior:

- Admin clicks Issue refund.
- Backend validates card order, paid status, Stripe PaymentIntent, and refund amount.
- Backend creates Stripe refund using an idempotency key.
- Payment becomes refund_pending.
- payment_refunds row stores Stripe refund ID and amount.
- Stripe webhook confirms final status.
- Full refund sets payment_status to refunded.
- Partial refund sets payment_status to partially_refunded.
- Failed refund creates admin review.

## Main Scenarios

### 1. Card checkout abandoned

- Order is created.
- Customer never pays.
- Do not send the order to courier.
- Do not automatically cancel immediately.
- Move it into an admin callback/review queue.
- Treat it as a possible payment-on-delivery conversion only after admin confirms with the customer.
- Admin should call the customer to check what happened and whether they still want the order.
- If the customer confirms, admin can switch/confirm the order as payment on delivery.
- If the customer does not confirm, the reservation expires and stock is released.
- No refund.
- Suggested state: payment_status review_required, order remains pending/unconfirmed until admin action.

### 2. Card paid, cancelled before shipping

- Order: confirmed to cancelled.
- Payment: paid to refund_pending to refunded.
- Stock: restore immediately if stock was reserved/decremented.
- Courier: no courier cost unless a label was already created.
- Accounting: Stripe refund must reconcile.

### 3. COD cancelled before shipping

- Order: confirmed to cancelled.
- Payment: cod_pending to failed/cancelled-equivalent.
- Stock: restore.
- Courier: no courier cost unless a label was already created.

### 4. Label created, not handed to courier

- Admin must cancel label/shipment if possible.
- Stock can be restored after confirming package was not dispatched.
- Accounting may need label fee tracking if the courier charges it.

### 5. Shipped, customer asks to cancel

- This is not a normal cancellation anymore.
- Treat as return-to-sender.
- Order: shipped to return_in_transit to returned.
- Card: paid to refund_pending to refunded/partially_refunded.
- COD: cod_pending to failed/uncollected.
- Stock: restore only after receipt and inspection.

### 6. Customer refuses delivery

- Order: shipped to return_in_transit to returned.
- Return reason: refused_delivery.
- Card: refund pending after admin decision.
- COD: mark failed/uncollected.
- Stock: restore only after inspection.
- Accounting: outbound and return courier fees may be merchant cost.

### 7. Customer does not pick up from Speedy/Econt office

- Order: shipped to return_in_transit to returned.
- Return reason: not_picked_up.
- Card: refund pending after admin decision.
- COD: failed/uncollected.
- Stock: restore only after inspection.
- Accounting: track lost sale plus courier fees.

### 8. Wrong address or unreachable customer

- Create admin review.
- Possible outcomes:
  - correct address and resend,
  - customer pays second shipping,
  - return to sender,
  - cancel/refund.
- Do not auto-refund until admin chooses outcome.

### 9. Courier loses parcel

- Order enters shipment issue or return case with reason lost_by_courier.
- Customer may receive refund or replacement.
- Stock is lost, not restocked.
- Accounting needs courier claim tracking.

### 10. Courier damages parcel

- Return reason: damaged_by_courier.
- Customer may receive refund or replacement.
- Stock usually should not be restocked.
- Admin can enter courier claim ID, claim status, amount, and notes.
- No extra courier claim integration is needed for now.
- Accounting needs the manual claim record for follow-up and reconciliation.

### 11. Delivered, then customer returns

- Order: delivered to return_in_transit to returned.
- Payment: paid to refund_pending to refunded/partially_refunded.
- Stock: restore only after receipt and inspection.
- Accounting: refund plus any non-refundable shipping/fees.

### 12. Partial return

- Customer returns some items only.
- Needs line-level refund and partial stock adjustment.
- Payment: paid to partially_refunded.
- Accounting needs item-level amounts.

### 13. Exchange instead of refund

- Do not support exchange as a combined workflow for now.
- Treat the return as one process.
- If the customer wants another item, they place a new order separately.
- Do not create linked exchange/replacement orders in this phase.

### 14. Stripe dispute or chargeback

- Separate from refund.
- Customer disputes card payment through bank.
- Payment status should become dispute_open.
- Track evidence, Stripe dispute ID, deadline, outcome.
- Outcomes: dispute_won or dispute_lost.

### 15. Refund fails

- Stripe refund can fail.
- Do not set refunded immediately.
- Keep refund_pending until Stripe confirms.
- Failed refund creates admin review.

### 16. Double refund risk

- Admin may click twice.
- Webhook may arrive twice.
- Use idempotency keys.
- Enforce total refunded amount <= paid amount.
- Stripe event IDs must be deduplicated.

### 17. COD delivered but courier payout not received

- Order can be delivered.
- Payment may be collected by courier, but not settled to merchant yet.
- Need COD settlement reconciliation.
- Payment status paid may not be enough for accounting.

### 18. Custom or personalized products

- Return/refund rules may differ.
- Product/order item should carry a custom/non-returnable policy flag.
- Admin should see this before approving refund.

## Stock Rules

- Before shipping cancellation: restore stock.
- Shipped return: do not restore stock from courier scan alone.
- Returned received and inspected: admin chooses restock/do not restock/partial.
- Lost/damaged: do not restock.
- No exchange stock logic for now; returned item stock and any new order stock are handled separately.

## Accounting Rules

Track enough data to answer these questions:

- Was money collected?
- Was money refunded?
- Was refund full or partial?
- What Stripe refund ID proves it?
- What courier fee was charged?
- Was COD money collected by courier?
- Was COD money paid out to merchant?
- Was the item restocked, damaged, or lost?
- Was there a courier claim?
- Was this a normal return, uncollected order, refusal, or merchant/courier fault?

The extra payment/order tables help, but they are not a full accounting system yet.

## Admin Actions Needed

Parallel work note: `speedy-admin-parity` is being implemented at the same time.
Keep admin changes additive where possible, avoid broad admin page/sidebar refactors in
this change, and reconcile shared admin UI surfaces before marking the larger admin UI
tasks complete.

- Mark return in transit.
- Mark uncollected.
- Mark refused delivery.
- Receive return.
- Inspect return.
- Restock item.
- Do not restock item.
- Issue full refund.
- Issue partial refund.
- Call customer for abandoned card payment.
- Convert abandoned card order to payment on delivery after customer confirmation.
- Record courier fee.
- Record courier claim.
- Record courier claim ID/status/amount manually.
- Record COD settlement.
- Open payment review.
- Close return case.

Every admin action should write an audit event.

## Customer-Facing Policy Copy

- Terms should be the detailed public policy source for uncollected/refused parcels, return shipping, refund timing, card refunds, payment-on-delivery orders, courier damaged/lost parcels, and inspection/restock timing.
- FAQ should get only a short delivery/returns answer for uncollected or refused parcels, with a link to `/[locale]/terms#returns`.
- Public copy should not promise automatic refunds, automatic restocks, or courier-status-driven outcomes. It should explain admin review/contact where needed.
- Content and tests should cover English and Bulgarian.

## Courier Integration

### Econt branch porting synergy

- The `econt` branch should be ported selectively, not merged wholesale.
- Useful Econt branch pieces:
  - Econt settings table/service and admin settings UI.
  - Econt redaction helpers.
  - Native Econt office `code` support.
  - Courier metadata fields on orders.
  - `order_courier_events` audit table.
  - Econt Delivery client concepts for `updateOrder`, `createAWB`, `getTrace`, and `deleteLabel`.
  - Econt fulfillment service mapping local orders to courier payloads.
  - Admin Econt fulfillment panel and repair flow.
- Required changes while porting:
  - Convert synchronous Econt client code to async for polling/trace paths.
  - Do not use worker threads or `asyncio.to_thread` for courier polling.
  - Disable/remove `auto_delivered_on_trace`; courier trace creates evidence/review signals only.
  - Keep `auto_confirm_on_label` off unless it cannot bypass admin confirmation or abandoned-payment review.
  - Extend Econt shipment models with typed return/COD fields instead of relying only on raw extra payloads.
  - Merge with current `extras` payment work; do not lose Stripe refunds, payment review, payment settings, or admin payment actions.
- Best porting order:
  1. Office code and Econt settings/redaction.
  2. Courier metadata and courier events schema.
  3. Async Econt client and fulfillment mapping.
  4. Admin Econt endpoints/panel adjusted for current order/payment states.
  5. Async trace polling and Econt return/COD evidence normalization.
  6. Return/refund workflows on top of the evidence layer.
- Current branch note: Econt fulfillment actions should stay awaitable end-to-end.
  Use `httpx.AsyncClient` for Econt Delivery calls and do not add sync wrappers or
  threadpool bridges around courier trace/polling/label calls.

### Courier status polling

- Use scheduled polling instead of depending on courier push notifications.
- Poll active Speedy/Econt shipments with tracking/shipment identifiers.
- Polling creates courier evidence and admin review signals only.
- Polling must not automatically refund, restock, mark COD settled, close returns, or force order/payment transitions.
- The poller must be async-only.
- Do not use worker threads or `asyncio.to_thread` for courier polling.
- Use async courier clients and await provider calls directly from the async background loop.
- Use database-backed leases so multiple app workers do not poll the same order at the same time.
- Use configurable interval, batch size, provider enablement, and backoff after failures.
- Keep manual admin refresh available, using the same async polling/normalization path.

### Speedy

- Use tracking to detect delivered, failed, returned, out for delivery, in transit.
- Returned/failed statuses should create admin review.
- Do not automatically close order or refund payment.

### Econt

- Econt should be first-class in this return/refund work, not only a manual fallback.
- Official Econt docs expose two relevant API families:
  - EE API: `https://ee.econt.com/services/Shipments/LabelService.createLabel.json`, currently used for price calculation with `mode=calculate`.
  - Econt Delivery API: `https://delivery.econt.com/services/OrdersService.getTrace.json`, plus `updateOrder`, `createAWB`, and `deleteLabel`.
- EE shipment docs include return/reject instruction fields such as `returnParcelDestination`, `daysUntilReturn`, `returnParcelPaymentSide`, `rejectAction`, `executeIfNotTaken`, `rejectOriginalParcelPaySide`, and `rejectReturnParcelPaySide`.
- EE/Econt status docs include return and failure evidence:
  - `shortDeliveryStatusEn`: includes values like `Is returning to sender` and `Returned to sender`.
  - `trackingEvents`: includes event types like `failed_delivery`, `is_returning_to_sender`, and `returned_to_sender`.
  - Return linkage fields include `returnShipmentURL`, `previousShipmentNumber`, `nextShipments`, and `lastProcessedInstruction`.
- Econt status docs include COD evidence fields:
  - `cdCollectedAmount`, `cdCollectedTime`
  - `cdPaidAmount`, `cdPaidTime`
- These Econt fields should create/admin-update review signals and accounting evidence, but still must not automatically refund, restock, or close orders.
- Manual Econt updates must remain available when credentials, shipment number, or API access is missing.
- Econt office fulfillment needs native Econt office `code`; our current normalized office data exposes internal ids like `econt-1053` but not the native code.
- The OpenSpec proposal now includes an Econt-specific return-signal capability.

## Implementation Phases

OpenSpec proposal created: `openspec/changes/manage-order-returns-refunds`.

### Phase 1: Manual return/uncollected workflow

- Add order/payment statuses.
- Add order_returns table.
- Add admin actions.
- Add audit events.
- Add tests for COD and card uncollected scenarios.

### Phase 2: Stripe refunds

- Add payment_refunds table.
- Add Issue refund backend action.
- Add full and partial refund support.
- Add Stripe webhook handling for refund confirmation/failure.
- Add idempotency and double-refund protection.

### Phase 3: Stock inspection workflow

- Add receive/inspect/restock admin flow.
- Add stock adjustment reason tracking.
- Add tests for damaged/lost/partial restock.

### Phase 4: Courier signals

- Async-only scheduled courier polling.
- Speedy return/uncollected detection.
- Econt trace/status refresh using official APIs where configured.
- Econt return/reject instruction configuration for label creation.
- Econt COD collected/paid evidence capture for settlement reconciliation.
- Manual Econt import/update fallback.
- Admin review queue for courier issues.

### Phase 5: Accounting and reconciliation

- Stripe refund export.
- COD settlement report.
- Courier fee report.
- Return reason report.
- Inventory adjustment report.

### Phase 6: Customer policy content

- Update Terms & Conditions returns/refunds language.
- Add the small FAQ entry that links to the full Terms returns section.
- Verify EN/BG frontend content and links.

## Open Decisions

- For card-paid uncollected orders, do we refund full amount including delivery, or product amount only?
- Decision: abandoned card payments should use payment_status `review_required` instead of `failed` while waiting for admin callback.
- When admin converts abandoned card payment to payment on delivery, should the original payment_method change or should we keep original_payment_method for audit?
- Do we need line-level refunds immediately, or can partial refund start at order-level amount?
- Do we want a dedicated shipment_issue order status, or represent lost/damaged through return cases only?
- Should COD uncollected be payment_status failed, uncollected, or cancelled?
- How should custom/personalized products block or warn on returns?
