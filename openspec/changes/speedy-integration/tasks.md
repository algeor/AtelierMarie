# Speedy Integration — Tasks

## 0. Verify demo account (BEFORE building)
- [x] Set `.env`: `SPEEDY_API_USERNAME=1996593`, `SPEEDY_API_PASSWORD=<pw>` (never commit).
- [x] Determine the value Speedy accepts for `sender.clientId` (login user vs. separate client object id); set `SPEEDY_CLIENT_ID=<numeric>`. → real 14-digit client number (NOT login user); verified accepted.
- [x] Live `calculate` (door mode) → confirm `price_source="live"` WITH the numeric `clientId` (proves sender identity, not just that a price returned). → DOOR 5.94 EUR / OFFICE 3.56 EUR, serviceId 505. Found bug: empty `serviceIds` → 400.
- [x] Confirm whether demo account permits `/shipment` create (gates section 3). → YES; `POST /v1/shipment` returned `id:63689182611` (=tracking number), `parcels[].id`, `pickupDate`, `price`. Test waybill VERIFY-PROBE exists (non-billing).
- [x] Identify Speedy office nomenclature endpoint + numeric-ID field (docs/live feed). → `POST /v1/location/office`, records have numeric `id`, `type` OFFICE/APS; 1284 offices.

## 1. Config-driven host + sender identity
- [x] Add `speedy_base_url` to `app/config.py` (default `https://api.speedy.bg/v1`).
- [x] Rename `speedy_sender_office_id` → `speedy_client_id`; thread into `sender.clientId`. Update `shipping_service.py` call site + tests.
- [x] Replace hardcoded `_CALCULATE_URL` in `speedy_client.py`; derive all endpoints from base.
- [x] Log a distinct `speedy_sender_client_id_invalid` warning when `speedy_client_id` is empty/non-numeric (not a generic fallback).
- [x] Prod-safety: if `ENVIRONMENT=production` and Speedy creds/client id empty → warn.

## 2. Fix office-ID pricing (Phase A blocker)
- [x] Repopulate `data/speedy_offices.json` with real numeric Speedy office IDs (extend `scripts/fetch_courier_offices.py`). → 1284 real offices, numeric `id` stored directly.
- [x] Thread numeric ID through `Office`/`OfficeResponse`/`DeliveryOffice` (or store as `id`) — decide per real feed shape. → stored numeric ID AS `id` (feed `id` is int); no new field needed.
- [x] `speedy_client.calculate` sends numeric `pickupOfficeId`. → office mode sends ONLY `pickupOfficeId` (no `addressLocation` — Speedy rejects both together).
- [x] Verify office-mode quote returns live price (no more 400 / €5 fallback). → OFFICE 3.56 EUR live, DOOR 5.94 EUR live (verified 2026-07-31).

## 3. Shipment creation (waybill)
- [x] `create_shipment(...)` → `POST {base}/shipment`, real recipient from order snapshot.
- [x] Wire into `update_status(order, "shipped")` (confirmed→shipped), NOT confirm: call only when courier is Speedy AND no tracking number supplied; use returned id as tracking_number. Extends the existing shipped-path + `TrackingRequiredError` guard.
- [x] Idempotent: existing `if not tracking_number` guard skips the courier call when a number already exists (re-ship never creates a 2nd waybill).
- [x] Failure raises `ShipmentCreationError` before the `UPDATE orders` — order stays `confirmed`, never `shipped` without a waybill; manual tracking-entry fallback preserved.
- [x] Persist `courier` (+ optional label id/url) on order; add DB column(s) if missing (`tracking_*` already exist).

## 4. Tracking
- [x] `track_shipment(tracking_number)` → `POST {base}/track`; normalize Speedy code → our `courier_status` display enum (`in_transit`/`out_for_delivery`/`delivered`/`returned`/`failed`).
- [x] Read-only/display-only: MUST NOT call `update_status` — the state machine stays admin-driven (delivery = human confirm through the guarded transition).
- [x] Surface `courier_status` on order detail (admin + customer).

## 5. Label printing
- [x] `print_label(tracking_number)` → `POST {base}/print` (PDF bytes).
- [x] Admin-only route streams the PDF.

## 6. Error handling
- [x] Map documented Speedy error codes (errorsExplanation) to typed exceptions for shipment/track/print.
- [x] Keep pricing fallback behavior unchanged; log truncated Speedy error body everywhere.

## 7. Tests + verification
- [x] Payload-contract test: assert assembled Speedy calculate payload has numeric `sender.clientId` (+ numeric `pickupOfficeId` in office mode) — independent of the mocked HTTP response, so a bad payload can't stay green.
- [x] Unit tests: shipment/track/print happy path + error mapping (mock httpx).
- [x] Live verification (section "Verification plan" in design.md) against demo account.
- [x] Full backend suite + ruff green; frontend order-detail tracking render test.
