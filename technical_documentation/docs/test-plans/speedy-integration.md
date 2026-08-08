# Speedy Integration Live Verification Plan

OpenSpec changes: `speedy-integration`, `speedy-admin-parity`.
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

7. Open `/admin/delivery/speedy` from `Admin -> Delivery -> Speedy`.
   - Expected: health/configuration summary uses `POST /client` and shows the verified client id.
   - Expected: password/credential payloads are not visible in the page or API response.
   - Expected: confirmed Speedy orders without tracking appear in the ready-to-ship queue.
   - Expected: shipped Speedy orders with tracking appear in the shipped queue.
   - Expected: legacy direct route `/admin/speedy` still renders the same operations page for existing links.

8. Exercise Speedy admin diagnostics with the demo order.
   - Expected: shipment search by local order id/reference returns the demo shipment id.
   - Expected: shipment info returns safe shipment details.
   - Expected: refresh tracking updates `courier_status` only.
   - Expected: recent history shows redacted operation events.

9. Exercise pickup terms with the demo shipment if the demo account supports pickup.
   - Expected: selected eligible shipment ids are sent to the pickup terms/request flow.
   - Expected: pickup failures return admin-safe validation/configuration errors.
   - Expected: no pickup request runs automatically during checkout or order confirmation.

## Error Checks

1. Use a bad office id for calculate.
   - Expected: pricing falls back cleanly and logs the Speedy error body in truncated form.

2. Use missing or bad credentials in a local/dev environment.
   - Expected: typed Speedy error is surfaced for shipment/track/print operations.
   - Expected: checkout/storefront paths do not crash.

3. Try shipping when Speedy create-shipment fails.
   - Expected: order stays `confirmed`.
   - Expected: no `shipped` state is committed without a waybill.

4. Try cancelling a Speedy shipment that Speedy rejects.
   - Expected: a redacted failed courier event is recorded.
   - Expected: local `tracking_number`, `courier_status`, and `courier_sync_status` remain unchanged.

5. Force returned/failed tracking in a fake/local test.
   - Expected: the order/payment/stock state is not mutated.
   - Expected: a returns/refunds review signal is created only when no return case exists yet.

## Evidence To Record

- Date, environment, and Speedy account type.
- Sanitized request scenario only; do not record secrets.
- Door quote price/source.
- Office quote price/source.
- Demo tracking number.
- Confirmation that retry did not create a duplicate waybill.
- Label PDF opened successfully.
- `/admin/delivery/speedy` health state and verified client id, without secrets.
- Recent Speedy event ids/actions, without request credentials.
- Cancellation rejection result proving local shipment metadata was preserved.
