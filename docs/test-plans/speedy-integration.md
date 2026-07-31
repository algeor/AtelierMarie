# Speedy Integration Live Verification Plan

OpenSpec change: `speedy-integration`.
Manual gate moved from the change tasks before archive.

## Preconditions

- Use Speedy demo credentials only.
- Set env vars outside git:
  - `SPEEDY_API_USERNAME`
  - `SPEEDY_API_PASSWORD`
  - `SPEEDY_CLIENT_ID`
  - `SPEEDY_BASE_URL=https://api.speedy.bg/v1`
- Backend test suite and ruff have already passed.
- Use a non-billing demo shipment/order.

## Live API Checks

1. Calculate a door quote.
   - Use a known-good recipient city, postcode, address, and parcel weight.
   - Expected: quote returns `price_source="live"`, `is_fallback=false`, and a positive price.

2. Calculate an office quote.
   - Use a real numeric Speedy office id from `data/speedy_offices.json`.
   - Expected: quote returns `price_source="live"`, `is_fallback=false`, and a positive price.

3. Create a shipment for a demo order.
   - Expected: Speedy returns a tracking number / shipment id.
   - Expected: order moves to `shipped` only when a tracking number is available.

4. Retry the same ship action.
   - Expected: no second waybill is created.
   - Expected: existing tracking number remains unchanged.

5. Track the demo shipment.
   - Expected: Speedy status maps to the local read-only courier status.
   - Expected: local order lifecycle status is not advanced by tracking alone.

6. Print the label.
   - Expected: admin-only label endpoint returns valid PDF bytes.

## Error Checks

1. Use a bad office id for calculate.
   - Expected: pricing falls back cleanly and logs the Speedy error body in truncated form.

2. Use missing or bad credentials in a local/dev environment.
   - Expected: typed Speedy error is surfaced for shipment/track/print operations.
   - Expected: checkout/storefront paths do not crash.

3. Try shipping when Speedy create-shipment fails.
   - Expected: order stays `confirmed`.
   - Expected: no `shipped` state is committed without a waybill.

## Evidence To Record

- Date, environment, and Speedy account type.
- Sanitized request scenario only; do not record secrets.
- Door quote price/source.
- Office quote price/source.
- Demo tracking number.
- Confirmation that retry did not create a duplicate waybill.
- Label PDF opened successfully.
