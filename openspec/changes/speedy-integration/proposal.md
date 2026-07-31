# Speedy Integration — Proposal

## Why

We now have a **Speedy demo account** (user `1996593`, connected to a fictional
client object in Speedy's *real* system, so test traffic never bills a real
contract). This unblocks the work that Phase A left as a known gap: Speedy live
pricing does not actually work today, and shipment creation/tracking/labels do
not exist at all.

Two problems block correct Speedy pricing (both documented in project memory
`project-shipping-speedy-office-id`):

1. **Office pickup 400s.** `POST /v1/calculate` rejects our office IDs because
   `data/speedy_offices.json` stores synthetic slugs (`speedy-sf-002`) but
   Speedy's `pickupOfficeId` must be a **numeric integer**. Every office-mode
   quote silently degrades to the €5 flat fallback.
2. **Unverified against a real account.** All Speedy calls have run
   anonymously / with placeholder creds, so we have never confirmed a live
   `price_source="live"` quote end-to-end.

Beyond pricing, the store cannot yet actually *ship*: there is no waybill
creation, no tracking, no printable label.

## What changes

Correct and complete the Speedy integration against the demo account, per the
official REST API (`https://api.speedy.bg/web-api.html`, examples at
`https://services.speedy.bg/api/api_examples.html`):

1. **Fix pricing** — real numeric office IDs so office-mode quotes price live;
   verify door + office quotes return `price_source="live"` with the demo creds.
2. **Config-driven** — Speedy base URL + credentials from settings/env (no
   hardcoded host), so demo↔prod is an env change.
3. **Create shipments (waybills)** at order confirmation, store the parcel /
   tracking number on the order.
4. **Track shipments** — fetch status, surface on the order.
5. **Print labels** — fetch the PDF label for a created shipment.

## Scope

- **In:** Speedy `calculate`, `shipment` (create), `track`, `print` REST
  endpoints; office-ID data fix; config-driven host+creds; order-level storage
  of tracking number; error-code mapping from Speedy's documented errors.
- **Out:** Econt waybill/tracking/label (separate change — see
  `ECONT_HANDOVER.md`); Speedy pickup scheduling; returns; COD reconciliation
  beyond storing the flag.

## Impact

- `app/services/speedy_client.py` — add shipment/track/print; fix pricing IDs.
- `app/config.py` — `speedy_base_url` + rename `speedy_sender_office_id` →
  `speedy_client_id` (numeric `sender.clientId`, distinct from the API login).
- `data/speedy_offices.json` + `scripts/fetch_courier_offices.py` — real numeric IDs.
- `app/models/{shipping,orders,delivery}.py`, `app/services/order_service.py`,
  `app/routes/` — waybill/tracking fields + endpoints.
- Tests: `tests/test_courier_clients.py`, new shipment/track tests.

## Credentials (demo)

- User: `1996593`
- Password: stored via env (`SPEEDY_API_PASSWORD`), NOT committed.
- Note: demo user maps to a fictional client in Speedy's **real** system —
  waybills created will exist in Speedy's system but not bill a real contract.
  Still: create shipments deliberately, clean up test waybills where possible.
