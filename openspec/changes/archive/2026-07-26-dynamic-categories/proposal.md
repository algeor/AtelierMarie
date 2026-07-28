## Why

The shop should be mainly organized around candles, but it also needs to support other handcrafted product families such as decorative boxes. Candles and boxes both need subgrouping such as small, medium, and premium, and products also need purpose or seasonal labels such as winter, gift, Christmas, relaxing, and similar values.

A single flat `category` dropdown cannot represent this cleanly. It mixes product type, size or tier, scent family, purpose, and season into one value. It also prevents the storefront from offering the familiar sidebar filtering experience used by larger shops.

This change replaces the flat dynamic category idea with managed product taxonomy: product types, category or tier groups, and multi-select labels. The admin must be able to create and manage all of these dynamically in dedicated admin views. The frontend must not hardcode taxonomy values.

## What Changes

- **Managed product taxonomy** becomes the source of truth: product types (`candles`, `boxes`), category or tier terms (`small`, `medium`, `premium`), and labels (`winter`, `gift`, scent families, occasions, etc.). All taxonomy terms have stable slugs, bilingual display names, sort order, active state, and timestamps.
- **Dedicated admin management views** let admins create, rename, reorder, activate/deactivate, and delete unused product types, categories/tiers, and labels. Product forms and storefront filters consume these APIs only; there are no hardcoded product types, categories, or labels in the frontend.
- **Products get separate taxonomy assignments.** Products reference one product type, optionally one category/tier, and zero or more labels. This avoids forcing candles, boxes, sizes, and purposes into one category string.
- **Existing `products.category` values are migrated safely.** Existing fragrance-family values such as `Floral`, `Woody`, and `Fresh` are preserved as labels. Existing products default to product type `candles`, and the old category values are copied into the product-label relation.
- **Public product APIs support faceted filtering.** `GET /v1/products` accepts filters for product type, category/tier, and labels. Product responses include localized display metadata for product type, category/tier, and labels while keeping slugs for filtering.
- **Public taxonomy endpoint** returns active product types, category/tier terms, and labels for building storefront sidebars, localized by `locale`.
- **Admin product forms** use managed taxonomy APIs instead of hardcoded category constants. Product type and category/tier are dropdowns; labels are multi-select checkboxes or token-style controls.
- **Storefront product listing** uses a left-side faceted filter menu on desktop and a collapsible filter panel on mobile. Filters can combine product type, category/tier, labels, stock, search, and sort.
- **Product detail** displays localized product type/category badges and purpose/season labels instead of raw slugs.

## Capabilities

### New Capabilities
- `product-taxonomy`: product type/category/label tables, public taxonomy endpoint, admin taxonomy CRUD, slug model, migration from legacy category text, and delete/deactivate rules.

### Modified Capabilities
- `product-public-api`: list/detail responses expose localized taxonomy metadata and filtering by product type, category/tier, and labels.
- `product-admin-api`: create/update/import validate taxonomy assignments against managed active terms.
- `admin-products`: product form taxonomy controls are sourced from the API and support multi-label assignment.
- `product-listing`: storefront uses sidebar faceted filters instead of simple category pills.
- `product-detail`: product detail displays localized taxonomy badges and labels.

## Impact

- **Backend:** `app/database.py` (taxonomy tables, product columns/relation table, marker-guarded migration from legacy category text), `app/models/` (new taxonomy schemas plus taxonomy fields on product responses), new `app/services/taxonomy_service.py`, new `app/routes/taxonomy.py` with admin routes, product create/update/import validation in `product_service`, taxonomy joins/batched resolvers in product list/search/detail, router registration in `main.py`.
- **Frontend:** new admin taxonomy management views, `AdminSidebar` nav entry, `ProductForm.tsx` product type/category/labels controls from API, storefront sidebar filter UI, product detail badges/labels, `lib/types.ts`, `lib/api*.ts`, `lib/mock-api.ts`, i18n `en.json`/`bg.json`.
- **Data migration:** existing `products.category` display values are converted into managed labels and product-label assignments. Existing products default to product type `candles`. Category/tier starts nullable until the admin assigns small/medium/premium terms.
- **Not affected:** cart, checkout, pricing, orders.
