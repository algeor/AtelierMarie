## Context

Speedy is already integrated for pricing, waybill creation, tracking, and label printing. The current admin experience is fragmented: shipping a Speedy order happens through the generic order status flow, label printing and tracking refresh are order-level endpoints, delivery enablement lives in `/admin/delivery`, and credentials are environment-backed. There is no single place to verify Speedy health, diagnose client-id mismatch, inspect shipments, cancel a waybill, request pickup, or review Speedy operation history.

Official Speedy REST documentation confirms safe and operational endpoints that map well to an admin surface:

- Client Service: `POST BASE_URL/client` returns own client id; `POST BASE_URL/client/{id}` returns client details.
- Shipment Service: create, cancel, update, shipment info, and search by reference.
- Print Service: print labels and label info.
- Track And Trace Service: tracking status for parcels.
- Pickup Service: pickup terms and pickup requests.
- Location Service: office search/lookup for Speedy office data refresh.

## Goals / Non-Goals

**Goals:**

- Add a dedicated `/admin/speedy` page that gives Speedy parity with Econt from an operations perspective.
- Keep Phase 1 focused on safe, high-value operations: health, configuration summary, order queues, label/track/search/info/cancel actions, and audit visibility.
- Add Phase 2 for pickup scheduling, official office refresh, richer diagnostics, metrics, and background polling alignment.
- Reuse existing order state-machine guarantees: Speedy waybill creation occurs on valid `confirmed -> shipped`, and failure leaves the order unshipped.
- Use safe Client Service calls for health checks instead of creating test shipments.
- Redact credentials from logs, events, and admin responses.

**Non-Goals:**

- Moving Speedy credentials from environment variables into editable database-backed settings in the first phase.
- Changing customer checkout courier selection or pricing behavior.
- Automatically marking orders delivered, paid, refunded, or restocked from Speedy tracking.
- Creating Speedy shipments at checkout time.
- Replacing the existing Econt admin page.

## Decisions

### 1. Build a dedicated Speedy admin page, not a generic courier page first

Speedy and Econt use different operational APIs, credential models, readiness blockers, and failure modes. A generic courier console would be tempting, but it would either hide useful Speedy-specific controls or overfit to the Econt flow. `/admin/speedy` should use shared admin UI primitives but own its Speedy-specific actions.

Alternative considered: add more buttons to `/admin/orders`. Rejected because it does not solve health, lookup, pickup, office refresh, or audit visibility.

### 2. Keep credentials env-backed in Phase 1

Current Speedy configuration lives in `Settings` as `speedy_api_username`, `speedy_api_password`, `speedy_base_url`, and `speedy_client_id`. Phase 1 should show configured/missing/mismatch status, but not introduce editable secret storage. This keeps scope smaller and avoids designing a second secret-management path while Econt settings are still settling.

Phase 2 can revisit DB-backed settings only if operators need runtime editing.

### 3. Use official Client Service for health checks

The health check should call `POST BASE_URL/client` to get own client id and compare it with configured `speedy_client_id`. This verifies credentials and sender identity without creating a shipment or depending on a real order.

Alternative considered: use `/calculate` or create a fake shipment as a probe. Rejected because calculation can fallback silently by design, and fake shipments risk side effects.

### 4. Add a Speedy operations service above the thin client

`speedy_client.py` should remain the HTTP protocol boundary: payload shape, endpoints, parsing, typed errors. A new service layer should own admin use cases: health aggregation, eligible order queues, cancellation policy, audit persistence, and response shaping.

This mirrors the Econt split between thin client and fulfillment service without forcing identical models.

### 5. Use `order_courier_events` for Speedy audit history

The existing courier event table already supports `courier IN ('speedy', 'econt')`. Reusing it gives consistent audit history for Speedy operations and avoids a new table. Payload snapshots must be redacted before insert; credentials should not be stored at all.

If more detailed pickup entities are needed in Phase 2, add a focused pickup table then.

### 6. Treat cancellation as shipment metadata management, not order cancellation

Speedy cancellation cancels the courier shipment, not the customer order. The local order should not become `cancelled` automatically. If Speedy accepts cancellation, local shipment metadata can be cleared or marked canceled according to a narrow policy, and the admin can then decide whether to recreate a waybill or cancel the order through the normal order state machine.

### 7. Keep pickup scheduling explicit and Phase 2

Pickup requests can affect courier operations and timing. They should require a deliberate admin action after operators can inspect eligible shipments and pickup terms. They should not run from checkout or automatic shipped transitions.

### 8. Official office refresh belongs in Phase 2

Checkout already uses static Speedy office data. Refreshing it from Speedy Location Service is useful, but it touches data scripts, normalization, and operational visibility. It should follow the core admin page rather than block Phase 1.

## Risks / Trade-offs

- Real courier side effects from shipment/cancel/pickup calls -> require explicit admin actions, reuse existing state guards, and test with fakes by default.
- Client-id mismatch can be confusing -> show the returned id and configured id, but never expose password or raw payload.
- Speedy cancellation may be rejected after pickup -> leave local metadata unchanged and show the courier reason.
- More admin UI complexity -> separate Phase 1 queues/actions from Phase 2 pickup/refresh tools with clear sections.
- Audit payloads could leak credentials -> construct audit payloads from safe inputs only and run shared redaction before persistence.
- Background polling overlap with returns/refunds work -> Phase 2 should integrate with that change rather than create a competing poller.

## Migration Plan

1. Add Speedy client methods for safe health, shipment search/info/cancel, pickup terms/request, and optional label info.
2. Add a Speedy admin service for health aggregation, queues, action guards, and event persistence.
3. Add admin API routes under `/v1/admin/speedy/*` and reuse existing order routes where appropriate.
4. Add `/admin/speedy` page and sidebar link.
5. Add Phase 1 tests and documentation.
6. Add Phase 2 pickup and office refresh after Phase 1 is stable.

Rollback: remove or hide the `/admin/speedy` sidebar link and disable new Speedy admin routes. Existing order shipping, label, and tracking behavior remains intact.

## Open Questions

- Should successful Speedy cancellation clear local `tracking_number`, or preserve it with a `courier_sync_status='shipment_cancelled'` marker for audit? Recommendation: preserve audit and clear active label/tracking only when recreating is supported.
- Do operators need DB-editable Speedy credentials, or is env-backed configuration sufficient?
- Should pickup confirmations be stored only in `order_courier_events`, or should Phase 2 add a dedicated pickup table for future reporting?
- Should shipment lookup by reference search only local order ids, or also support arbitrary admin-entered references?
