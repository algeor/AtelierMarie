# Econt Integration Operations

## Credentials

- Ask Econt for the Delivery API `SHOP_ID` and private connection code for the shop account.
- Store only the private connection code in `ECONT_DELIVERY_PRIVATE_KEY`; do not include a `SHOP_ID@` prefix and do not paste it into frontend env files.
- Store the shop id in `ECONT_DELIVERY_SHOP_ID` or in Admin -> Econt -> Shop ID.
- Keep `ECONT_DELIVERY_BASE_URL=https://delivery-demo.econt.com/services/` until demo verification is complete.
- Leave `ECONT_OFFICE_LOCATOR_URL` unset unless Econt gives a shop-specific locator URL; the app derives demo/production locator URLs from the selected Econt environment.

## Demo Verification

1. Set backend Econt env vars and restart the backend.
2. Open Admin -> Econt, enable the integration, confirm sender origin/defaults, and run Test connection.
3. Place an Econt checkout order using the static picker or Office Locator.
4. Open the admin order detail and confirm the Econt panel is ready.
5. Run Sync order, Create label, Refresh trace, and confirm the customer order page shows only shipment number/tracking link.

For a guarded credentials-only smoke test that does not create shipments, run:

```bash
ECONT_DEMO_SMOKE=1 uv run python scripts/econt_demo_smoke.py
```

The smoke script refuses `https://delivery.econt.com/services/` even when a custom base URL override is enabled. Use `ECONT_DEMO_ALLOW_CUSTOM_BASE_URL=1` only for an Econt-approved non-production endpoint.

Do not switch to production until Econt confirms the demo payload fields and label output.

## Production Enablement

- Change the base URL to `https://delivery.econt.com/services/` only after demo sign-off.
- Keep label creation as a manual admin action for the first production orders.
- Verify COD amount/currency, sender office/address, recipient office code, and payment side on the first production label.
- Keep duplicate label prevention enabled by relying on existing shipment metadata.

## Rollback

- Disable Econt in Admin -> Econt.
- Existing orders keep local delivery details and manual tracking fields.
- Checkout does not need rollback because it does not call Econt during order creation.
- Admins can continue using manual tracking through the existing shipped status flow.
