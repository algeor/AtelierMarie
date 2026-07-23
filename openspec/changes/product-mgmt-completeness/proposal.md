## Why

Admin product management is inconsistent across its three surfaces (Pydantic models, the admin form, and CSV import). The edit form can't set `is_active`, CSV import silently drops several fields the form supports, and products have no shipping weight at all — a field the shipping specs already require. This closes those gaps as a small, safe, admin-only change with no impact on the customer-facing store or checkout.

## What Changes

- **Add `weight_grams` to products** (shipping weight, product + container). Extracted from the `shipping-pricing` design (Decision 13) so the data-entry half can ship independently of the blocked courier-API work.
  - New DB column `weight_grams INTEGER NOT NULL DEFAULT 300` on `products` (and the `products_new` migration table).
  - Added to `CreateProductRequest`, `UpdateProductRequest`, and `ProductAdminResponse`.
  - **Deliberately NOT added to the public `ProductResponse`** — this is a shipping input only, not a customer-facing attribute. Shipping cost calculation reads weight server-side from the DB, so nothing downstream breaks. This is a conscious deviation from Decision 13 (which listed `ProductResponse.weight_grams`).
  - Admin product form gains a grams input; CSV import gains an optional `weight_grams` column (defaults to 300 when absent).
- **Add an `is_active` toggle to the edit form.** Today `is_active` is only settable via the Activate/Deactivate button on the products *list*; the model already supports it, so surface it in the form too.
- **Complete CSV import.** Import currently parses only `id, name_en/name, name_bg, description_en/description, description_bg, price_cents, category, stock, image_url`. Extend it to also parse the optional columns `is_featured`, `materials`, `days_to_craft`, `is_active`, and `weight_grams`, so bulk import matches what the form and model already support.
- **Note the extraction in `shipping-pricing`** so the two changes don't collide: the `weight_grams` data half now lives here; `shipping-pricing` only consumes it.

## Capabilities

### New Capabilities
<!-- None — this change modifies existing capabilities only. -->

### Modified Capabilities
- `product-admin-api`: `CreateProductRequest` / `UpdateProductRequest` / `ProductAdminResponse` gain `weight_grams`; CSV import accepts optional `weight_grams`, `is_featured`, `materials`, `days_to_craft`, `is_active` columns.
- `admin-products`: admin product form gains a `weight_grams` (grams) input and an `is_active` toggle.
- `product-service`: product INSERT/UPDATE column lists include `weight_grams`.

## Impact

- **Backend:** `app/database.py` (schema + `products_new` migration + backfill), `app/models/products.py`, `app/services/product_service.py`, `app/routes/admin.py` (CSV import parsing).
- **Frontend:** `frontend/components/admin/ProductForm.tsx` (grams input, is_active toggle), `frontend/lib/types.ts`, `frontend/lib/mock-api.ts`, `frontend/messages/en.json` + `bg.json` (i18n labels).
- **Docs/specs:** annotate `openspec/changes/shipping-pricing` that the `weight_grams` data half moved here.
- **No impact** on cart, checkout, order snapshots, pricing, or the public product API.
- **Tests:** model validation, CSV import (new columns + defaults), admin route create/update round-trip.
