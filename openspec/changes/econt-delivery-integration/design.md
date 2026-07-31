## Context

The current app already has a structured delivery picker, static Econt/Speedy office data, order delivery snapshots, payment methods, order emails, admin order pages, tracking fields, and product `weight_grams`. The missing piece is operational fulfillment: creating Econt shipments, printing labels, refreshing trace data, and letting the admin configure the integration without code changes.

Econt Delivery exposes JSON endpoints under `https://delivery.econt.com/services/` and demo endpoints under `https://delivery-demo.econt.com/services/`. The relevant methods are `OrdersService.updateOrder`, `OrdersService.createAWB`, `OrdersService.getTrace`, and `OrdersService.deleteLabel`. Requests are POST JSON and use `Authorization: <connection code>` plus shop identity. The docs use `CustomerInfo.officeCode` for office delivery, while our normalized `data/econt_offices.json` currently stores only an internal id like `econt-1029`. The raw Econt dump contains both `id` and `code`, so the normalized catalog must preserve `code` before label generation is reliable.

## Goals / Non-Goals

**Goals:**

- Give customers a polished Econt delivery path that fits the existing checkout instead of redirecting them into a foreign checkout.
- Let admins configure Econt credentials, sender origin, defaults, and fulfillment behavior from the admin app.
- Create, update, delete, and track Econt shipments from local order records.
- Keep checkout fast and reliable by avoiding external Econt calls inside the order transaction.
- Persist enough courier metadata to make fulfillment auditable, retryable, and recoverable.
- Make the implementation testable without real Econt credentials by isolating the API client behind fakes.

**Non-Goals:**

- Replacing the full checkout with Econt's hosted `customer_info.php` flow.
- Building a live sync daemon or webhook receiver in the first version.
- Supporting international shipping outside Bulgaria.
- Supporting multi-parcel optimization beyond a default single parcel plus admin override.
- Replacing Speedy integration. Econt becomes first-class; Speedy remains supported by the existing delivery abstractions.

## Decisions

### 1. Keep AtelierMarie checkout as source of truth

Customers continue to complete checkout in AtelierMarie. We do not redirect to Econt's hosted checkout because the app already owns cart, pricing, payments, emails, order history, and legal disclosures. Econt is used as a fulfillment provider after local order creation.

Alternative considered: embed `customer_info.php` for the whole delivery form. Rejected because it duplicates checkout state, complicates Stripe/bank/COD behavior, and makes the UX inconsistent with Speedy.

### 2. Add optional Econt Office Locator, but keep static picker fallback

The Econt Office Locator iframe is valuable because it returns live office data with `id`, `code`, `name`, and full address. The checkout may use it when `ECONT_OFFICE_LOCATOR_ENABLED` is true. The existing static office picker remains the default/fallback because it is already integrated, testable, and consistent with Speedy.

When the locator is used, the selected office is normalized into the same `DeliveryOffice` object plus `office_code`. The message listener validates origin against configured staging/prod locator origins.

### 3. Preserve courier-native office codes

`OfficeResponse` and normalized office JSON gain `code: string | null`. For Econt this is the official office code required by `CustomerInfo.officeCode`. For Speedy it can be null or the provider's office id if useful later. Existing `office_id` remains the stable internal key (`econt-<id>`) to avoid breaking stored orders.

At checkout, Econt office delivery stores both `office_id` and `office_code`. At label creation, missing `office_code` is a blocking validation error with an admin repair path.

### 4. Store Econt settings in the database, secrets encrypted or env-backed

Admin settings are persisted in a small integration settings table. Non-secret fields live in DB: enabled flag, environment, shop id, sender delivery mode, sender office code/address, default pack count, shipment description, declared value flag, default payment side, office locator toggle. Secrets use one of two modes:

- env mode: `ECONT_DELIVERY_PRIVATE_KEY` and related values come from environment and the admin UI shows configured/not configured;
- stored mode: encrypted secret storage if an app encryption key is configured.

MVP implementation can start with env-backed secrets and DB-backed non-secrets. The UI must not echo secrets after save.

### 5. Econt client is thin; fulfillment service owns business mapping

`econt_delivery_client.py` only knows HTTP, headers, endpoints, timeouts, and typed responses. `econt_fulfillment_service.py` maps local orders to Econt `Order`, applies payment rules, validates delivery details, handles idempotency, persists snapshots, and updates local tracking/status fields.

This keeps courier protocol concerns separate from AtelierMarie order semantics.

### 6. No external API call inside checkout transaction

Checkout creates the local order only. Econt shipment creation is an admin action or a post-checkout background/outbox action controlled by settings. The default is manual admin action: safer for production because `createAWB` can create real shipments.

Future auto-create can be enabled after real-account testing by queueing a fulfillment job after the checkout transaction commits.

### 7. Admin fulfillment is explicit and idempotent

Admin order detail gets an Econt panel with actions:

- validate Econt readiness;
- sync/update order in Econt;
- create AWB/label;
- open/download label PDF;
- refresh trace;
- delete label when order is not shipped/delivered;
- retry failed action.

If an order already has `econt_shipment_number`, `createAWB` is not called again unless the admin explicitly chooses a guarded recreate flow. This prevents duplicate labels.

### 8. Shipment metadata lives on the order plus an event table

Orders gain denormalized fields for common display and filtering: `courier_order_id`, `courier_shipment_number`, `courier_label_url`, `courier_label_created_at`, `courier_sync_status`, `courier_last_error`, `courier_last_synced_at`. A separate `order_courier_events` table stores action history and trace events with JSON payloads.

This avoids stuffing all state into `delivery_details` while preserving auditability.

### 9. Payment mapping is deterministic

COD orders (`payment_method='cod'`) send `cod=true`, `orderSum`, and configured currency. Card and bank transfer orders send `cod=false`. Currency defaults to the shop currency (`EUR` in AtelierMarie), but admin settings allow a courier currency override if the Econt account requires BGN. If BGN is selected, conversion must use an explicit configured fixed rate and must be shown as an operational setting, not hidden logic.

### 10. Weight and package defaults are conservative

Shipment `items[].totalWeight` is computed from product `weight_grams`; order-level packaging grams are added from settings. MVP uses `packCount=1` by default. Admin may override pack count before creating the label.

### 11. Status and tracking updates respect the existing state machine

Creating an AWB stores the Econt shipment number and tracking URL. It may move `pending -> confirmed` automatically if configured, but it must not jump `pending -> shipped` because the current state machine forbids that. The default admin flow is: confirm order, create label, then mark shipped using the returned shipment number. A convenience action may perform valid chained transitions when allowed.

Trace refresh updates tracking events and may suggest a local status change. Automatic `shipped -> delivered` is allowed only when the trace clearly indicates delivery and the admin setting is enabled.

### 12. Econt failures are operational, not customer-facing

Econt failures are stored with redacted payloads and shown to admins with actionable messages. Customers see only local order/tracking state. Secrets and Authorization headers are never stored in snapshots or logs.

### 13. Circuit breaker and timeout rules mirror existing external-call patterns

Each Econt call uses a short timeout, retry classification, and a dedicated circuit breaker. 5xx and timeouts count as service failures. 4xx validation/auth errors are shown as configuration/order-data problems and do not trip the outage circuit.

## Risks / Trade-offs

- Econt docs are incomplete around some validation fields -> mitigate with typed fakes first, demo-account smoke tests, and payload snapshots for support.
- Duplicate real shipments could cost money -> default to manual creation, enforce idempotency on existing shipment numbers, and require explicit recreate confirmation.
- Stored secrets raise security risk -> start env-backed, redact everywhere, and only add encrypted DB secrets with an app encryption key.
- Office catalog may be stale -> preserve office code in refresh script, offer Econt Office Locator for live selection, and block label creation if office code is missing.
- Currency mismatch could cause COD errors -> expose currency choice in admin settings and do not auto-convert without an explicit configured rate.
- Admin UI can become cluttered -> place fulfillment controls inside a dedicated Econt panel on order detail and a dedicated Econt settings page.

## Migration Plan

1. Add nullable DB columns/tables for Econt settings, courier shipment fields, and courier events.
2. Extend Econt office normalization with `code`, regenerate `data/econt_offices.json`, and keep compatibility for existing records without code.
3. Add backend models/client/service behind disabled settings; tests use fake client.
4. Add admin settings UI and health/test-connection endpoint.
5. Add admin order Econt fulfillment panel and actions.
6. Add customer-facing order/tracking display for Econt shipment metadata.
7. Enable demo mode in development; production remains disabled until real credentials are configured and a test label is verified.

Rollback: disable Econt integration in settings. Existing orders keep local delivery details and manual tracking fields; no checkout rollback is required.

## Resolved Questions

- Hosted Econt checkout vs local checkout: local checkout wins.
- Static office data vs Office Locator: support both; static fallback remains.
- Automatic label at checkout vs admin action: admin action by default.
- Which Econt endpoints matter first: `updateOrder`, `createAWB`, `getTrace`, `deleteLabel`.
- What blocks reliable label creation: missing `officeCode`, credentials, sender origin, currency/COD settings, package defaults.
