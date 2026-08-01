## 1. Phase 1 Backend Client Operations

- [x] 1.1 Add Speedy typed errors/categories for health, shipment lookup, cancellation, and pickup operations without changing existing shipment/track/print error behavior.
- [x] 1.2 Implement `get_own_client_id` using official `POST /client` and safe response parsing.
- [x] 1.3 Implement optional `get_client` using official `POST /client/{id}` for admin diagnostics.
- [x] 1.4 Implement `find_parcels_by_reference` using official `POST /shipment/search`.
- [x] 1.5 Implement `get_shipment_info` using official `POST /shipment/info`.
- [x] 1.6 Implement `cancel_shipment` using official `POST /shipment/cancel` with Speedy context/message mapping.
- [x] 1.7 Add unit tests for the new Speedy client payloads, successful responses, HTTP errors, Speedy error bodies, malformed responses, and transport failures.

## 2. Phase 1 Speedy Admin Service And Audit

- [x] 2.1 Create a Speedy admin service that aggregates configuration presence, numeric `speedy_client_id` validation, Client Service health, and client-id match status.
- [x] 2.2 Add service queries for confirmed Speedy orders ready to ship and shipped Speedy orders with tracking numbers.
- [x] 2.3 Add service action for creating/reusing a Speedy waybill through the existing valid shipped transition.
- [x] 2.4 Add service actions for print label, refresh tracking, shipment search, shipment info, and guarded cancellation.
- [x] 2.5 Persist Speedy operation events in `order_courier_events` with redacted request/response/error snapshots.
- [x] 2.6 Define cancellation local metadata policy and implement it consistently after courier success.
- [x] 2.7 Add backend tests for health aggregation, queues, action guards, cancellation success/rejection, event persistence, and no credential leakage.

## 3. Phase 1 Admin API

- [x] 3.1 Add admin-only Speedy health endpoint under `/v1/admin/speedy/health`.
- [x] 3.2 Add admin-only Speedy queues endpoint for ready-to-ship and shipped Speedy orders.
- [x] 3.3 Add admin-only Speedy shipment search and shipment info endpoints.
- [x] 3.4 Add admin-only Speedy cancellation endpoint with local state guards.
- [x] 3.5 Reuse or wrap existing Speedy label and tracking endpoints so the Speedy admin page has one API client surface.
- [x] 3.6 Add route tests for auth, healthy/misconfigured health, queue shape, lookup, cancellation, label, tracking, and error envelopes.

## 4. Phase 1 Frontend Page

- [x] 4.1 Add `/admin/speedy` route following existing admin layout and restrained operational UI patterns.
- [x] 4.2 Add Speedy sidebar navigation item with active route styling and translations.
- [x] 4.3 Build health/configuration summary section showing credential presence, numeric client id status, verified client id, mismatch state, circuit state, and last check.
- [x] 4.4 Build ready-to-ship and shipped Speedy order queues with links to admin order detail.
- [x] 4.5 Add actions for create waybill, print label, refresh tracking, shipment search, shipment info, and cancel shipment with loading/disabled states.
- [x] 4.6 Add recent Speedy operation history section with redacted failure messages.
- [x] 4.7 Add frontend API functions/types, mock API support, English/Bulgarian strings, and UI tests for healthy, blocked, action success, and action failure states.

## 5. Phase 1 Admin Orders Integration

- [x] 5.1 Add Speedy-specific order detail panel or compact section for Speedy shipment metadata and diagnostics links.
- [x] 5.2 Add links from Speedy rows in the admin order list to the Speedy admin page filtered/focused by order where practical.
- [x] 5.3 Preserve existing order-list `shipped` behavior for Speedy orders and add regression tests proving it still creates the waybill through the existing transition.
- [x] 5.4 Ensure non-Speedy orders do not show Speedy-specific controls.

## 6. Phase 2 Pickup Workflow

- [x] 6.1 Implement Speedy `pickup_terms` client method using official `POST /pickup/terms`.
- [x] 6.2 Implement Speedy `request_pickup` client method using official `POST /pickup`.
- [x] 6.3 Add backend service guards for eligible Speedy shipments, shipment scope, visit end time, contact name, and phone.
- [x] 6.4 Add admin API endpoints for pickup terms and pickup request.
- [x] 6.5 Add pickup UI section to `/admin/speedy` with selected shipments, available cutoff times, request form, and returned pickup orders.
- [x] 6.6 Persist pickup request results in courier events or a dedicated pickup table if reporting needs require it.
- [x] 6.7 Add backend and frontend tests for pickup terms, request success, validation errors, Speedy rejection, and redaction.

## 7. Phase 2 Office Data Refresh

- [x] 7.1 Extend or create courier office refresh tooling to fetch Speedy offices/lockers from official Speedy Location Service APIs.
- [x] 7.2 Normalize Speedy office records into the existing `data/speedy_offices.json` shape without breaking checkout consumers.
- [x] 7.3 Track last Speedy office refresh status and timestamp for display in `/admin/speedy`.
- [x] 7.4 Add tests for successful Speedy refresh, partial courier failure, output shape, and delivery endpoint compatibility.

## 8. Phase 2 Polling And Operational Metrics

- [x] 8.1 Align Speedy status polling with the returns/refunds courier polling design instead of creating a competing poller.
- [x] 8.2 Add Speedy returned/failed review-signal integration if the returns/refunds change is active.
- [x] 8.3 Add simple Speedy operational metrics for recent successes, failures by category, cancellation count, pickup requests, and last successful health check.
- [x] 8.4 Add admin UI display for metrics without exposing sensitive payloads.

## 9. Documentation And Verification

- [x] 9.1 Update shipping/courier technical documentation with `/admin/speedy`, supported actions, and safety rules.
- [x] 9.2 Update operations troubleshooting docs for Speedy client-id health, credential mismatch, cancellation rejection, and pickup failures.
- [x] 9.3 Run targeted backend tests for Speedy client, admin routes, order service, courier events, and delivery data.
- [x] 9.4 Run targeted frontend tests for admin Speedy page, admin sidebar, admin orders, and API mocks.
- [x] 9.5 Run frontend typecheck and OpenSpec validation/status for `speedy-admin-parity`.
