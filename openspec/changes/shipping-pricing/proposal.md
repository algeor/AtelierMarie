## Why

The `shipping-courier-integration` change (parent) delivers the structured delivery picker: customers choose method (office/door), courier (Speedy/Econt), and specifics (office_id + phone, or full address). But it ships with a placeholder shipping cost — either flat `€0` or a fixed constant — because real courier price calculation depends on API accounts, product weight data, and a two-phase UX flow that materially expands scope.

This change adds the pricing layer on top of the picker: real-time price calculation via Speedy and Econt calculation APIs, per-product weight, free shipping above €50, courier-comparison UI, and a graceful fallback when the courier APIs are down.

Splitting this off lets the delivery picker ship as soon as it's built (customers pick real offices, orders carry structured delivery info) without blocking on courier account provisioning or the more complex two-phase price UX.

## What Changes

> **Phase A of a phased rollout.** This change delivers **live courier pricing + flat fallback + price provenance**. The shaped snapshot-table fallback (Phase B) and quoted-vs-invoice reconciliation (Phase C) are follow-on changes — see `design.md` → Phasing. Provenance is captured now so B/C need no schema change.

> **Note:** The per-product `weight_grams` **data half** (DB column, product models, admin form field, CSV import column) is delivered by the **`product-mgmt-completeness`** change and is no longer in scope here — it is already in the codebase. `shipping-pricing` only **consumes** the field for cost calculation, reading each line item's weight server-side from the DB.

- Add per-product weight for shipping calculation: ~~new `weight_grams` column on `products` (default 300g), `ProductResponse.weight_grams`, optional CSV import column, admin product form field~~ — **delivered by `product-mgmt-completeness`; consumed here only**
- Add packaging weight buffer as a config constant (`PACKAGING_WEIGHT_GRAMS = 200`)
- New backend endpoint: `POST /v1/delivery/calculate` — accepts courier(s), method, destination (city for approximate, office_id / full address for exact), cart weight; returns price per courier
- Real-time courier API integration: Speedy `/calculate`, Econt Shipments service
- Two-phase pricing UX in checkout: approximate prices after city selection (both couriers, for comparison) → exact price after specific office/address
- Free shipping threshold: `items_total_cents >= 5000` (€50) → `shipping_cents = 0` (server-enforced), short-circuits pricing before any fallback
- Tiered fallback (Phase A: flat `FALLBACK_SHIPPING_CENTS = 500` when a courier API times out or errors; the shaped snapshot tier is Phase B)
- **Price provenance**: each quote and each order records `price_source` (`live`/`table`/`flat`), `is_fallback`, `quoted_at` — auditable, and the basis for the phased evidence loop
- `shipping_cents` + provenance columns on `orders`; `total_cents = items_total_cents + shipping_cents`
- Server-side validation of `shipping_cents` from checkout payload (bounded range check, per parent design Decision 16)
- New frontend components: `CourierComparison` (prices side-by-side, disclaimer only on non-live prices), `ShippingPriceSummary` (final price + free-shipping progress)
- Admin order view: shipping breakdown (items subtotal + shipping) + fallback indicator
- New env config: `SPEEDY_API_USERNAME`, `SPEEDY_API_PASSWORD`, `SPEEDY_SENDER_OFFICE_ID`, `ECONT_API_USERNAME`, `ECONT_API_PASSWORD`, `ECONT_SENDER_OFFICE_ID`

## Depends On

- `shipping-courier-integration` — must land first. This change assumes the structured `delivery` object, office/door models, `/v1/delivery/offices` and `/v1/delivery/cities` endpoints, and admin delivery-details view are all in place.

## Capabilities

### New Capabilities
- `shipping-pricing`: Real-time shipping cost calculation via courier APIs, free-shipping threshold, fallback pricing, per-product weight management, two-phase pricing UX

### Modified Capabilities
- `checkout-flow`: `POST /v1/orders` includes `shipping_cents` in the total; server validates and enforces free-shipping threshold
- `checkout-ui`: Delivery section gains a courier-comparison step with prices, and a final price summary before submit
- `admin-products`: Product form gains `weight_grams` field; CSV import accepts optional `weight_grams` column
- `admin-orders`: Order detail view shows shipping breakdown

## Impact

- **Backend**: New `app/services/shipping_service.py` (courier API clients, calculate orchestration, tiered fallback, provenance tagging), new `/v1/delivery/calculate` route, `orders.shipping_cents` + provenance columns (`shipping_price_source`, `shipping_is_fallback`, `shipping_quoted_at`), order_service checkout accepts/validates `shipping_cents` and persists provenance. Consumes existing `products.weight_grams`.
- **Frontend**: `CourierComparison` and `ShippingPriceSummary` components, checkout state machine extended for two-phase pricing, mock-api gains `/delivery/calculate` mock, admin order view (breakdown + fallback indicator)
- **External dependencies**: Live Speedy and Econt API accounts with production credentials
- **Config**: 6 new env vars (2 courier accounts × username/password/sender_office_id)
- **Deferred to later phases**: Shaped snapshot-table fallback + fetch script (Phase B), quoted-vs-invoice reconciliation view (Phase C), signed price tokens

## Open Questions (Draft)

- Econt calculation endpoint exact request shape (verify once account is created)
- Speedy `serviceId` selection — which service tier (standard vs. express) to offer
- Whether the "approximate" phase can be skipped for small towns where only one courier operates
- Timeout budget for the calculate endpoint (5s? 3s?)
