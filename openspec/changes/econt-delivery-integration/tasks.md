## 1. Data Model And Office Codes

- [x] 1.1 Extend normalized courier office schema with `code: str | None` in backend models and frontend types.
- [x] 1.2 Update `scripts/normalize_econt_office_data.py` to preserve raw Econt `code` as normalized `code`.
- [x] 1.3 Regenerate `data/econt_offices.json` from `data/econt_offices_raw.json` and verify representative offices include `code`.
- [x] 1.4 Update `delivery_service` locale projection to include `code` without breaking older records.
- [x] 1.5 Update `/v1/delivery/offices` tests for Econt code presence and legacy missing-code fallback.
- [x] 1.6 Extend `DeliveryOffice` with optional `office_code` and validate that Econt office delivery has a code at checkout.
- [x] 1.7 Update checkout/order tests to assert Econt `office_code` persists in `delivery_details`.

## 2. Database Migration

- [x] 2.1 Add `integration_settings` or Econt-specific settings table for non-secret settings.
- [x] 2.2 Add order courier metadata columns: `courier_order_id`, `courier_shipment_number`, `courier_label_url`, `courier_label_created_at`, `courier_sync_status`, `courier_last_error`, `courier_last_synced_at`.
- [x] 2.3 Add `order_courier_events` table with order id, courier, action, status, redacted payload JSON, error JSON, actor/admin id if available, and timestamp.
- [x] 2.4 Add additive startup migrations for existing SQLite DBs.
- [x] 2.5 Add database tests for fresh schema and existing DB migration.

## 3. Settings Backend

- [x] 3.1 Add Econt settings models for public admin reads, updates, secret state, and test-connection result.
- [x] 3.2 Add `Settings` env vars for Econt secret fallback: base URL, private key, shop id, office locator URL/origins, and optional encryption key.
- [x] 3.3 Implement settings service to merge DB non-secret settings with env-backed secret state.
- [x] 3.4 Implement secret redaction helpers used by settings, client logs, and event snapshots.
- [x] 3.5 Add admin routes for get/update Econt settings and test connection.
- [x] 3.6 Add backend tests for admin auth, env-backed secrets, update persistence, redaction, and missing config errors.

## 4. Econt Client

- [x] 4.1 Create typed Econt client request/response models for `Order`, `CustomerInfo`, `OrderItem`, `ShipmentStatus`, and trace events.
- [x] 4.2 Implement `EcontDeliveryClient` with `update_order`, `create_awb`, `get_trace`, `delete_label`, and a safe test call.
- [x] 4.3 Add per-request timeout, base URL switching between demo/production, shop id headers, and Authorization header injection.
- [x] 4.4 Classify errors into config/auth, validation, transient outage, circuit-open, and unexpected response.
- [x] 4.5 Add dedicated Econt circuit breaker and admin health exposure.
- [x] 4.6 Add unit tests using mocked `httpx` for success, auth error, validation error, timeout, 5xx, malformed JSON, and circuit-open behavior.

## 5. Fulfillment Service

- [x] 5.1 Implement local order to Econt payload mapping for office delivery, door delivery, COD, non-COD, currency, pack count, description, declared value, sender origin, and item weights.
- [x] 5.2 Validate label readiness before Econt calls: enabled settings, credentials, shop id, sender origin, Econt courier, recipient phone, office code for office delivery, and supported order status.
- [x] 5.3 Implement `sync_order` via `OrdersService.updateOrder` and persist courier order id/status where available.
- [x] 5.4 Implement `create_label` via `OrdersService.createAWB` with idempotency guard when shipment number already exists.
- [x] 5.5 Persist shipment number, label URL, local tracking fields, sync timestamps, and fulfillment events after successful label creation.
- [x] 5.6 Implement `delete_label` with local status safety checks and local metadata cleanup only after courier success.
- [x] 5.7 Implement `refresh_trace` with trace event persistence and optional valid local status transitions.
- [x] 5.8 Add tests for payload mapping, validation blockers, idempotency, status transitions, metadata persistence, event audit, and redaction.

## 6. Admin API And Order Integration

- [x] 6.1 Add admin route to validate Econt readiness for an order.
- [x] 6.2 Add admin route to sync/update an Econt order.
- [x] 6.3 Add admin route to create Econt AWB/label.
- [x] 6.4 Add admin route to delete Econt label where safe.
- [x] 6.5 Add admin route to refresh Econt trace.
- [x] 6.6 Extend order response models with public-safe courier shipment fields and admin-only last error/event details where appropriate.
- [x] 6.7 Update existing admin status route behavior so Econt label metadata can satisfy shipped tracking requirements.
- [x] 6.8 Add route tests for auth, non-Econt rejection, missing code/config errors, successful fake-client actions, duplicate-create prevention, and trace refresh.

## 7. Customer Checkout UI

- [x] 7.1 Extend frontend delivery types and API client types with `office_code` and office response `code`.
- [x] 7.2 Update static Econt office picker to store `office_code` when selecting an Econt office.
- [x] 7.3 Add optional Econt Office Locator component with origin validation, environment URL config, city/language params, loading state, and selected-office confirmation.
- [x] 7.4 Keep static office picker as fallback when locator is disabled or unavailable.
- [x] 7.5 Update checkout validation to block Econt office submission without `office_code`.
- [x] 7.6 Update checkout tests for static picker code, locator message normalization, unknown-origin ignore, and form preservation on errors.

## 8. Customer Order And Tracking UI

- [x] 8.1 Update order confirmation page to show Econt shipment number and tracking link once available.
- [x] 8.2 Update customer order detail page to show public-safe Econt tracking summary and latest trace state.
- [x] 8.3 Ensure customer pages hide raw courier errors and admin-only fulfillment state.
- [x] 8.4 Add frontend tests for label-not-created, label-created, trace-available, and trace-error-hidden states.

## 9. Admin Settings UI

- [x] 9.1 Add Econt settings page or admin settings panel route following existing admin design patterns.
- [x] 9.2 Render non-secret settings, credential configured state, environment selector, enabled toggle, sender origin fields, shipment defaults, office locator toggle, and auto-status-sync toggles.
- [x] 9.3 Add save flow with dirty state, validation, loading state, success/error messages, and secret masking.
- [x] 9.4 Add test-connection action with categorized result display.
- [x] 9.5 Add admin settings UI tests for loading, save, secret masking, validation errors, and test-connection outcomes.

## 10. Admin Order Fulfillment UI

- [x] 10.1 Add Econt fulfillment panel to admin order detail for Econt orders.
- [x] 10.2 Show readiness checklist, sync status, shipment number, label PDF action, tracking link, last sync time, and last admin-safe error.
- [x] 10.3 Add actions for validate, sync order, create label, delete label, refresh trace, and use shipment number for shipped transition.
- [x] 10.4 Add repair controls for missing office code, package count, shipment description, and payment side before label creation.
- [x] 10.5 Add loading/disabled states to prevent duplicate action clicks.
- [x] 10.6 Add admin order UI tests for ready, blocked, created, failed, retry, and non-Econt states.

## 11. i18n And Copy

- [x] 11.1 Add Bulgarian and English strings for Econt settings, checkout locator, fulfillment panel, readiness blockers, actions, success states, and error categories.
- [x] 11.2 Keep customer copy concise and non-technical; keep admin copy actionable and specific.
- [x] 11.3 Add tests or snapshots covering the new translation keys used by checkout/admin components.

## 12. Documentation And Operations

- [x] 12.1 Update `.env.example` with Econt env vars and safe demo/prod notes.
- [x] 12.2 Add admin/operator notes for obtaining Econt `SHOP_ID` and private connection code.
- [x] 12.3 Document demo-mode verification steps and production enablement checklist.
- [x] 12.4 Document rollback: disable Econt integration, keep manual tracking, no checkout rollback required.

## 13. End-To-End Verification

- [x] 13.1 Run backend tests covering delivery, orders, admin routes, config, database, and Econt services.
- [x] 13.2 Run frontend tests covering checkout, admin settings, admin order detail, and customer order pages.
- [x] 13.3 Run OpenSpec validation/status for this change.
- [x] 13.4 Manually verify demo-mode flow with fake client: Econt checkout -> order -> admin create label -> label visible -> customer tracking visible.
- [ ] 13.5 When real demo credentials exist, run a guarded Econt demo smoke test without production shipment creation.
