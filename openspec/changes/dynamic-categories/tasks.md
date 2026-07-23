## 1. Database schema & migration (`app/database.py`)

- [ ] 1.1 Create `categories` table (slug PK, name_en NOT NULL, name_bg, sort_order, is_active, created_at, updated_at)
- [ ] 1.1a Create migration support tables/markers (`schema_migrations`, `category_slug_migrations`) for `dynamic_categories_v1`
- [ ] 1.2 Add a `slugify()` helper (lowercase, hyphenate, strip non-alphanumerics)
- [ ] 1.3 Idempotent migration: read distinct original `products.category` values, assign deterministic unique slugs, persist exact original-value-to-slug mappings, ensure 6 default families
- [ ] 1.4 Backfill products from the persisted mapping (`WHERE category = original_value`), not by recomputing slugify in one global update
- [ ] 1.5 Guard the migration with a marker so it runs once; verify re-run is a no-op even when default categories already exist

## 2. Models (`app/models/categories.py`)

- [ ] 2.1 `CategoryResponse` (slug, name, sort_order) for public; `CategoryAdminResponse` (adds name_en, name_bg, is_active, product_count, timestamps)
- [ ] 2.2 `CreateCategoryRequest` (name_en required, name_bg, sort_order) — slug derived server-side
- [ ] 2.3 `UpdateCategoryRequest` (name_en?, name_bg?, sort_order?, is_active?)
- [ ] 2.4 Add nullable `category_name` to public `ProductResponse` / frontend `ProductResponse`; keep `category` as the slug

## 3. Category service (`app/services/category_service.py`)

- [ ] 3.1 `list_categories(active_only, locale)` with locale name resolution + fallback
- [ ] 3.2 `create_category` (derive unique slug), `update_category`, `get_category`
- [ ] 3.3 `delete_category` — 409 if referenced by any product; else delete
- [ ] 3.4 `slug_is_valid_active(slug)` plus validation helper for product updates that allows preserving the product's current inactive slug but rejects assigning inactive slugs
- [ ] 3.5 Product count per category for admin list
- [ ] 3.6 Batched category display-name resolver for product list/search/detail (includes inactive categories; locale fallback)

## 4. Routes

- [ ] 4.1 `app/routes/categories.py`: `GET /v1/categories` (public, localized)
- [ ] 4.2 Admin category endpoints: `GET/POST /v1/admin/categories`, `PATCH/DELETE /v1/admin/categories/{slug}` (require_admin)
- [ ] 4.3 Register routers in `app/main.py`

## 5. Product validation (`app/services/product_service.py` / models)

- [ ] 5.1 Validate `category` on create is an existing active slug → 422 otherwise; allow NULL
- [ ] 5.2 Validate update reassignment to active slugs while allowing omitted category and preserving the product's current inactive slug
- [ ] 5.3 Validate CSV import category values as active slugs with row-level errors; do not auto-create categories
- [ ] 5.4 Resolve `category_name` on public list/search/detail responses without N+1 category queries

## 6. Frontend — admin

- [ ] 6.1 Categories management page (`/admin/categories`): list, create, rename, reorder, activate/deactivate, delete (with in-use 409 handling)
- [ ] 6.2 Add "Categories" entry to `AdminSidebar`
- [ ] 6.3 `ProductForm.tsx`: fetch managed categories from API, drop the hardcoded `CATEGORIES` const, submit slug
- [ ] 6.3a In edit mode, show and preserve the current inactive category as retired; do not allow assigning inactive categories to other products
- [ ] 6.4 API client + mock-api handlers for category endpoints; `lib/types.ts` category types

## 7. Frontend — storefront

- [ ] 7.1 `ProductListingClient`/`CategoryFilter`: derive slug → localized label from product `category_name` metadata (still filter by slug)
- [ ] 7.2 Product detail badge: show product `category_name`
- [ ] 7.3 i18n strings for the categories admin page + validation messages (`en.json`, `bg.json`)

## 8. Tests

- [ ] 8.1 Migration: distinct values seeded, defaults ensured, exact mapping persisted, products backfilled to mapped slugs, idempotent re-run, pre-existing defaults do not skip backfill, collision suffixing
- [ ] 8.2 Public `GET /v1/categories`: active-only, ordering, locale fallback
- [ ] 8.3 Admin CRUD: create/rename/reorder/deactivate; auth required
- [ ] 8.4 Delete: 409 when in use, success when unused; deactivate hides but keeps products
- [ ] 8.5 Product create rejects unknown/inactive category slug; update rejects reassignment to unknown/inactive but preserves current inactive; allows NULL
- [ ] 8.6 Public product API: list/search/detail include `category_name`, including inactive referenced categories
- [ ] 8.7 CSV import rejects unknown/inactive category slugs with row-level errors
- [ ] 8.8 Frontend: form dropdown from API; current inactive category preserved on edit; pills/badge show localized names from `category_name`

## 9. Verify

- [ ] 9.1 `make test-backend`, `make test-frontend`, `make lint`
- [ ] 9.2 Manual smoke: add a category in admin → appears in product form → assign to product → shows localized on storefront → deactivate → gone from pickers, product still displays it
