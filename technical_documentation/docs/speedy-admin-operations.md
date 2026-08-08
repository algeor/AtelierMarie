# Speedy Admin Operations

OpenSpec change: `speedy-admin-parity`.

This is the technical reference for the dedicated Speedy admin surface added on
top of the existing checkout pricing, waybill, label, and tracking integration.
It documents the intended service boundaries and safety rules so future Econt,
returns/refunds, or courier-polling work does not change order state from courier
evidence alone.

## Admin Surface

- Page: `/admin/delivery/speedy` from the admin sidebar.
- Compatibility page: `/admin/speedy` still renders the same Speedy operations UI for existing direct links.
- Sidebar entry: Admin -> Delivery -> Speedy.
- Delivery parent: `/admin/delivery` remains the courier-method enablement page; Econt is grouped beside Speedy at `/admin/delivery/econt`.
- API prefix: `/v1/admin/speedy/*`.
- Legacy-compatible label/track wrappers remain at `/v1/admin/orders/{order_id}/label` and `/v1/admin/orders/{order_id}/track`.
- Credentials remain env-backed: `SPEEDY_API_USERNAME`, `SPEEDY_API_PASSWORD`, `SPEEDY_CLIENT_ID`, `SPEEDY_BASE_URL`.
- The page returns configured/missing credential state only. It must never return raw Speedy passwords or credential-bearing request payloads.

## Backend Boundaries

- `app/services/speedy_client.py` is the Speedy REST boundary: endpoint names, request payloads, response parsing, typed errors, timeouts, and the Speedy operational circuit breaker.
- `app/services/speedy_admin_service.py` owns admin behavior: health aggregation, local queue queries, action guards, cancellation policy, event persistence, metrics, office refresh status, and returns/refunds review signals.
- `app/routes/admin.py` exposes admin-only response models from `app/models/speedy.py` and maps Speedy/admin validation failures to safe error envelopes.
- `order_courier_events` is the audit store for Speedy operation requests, responses, and errors after redaction.
- `site_settings.speedy_admin_health` stores last safe health-check metadata. `data/courier_refresh_status.json` stores office refresh status written by the office refresh script.

## Official Speedy Operations Used

- `POST /client`: safe health probe; returns the authenticated client id.
- `POST /client/{id}`: optional client details for admin diagnostics.
- `POST /shipment/search`: search by local reference/order id.
- `POST /shipment/info`: fetch shipment details by shipment id.
- `POST /shipment/cancel`: cancel an existing Speedy shipment.
- `POST /pickup/terms`: fetch available pickup cutoff timestamps.
- `POST /pickup`: request pickup for selected shipments.
- Existing shipment creation, tracking, and print endpoints remain the source of truth for waybill creation, courier status refresh, and PDF labels.

## Supported Actions

- Health: calls official Speedy `POST /client` and compares the returned client id with `SPEEDY_CLIENT_ID`.
- Queues: lists confirmed Speedy orders without waybills, and shipped Speedy orders with tracking.
- Create waybill: reuses the existing `confirmed -> shipped` transition. If Speedy rejects the shipment, the order stays unshipped.
- Print label: streams the Speedy PDF label through the admin API.
- Refresh tracking: updates display-only `courier_status`; it does not mark orders delivered, refunded, paid, or restocked.
- Search/info: calls official shipment search/info operations for diagnostics.
- Cancel shipment: cancels the courier shipment only. Local order status is not changed to `cancelled`; on Speedy success the shipment is marked with `courier_sync_status='shipment_cancelled'` and `courier_status='cancelled'`.
- Pickup: admins explicitly select eligible local Speedy shipments, request pickup terms, then submit pickup details.
- Office refresh: `scripts/fetch_courier_offices.py` writes `data/speedy_offices.json`, `data/speedy_sites.json`, and `data/courier_refresh_status.json`.

## Local State Policy

| Operation | Local mutation | Explicit non-goal |
|---|---|---|
| Health | Writes safe last-success/failure metadata only. | Does not create shipments. |
| Create waybill | Uses the existing shipped transition and writes tracking/courier metadata. | Does not ship if Speedy rejects the waybill. |
| Print label | Writes a successful/failed courier event. | Does not change order status. |
| Refresh tracking | Writes `courier_status`, sync timestamp, and courier event. | Does not change payment, refund, stock, or order lifecycle status. |
| Shipment search/info | Writes an event only when the reference/shipment maps to a local order. | Does not create local orders or shipments. |
| Cancel shipment accepted | Marks the shipment metadata cancelled and records an event. | Does not cancel the customer order. |
| Cancel shipment rejected | Records a redacted failed event only. | Does not mutate tracking number, courier status, or sync status. |
| Pickup terms/request | Records courier events for eligible selected shipments. | Does not run automatically from checkout or confirmation. |

## Safety Rules

- Shipment creation still happens only through the valid shipped transition.
- Tracking is courier evidence only; business return/refund/restock decisions remain in the returns/refunds workflow.
- Speedy returned/failed tracking creates a lightweight review signal only when the returns table exists and no return case exists yet.
- Validation/auth errors are actionable admin errors and do not trip the outage circuit.
- Transient failures and malformed Speedy responses are counted by the Speedy operational circuit breaker.
- Courier events in `order_courier_events` must store redacted request/response/error snapshots.
- Do not add a competing Speedy poller. Courier polling belongs to the returns/refunds courier polling design and should consume the same metadata/events.

## Frontend Notes

- The page lives at `frontend/app/[locale]/admin/speedy/page.tsx` and follows the existing admin operational UI style.
- The grouped Delivery route `frontend/app/[locale]/admin/delivery/speedy/page.tsx` re-exports the same page so there is one Speedy UI implementation.
- `frontend/components/admin/AdminSidebar.tsx` renders Delivery as the parent section and Speedy/Econt as child links. Active state recognizes both grouped routes and legacy direct routes.
- API helpers and types live in `frontend/lib/api.ts`, `frontend/lib/types.ts`, and `frontend/lib/mock-api.ts`.
- The order list links Speedy rows to `/admin/speedy?order_id=<id>` until those deep links are moved to the grouped route.
- The order detail page shows a compact Speedy fulfillment panel only for Speedy orders.
- Frontend status maps include `return_in_transit` and `returned` so the parallel returns/refunds flow can render those states consistently.

## Troubleshooting

### Health Is Blocked

- `username_missing`: set `SPEEDY_API_USERNAME`.
- `password_missing`: set `SPEEDY_API_PASSWORD`.
- `client_id_missing`: set `SPEEDY_CLIENT_ID`.
- `client_id_not_numeric`: `SPEEDY_CLIENT_ID` must be the numeric registered client id, not an office slug.

### Client Id Mismatch

- `/admin/delivery/speedy` shows both configured and verified client ids.
- Re-run the client-id discovery for the current Speedy account/environment.
- Do not create test shipments to validate this; use the safe Client Service check.

### Cancellation Rejected

- Speedy may reject cancellation after pickup, closure, or access restrictions.
- The local tracking number, courier status, and sync status are preserved.
- Check the recent Speedy event error category/context on `/admin/delivery/speedy`.

### Pickup Fails

- Ensure at least one selected shipment is a local Speedy shipment.
- Do not include cancelled shipments.
- Verify contact name, phone, pickup date/time, and visit end time.
- If terms fail with configuration errors, fix health first.

### Office Refresh Fails

- Run `.venv/bin/python scripts/fetch_courier_offices.py --courier speedy`.
- Check `data/courier_refresh_status.json` and the `/admin/delivery/speedy` office status panel.
- A Speedy failure should not block Econt refreshes or checkout reads from the last valid JSON files.

## Verification

Targeted checks used for this surface:

```bash
.venv/bin/python -m pytest tests/test_courier_clients.py tests/test_speedy_admin_service.py tests/test_admin_speedy_routes.py tests/test_fetch_courier_offices.py tests/test_order_service.py tests/realapp/test_order_routes.py -q
npm --prefix frontend run test -- __tests__/app/admin/speedy.test.tsx __tests__/app/admin/orders.test.tsx __tests__/app/admin/order-detail-econt.test.tsx __tests__/lib/mock-api.test.ts
npm --prefix frontend run typecheck
openspec validate speedy-admin-parity --type change --strict --no-interactive
git diff --check
```
