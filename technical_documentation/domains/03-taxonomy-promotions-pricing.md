# Taxonomy, Promotions, And Pricing

These systems decide how products are grouped and what price customers see/pay.

## Mental Model

Taxonomy controls discovery.

Promotions write discount fields to products.

Pricing computes the effective price from product fields.

Checkout snapshots effective price into the order.

## Main Backend Files

- `app/services/taxonomy_service.py`
- `app/routes/taxonomy.py`
- `app/models/taxonomy.py`
- `app/services/promotion_service.py`
- `app/routes/promotions.py`
- `app/services/banner_service.py`
- `app/services/pricing.py`
- `app/services/product_service.py`
- `app/services/order_service.py`

## Main Frontend Files

- `frontend/components/admin/TaxonomyManager.tsx`
- `frontend/app/[locale]/admin/taxonomy/page.tsx`
- `frontend/app/[locale]/admin/promotions/page.tsx`
- `frontend/components/products/ProductListingClient.tsx`
- `frontend/components/products/PriceDisplay.tsx`
- `frontend/components/layout/AnnouncementBar.tsx`

## Taxonomy Shape

Three managed groups:

- product types
- categories
- labels

Products have:

- one product type
- optional category
- multiple labels

Taxonomy terms have:

- slug
- English name
- Bulgarian name
- sort order
- active flag

## Taxonomy Flow

```text
Admin creates/edits taxonomy term
  -> taxonomy service validates slug/name
  -> products can reference active terms
  -> public taxonomy endpoint returns active terms
  -> product listing builds filters from API data
```

Rules:

- Frontend filters must not hardcode taxonomy values.
- Term slugs are stable identifiers.
- Display names are localized.
- Used terms should be deactivated instead of deleted when deletion would break references.

## Promotion Campaign Flow

```text
Admin creates campaign
  -> target is explicit product IDs or filter descriptor
  -> applying campaign resolves product targets
  -> product discount fields are written
  -> campaign_products records what was applied
  -> storefront/cart/checkout see product-level discounts
```

Important detail:

- Runtime pricing reads product fields, not campaign rows.
- Campaign rows are admin management/audit data.

## Pricing Rules

- Base price is `price_cents`.
- Active discount creates `effective_price_cents`.
- Discount percent must be 1 to 99 when present.
- Discount windows use server time.
- Public API exposes active discount display fields, not internal window details.
- Checkout uses effective price at checkout time.

## Site Banner

Campaign management also includes a public announcement banner.

Rules:

- Banner content is bilingual.
- `version` changes so old dismissals do not hide new banner content.
- Public API returns only currently visible banner.

## Safe Change Checklist

- Product listing filters still use API taxonomy data.
- Product create/update rejects invalid taxonomy slugs.
- Cart totals use effective prices.
- Checkout item snapshots use effective prices.
- Campaign remove only clears discounts it safely owns.
- Banner dismissal behavior still works after content changes.

