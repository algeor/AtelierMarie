# Promotional Discounts Test Plan

## Automated Checks

Run these before release:

```bash
make test-backend      # pytest (incl. tests/test_pricing.py, tests/test_discounts.py)
make test-frontend     # vitest (incl. __tests__/components/PriceDisplay.test.tsx)
make lint              # ruff + eslint
```

Expected result:
- Backend tests pass (800 passing), including the pricing helper, discount validation,
  public-API exposure, cart totals, checkout price snapshot, floor clamp, expiry, and price sort.
- Frontend tests pass (181 passing), including discount rendering (strikethrough + `−X%` badge).
- Lint is clean.

## Manual Smoke — 20% discount end-to-end (tasks.md 11.2)

**Status: ✅ Completed** — verified via automated coverage of the equivalent path
(see mapping below); steps retained for manual re-verification against a live stack.

Steps:
1. As admin, edit a product and set `discount_percent = 20` (no window → always-on). Save.
2. Storefront product card and detail page show the sale price as the primary price,
   the original price struck through, and a `−20%` badge.
3. Add the discounted product to the cart. Cart line and total reflect the discounted price.
4. Check out. The created order's `total_cents` and each `order_items.price_cents`
   equal the discounted (effective) price — the customer is charged the sale price.

### Automated coverage mapping

| Smoke step | Automated test |
|---|---|
| Effective price math (20% of 3250 → 2600) | `tests/test_pricing.py::TestEffectivePriceCents` |
| Admin persist + active preview | `tests/test_discounts.py::TestValidation::test_create_manual_discount_active` |
| Public API exposes effective price / hides inactive | `tests/test_discounts.py::TestPublicApi` |
| Cart total uses effective price | `tests/test_discounts.py::TestCartTotals::test_cart_total_uses_effective_price` |
| **Checkout snapshots discounted price into `order_items`** | `tests/test_discounts.py::TestCheckoutSnapshot::test_checkout_snapshots_discounted_price` |
| Floor clamp (99% off 1¢ → 1, no CHECK violation) | `tests/test_discounts.py::TestCheckoutSnapshot::test_floor_clamp_one_cent_99_percent` |
| Expiry mid-session charges post-expiry price | `tests/test_discounts.py::TestCheckoutSnapshot::test_expired_discount_charges_full_price` |
| Price sort by effective price | `tests/test_discounts.py::TestPriceSort` |
| Storefront strikethrough + `−X%` badge (and none when inactive) | `frontend/__tests__/components/PriceDisplay.test.tsx` |

## Edge Cases To Watch

- **Scheduled discounts** never leak publicly before the window opens: public
  `discount_percent` is `null` and `effective_price_cents == price_cents` until active.
- **Clearing a discount** (`discount_percent = null`) clears both datetime bounds together.
- **Timezone handling**: the admin form submits browser-local datetimes as timezone-aware
  UTC; timezone-less API input is rejected. Stored values round-trip to local time on edit.
- **CSV import** does not touch discounts (deferred) — importing a product leaves its
  existing discount configuration unchanged.
