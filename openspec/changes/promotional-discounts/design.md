## Context

Prices are read **live** from `products.price_cents` at three tiers, and only snapshotted at order creation:

```
products.price_cents
   ├──▶ product_service.get_product / list_products  → public API response
   ├──▶ cart_service (line ~206)                      → cart line + total
   └──▶ order_service (line ~240 → snapshot ~276)     → order_items.price_cents (IMMUTABLE)
```

Because nothing is snapshotted before checkout, a discount can be introduced as a computed **effective price** at each read site without touching the storage of past orders. `order_items` enforces `CHECK (price_cents > 0)`, so the effective price must never floor to 0.

## Goals / Non-Goals

**Goals:**
- Per-product percentage discount, optionally windowed by start/end datetime.
- One shared effective-price function used by API, cart, and checkout — no divergent math.
- Customer is charged the discounted price; the discounted price is what lands in `order_items`.
- Storefront shows original (struck-through), sale price, and `−X%` badge.

**Non-Goals:**
- Coupon codes, cart-level or order-level discounts, tiered/quantity discounts, free shipping (separate concerns).
- Fixed-amount discounts (percentage only, per decision).
- Stacking multiple discounts.

## Decisions

### 1. Discount model: percent + optional window
Product columns: `discount_percent INTEGER` (nullable, CHECK 1–99), `discount_starts_at TEXT` (nullable, ISO-8601 UTC), `discount_ends_at TEXT` (nullable). A discount is **active** iff:
```
discount_percent IS NOT NULL
  AND (discount_starts_at IS NULL OR now >= discount_starts_at)
  AND (discount_ends_at   IS NULL OR now <= discount_ends_at)
```
No dates → manual on/off (active whenever percent is set). This gives both modes from one model.

**Alternatives:** separate boolean `discount_active` column (rejected — denormalized state that drifts from the window); fixed-amount discount (rejected per product decision).

### 2. Single effective-price helper (source of truth)
New module `app/services/pricing.py`:
```
def discount_is_active(percent, starts_at, ends_at, now) -> bool
def effective_price_cents(price_cents, percent, active) -> int
```
`effective_price_cents` = `round_half_up(price_cents * (100 - percent) / 100)` when active, clamped to **≥ 1**; otherwise returns `price_cents` unchanged. Called by product_service (API), cart_service (totals), order_service (snapshot). No consumer computes discount math inline.

**Rationale:** money math in exactly one place is the core defense against the display-vs-charge divergence bug.

### 3. Rounding: round-half-up, integer cents, floor ≥ 1
`price_cents × (100−percent)/100` then round half-up to the nearest cent. Clamp to a minimum of 1 cent so `order_items CHECK (price_cents > 0)` can never be violated (e.g. 99% off a 1-cent item). Computed with integer arithmetic to avoid float drift: `(price_cents * (100 - percent) + 50) // 100`, then `max(1, …)`.

### 4. Response semantics: `price_cents` stays the original
Public and admin responses keep `price_cents` = base list price, and **add** `effective_price_cents`, `discount_percent`, `discount_active`. Request models (`Create`/`Update`) treat `price_cents` as the base price and accept the discount fields separately. Keeping `price_cents` meaning stable (always the list price) avoids a request/response semantic mismatch; the frontend shows `price_cents` struck-through and `effective_price_cents` as the live price when `discount_active`.

**Alternative:** make response `price_cents` = discounted and add `original_price_cents`. Rejected — overloads the field's meaning between request and response and risks a consumer charging the wrong number.

### 5. Live pricing at checkout (no cart price snapshot)
The customer pays whatever discount is active **at checkout time**, matching the existing behavior where price is read live (not frozen at add-to-cart). If a windowed discount expires between viewing the cart and checking out, the checkout total reflects the post-expiry price. This is the same class of behavior as an admin editing a price mid-session — documented, not a bug.

### 6. Time source
Server-side `datetime.now(UTC)`, compared against stored ISO-8601 UTC strings (lexicographic comparison is valid for zero-padded ISO-8601 UTC). Admin inputs are normalized to UTC on write.

### 7. Admin form validation mirrors server
Percent 1–99; if both dates set, `starts_at < ends_at`; a percent is required if any date is set. Same rules enforced in the Pydantic model (server is authoritative).

## Risks / Trade-offs

- **Display shows discount but checkout charges full price** (the headline risk) → single effective-price helper used by *both* the response and the checkout snapshot; test asserts `order_items.price_cents == effective_price_cents` for a discounted product.
- **Rounding to €0 violates DB CHECK** → floor clamp to ≥ 1 cent, with a dedicated test at 99% off a 1-cent price.
- **Float rounding drift** → integer-only arithmetic for the effective price.
- **Window boundary off-by-one** (inclusive vs exclusive) → define `>=` start and `<=` end (inclusive both ends); scenarios cover exactly-at-boundary.
- **Cart total ≠ checkout total when a window expires mid-session** → accepted and documented (Decision 5); the authoritative charge is computed at checkout.
- **Two changes (A and B) modify the admin product form** → B adds discount fields as a *separate ADDED requirement* rather than re-modifying A's form requirement, avoiding a spec conflict at archive time.

## Migration Plan

1. Add three nullable columns to `products` + `products_new` + migration copy list. Existing rows: all NULL → no active discounts, effective price == price_cents. Fully backward-compatible.
2. Ship the pricing helper + all three consumer sites together so display and charge stay consistent.
3. Rollback: columns are additive and nullable; reverting code leaves them unused and harmless. Already-placed orders are unaffected (they store snapshots).

## Open Questions

- Should CSV import accept the discount columns too? Proposed: yes, optional, but low priority — can be deferred to a follow-up task without blocking the feature. (Tasks mark it optional.)
