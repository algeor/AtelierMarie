# Econt Integration Handover

Status: checkout pricing, place/office discovery, customer checkout, and manual admin shipment are implemented and covered by local tests. Automatic Econt waybill creation, live tracking polling, and label/PDF printing are future work.

## What Exists

- `app/services/econt_client.py` implements `calculate()` using Econt `LabelService.createLabel` with `mode=calculate` and degrades to the flat fallback on any error.
- `app/config.py` exposes `ECONT_CALCULATE_URL`; default is the production Econt calculate URL, and tests/Chrome smoke can point it to a fake local endpoint.
- `app/services/shipping_service.py` fans out quotes for Speedy and Econt and forwards door-address details with courier-specific Bulgarian city resolution.
- `app/routes/delivery.py` exposes courier offices, office cities, served places, and shipping calculation.
- `data/econt_cities.json` is the current local Econt settlement feed; `data/served_places_supplement.json` adds verified missing served places.
- `scripts/chrome_smoke.mjs` includes an Econt office checkout flow and manual admin ship/tracking URL verification, using a fake local Econt pricing server when `CHROME_SMOKE_START_SERVERS=1`.
- Tests covering Econt behavior live in `tests/test_courier_clients.py`, `tests/test_shipping_service.py`, `tests/test_delivery_calculate_routes.py`, `tests/test_delivery_routes.py`, `tests/realapp/test_order_routes.py`, and frontend checkout/mock tests.

## Live Safety Notes

- Econt pricing still carries a high-safety TODO: prove `mode=calculate` creates no billable waybill before using production credentials.
- Prefer demo/test credentials first. Record whether the credentials target `demo.econt.com` or `ee.econt.com` before creating any non-calculate labels.
- Do not add Econt waybill creation until the account host and billing behavior are clear.
- Keep live probes opt-in; default tests should continue using mocks/fakes.

## Future Econt Parity Work

1. Verify `mode=calculate` with Econt demo/test account and confirm no shipment appears in the dashboard.
2. Verify the correct office code field for `receiverOfficeCode`; local normalized ids may need to preserve the raw Econt office code separately.
3. Build real Econt waybill creation behind an explicit admin ship action or status transition.
4. Store returned Econt tracking/label identifiers on the existing order tracking fields.
5. Add Econt track/status polling endpoint analogous to Speedy, but keep order status unchanged unless an admin changes it.
6. Add Econt label/PDF printing endpoint once real waybills exist.
7. Extend Chrome/full-stack smoke from manual Econt tracking to real Econt fake waybill/track/label once the implementation exists.

## Current Verification Command

Run the full local browser stack from a normal terminal, not the Codex sandbox:

```bash
make test-chrome-stack
```

The Codex sandbox currently blocks local server binding with `listen EPERM 127.0.0.1`.
