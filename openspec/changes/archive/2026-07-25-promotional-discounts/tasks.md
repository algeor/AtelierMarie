## 1. Database schema (`app/database.py`)

- [x] 1.1 Add `discount_percent INTEGER CHECK (discount_percent IS NULL OR discount_percent BETWEEN 1 AND 99)`, `discount_starts_at TEXT`, `discount_ends_at TEXT` (all nullable) to `CREATE TABLE products`
- [x] 1.2 Add the same three columns to the `products_new` migration table
- [x] 1.3 Add the three columns to the migration column-copy list (legacy rows copy as NULL)
- [x] 1.4 Verify fresh init and existing-DB startup both produce the columns, all NULL by default

## 2. Pricing helper (`app/services/pricing.py`) — single source of truth

- [x] 2.1 `normalize_discount_datetime(value) -> str | None` accepts timezone-aware ISO-8601 or canonical `YYYY-MM-DD HH:MM:SS` UTC and rejects timezone-less non-canonical input
- [x] 2.2 `discount_is_active(percent, starts_at, ends_at, now) -> bool` (inclusive bounds; canonical UTC string compare)
- [x] 2.3 `effective_price_cents(price_cents, percent, active) -> int` = integer round-half-up `(price*(100-percent)+50)//100`, clamped `max(1, …)`
- [x] 2.4 `annotate_product_pricing(product, now, public=...)` adds `discount_active`, `effective_price_cents`, and the correct public/admin discount fields
- [x] 2.5 Unit tests: 20% of 3250 → 2600; 15% of 999 → 849; 99% of 1 → 1 (floor clamp); inactive → price unchanged; timestamp normalization and boundary comparisons

## 3. Models (`app/models/products.py`)

- [x] 3.1 Add `discount_percent` (1–99), `discount_starts_at`, `discount_ends_at` to `CreateProductRequest` + `UpdateProductRequest`; create validators cover self-contained payloads, while update merge validation lives in the service
- [x] 3.2 Add public `discount_percent` (active display percent or null), `discount_active`, `effective_price_cents` to `ProductResponse`
- [x] 3.3 Add raw discount fields (`discount_percent`, `discount_starts_at`, `discount_ends_at`) + `discount_active` + `effective_price_cents` to `ProductAdminResponse`

## 4. Product service (`app/services/product_service.py`)

- [x] 4.1 Persist normalized discount columns on create/update
- [x] 4.2 On update, merge submitted discount fields with existing row before validation; `discount_percent = null` clears both datetime bounds
- [x] 4.3 In public `get_product`/`list_products`, capture `now` once per request and compute public display pricing via the helper (`discount_percent` null unless active)
- [x] 4.4 In admin reads, include raw discount fields + computed preview values
- [x] 4.5 Make `sort=price_asc|price_desc` order by `effective_price_cents` before pagination; search with explicit price sort uses the same effective-price ordering

## 5. Cart (`app/services/cart_service.py`)

- [x] 5.1 Capture `now` once per cart read and use effective price for line totals and `total_cents` (replace raw `price_cents` at ~line 206)
- [x] 5.2 Embed public discount fields + `effective_price_cents` in each cart item's product detail (`discount_percent` null unless active)

## 6. Checkout (`app/services/order_service.py`) — CRITICAL PATH

- [x] 6.1 Capture `now` once inside the checkout transaction, compute effective price per cart row, and use it for `items_total_cents` (~line 240)
- [x] 6.2 Snapshot the effective price into `order_items.price_cents` (~line 276)
- [x] 6.3 Confirm floor clamp guarantees the `CHECK (price_cents > 0)` constraint holds

## 7. Admin CSV import (`app/routes/admin.py`) — deferred

- [x] 7.1 Do not silently clear or mutate discounts during CSV import; leave discount parsing out unless explicit column semantics and tests are added

## 8. Frontend — types, mock, form

- [x] 8.1 Add discount fields + `effective_price_cents` + `discount_active` to product interfaces in `lib/types.ts`
- [x] 8.2 Update `lib/mock-api.ts` fixtures + create/update handlers + compute effective price for mock responses
- [x] 8.3 `ProductForm.tsx`: discount percent input + start/end datetime pickers + client validation + sale-price preview
- [x] 8.4 i18n strings in `en.json` + `bg.json` (discount, sale, ends, −X% badge, validation messages)

## 9. Frontend — storefront display

- [x] 9.1 `ProductCard`: show effective price primary, original struck-through, `−X%` badge when `discount_active`
- [x] 9.2 Product detail page: same discount display
- [x] 9.3 Cart display: show discounted line prices

## 10. Tests

- [x] 10.1 Model/service validation: percent range, inverted window, percent-required-with-date, timezone-less datetime rejection, PATCH merge semantics, percent-null clears dates
- [x] 10.2 Active-window boundaries: before/at-start/within/at-end/after
- [x] 10.3 Public API: active discounted product exposes correct `effective_price_cents`/`discount_active`; inactive scheduled discount returns `discount_percent = null` and `effective_price_cents = price_cents`
- [x] 10.4 Cart totals reflect effective price
- [x] 10.5 **Checkout snapshot** asserts `order_items.price_cents == effective_price_cents` for a discounted product; total is discounted
- [x] 10.6 Floor clamp: 99% off a 1-cent product → snapshot = 1, no CHECK violation
- [x] 10.7 Discount-expiry-mid-session charges post-expiry price
- [x] 10.8 Price sorting uses effective price for `price_asc`/`price_desc`
- [x] 10.9 Frontend: card/detail/cart render strikethrough + badge when discount active and regular price when inactive

## 11. Verify

- [x] 11.1 `make test-backend`, `make test-frontend`, `make lint`
- [x] 11.2 Manual smoke: set a 20% discount on a product → see badge in storefront → add to cart → checkout → confirm order total and order-item price are discounted (documented in `test-plans/promotional-discounts.md`; verified via automated coverage)
