# Shipping, Delivery, And Couriers

Use this when touching delivery choice, courier offices, shipping prices, tracking, labels, Econt, or Speedy.

## Main Backend Files

- `app/models/delivery.py`: structured delivery input/output.
- `app/models/shipping.py`: shipping quote models.
- `app/routes/delivery.py`: public delivery settings, offices, cities/places, shipping quote endpoint.
- `app/routes/admin.py`: admin delivery settings, labels, tracking, order shipping.
- `app/services/delivery_service.py`: office/city/place lookup.
- `app/services/delivery_settings_service.py`: enable/disable courier/method combinations.
- `app/services/shipping_service.py`: quote orchestration and fallback.
- `app/services/econt_client.py`: Econt API client.
- `app/services/speedy_client.py`: Speedy API client.
- `app/services/order_service.py`: checkout delivery validation and ship transition.
- `app/services/pricing.py`: totals/free shipping helpers.

## Main Frontend Files

- `frontend/components/checkout/DeliverySection.tsx`
- `frontend/components/checkout/CourierComparison.tsx`
- `frontend/components/checkout/DeliveryDetails.tsx`
- `frontend/components/checkout/ShippingPriceSummary.tsx`
- `frontend/app/[locale]/checkout/page.tsx`
- `frontend/app/[locale]/admin/delivery/page.tsx`
- `frontend/components/admin/ShipOrderModal.tsx`

## Delivery Model

Customers choose:

1. method: office or door
2. courier: Speedy or Econt
3. location details
4. final shipping quote

Office delivery stores a chosen office. Door delivery stores structured address fields.

Do not go back to a single free-text shipping textarea.

## Quote Rules

- Quote endpoint returns live courier prices when credentials and APIs work.
- If courier API fails, the app can fallback to table/flat pricing.
- Quote provenance is recorded: source, fallback flag, quoted timestamp.
- Free shipping threshold can force shipping to 0.
- Checkout validates the submitted shipping cents range and normalizes provenance.
- The current MVP does not cryptographically sign quote tokens. Admin review still matters.

## Courier Data Rules

- Office/city/place data is courier-specific.
- Same-named places need disambiguation by region/postcode where available.
- Office IDs and office type are validated at checkout.
- Disabled courier/method pairs should be rejected before order creation.

## Speedy Rules

- Speedy credentials and sender identity come from config.
- `speedy_client_id` must be numeric for real shipment calls.
- On confirmed-to-shipped transition, a Speedy order can create a waybill automatically if no manual tracking number is supplied.
- Waybill creation runs before the order is marked shipped.
- If waybill creation fails, the order must stay `confirmed`.
- Tracking is read-only display data. It does not drive the order state machine.
- Label printing should not expose customer data in logs.

## Econt Rules

- Econt sender identity comes from config.
- Live pricing can degrade to fallback if credentials/API are unavailable.
- Keep payload/client code isolated in the Econt client/service layer.

## Safe Change Checklist

- Office and door delivery both still validate.
- Disabled methods are rejected.
- Free shipping still wins when threshold is reached.
- Checkout total includes shipping.
- Admin order detail shows delivery details and tracking.
- Speedy ship failure does not mark order shipped.
- Tests cover quote success, fallback, invalid office, disabled method, and ship transition.

