> This change is **Phase A** of the shipping-pricing rollout (see `design.md` →
> Phasing): **live courier pricing + flat fallback + price provenance**. The shaped
> snapshot-table fallback (Phase B) and reconciliation (Phase C) are follow-on
> changes and are **out of scope here** — but the `price_source` provenance shipped
> in Phase A includes the reserved `"table"` value so nothing changes when B lands.

## 1. Backend — Courier Clients & Shipping Service

- [x] 1.1 Add config: `SPEEDY_API_USERNAME`, `SPEEDY_API_PASSWORD`, `SPEEDY_SENDER_OFFICE_ID`, `ECONT_API_USERNAME`, `ECONT_API_PASSWORD`, `ECONT_SENDER_OFFICE_ID` in `app/config.py`
- [x] 1.2 Add shipping constants: `FREE_SHIPPING_THRESHOLD_CENTS = 5000`, `FALLBACK_SHIPPING_CENTS = 500`, `PACKAGING_WEIGHT_GRAMS = 200`, `SHIPPING_CENTS_MAX = 3000`, `COURIER_TIMEOUT_SECONDS = 3` in `app/constants.py`
- [x] 1.3 Create `app/services/speedy_client.py` — `async calculate(sender_office_id, recipient, weight_grams) -> ShippingQuote`, HTTP call to `POST https://api.speedy.bg/v1/calculate` with credentials in JSON body, per-request timeout; on success tag `price_source="live"`, on error return flat fallback tagged `price_source="flat", is_fallback=True`
- [x] 1.4 Create `app/services/econt_client.py` — `async calculate(...)` via Econt Shipments service, HTTP Basic auth, same interface + provenance tagging as Speedy client
- [x] 1.5 Create `app/services/shipping_service.py` — orchestrator: evaluate free-shipping short-circuit FIRST (→ 0¢ before any courier call); reads each cart line's `weight_grams` from the DB and sums (× quantity) plus `PACKAGING_WEIGHT_GRAMS`; fans out to both couriers in parallel (approximate phase) or calls one (exact phase); returns `list[ShippingQuote]` each carrying `price_source`/`is_fallback`
- [x] 1.6 Create `app/models/shipping.py` — `ShippingQuote` (with `price_source: Literal["live","table","flat"]`, `is_fallback: bool`), `CalculateShippingRequest` Pydantic models

## 2. Backend — Endpoint & Order Integration

- [x] 2.1 Create `app/routes/delivery.py` addition (or new file) — `POST /v1/delivery/calculate` route, validates request, calls `shipping_service`, returns quotes
- [x] 2.2 Update `orders` table — add `shipping_cents INTEGER NOT NULL DEFAULT 0`, plus provenance columns `shipping_price_source TEXT NOT NULL DEFAULT 'live'`, `shipping_is_fallback INTEGER NOT NULL DEFAULT 0`, `shipping_quoted_at TEXT`
- [x] 2.3 Update `CreateOrderRequest` — add `shipping_cents: int`, `courier`, and provenance echo (`price_source`, `is_fallback`, `quoted_at`) from the selected quote
- [x] 2.4 Update `OrderResponse` — add `items_total_cents`, `shipping_cents`, `shipping_price_source`, `shipping_is_fallback`; `total_cents = items_total_cents + shipping_cents`
- [x] 2.5 Update `order_service.checkout()` — server-enforce free-shipping override (also forces `price_source="live", is_fallback=false` on a free order), range-validate `shipping_cents ∈ [0, SHIPPING_CENTS_MAX]`, raise `InvalidShippingPriceError` on out-of-range, persist provenance columns
- [x] 2.6 Add `InvalidShippingPriceError` to `app/exceptions.py` → maps to HTTP 422

## 3. Backend — Tests

- [x] 3.1 Test each courier client: happy path (`price_source="live"`), timeout → flat fallback (`price_source="flat", is_fallback=True`), 5xx → fallback, auth failure → fallback
- [x] 3.2 Test shipping_service orchestration: free-shipping short-circuits before any courier call, cart-weight summed from DB `weight_grams` + packaging buffer, both couriers, one courier up / one down (independent provenance per quote)
- [x] 3.3 Test `/v1/delivery/calculate` endpoint: approximate mode, exact mode, invalid method/courier, validation errors
- [x] 3.4 Test checkout with valid `shipping_cents`: persisted, included in `total_cents`, provenance columns persisted
- [x] 3.5 Test checkout free-shipping enforcement: frontend sends non-zero `shipping_cents` but total ≥ €50 → server forces 0 and normalizes provenance to live/non-fallback
- [x] 3.6 Test checkout range validation: `shipping_cents = -1` → 422, `shipping_cents = 100000` → 422
- [x] 3.7 Test order retrieval: legacy orders (no `shipping_cents` / provenance column values) return `shipping_cents = 0`, `price_source = "live"`, `is_fallback = false`

## 4. Frontend — Components & State

- [x] 4.1 Create `CourierComparison` component — side-by-side cards showing both quotes with prices, delivery estimates, radio selection; show the fallback disclaimer **only when `price_source != "live"`** (live prices carry no disclaimer)
- [x] 4.2 Create `ShippingPriceSummary` component — final price row, free-shipping progress ("Добави още за X€"), free-shipping achieved badge
- [x] 4.3 Extend checkout state: `deliveryPhase = "method" | "approximate" | "exact" | "ready"`, `quotes: ShippingQuote[]`, `selectedQuote: ShippingQuote | null`
- [x] 4.4 Wire calculate calls: on city selection → approximate (both couriers), on office/address confirmation → exact (chosen courier)
- [x] 4.5 Update `lib/types.ts` — `ShippingQuote` (incl. `price_source`, `is_fallback`), `CalculateShippingRequest`, extend `CreateOrderRequest` with `shipping_cents` + selected-quote provenance
- [x] 4.6 Update `lib/api-client.ts` — `calculateShipping(payload)`
- [x] 4.7 Update `lib/mock-api.ts` — mock `/delivery/calculate` returning realistic quotes with `price_source="live"`; simulate fallback (`price_source="flat"`) via a query flag

## 5. Frontend — Checkout & Admin

- [x] 5.1 Update checkout page — insert `CourierComparison` between city/office selection, insert `ShippingPriceSummary` above submit
- [x] 5.2 Update checkout submit — include `shipping_cents` (from `selectedQuote.cents`) and the selected quote's provenance in the payload
- [x] 5.3 Update order confirmation page — show shipping breakdown (items subtotal + shipping)
- [x] 5.4 Update admin order detail — shipping breakdown row + a provenance indicator when `shipping_is_fallback` is true (so staff can spot guessed prices)

## 6. i18n

- [x] 6.1 Add `checkout.delivery.priceEstimate`, `priceExact`, `freeShipping`, `amountToFreeShipping`, courier-comparison labels, fallback-price disclaimer to `messages/en.json` and `messages/bg.json`
