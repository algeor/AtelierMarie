## 1. Product Weight

- [ ] 1.1 Add `weight_grams INTEGER NOT NULL DEFAULT 300` to `products` table in `app/database.py`
- [ ] 1.2 Add `weight_grams: int` to `ProductResponse` and product create/update models
- [ ] 1.3 Add optional `weight_grams` column to CSV import parser (default 300 when missing)
- [ ] 1.4 Add weight input (grams) to admin product form; update `ProductForm` component and validation

## 2. Backend — Courier Clients & Shipping Service

- [ ] 2.1 Add config: `SPEEDY_API_USERNAME`, `SPEEDY_API_PASSWORD`, `SPEEDY_SENDER_OFFICE_ID`, `ECONT_API_USERNAME`, `ECONT_API_PASSWORD`, `ECONT_SENDER_OFFICE_ID` in `app/config.py`
- [ ] 2.2 Add shipping constants: `FREE_SHIPPING_THRESHOLD_CENTS = 5000`, `FALLBACK_SHIPPING_CENTS = 500`, `PACKAGING_WEIGHT_GRAMS = 200`, `SHIPPING_CENTS_MAX = 3000`, `COURIER_TIMEOUT_SECONDS = 3` in `app/constants.py`
- [ ] 2.3 Create `app/services/speedy_client.py` — `async calculate(sender_office_id, recipient, weight_grams) -> ShippingQuote`, HTTP call to `POST https://api.speedy.bg/v1/calculate` with credentials in JSON body, per-request timeout, fallback on error
- [ ] 2.4 Create `app/services/econt_client.py` — `async calculate(...)` via Econt Shipments service, HTTP Basic auth, same interface as Speedy client
- [ ] 2.5 Create `app/services/shipping_service.py` — orchestrator: fans out to both couriers in parallel (approximate phase) or calls one (exact phase), applies free-shipping override, returns `list[ShippingQuote]`
- [ ] 2.6 Create `app/models/shipping.py` — `ShippingQuote`, `CalculateShippingRequest` Pydantic models

## 3. Backend — Endpoint & Order Integration

- [ ] 3.1 Create `app/routes/delivery.py` addition (or new file) — `POST /v1/delivery/calculate` route, validates request, calls `shipping_service`, returns quotes
- [ ] 3.2 Update `orders` table — add `shipping_cents INTEGER NOT NULL DEFAULT 0` column
- [ ] 3.3 Update `CreateOrderRequest` — add `shipping_cents: int`
- [ ] 3.4 Update `OrderResponse` — add `items_total_cents`, `shipping_cents`; `total_cents = items_total_cents + shipping_cents`
- [ ] 3.5 Update `order_service.checkout()` — server-enforce free-shipping override, range-validate `shipping_cents ∈ [0, SHIPPING_CENTS_MAX]`, raise `InvalidShippingPriceError` on out-of-range
- [ ] 3.6 Add `InvalidShippingPriceError` to `app/exceptions.py` → maps to HTTP 422

## 4. Backend — Tests

- [ ] 4.1 Test each courier client: happy path, timeout → fallback, 5xx → fallback, auth failure → fallback
- [ ] 4.2 Test shipping_service orchestration: both couriers, one courier, free-shipping override wins over API response
- [ ] 4.3 Test `/v1/delivery/calculate` endpoint: approximate mode, exact mode, invalid method/courier, validation errors
- [ ] 4.4 Test checkout with valid `shipping_cents`: persisted, included in `total_cents`
- [ ] 4.5 Test checkout free-shipping enforcement: frontend sends non-zero `shipping_cents` but total ≥ €50 → server forces 0
- [ ] 4.6 Test checkout range validation: `shipping_cents = -1` → 422, `shipping_cents = 100000` → 422
- [ ] 4.7 Test order retrieval: legacy orders (no `shipping_cents` column value) return 0

## 5. Frontend — Components & State

- [ ] 5.1 Create `CourierComparison` component — side-by-side cards showing both quotes with prices, delivery estimates, `is_fallback` disclaimer, radio selection
- [ ] 5.2 Create `ShippingPriceSummary` component — final price row, free-shipping progress ("Добави още за X€"), free-shipping achieved badge
- [ ] 5.3 Extend checkout state: `deliveryPhase = "method" | "approximate" | "exact" | "ready"`, `quotes: ShippingQuote[]`, `selectedQuote: ShippingQuote | null`
- [ ] 5.4 Wire calculate calls: on city selection → approximate (both couriers), on office/address confirmation → exact (chosen courier)
- [ ] 5.5 Update `lib/types.ts` — `ShippingQuote`, `CalculateShippingRequest`, extend `CreateOrderRequest` with `shipping_cents`
- [ ] 5.6 Update `lib/api-client.ts` — `calculateShipping(payload)`
- [ ] 5.7 Update `lib/mock-api.ts` — mock `/delivery/calculate` returning realistic quotes; simulate fallback with a query flag

## 6. Frontend — Checkout & Admin

- [ ] 6.1 Update checkout page — insert `CourierComparison` between city/office selection, insert `ShippingPriceSummary` above submit
- [ ] 6.2 Update checkout submit — include `shipping_cents` (from `selectedQuote.cents`) in the payload
- [ ] 6.3 Update order confirmation page — show shipping breakdown (items subtotal + shipping)
- [ ] 6.4 Update admin order detail — shipping breakdown row
- [ ] 6.5 Update admin product form — weight_grams input with grams unit, default 300, min 1

## 7. i18n

- [ ] 7.1 Add `checkout.delivery.priceEstimate`, `priceExact`, `freeShipping`, `amountToFreeShipping`, courier-comparison labels, fallback-price disclaimer to `messages/en.json` and `messages/bg.json`
- [ ] 7.2 Add `admin.products.weightGrams` label + placeholder to both locale files
