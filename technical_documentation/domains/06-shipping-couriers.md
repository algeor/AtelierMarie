# Shipping And Couriers

Shipping covers delivery selection, live/fallback pricing, courier data, tracking, and labels.

## Main Backend Files

- `app/models/delivery.py`
- `app/models/shipping.py`
- `app/routes/delivery.py`
- `app/routes/admin.py`
- `app/services/delivery_service.py`
- `app/services/delivery_settings_service.py`
- `app/services/shipping_service.py`
- `app/services/econt_client.py`
- `app/services/speedy_client.py`
- `app/services/order_service.py`

## Main Frontend Files

- `frontend/components/checkout/DeliverySection.tsx`
- `frontend/components/checkout/CourierComparison.tsx`
- `frontend/components/checkout/DeliveryDetails.tsx`
- `frontend/components/checkout/ShippingPriceSummary.tsx`
- `frontend/components/admin/ShipOrderModal.tsx`
- `frontend/app/[locale]/admin/delivery/page.tsx`

## Delivery Payload

Checkout sends a `DeliveryInfo` object.

Office delivery:

- method `office`
- `office` object present
- `door` null
- courier, office id/name/type, city, phone

Door delivery:

- method `door`
- `door` object present
- `office` null
- courier, city, postal code, street, optional building/apartment, phone

## Shipping Quote Flow

```text
checkout asks for quote
  -> POST /v1/delivery/calculate
  -> shipping_service.cart_weight_grams reads product weights
  -> if items total >= free threshold, return 0 cent quotes
  -> otherwise call requested courier clients concurrently
  -> each quote is live or fallback independently
  -> frontend stores chosen shipping cents/source/timestamp
  -> checkout submits selected quote fields
```

## Checkout Shipping Validation

During checkout:

- delivery method and details are validated by Pydantic
- office id/type is checked against delivery catalogue
- disabled courier/method pairs are rejected
- free shipping is re-enforced server-side
- shipping cents is range-validated
- price source is normalized
- fallback flag is derived from source
- quoted timestamp is kept only if it parses

## Courier Data

Public endpoints expose:

- offices
- cities
- places/postcodes
- delivery availability settings

Same-named places need region/postcode disambiguation.

## Speedy Shipment Flow

When admin marks a Speedy order shipped and does not provide a tracking number:

```text
order_service.update_status
  -> detect delivery_courier=speedy
  -> create Speedy shipment before status update
  -> returned tracking becomes tracking_number
  -> status update commits
```

If Speedy shipment creation fails, the order remains `confirmed`.

## Tracking And Labels

- Tracking is display-only.
- Tracking does not drive fulfillment state.
- Label URL/id is stored when courier API returns it.
- Admin can print/poll labels/tracking where implemented.

## Safe Change Checklist

- Office and door payloads still reject mismatched objects.
- Free shipping short-circuits before courier calls.
- Courier API failure returns fallback instead of crashing checkout.
- Checkout total includes shipping snapshot.
- Speedy ship failure does not mark order shipped.
- COD shipment uses COD amount only when payment is not already paid.

