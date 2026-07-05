## 1. Database Layer

- [ ] 1.1 Create `app/db/sqlite.py` — SQLite connection management with WAL mode, foreign keys enabled, and schema initialization
- [ ] 1.2 Define the `products` table schema with CREATE TABLE IF NOT EXISTS (id TEXT PK, name, description, price, category, image_url, is_active, is_featured, created_at, updated_at)
- [ ] 1.3 Add indexes on `category` and `is_active` columns
- [ ] 1.4 Wire `init_schema()` call into FastAPI lifespan (app startup)

## 2. Configuration

- [ ] 2.1 Add `ATELIER_ADMIN_API_KEY` to pydantic-settings config class (required field, no default)
- [ ] 2.2 Add `SQLITE_DB_PATH` setting with default `app/data/atelier.db`
- [ ] 2.3 Ensure app refuses to start if `ATELIER_ADMIN_API_KEY` is not set

## 3. Pydantic Models

- [ ] 3.1 Create `app/models/products.py` — define `ProductCreate` schema (id, name, price required; description, category, image_url, is_active, is_featured optional)
- [ ] 3.2 Define `ProductUpdate` schema (all fields optional for partial update)
- [ ] 3.3 Define `Product` response schema (all fields including timestamps)
- [ ] 3.4 Define `ProductList` response schema with pagination metadata (items, total, page, per_page)
- [ ] 3.5 Define `ImportResult` response schema (imported, updated, errors)

## 4. Authentication Dependency

- [ ] 4.1 Create `app/dependencies/auth.py` — implement `verify_admin_key()` FastAPI dependency
- [ ] 4.2 Extract bearer token from Authorization header, compare against config
- [ ] 4.3 Return 401 for missing, malformed, or invalid keys

## 5. Admin CRUD Endpoints

- [ ] 5.1 Create `app/api/v1/admin/__init__.py` and `app/api/v1/admin/products.py` router
- [ ] 5.2 Implement POST `/v1/admin/products` — create product, return 201 or 409 on duplicate
- [ ] 5.3 Implement GET `/v1/admin/products` — list all products with pagination and filters (category, is_active, is_featured)
- [ ] 5.4 Implement GET `/v1/admin/products/{id}` — get any product by ID, 404 if not found
- [ ] 5.5 Implement PUT `/v1/admin/products/{id}` — partial update, refresh updated_at, 404 if not found
- [ ] 5.6 Implement DELETE `/v1/admin/products/{id}` — set is_active=FALSE, 404 if not found
- [ ] 5.7 Apply `verify_admin_key` dependency to all admin routes

## 6. CSV Bulk Import

- [ ] 6.1 Implement POST `/v1/admin/products/import` — accept file upload (multipart/form-data)
- [ ] 6.2 Validate CSV headers (require id, name, price; optional description, category, image_url)
- [ ] 6.3 Stream-parse CSV rows, validate each row, collect errors with row numbers
- [ ] 6.4 Batch upsert valid rows (INSERT OR REPLACE) in groups of 500 within a transaction
- [ ] 6.5 Preserve is_active and is_featured flags on upsert (do not override existing values)
- [ ] 6.6 Return ImportResult with counts and error details

## 7. Public Read Endpoints

- [ ] 7.1 Create `app/api/v1/products.py` router (no auth dependency)
- [ ] 7.2 Implement GET `/v1/products` — list active-only products with pagination and category filter
- [ ] 7.3 Implement GET `/v1/products/{id}` — get product only if is_active=TRUE, else 404

## 8. App Wiring

- [ ] 8.1 Register admin products router on the FastAPI app with prefix `/v1/admin/products`
- [ ] 8.2 Register public products router on the FastAPI app with prefix `/v1/products`
- [ ] 8.3 Ensure `app/data/` directory is created at startup if it doesn't exist

## 9. Testing

- [ ] 9.1 Unit tests for Pydantic models (validation, optional fields, defaults)
- [ ] 9.2 Unit tests for auth dependency (valid key, invalid key, missing header, wrong scheme)
- [ ] 9.3 Integration tests for admin CRUD (create, list, get, update, soft-delete, 409, 404)
- [ ] 9.4 Integration tests for public read API (active-only filtering, 404 on inactive)
- [ ] 9.5 Integration tests for CSV import (new, upsert, invalid rows, large file, missing columns)
- [ ] 9.6 Test that CSV import preserves is_active/is_featured flags
