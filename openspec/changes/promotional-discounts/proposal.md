## Why

The shop needs to run promotions — a product shown at a reduced price that the customer is actually charged at checkout. Today prices are fixed with no discount concept anywhere. A discount that only *displays* a lower price without charging it would be misleading and a data-integrity bug, so this change threads the discount through the entire price path: storefront display → cart totals → the immutable order snapshot.

## What Changes

- **Add a per-product percentage discount** with an optional scheduled window:
  - New product fields: `discount_percent` (1–99, nullable), `discount_starts_at`, `discount_ends_at` (nullable UTC timestamp text stored as `YYYY-MM-DD HH:MM:SS`, matching the existing SQLite schema convention).
  - **Both modes from one model:** dates present → auto-activates/expires; no dates → manually on while `discount_percent` is set.
- **Introduce a single "effective price" source of truth.** A shared helper computes the discounted, rounded, floor-clamped price and whether a discount is currently active. Every price read uses it:
  - Public product API responses gain `discount_percent`, `discount_active`, and `effective_price_cents` (`price_cents` stays the original list price for the struck-through display; public `discount_percent` is only populated while the discount is active).
  - **Cart** totals use the effective price.
  - **Checkout** snapshots the *effective* price into `order_items` — the customer is charged the discounted amount. **This is the critical-path guarantee.**
- **Rounding & integrity rules:** effective price = round-half-up of `price_cents × (100 − percent) / 100`, **clamped to ≥ 1 cent** so it never violates `order_items CHECK (price_cents > 0)`.
- **Storefront display:** product cards and detail page show the original price struck-through, the sale price, and a `−X%` badge when a discount is active.
- **Admin:** create/edit form and admin API accept the discount fields, normalize datetime input to the stored UTC format, and clear stale windows when a discount is removed.

## Capabilities

### New Capabilities
- `product-discounts`: the discount data model, active-window rules, and the effective-price computation (rounding + floor clamp) that all price consumers share.

### Modified Capabilities
- `product-public-api`: list/detail responses expose `discount_percent`, `discount_active`, `effective_price_cents`.
- `product-admin-api`: create/update accept discount fields; admin response includes them.
- `admin-products`: product form gains discount inputs (percent + optional start/end).
- `cart-management`: cart line/total pricing uses the effective price.
- `checkout-flow`: order-item price snapshot uses the effective (discounted) price.
- `product-listing`: product card shows sale price, original struck-through, and `−X%` badge.
- `product-detail`: detail page shows sale price, original struck-through, and discount badge.

## Impact

- **Backend:** `app/database.py` (3 columns + `products_new` + migration copy), `app/models/products.py` (request/response), new pricing helper (e.g. `app/services/pricing.py`), `app/services/product_service.py` (public/admin reads + persistence), `app/services/cart_service.py` (totals), `app/services/order_service.py` (snapshot). CSV import is deferred and must not silently mutate discounts.
- **Frontend:** `ProductForm.tsx` (discount inputs), `ProductCard`, product detail page, cart display, `lib/types.ts`, `lib/mock-api.ts`, i18n `en.json`/`bg.json` (sale/discount strings).
- **Critical path:** checkout pricing changes — requires careful tests for snapshot correctness, rounding, floor clamp, window boundaries, update/clear semantics, and price sorting by the displayed effective price.
- **Time-dependence:** discount active state depends on server time; the cart-vs-checkout window edge is a documented, accepted behavior (live pricing, no cart price snapshot).
