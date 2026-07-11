## 1. Database Schema Updates

- [x] 1.1 Add `CHECK (stock >= 0)` constraint to the products table in `app/database.py`
- [x] 1.2 Add `materials TEXT` and `days_to_craft INTEGER` columns to products table schema
- [x] 1.3 Create FTS5 virtual table `products_fts` (id, name, description) in schema SQL
- [x] 1.4 Create triggers to sync `products_fts` on INSERT, UPDATE, DELETE of products table
- [x] 1.5 Add indexes on `category` and `is_active` columns

## 2. Model Alignment

- [x] 2.1 Rename `price` → `price_cents` in `ProductResponse`, `CreateProductRequest`, and `UpdateProductRequest` in `app/models/products.py`
- [x] 2.2 Rename `price` → `price_cents` in `OrderItemResponse` in `app/models/orders.py`
- [x] 2.3 Rename `total` → `total_cents` in `CartResponse` in `app/models/cart.py`
- [x] 2.4 Rename `total` → `total_cents` in `OrderResponse` in `app/models/orders.py`
- [x] 2.5 Add `id: str` field to `CreateProductRequest` (slug/SKU provided by admin, not auto-generated)
- [x] 2.6 Add `CSVImportResponse` model with fields `created: int`, `updated: int`, `errors: list[dict]`
- [x] 2.7 Update `frontend/lib/types.ts` — rename `price` → `price_cents`, `total` → `total_cents` in all interfaces
- [x] 2.8 Update `frontend/lib/mock-api.ts` — rename fields to match updated types

## 3. Product Service

- [x] 3.1 Create `app/services/__init__.py`
- [x] 3.2 Create `app/services/product_service.py` with custom exceptions (`NotFoundError`, `DuplicateError`)
- [x] 3.3 Implement `list_products(category, sort, in_stock, page, limit)` — active-only, paginated, filterable
- [x] 3.4 Implement `get_product(product_id)` — returns active product or raises NotFoundError
- [x] 3.5 Implement `create_product(data)` — inserts product, raises DuplicateError on conflict
- [x] 3.6 Implement `upsert_product(id, data)` — INSERT ... ON CONFLICT(id) DO UPDATE SET (only provided fields), used by CSV import and seed script
- [x] 3.7 Implement `update_product(product_id, data)` — partial update, refreshes updated_at
- [x] 3.7 Implement `deactivate_product(product_id)` — sets is_active=0, idempotent
- [x] 3.8 Implement `search_products(query, limit)` — FTS5 search on name+description, active-only
- [x] 3.9 Implement `get_product_admin(product_id)` — returns any product (active or inactive) for admin use
- [x] 3.10 Implement `list_products_admin(page, limit)` — all products including inactive

## 4. Admin Auth Dependency

- [x] 4.1 Create `app/dependencies/__init__.py` and `app/dependencies/auth.py`
- [x] 4.2 Implement `require_admin` dependency — checks Bearer API key against config (JWT path deferred to Day 5)
- [x] 4.3 Return 401 for missing/invalid credentials; reject if `admin_api_key` is empty (never match empty string)

## 5. Public Product Routes

- [x] 5.1 Replace stub in `app/routes/products.py` with real `GET /v1/products` endpoint (query params: category, q, sort, in_stock, page, limit)
- [x] 5.2 Implement `GET /v1/products/{product_id}` — returns ProductResponse or 404
- [x] 5.3 Cap `limit` parameter at 100; default to 20

## 6. Admin Product Routes

- [x] 6.1 Replace stub in `app/routes/admin.py` with real admin router protected by `require_admin`
- [x] 6.2 Implement `POST /v1/admin/products` — create product, return 201 or 409
- [x] 6.3 Implement `GET /v1/admin/products` — list all products (active + inactive) with pagination
- [x] 6.4 Implement `GET /v1/admin/products/{product_id}` — get any product (active or inactive), return 200 or 404
- [x] 6.5 Implement `PUT /v1/admin/products/{product_id}` — partial update, return 200 or 404
- [x] 6.5 Implement `DELETE /v1/admin/products/{product_id}` — soft delete, return 200 or 404
- [x] 6.6 Implement `POST /v1/admin/products/import` — CSV multipart upload with streaming parse and upsert

## 7. CSV Import Implementation

- [x] 7.1 Accept multipart/form-data file upload in the import endpoint
- [x] 7.2 Validate CSV headers (require: id, name, price_cents; optional: description, category, stock, image_url)
- [x] 7.3 Stream-parse rows with `csv.DictReader`, validate each row
- [x] 7.4 Upsert valid rows using `INSERT ... ON CONFLICT(id) DO UPDATE SET` (only CSV-provided columns), track created vs updated counts
- [x] 7.5 Collect per-row errors with row number and message, skip invalid rows
- [x] 7.6 Return `CSVImportResponse` with created/updated counts and errors array

## 8. Seed Script

- [x] 8.1 Create `scripts/seed_products.py` with ~10 sample luxury candle products
- [x] 8.2 Cover multiple categories: dessert, luxury-jar, gift-set, seasonal
- [x] 8.3 Use `upsert_product` for idempotency (safe to run multiple times)
- [x] 8.4 Use the product service layer (not raw SQL) to validate data

## 9. Tests

- [x] 9.1 Create `tests/test_product_service.py` — unit tests for list, get, create, update, deactivate, search
- [x] 9.2 Test duplicate product creation raises DuplicateError
- [x] 9.3 Test get/deactivate non-existent product raises NotFoundError
- [x] 9.4 Test stock CHECK constraint (negative stock rejected at DB level)
- [x] 9.5 Test FTS5 search finds by name and description, excludes inactive
- [x] 9.6 Test pagination (correct slice, total count, empty page)
- [x] 9.7 Create `tests/test_product_routes.py` — integration tests for public endpoints (GET list, GET detail, 404)
- [x] 9.8 Create `tests/test_admin_routes.py` — integration tests for admin endpoints (CRUD, CSV import, auth required)
- [x] 9.9 Test CSV import: new products, upsert, validation errors, missing columns, empty CSV
