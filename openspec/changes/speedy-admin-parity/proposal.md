## Why

Speedy fulfillment works today, but it is scattered across the order list, order status transition, label endpoint, tracking endpoint, environment variables, and delivery toggles. Econt now has a dedicated admin surface, so Speedy needs the same operational clarity: health, lookup, label, track, cancel, pickup planning, and audit visibility in one place.

This change makes Speedy a first-class admin integration without changing the existing rule that shipment creation happens on the `confirmed -> shipped` transition and tracking remains read-only.

## What Changes

- Add a dedicated `/admin/speedy` page and sidebar entry.
- Add Phase 1 Speedy admin operations:
  - credential/client health check using safe official Client Service calls;
  - configuration summary for env-backed Speedy credentials and delivery toggles;
  - recent Speedy order queues for ready-to-ship and shipped orders;
  - order-level actions for create/reuse waybill, print label, refresh tracking, shipment lookup, and guarded cancellation;
  - admin-safe error display and recent Speedy operation history.
- Add Phase 2 Speedy admin operations:
  - pickup terms and pickup request workflow;
  - Speedy office/location data refresh from official Location Service APIs;
  - richer shipment inspection/search by order reference;
  - durable Speedy audit events and operational metrics;
  - optional background courier polling alignment with the returns/refunds workflow.
- Extend the Speedy client/service layer for official endpoints currently not exposed by the app: `client`, `client/{id}`, `shipment/info`, `shipment/search`, `shipment/cancel`, `pickup/terms`, and `pickup`.
- Preserve existing customer checkout behavior and the current Speedy shipped-transition safety guarantees.

## Capabilities

### New Capabilities

- `speedy-admin`: Dedicated Speedy admin page, admin API operations, health/readiness, shipment lookup, label/track/cancel actions, pickup workflow, and operator-facing audit state.

### Modified Capabilities

- `speedy-integration`: Add safe account/client health checks, shipment info/search/cancel, pickup terms/request, and audit requirements to the existing Speedy API integration contract.
- `admin-layout`: Add a Speedy navigation item and active-route behavior for `/admin/speedy`.
- `admin-orders`: Cross-link Speedy order fulfillment state/actions with the dedicated Speedy page while preserving existing order list/detail workflows.
- `courier-offices-data`: Add Phase 2 Speedy office/location refresh from official Speedy Location Service APIs.
- `external-call-resilience`: Apply timeout, typed error, redaction, and circuit-breaker rules consistently to all new Speedy operational calls.

## Impact

- Backend: `app/services/speedy_client.py`, new Speedy admin/service helpers, admin routes, order courier event persistence, response models, config health checks, tests.
- Frontend: new `/admin/speedy` route, sidebar/i18n strings, API client/types, admin order list/detail integration, tests.
- Data: possible reuse or extension of `order_courier_events` for Speedy; no customer/order breaking migration expected.
- External systems: official Speedy REST API under `SPEEDY_BASE_URL` for Client, Shipment, Print, Track, Pickup, and Location services.
- Operations: gives admins a safe place to validate credentials, diagnose misconfiguration, and manage Speedy shipments without manually probing API endpoints.
