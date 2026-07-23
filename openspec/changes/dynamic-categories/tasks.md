## 1. Database schema & migration (`app/database.py`)

- [ ] 1.1 Create `categories` table (slug PK, name_en NOT NULL, name_bg, sort_order, is_active, created_at, updated_at)
- [ ] 1.2 Add a `slugify()` helper (lowercase, hyphenate, strip non-alphanumerics)
- [ ] 1.3 Idempotent migration: seed from `DISTINCT products.category`, ensure 6 default families, suffix slug collisions
- [ ] 1.4 Backfill `UPDATE products SET category = slugify(category)` so products reference slugs
- [ ] 1.5 Guard the migration so it runs once; verify re-run is a no-op

## 2. Models (`app/models/categories.py`)

- [ ] 2.1 `CategoryResponse` (slug, name, sort_order) for public; `CategoryAdminResponse` (adds name_en, name_bg, is_active, product_count, timestamps)
- [ ] 2.2 `CreateCategoryRequest` (name_en required, name_bg, sort_order) — slug derived server-side
- [ ] 2.3 `UpdateCategoryRequest` (name_en?, name_bg?, sort_order?, is_active?)

## 3. Category service (`app/services/category_service.py`)

- [ ] 3.1 `list_categories(active_only, locale)` with locale name resolution + fallback
- [ ] 3.2 `create_category` (derive unique slug), `update_category`, `get_category`
- [ ] 3.3 `delete_category` — 409 if referenced by any product; else delete
- [ ] 3.4 `slug_is_valid_active(slug)` used by product validation
- [ ] 3.5 Product count per category for admin list

## 4. Routes

- [ ] 4.1 `app/routes/categories.py`: `GET /v1/categories` (public, localized)
- [ ] 4.2 Admin category endpoints: `GET/POST /v1/admin/categories`, `PATCH/DELETE /v1/admin/categories/{slug}` (require_admin)
- [ ] 4.3 Register routers in `app/main.py`

## 5. Product validation (`app/services/product_service.py` / models)

- [ ] 5.1 Validate `category` on create/update is an existing active slug → 422 otherwise; allow NULL

## 6. Frontend — admin

- [ ] 6.1 Categories management page (`/admin/categories`): list, create, rename, reorder, activate/deactivate, delete (with in-use 409 handling)
- [ ] 6.2 Add "Categories" entry to `AdminSidebar`
- [ ] 6.3 `ProductForm.tsx`: fetch categories from API, drop the hardcoded `CATEGORIES` const, submit slug
- [ ] 6.4 API client + mock-api handlers for category endpoints; `lib/types.ts` category types

## 7. Frontend — storefront

- [ ] 7.1 `ProductListingClient`/`CategoryFilter`: resolve slug → localized name for pill labels (still filter by slug)
- [ ] 7.2 Product detail badge: show localized category name
- [ ] 7.3 i18n strings for the categories admin page + validation messages (`en.json`, `bg.json`)

## 8. Tests

- [ ] 8.1 Migration: distinct values seeded, defaults ensured, products backfilled to slugs, idempotent re-run, collision suffixing
- [ ] 8.2 Public `GET /v1/categories`: active-only, ordering, locale fallback
- [ ] 8.3 Admin CRUD: create/rename/reorder/deactivate; auth required
- [ ] 8.4 Delete: 409 when in use, success when unused; deactivate hides but keeps products
- [ ] 8.5 Product create/update rejects unknown/inactive category slug; allows NULL
- [ ] 8.6 Frontend: form dropdown from API; pills/badge show localized names

## 9. Verify

- [ ] 9.1 `make test-backend`, `make test-frontend`, `make lint`
- [ ] 9.2 Manual smoke: add a category in admin → appears in product form → assign to product → shows localized on storefront → deactivate → gone from pickers, product still displays it
