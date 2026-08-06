# Product Catalog

Products are the center of the storefront and admin workflow.

## What It Does

The product catalog supports:

- public listing and detail pages
- admin create/update/deactivate
- bilingual content
- search
- managed taxonomy
- discounts
- stock
- media attachment
- CSV import

## Main Backend Files

- `app/models/products.py`: product models.
- `app/routes/products.py`: public listing/detail.
- `app/routes/admin.py`: admin product CRUD/import/media endpoints.
- `app/services/product_service.py`: product business logic.
- `app/services/taxonomy_service.py`: taxonomy validation/display.
- `app/services/pricing.py`: discount/effective price helpers.
- `app/services/product_image_service.py`: image attachment.
- `app/services/product_video_service.py`: video attachment.

## Main Frontend Files

- `frontend/app/[locale]/products/page.tsx`
- `frontend/app/[locale]/products/[id]/page.tsx`
- `frontend/components/products/*`
- `frontend/components/admin/ProductForm.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/lib/mock-api.ts`

## How Listing Works

```text
GET /v1/products
  -> route parses locale, page, filters, search
  -> product_service lists/searches active products
  -> taxonomy display names resolved in batch
  -> image/video fields attached in batch
  -> response returns localized ProductResponse objects
```

Important details:

- Public listing shows active products.
- Admin listing can include inactive products.
- Pagination is clamped.
- Search uses Postgres full-text search (GIN + `to_tsvector`/`plainto_tsquery`).
- Taxonomy filters use slugs.

## How Detail Works

```text
GET /v1/products/{id}
  -> fetch product by text id
  -> resolve locale fields
  -> annotate effective price
  -> attach images and ready video
  -> return product detail
```

## Product Data Shape

Important product fields:

- `id`: text key, often slug-like.
- `name_en`, `name_bg`: bilingual names.
- `description_en`, `description_bg`: bilingual descriptions.
- `safety_warnings_*`, `care_instructions_*`: product safety/compliance.
- `materials`, `days_to_craft`: offer details.
- `price_cents`: base price.
- `discount_percent`, `discount_starts_at`, `discount_ends_at`: active sale logic.
- `stock`: available quantity.
- `weight_grams`: shipping quote input.
- `is_active`: public visibility and cart eligibility.
- `is_featured`: homepage/promo display.
- `product_type_slug`, `category_slug`, labels: managed taxonomy.

## Admin Product Update Flow

```text
ProductForm
  -> frontend/lib/api update/create function
  -> admin route
  -> Pydantic model validation
  -> product_service validates taxonomy + discount fields
  -> SQL update/insert
  -> response returned to admin UI
```

## Invariants

- `price_cents` is positive integer cents.
- `stock` cannot be negative.
- Public products must be active.
- Product IDs are strings, not numeric DB IDs.
- Frontend product type must mirror backend response model.
- Checkout snapshots the effective price. Do not mutate order history from product edits.

## Safe Change Checklist

- Public listing still works in English and Bulgarian.
- Detail page still works for products with no image/video.
- Admin create/update validates taxonomy and discount fields.
- Cart rejects inactive/missing products.
- Checkout still snapshots correct price.
- Mock API was updated when types changed.

