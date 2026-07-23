## Why

Product categories are half-managed today: the storefront filter pills are already derived dynamically from product data, but the **admin form's category dropdown is a hardcoded list of six fragrance families** (`Floral, Woody, Fresh, Gourmand, Spicy, Citrus`) baked into the frontend. Adding or renaming a category requires a code change and redeploy. This change turns categories into managed data with an admin CRUD, so the shop owner can maintain them without a developer.

## What Changes

- **New `categories` table** as the source of truth: `slug` (stable key), bilingual `name_en` / `name_bg`, `sort_order`, `is_active`, timestamps.
- **Products reference categories by slug.** The existing `products.category` column keeps storing a category identifier, now standardized to a category **slug**. A one-time mapping-based migration converts existing distinct values to deterministic unique slugs and seeds the table (including the current six defaults).
- **Public endpoint `GET /v1/categories`** returns active categories (localized) for storefront filter/navigation uses. Admin forms use the admin category list so they can safely display an existing inactive category on edit.
- **Admin category CRUD** (`/v1/admin/categories`): create, list, update (rename/reorder/activate), delete. Delete is blocked (409) while products still reference the category; a category can instead be deactivated to hide it from pickers without touching products.
- **Product create/update validates category assignment against active category slugs.** Updating unrelated product fields or preserving the product's current inactive category remains allowed, so retired categories do not block product maintenance.
- **Public product responses include localized category display metadata.** `category` remains the slug used for filtering; a new nullable `category_name` field resolves slug → localized name (en/bg) with fallback, including inactive categories that are still referenced by products.
- **Storefront localization:** category names on filter pills and the product detail badge use product `category_name` metadata instead of showing a raw slug.
- **Admin UI:** a categories management page, and the product form dropdown is populated from the API.

## Capabilities

### New Capabilities
- `category-management`: the categories table, public list endpoint, admin CRUD, slug model, and delete/deactivate rules.

### Modified Capabilities
- `product-public-api`: list/detail product responses expose localized `category_name` while keeping `category` as the filtering slug.
- `product-admin-api`: create/update validate `category` against managed category slugs.
- `admin-products`: product form category dropdown is sourced from the categories API (not a hardcoded constant).
- `product-listing`: filter pills display localized category names resolved from slugs.
- `product-detail`: category badge displays the localized category name.

## Impact

- **Backend:** `app/database.py` (new `categories` table + mapping-based seed/migration of existing values; note FTS still indexes `products.category`), `app/models/` (new `categories.py` schemas + `category_name` on public product responses), new `app/services/category_service.py`, new `app/routes/categories.py` (+ admin routes), product create/update validation in `product_service`, category label joins in product list/detail, router registration in `main.py`.
- **Frontend:** new admin categories page + management component + `AdminSidebar` nav entry, `ProductForm.tsx` dropdown fetches categories, `CategoryFilter`/`ProductListingClient` resolve localized names, product detail badge, `lib/types.ts`, `lib/api*.ts`, `lib/mock-api.ts`, i18n `en.json`/`bg.json`.
- **Data migration:** existing `products.category` values are mapped deterministically to unique slugs and preserved in a migration mapping table for audit/rollback.
- **Not affected:** cart, checkout, pricing, orders.
