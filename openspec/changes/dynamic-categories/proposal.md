## Why

Product categories are half-managed today: the storefront filter pills are already derived dynamically from product data, but the **admin form's category dropdown is a hardcoded list of six fragrance families** (`Floral, Woody, Fresh, Gourmand, Spicy, Citrus`) baked into the frontend. Adding or renaming a category requires a code change and redeploy. This change turns categories into managed data with an admin CRUD, so the shop owner can maintain them without a developer.

## What Changes

- **New `categories` table** as the source of truth: `slug` (stable key), bilingual `name_en` / `name_bg`, `sort_order`, `is_active`, timestamps.
- **Products reference categories by slug.** The existing `products.category` column keeps storing a category identifier, now standardized to a category **slug**. A one-time migration slugifies existing distinct values and seeds the table (including the current six defaults).
- **Public endpoint `GET /v1/categories`** returns active categories (localized) for the storefront and the admin form to consume — replacing the hardcoded frontend constant.
- **Admin category CRUD** (`/v1/admin/categories`): create, list, update (rename/reorder/activate), delete. Delete is blocked (409) while products still reference the category; a category can instead be deactivated to hide it from pickers without touching products.
- **Product create/update validates `category` against existing category slugs.**
- **Storefront localization:** category names on filter pills and the product detail badge resolve slug → localized name (en/bg) with fallback, instead of showing a raw string.
- **Admin UI:** a categories management page, and the product form dropdown is populated from the API.

## Capabilities

### New Capabilities
- `category-management`: the categories table, public list endpoint, admin CRUD, slug model, and delete/deactivate rules.

### Modified Capabilities
- `product-admin-api`: create/update validate `category` against managed category slugs.
- `admin-products`: product form category dropdown is sourced from the categories API (not a hardcoded constant).
- `product-listing`: filter pills display localized category names resolved from slugs.
- `product-detail`: category badge displays the localized category name.

## Impact

- **Backend:** `app/database.py` (new `categories` table + seed/migration of existing values + `products_new` copy; note FTS still indexes `products.category`), `app/models/` (new `categories.py` schemas), new `app/services/category_service.py`, new `app/routes/categories.py` (+ admin routes), product create/update validation in `product_service`, router registration in `main.py`.
- **Frontend:** new admin categories page + management component + `AdminSidebar` nav entry, `ProductForm.tsx` dropdown fetches categories, `CategoryFilter`/`ProductListingClient` resolve localized names, product detail badge, `lib/types.ts`, `lib/api*.ts`, `lib/mock-api.ts`, i18n `en.json`/`bg.json`.
- **Data migration:** existing `products.category` values are slugified; a rollback plan preserves the original values.
- **Not affected:** cart, checkout, pricing, orders.
