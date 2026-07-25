## 1. Database schema & migration (`app/database.py`)

- [x] 1.1 Create `product_types`, `product_categories`, `product_labels`, and `product_label_assignments` tables
- [x] 1.2 Add `product_type_slug` and `category_slug` columns to `products`; keep legacy `products.category` available during migration compatibility
- [x] 1.3 Create migration support tables/markers (`schema_migrations`, taxonomy mapping table) for `product_taxonomy_v1`
- [x] 1.4 Add a shared `slugify()` helper (lowercase, hyphenate, strip non-alphanumerics, deterministic suffixes on collision)
- [x] 1.5 Seed starter taxonomy values: product types (`candles`, `boxes`), categories (`small`, `medium`, `premium`), labels (`floral`, `woody`, `fresh`, `gourmand`, `spicy`, `citrus`, `winter`, `gift`, `christmas`)
- [x] 1.6 Idempotent migration: read distinct legacy `products.category` values, create/reuse labels, persist exact original-value-to-label mappings, assign labels to matching products
- [x] 1.7 Default existing products to `product_type_slug = 'candles'`; leave `category_slug` NULL
- [x] 1.8 Guard migration with marker so re-run is a no-op even when seed taxonomy already exists

## 2. Models (`app/models/taxonomy.py`, `app/models/products.py`)

- [x] 2.1 Public taxonomy response models for product types, categories, and labels (`slug`, localized `name`, `sort_order`)
- [x] 2.2 Admin taxonomy response models adding `name_en`, `name_bg`, `is_active`, `product_count`, timestamps
- [x] 2.3 Create/update taxonomy request models; slugs derived server-side and immutable
- [x] 2.4 Add public product taxonomy fields: `product_type`, `product_type_name`, nullable `category`, nullable `category_name`, `labels: [{slug, name}]`
- [x] 2.5 Add admin product taxonomy fields: `product_type`, nullable `category`, `labels: string[]`
- [x] 2.6 Add frontend TypeScript types for taxonomy terms and product taxonomy fields

## 3. Taxonomy service (`app/services/taxonomy_service.py`)

- [x] 3.1 `list_taxonomy(locale)` for public active terms with locale fallback
- [x] 3.2 Admin list/create/update/get/delete helpers for product types, categories, and labels
- [x] 3.3 Delete guards returning 409 when a product references the term
- [x] 3.4 Validation helpers for active assignment and preserve-current inactive assignment
- [x] 3.5 Product count per taxonomy term for admin lists
- [x] 3.6 Batched taxonomy display-name resolver for product list/search/detail including inactive referenced terms
- [x] 3.7 Label assignment helpers for replacing a product's label set transactionally

## 4. Routes

- [x] 4.1 `app/routes/taxonomy.py`: `GET /v1/taxonomy` public endpoint
- [x] 4.2 Admin product type endpoints under `/v1/admin/taxonomy/product-types`
- [x] 4.3 Admin category/tier endpoints under `/v1/admin/taxonomy/categories`
- [x] 4.4 Admin label endpoints under `/v1/admin/taxonomy/labels`
- [x] 4.5 Register taxonomy router(s) in `app/main.py`

## 5. Product service/API validation

- [x] 5.1 Validate `product_type` on create is an existing active product type
- [x] 5.2 Validate `category` on create is NULL or an existing active category/tier
- [x] 5.3 Validate `labels` on create are existing active labels
- [x] 5.4 Validate update reassignment while allowing omitted taxonomy fields and preserving current inactive terms
- [x] 5.5 Validate CSV import taxonomy values as active slugs with row-level errors; do not auto-create taxonomy
- [x] 5.6 Support public filters: `product_type`, `category`, `labels` plus existing search/sort/stock/pagination/locale
- [x] 5.7 Resolve taxonomy display metadata on public list/search/detail without N+1 queries

## 6. Frontend - admin taxonomy

- [x] 6.1 Dedicated taxonomy management UI reachable from `AdminSidebar`
- [x] 6.2 Product types view: list/create/rename/reorder/activate/deactivate/delete with in-use 409 handling
- [x] 6.3 Categories/tiers view: list/create/rename/reorder/activate/deactivate/delete with in-use 409 handling
- [x] 6.4 Labels view: list/create/rename/reorder/activate/deactivate/delete with in-use 409 handling
- [x] 6.5 API client + mock-api handlers for all taxonomy endpoints
- [x] 6.6 i18n strings for taxonomy admin pages and validation messages (`en.json`, `bg.json`)

## 7. Frontend - admin product form

- [x] 7.1 Remove hardcoded `CATEGORIES` and any hardcoded product type/category/label lists from production form behavior
- [x] 7.2 Fetch admin taxonomy data for product type dropdown, category/tier dropdown, and label multi-select
- [x] 7.3 Create mode shows active terms as assignable options
- [x] 7.4 Edit mode shows current inactive terms marked as retired and preserves them on unrelated edits
- [x] 7.5 Submit product type/category/label slugs to product APIs

## 8. Frontend - storefront

- [x] 8.1 Product listing fetches public taxonomy and products with locale
- [x] 8.2 Replace category pills with desktop left sidebar filters and mobile collapsible filter panel
- [x] 8.3 Filter groups: Product Type, Category, Labels, plus existing stock/sort/search where applicable
- [x] 8.4 Combine selected filters by slug and show selected filters as removable chips
- [x] 8.5 Product detail displays localized product type/category badges and label tags from product response metadata
- [x] 8.6 Ensure no hardcoded taxonomy lists remain in storefront filtering

## 9. Tests

- [x] 9.1 Migration: seed values ensured, legacy categories converted to labels, exact mapping persisted, products assigned labels, default product type set to candles, category remains NULL, idempotent re-run, collision suffixing
- [x] 9.2 Public `GET /v1/taxonomy`: active-only, ordering, locale fallback
- [x] 9.3 Admin taxonomy CRUD: create/rename/reorder/deactivate for product types/categories/labels; auth required
- [x] 9.4 Delete guards: 409 when in use, success when unused; deactivate hides but keeps product display
- [x] 9.5 Product create/update rejects unknown/inactive taxonomy assignment but preserves current inactive assignments; category may be NULL
- [x] 9.6 Public product API: list/search/detail include taxonomy metadata, including inactive referenced terms
- [x] 9.7 Public product API: filters by product type, category, labels, and combinations
- [x] 9.8 CSV import rejects unknown/inactive taxonomy slugs with row-level errors
- [ ] 9.9 Frontend: taxonomy admin views, form controls from API, current inactive taxonomy preserved on edit, sidebar filters and detail badges show localized names

## 10. Verify

- [ ] 10.1 `make test-backend`, `make test-frontend`, `make lint`
- [ ] 10.2 Manual smoke: see `test-plans/dynamic-categories.md` (create product type "Boxes" → product form → assign → storefront sidebar → create label "Winter" → assign → filter → deactivate → hidden from filters but product still displays it)
