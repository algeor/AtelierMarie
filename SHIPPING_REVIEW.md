# Shipping Delivery Stack Review

Status: local automated gates pass; Chrome/full-stack execution is blocked in the Codex sandbox by local bind permissions. No commits made.

## Verified Implemented

- Delivery fees: `shipping_service.calculate_quotes` handles Speedy and Econt, free-shipping short-circuit, fallback provenance, cart DB weight, and door-address city translation.
- Office discovery: `GET /v1/delivery/offices` serves Speedy and Econt office/locker data with localized city names.
- Door place discovery: Econt uses `data/econt_cities.json`; Speedy uses full `data/speedy_sites.json`; `data/served_places_supplement.json` fills verified feed gaps such as Zgorigrad.
- Speedy shipping integration: admin confirmed-to-shipped can create Speedy waybills automatically when no manual tracking number is supplied; Speedy track and label endpoints are implemented and tested.
- Econt shipping integration: checkout pricing and manual admin shipment/tracking URL are implemented; Econt automatic waybill, tracking poll, and label PDF are not implemented yet.
- Admin management: order detail shows shipping totals/provenance and structured delivery details; real-app tests cover Econt manual shipment and Speedy waybill/track/label flows.
- Customer/admin emails: placed, payment-pending, shipped, and admin-new-order templates include subtotal, shipping, total, courier, method, destination, phone, and estimated-shipping marker.
- Browser smoke script: `scripts/chrome_smoke.mjs` now covers Speedy door checkout/admin track/label and Econt office checkout/manual admin ship, using fake local Speedy and Econt pricing boundaries.

## Last Local Verification

- `.venv/bin/ruff check .` passed.
- `.venv/bin/pytest tests/ -q` passed: 1201 tests.
- `.venv/bin/pytest tests/ --cov=app --cov-report=term-missing --tb=short` passed: 88% coverage.
- `cd frontend && npx vitest run` passed: 39 files / 244 tests.
- `cd frontend && npm run lint` passed.
- `cd frontend && npm run build` passed; Next still logs the known SWC lockfile patch warning because sandbox network cannot reach `registry.npmjs.org`.
- `node --check scripts/chrome_smoke.mjs` passed.

## Chrome Stack Blocker

`make test-chrome-stack` cannot run inside the current Codex sandbox:

```text
Error: listen EPERM: operation not permitted 127.0.0.1
```

An escalated retry was also rejected by the app approval reviewer before user approval:

```text
codex-auto-review INVALID_MODEL
```

Run this from a normal local terminal to prove the browser/full-stack requirement:

```bash
make test-chrome-stack
```

Expected flow lines include:

- `ok flow customer-speedy-door-checkout`
- `ok flow admin-confirm-ship-tracking`
- `ok flow customer-econt-office-checkout`
- `ok flow admin-econt-manual-ship-tracking`
- `ok flow mobile-smoke`

## Remaining Production-Readiness Gaps

1. Econt live safety: `mode=calculate` on `LabelService.createLabel` must be verified against Econt demo/test credentials before production credentials are used, to prove no billable waybill is created during price calculation.
2. Econt lifecycle parity: automatic Econt waybill creation, Econt shipment-status polling, and Econt label/PDF printing are not built. Current Econt admin flow is manual tracking only.
3. Server-authoritative checkout pricing: sub-free-shipping orders still accept client-submitted `shipping_cents` within the allowed range. A stronger design should re-price server-side at checkout or sign quote payloads and reject stale/forged quote data.
4. Econt office-code fidelity: local Econt office ids are normalized slugs. Before enabling live Econt office pricing/waybills, verify that the code sent as `receiverOfficeCode` is the exact Econt office code expected by the API.
5. Place-feed gaps: Zgorigrad is manually supplemented for both couriers and Roman is covered by Speedy's full site feed. More missing places should be added only with verified source data and ideally refreshed from courier nomenclature exports.
6. Live API probes: keep live Speedy/Econt probes opt-in. They should run only with demo/test credentials and never as part of default CI.
