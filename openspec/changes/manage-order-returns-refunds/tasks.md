## 0. Econt Branch Porting Guardrails

- [x] 0.1 Port Econt branch changes selectively instead of merging the branch wholesale
- [x] 0.2 Preserve current `extras` payment, Stripe, admin payment review, analytics, and frontend settings work while porting Econt files
- [x] 0.3 Convert ported Econt client/service calls needed for polling and trace refresh to async implementations
- [x] 0.4 Remove or disable Econt `auto_delivered_on_trace`; trace refresh must create evidence/review signals only
- [x] 0.5 Keep Econt `auto_confirm_on_label` disabled unless the order is already eligible under current admin confirmation and payment-review rules
- [x] 0.6 Extend ported Econt shipment models with typed return/COD fields required by this change
- [x] 0.7 Coordinate admin UI scope with parallel `speedy-admin-parity`; keep return/refund controls localized and avoid broad admin navigation/sidebar changes in this change

## 1. Schema and Models

- [x] 1.1 Add order statuses `return_in_transit` and `returned` to backend models and database constraints
- [x] 1.2 Add payment statuses `review_required`, `refund_pending`, `partially_refunded`, `dispute_open`, `dispute_won`, and `dispute_lost`
- [x] 1.3 Add `order_returns` table with reason, source, status, refund amount, courier fee, manual claim fields, restock decision, timestamps, notes, and admin actor fields
- [x] 1.4 Add `order_return_events` table for return workflow audit entries
- [x] 1.5 Add `payment_refunds` table with provider refund ID, amount, status, idempotency key, failure reason, actor, and confirmation timestamps
- [x] 1.6 Add COD settlement storage for amount, date, courier reference, notes, mismatch/review flag, and actor
- [x] 1.7 Add model/type updates for backend API responses and frontend TypeScript types
- [x] 1.8 Add Econt native office `code` to office response models, checkout delivery payloads, order delivery snapshots, and frontend types
- [x] 1.9 Update Econt office normalization/data refresh so `data/econt_offices.json` preserves native Econt office codes

## 2. Order State and Stock Rules

- [x] 2.1 Extend order transition validation for `shipped -> return_in_transit`, `delivered -> return_in_transit`, and `return_in_transit -> returned`
- [x] 2.2 Keep `cancelled` and `returned` as terminal order statuses
- [x] 2.3 Preserve existing cancellation stock restoration for pre-shipment cancellations
- [x] 2.4 Prevent stock restoration when orders enter `return_in_transit` or `returned`
- [x] 2.5 Add explicit inspect/restock service action for restock, do not restock, and partial restock decisions
- [x] 2.6 Record inventory adjustment reasons for return restock decisions

## 3. Return Case Backend

- [x] 3.1 Implement service functions to create and update return cases transactionally
- [x] 3.2 Implement admin actions for mark return in transit, mark uncollected, and mark refused delivery
- [x] 3.3 Implement admin actions for receive return, inspect return, and close return case
- [x] 3.4 Persist return audit events for every return action
- [x] 3.5 Validate return reason/source/status values and invalid return state transitions
- [x] 3.6 Ensure courier tracking cannot mark a return case received, inspected, or closed automatically

## 4. Abandoned Card Payment Review

- [x] 4.1 Change expired/abandoned Stripe checkout handling to set payment status `review_required`
- [x] 4.2 Add abandoned-payment admin review filter/query support
- [x] 4.3 Block shipping for abandoned card orders still in payment review
- [x] 4.4 Implement admin callback outcome recording for abandoned card payments
- [x] 4.5 Implement admin-confirmed conversion from abandoned card payment to payment on delivery with payment status `cod_pending`
- [x] 4.6 Preserve original card attempt/payment records when converting to payment on delivery
- [x] 4.7 Restore stock and avoid refund creation when an unconfirmed abandoned card order is cancelled or expires

## 5. Stripe Refunds and Payment Events

- [x] 5.1 Implement Stripe refund creation service with full/partial amount support
- [x] 5.2 Use idempotency keys for refund creation and return existing refund records on duplicate requests
- [x] 5.3 Enforce total pending/succeeded refunds do not exceed paid amount
- [x] 5.4 Set payment status to `refund_pending` after refund creation
- [x] 5.5 Extend Stripe webhook handling to finalize succeeded full refunds as `refunded`
- [x] 5.6 Extend Stripe webhook handling to finalize succeeded partial refunds as `partially_refunded`
- [x] 5.7 Handle failed refunds by recording failure reason and leaving the order in admin-reviewable state
- [x] 5.8 Add Stripe dispute event handling for `dispute_open`, `dispute_won`, and `dispute_lost`

## 6. COD Settlement and Courier Claims

- [x] 6.1 Flag delivered COD orders without settlement as requiring COD settlement reconciliation
- [x] 6.2 Add admin action to record COD settlement amount, date, courier reference, and notes
- [x] 6.3 Flag COD settlement amount mismatches for accounting review
- [x] 6.4 Add admin action to record courier return fees on return cases
- [x] 6.5 Add admin action to record manual courier claim ID, status, amount, and notes
- [x] 6.6 Ensure courier claim handling performs no courier claim API calls

## 7. Courier Review Signals

- [x] 7.1 Create admin review signal when Speedy tracking maps to `returned` or `failed`
- [x] 7.2 Preserve Speedy tracking as read-only for order status, payment status, refund status, and stock
- [x] 7.3 Store raw courier tracking details in audit/event payloads where available
- [x] 7.4 Implement Econt trace refresh service using Econt Delivery `OrdersService.getTrace` when configured
- [x] 7.5 Support EE `LabelService` shipment status response mapping if the active Econt label implementation uses the EE API family
- [x] 7.6 Normalize Econt `shortDeliveryStatusEn` values such as `Is returning to sender` and `Returned to sender` into admin review signals
- [x] 7.7 Normalize Econt tracking event types `failed_delivery`, `is_returning_to_sender`, and `returned_to_sender` into admin review signals
- [x] 7.8 Store Econt return shipment metadata such as `returnShipmentURL`, `previousShipmentNumber`, `nextShipments`, and `lastProcessedInstruction`
- [x] 7.9 Preserve Econt trace as read-only for order status, payment status, refund status, and stock
- [x] 7.10 Keep manual Econt courier status entry available when credentials or shipment numbers are missing
- [x] 7.11 Implement async courier status polling service for eligible active Speedy/Econt shipments
- [x] 7.12 Add async FastAPI background loop that awaits the courier polling service directly with no `asyncio.to_thread`
- [x] 7.13 Ensure Speedy and Econt polling clients used by the poller are async HTTP clients
- [x] 7.14 Add database-backed polling leases to avoid duplicate courier calls across workers
- [x] 7.15 Add polling interval, batch size, provider enablement, and backoff settings
- [x] 7.16 Add manual admin refresh that awaits the same async polling/normalization path

## 8. Econt Label Return Instructions and COD Evidence

- [x] 8.1 Add Econt return/reject instruction settings for return destination, days until return, return payment side, reject action, and reject payment sides
- [x] 8.2 Include configured Econt unclaimed-return instruction fields when creating Econt labels for office pickup orders
- [x] 8.3 Include configured Econt reject/refused-parcel instruction fields when creating Econt labels
- [x] 8.4 Block Econt office label creation when native office code is missing and expose an admin repair path
- [x] 8.5 Capture Econt COD fields `cdCollectedAmount`, `cdCollectedTime`, `cdPaidAmount`, and `cdPaidTime` from trace/status responses
- [x] 8.6 Show Econt COD collected/paid evidence in COD settlement reconciliation without replacing explicit admin settlement records

## 9. Admin APIs and UI

- [x] 9.1 Extend admin order detail API to include return cases, refund records, courier claim fields, COD settlement state, and relevant events
- [x] 9.2 Add admin order list filters for abandoned payment, uncollected/refused, refund pending, inspection pending, courier claim follow-up, and COD settlement pending
- [x] 9.3 Add admin UI controls for return/uncollected/refused actions
- [x] 9.4 Add admin UI controls for receive, inspect, restock, do not restock, partial restock, and close return case
- [x] 9.5 Add admin UI controls for full and partial Stripe refunds with amount validation
- [x] 9.6 Add admin UI controls for abandoned card callback and conversion to payment on delivery
- [x] 9.7 Add admin UI controls for courier fees, manual claim ID/status/amount, and COD settlement
- [x] 9.8 Add admin UI controls for Econt trace refresh, Econt office-code repair, and Econt return/COD evidence display
- [x] 9.9 Display clear warnings for custom/personalized products before refund approval when product/order data supports it

## 10. Accounting and Reporting

- [x] 10.1 Add Stripe refund reconciliation export/report with refund IDs, amounts, statuses, and order references
- [x] 10.2 Add COD settlement report with unsettled, settled, mismatch orders, and Econt collected/paid evidence where present
- [x] 10.3 Add courier fee and courier claim report
- [x] 10.4 Add return reason report for uncollected, refused, customer return, damaged, lost, and merchant error cases
- [x] 10.5 Add inventory adjustment report for returned/restocked/not-restocked items

## 11. Customer-Facing Content

- [x] 11.1 Update Terms & Conditions returns/refunds sections for uncollected/refused parcels, damaged/lost courier cases, card refunds, payment-on-delivery orders, return shipping, and inspection/restock timing
- [x] 11.2 Add a small FAQ update for delivery/returns explaining uncollected/refused parcels and where to find the full Returns policy
- [x] 11.3 Add or adjust frontend tests for Terms and FAQ content in English and Bulgarian

## 12. Tests and Verification

- [x] 12.1 Add backend tests for new order/payment statuses and database constraints
- [x] 12.2 Add backend tests for valid and invalid return-related order transitions
- [x] 12.3 Add backend tests proving shipped/returned orders do not auto-restock
- [x] 12.4 Add backend tests for return case creation, receive, inspect, restock, and close actions
- [x] 12.5 Add backend tests for abandoned card payment review and COD conversion
- [x] 12.6 Add backend tests for Stripe full refund, partial refund, failed refund, idempotency, and over-refund rejection
- [x] 12.7 Add backend tests for Stripe dispute events
- [x] 12.8 Add backend tests for COD settlement and mismatch review
- [x] 12.9 Add backend tests for Speedy returned/failed review signals without order/payment/stock mutation
- [x] 12.10 Add backend tests for Econt trace normalization of returned, returning, and failed-delivery signals without order/payment/stock mutation
- [x] 12.11 Add backend tests for Econt office code preservation and label-blocking when code is missing
- [x] 12.12 Add backend tests for Econt return/reject instruction payload fields and COD collected/paid evidence capture
- [x] 12.13 Add backend tests for async polling eligibility, leases, backoff, batch limits, and manual refresh
- [x] 12.14 Add backend tests or code checks proving courier polling does not use worker threads or `asyncio.to_thread`
- [x] 12.15 Add frontend tests for admin return/refund/callback/settlement controls
- [x] 12.16 Add frontend tests for Econt trace refresh, office-code repair, and Econt COD evidence display
- [x] 12.17 Run backend test suite
- [x] 12.18 Run frontend tests and typecheck
